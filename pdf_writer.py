"""STEPS 2 AND 3: ADD THE SCRIPTS AND BUTTONS, WRITE THE PDF, THEN CHECK IT.

You don't need to open this file to change or make a form.

CONTENTS
    1. Step 2: the rules table, scripts, buttons and QR code rows   (add_scripts)
    2. Step 3: write the PDF with pikepdf                            (class Writer)
    3. Build: run the three steps                                    (build)
    4. Self-check: open the built PDF and check it                   (self_check)
"""
import io
import json
import re
import zlib

import pikepdf
from pikepdf import Array, Dictionary, Name, String

from acrobat_js import BUTTON_JS, DOCUMENT_JS, PIPE_JS
from layout import (ACCENT, FORMATS, INK, MARGIN, PAGE_HEIGHT, PAGE_WIDTH, RULE, TEXT, WHITE, Layout, active_rules,
                    fmt, js_json, num, pdf_string, rgb, safe, width, wrap)


# ====================================================================================================================
# 1. STEP 2: ADD THE SCRIPTS, BUTTONS AND QR CODE ROWS
# ====================================================================================================================
# The scripts themselves are in acrobat_js.py (DOCUMENT_JS and BUTTON_JS).

# Everything interactive in the PDF is Acrobat JavaScript, kept as text in acrobat_js.py. This step:
#   1. builds the "rules table" (which questions are mandatory, when, and their formats) from the form, and fills it
#      into DOCUMENT_JS (the rules engine, the QR code's text and the QR encoder): the one document-level
#      script stored in the PDF, named "lcRules".
#   2. says when the rules run: when a tick box or option is clicked, and when the person leaves a box
#   3. adds the hidden helper fields, the rows of the QR codes, and the buttons (Check form, Reset form on every page;
#      Generate QR Code and Print Form on the QR page)
# It only adds field descriptions to the layout; step 3 makes the PDF objects.

# The calls the events use. Both pass the name of the box that changed, so lcRules re-checks only the questions that read it.
# "/*calc*/" is a marker: build_all.py turns it into "only while this form is the open one" (the joined PDF has 13 of these).
RULES_ON_EVENT = "lcRules(this, event.target.name);"                                    # a click or a blur
RULES_ON_CALC = "/*calc*/lcRules(this, event.source ? event.source.name : null);"       # any value changed (no source = check all)

# Acrobat stops reading the whole form script at the first character it doesn't expect. Copying files between
# machines sometimes adds one you can't see (a "byte order mark") or turns ' and " into curly quotes, and then the
# red boxes, calendars and Check form all stop working in Acrobat. So the build refuses scripts that aren't plain ASCII.
for _name, _text in [("DOCUMENT_JS", DOCUMENT_JS), ("PIPE_JS", PIPE_JS)] + [("BUTTON_JS " + k, v) for k, v in BUTTON_JS.items()]:
    _bad = sorted({c for c in _text if ord(c) > 126 or (ord(c) < 32 and c not in "\n\t")})
    if _bad:
        raise SystemExit(f"PROBLEM IN acrobat_js.py ({_name}): it contains characters that break Acrobat: {_bad!r}. "
                         "The file was probably changed while being copied. Copy acrobat_js.py again, exactly as it is "
                         "on GitHub (use the 'Download raw file' button), and build again.")


def script(name, **values):
    """A script ("document", or a button's name such as "check-form"), with its __PLACEHOLDERS__ filled in."""
    text = DOCUMENT_JS if name == "document" else BUTTON_JS[name]
    for key, value in values.items():
        text = text.replace(f"__{key}__", value)
    return text


def rules_table(layout):
    """What the rules engine (DOCUMENT_JS) needs to know about each question, in form order (so Check form lists problems top to
    bottom). Short keys keep the script small:
      kind, label; hasRule (has a mandatory rule); always (always mandatory); requiredIf / activeIf as
      [field, values, not]; check: [pattern, message] for a format, or 1 for "allowed characters only";
      options for "tick any" questions."""
    layout_questions, by_id = layout.questions, layout.by_id

    def as_list(rules):
        return [[r["field"], [safe(v) for v in r["values"]], 1 if r.get("not") else 0] for r in rules]

    table = {}

    def entry(q):
        if q["id"] not in table:
            item = {"kind": q["kind"], "label": safe(q["label"])}
            if q["kind"] == "checks":
                item["options"] = [safe(o) for o in q.get("options") or []]
            table[q["id"]] = item
        return table[q["id"]]

    for q in [q for q in layout_questions if q.get("required") or q.get("requiredIf")]:   # mandatory questions
        item = entry(q)
        item["hasRule"] = 1
        if q.get("required"):
            item["always"] = 1
        if q.get("requiredIf"):
            item["requiredIf"] = as_list(q["requiredIf"])
        for r in q.get("requiredIf") or []:   # ... and the questions their rules look at
            if r["field"] in by_id:
                entry(by_id[r["field"]])
    for q in [q for q in layout_questions if active_rules(q)]:   # questions that are locked until switched on
        entry(q)["activeIf"] = as_list(active_rules(q))
        for r in active_rules(q):
            if r["field"] in by_id:
                entry(by_id[r["field"]])
    for q in [q for q in layout_questions if q.get("words")]:   # amounts in words, and the answers they are made from
        entry(q)["words"] = q["words"]
        for other in q["words"]:
            if other in by_id:
                entry(by_id[other])
    for c in layout.form.get("checks") or []:   # questions the checks across answers read
        for key in ("a", "b"):
            if c.get(key) in by_id:
                entry(by_id[c[key]])
    for q in [q for q in layout_questions if q["kind"] in ("text", "long", "date")]:   # typed answers are checked
        entry(q)["check"] = [FORMATS[q["format"]][1], FORMATS[q["format"]][2]] if q.get("format") else 1
    return {q["id"]: table[q["id"]] for q in layout_questions if q["id"] in table}


# What the checks across answers (rules 1-9 in DOCUMENT_JS, function across) read: question -> the questions it reads.
# Keep in step with across(): rules 1-6 are the LC's own, rules 7-9 come from FORM["checks"] (handled in dependency_index).
ACROSS_READS = {"expiry_date": ["latest_shipment_date", "application_date"], "latest_shipment_date": ["application_date"],
                "insurance_arrangement": ["price_basis"]}


def dependency_index(table, checks):
    """For each box: the questions to re-check when it changes (itself, everything that reads it, and everything that
    reads those: a question that stops applying clears its box, which others may read). None when a check kind of the form
    file is unknown to this index (then the rules engine checks everything every time)."""
    reads = {q: {q} for q in table}
    for q, item in table.items():
        for rule in (item.get("requiredIf") or []) + (item.get("activeIf") or []):
            reads[q].add(rule[0])
        reads[q].update(item.get("words") or [])
        reads[q].update(ACROSS_READS.get(q, []))
    for c in checks:
        if c["t"] not in ("order", "range", "lengths"):
            return None
        if c["a"] in reads:
            reads[c["a"]].update([c["a"], c.get("b", c["a"])] if c["t"] != "range" else [c["a"]])
    affects = {}
    for q, sources in reads.items():
        for x in sources:
            affects.setdefault(x, set()).add(q)
    index = {}
    for x in affects:
        todo, seen = [x], set()
        while todo:
            for q in affects.get(todo.pop(), ()):
                if q not in seen:
                    seen.add(q)
                    todo.append(q)
        index[x] = [q for q in table if q in seen]
    return index


def document_script(layout, table):
    """The one document-level script (DOCUMENT_JS), filled in for this form."""
    form, questions = layout.form, layout.questions
    tick_any = ", ".join(f"{json.dumps(q['id'])}: {js_json(q.get('options') or [])}" for q in questions if q["kind"] == "checks")
    code = re.search(r"[A-Z]+-\d+", form.get("formCode") or "")     # "LC-01"
    version = re.search(r"v([\d.]+)", form.get("formCode") or "")   # "1.0"
    pipe = form.get("qrFormat") == "pipe"   # the 4 pipe-delimited records of the old smart form instead of the JSON (acrobat_js.py, PIPE_JS)
    text = script("document", MODEL=js_json(table), DEPS=js_json(dependency_index(table, form.get("checks") or [])), DATES=js_json([q["id"] for q in questions if q["kind"] == "date"]),
                  GROUPS=tick_any, LONG=js_json([q["id"] for q in questions if q["kind"] == "long"]),
                  FORM=json.dumps(code.group(0) if code else safe(form["title"]), ensure_ascii=False),
                  VERSION=json.dumps(version.group(1) if version else "1"),
                  CHECKS=js_json([{k: (safe(v) if k == "m" else v) for k, v in c.items()} for c in form.get("checks") or []]))
    if pipe:
        text += "\n" + PIPE_JS.replace("__PIPE__", js_json(form["pipe"])).replace("__GROUPS__", tick_any)
    return text


def add_scripts(layout):
    """Adds the events, helper fields, QR rows and buttons to the layout. Returns the document script."""
    table = rules_table(layout)
    doc_script = document_script(layout, table)

    # When the rules run: when a tick box, option or date list is clicked (U = mouse up), and when the person
    # leaves any other box (Bl = blur).
    for qid, item in table.items():
        if item["kind"] == "checks":
            names = [f"{qid}__{i}" for i in range(len(item.get("options") or []))]
        elif item["kind"] == "date" and f"{qid}__list" in layout.by_name:
            names = [f"{qid}__list", qid]
        else:
            names = [qid]
        for name in names:
            for widget in layout.by_name.get(name, {"widgets": []})["widgets"]:
                clicked = item["kind"] in ("check", "checks", "radio") or (item["kind"] == "date" and name != qid)
                widget.setdefault("events", {})["U" if clicked else "Bl"] = RULES_ON_EVENT

    # ... and after any value changes (Acrobat's "calculate" event), as a safety net: a hidden field off the page.
    layout.page = layout.pages[0]
    recalc = layout.add_field("__checks", "text", size=3, events={"C": RULES_ON_CALC})
    layout.add_widget(recalc, -20, -20, 1, 1, hidden=True, border=INK, bg=WHITE)

    # The QR codes: a hidden field "__qr" holds the answers as JSON; DOCUMENT_JS draws each code into 177 read-only
    # "comb" text boxes, one per row of the code (a comb box spaces its characters evenly). Each dark square is
    # the letter "n" in the ZapfDingbats font, which prints as a solid black square. This avoids Acrobat's own
    # barcode feature, which some installations don't have.
    # Codes 1 and 2 sit on the QR code page: rows "__qr1_0" ... "__qr1_176" and "__qr2_0" ... "__qr2_176". The second
    # code, its frame ("__qr2_frame") and the labels ("__qr1_label", "__qr2_label") stay empty / hidden unless the answers are
    # too long for one code. Codes 3 to 16 go on the hidden page template "qrx" (two codes: "__qrx_1_..." and "__qrx_2_...",
    # each with a label and a frame), which Generate QR Code copies after the QR code page, once per two codes needed.
    qr = layout.qr
    layout.page = layout.pages[qr["page"]]
    holder = layout.add_field("__qr", "text", size=3)
    layout.add_widget(holder, -20, -20, 1, 1, hidden=True, border=INK, bg=WHITE)

    def qr_slot(tag, x, y0, size, frame):
        label = layout.add_field(f"__{tag}_label", "text", read_only=True, size=8)
        layout.add_widget(label, x, y0 + size + 1, size, 10)
        if frame:
            box = layout.add_field(f"__{tag}_frame", "text", read_only=True)
            layout.add_widget(box, x, y0, size, size, hidden=True, border=RULE, border_width=0.5)
        module = size / 185   # 177 squares + 4 squares of white margin on each side
        font_size = "/ZaDb %s Tf 0 g" % fmt(round(module / 0.692 * 1000) / 1000)   # the square is 0.692 of the font size
        for y in range(177):
            row = layout.add_field(f"__{tag}_{y}", "text", max=177, comb=True, appearance=font_size)
            layout.add_widget(row, x + 4 * module, y0 + size - (5 + y) * module, 177 * module, module)

    for k, (x, y0, size) in enumerate(qr["slots"], 1):
        qr_slot(f"qr{k}", x, y0, size, k > 1)
    layout.page = layout.qr_extra
    for k, (x, y0, size) in enumerate(qr["slots"], 1):
        qr_slot(f"qrx_{k}", x, y0, size, True)

    # Buttons a section adds (buttons=[...] in the form file): what each does.
    for field in layout.fields:
        if field.get("script"):
            for widget in field["widgets"]:
                widget["action"] = script(field["script"])

    # "Check form" and "Reset form" at the top right of every page (on screen only, never printed).
    buttons = [("__check_form", "Check form", script("check-form"), 64), ("__reset_form", "Reset form", script("reset-form"), 64)]
    for i, (name, caption, code, button_w) in enumerate(buttons):
        x = PAGE_WIDTH - MARGIN - sum(b[3] + 4 for b in buttons[i:]) + 4   # right-aligned, 4 points apart
        button = layout.add_field(name, "button", size=8)
        for page in layout.pages:
            layout.page = page
            layout.add_widget(button, x, PAGE_HEIGHT - 25, button_w, 13, caption=caption, border=ACCENT, bg=ACCENT,
                              border_width=0, action=code, flags=0)

    # "Generate QR Code" and "Print Form", under the QR code.
    layout.page = layout.pages[qr["page"]]
    for i, (name, caption, js_file) in enumerate((("__generate_qr", "Generate QR Code", "generate-qr"),
                                                  ("__print_form", "Print Form", "print-form"))):
        button = layout.add_field(name, "button", size=10)
        bx, by = qr["button"]
        layout.add_widget(button, bx + i * 162, by, 150, 22, caption=caption, border=ACCENT, bg=ACCENT, border_width=0,
                          action=script(js_file + ("-pipe" if layout.form.get("qrFormat") == "pipe" else "")), flags=0)
    return doc_script


# ====================================================================================================================
# 2. STEP 3: WRITE THE PDF
# ====================================================================================================================
# You shouldn't need to change this file.

# Turns the layout (pages, field descriptions, links) and the document script into a PDF:
#   - each page with its drawing (its "content stream") and the fonts it uses
#   - every field, with its settings and an "appearance" (a small drawing of how the box looks, so it shows
#     correctly in any PDF reader before anyone types into it)
#   - the page links, the document script, and the warnings before save / print
#   - a copy of the form's description (JSON of FORM) inside the PDF, for the bank's workbench to read
#
# PDF terms used below:
#   Dictionary   a PDF object with named entries, e.g. {/Type /Page, /MediaBox [...]}
#   widget       the visible box of a field on a page (one field can have several, e.g. one per page)
#   Ff           field flags: required (2), multiline (4096), comb (16777216), read-only (1), drop-down (131072),
#                radio (32768), push button (65536)
#   F            widget flags: 4 = print, 2 = hidden, 0 = on screen only
#   DA           default appearance: font and colour Acrobat uses when it redraws the box
#   MK           the box's border colour (BC), background (BG) and caption (CA)
#   AA / A       actions: JavaScript run on events (AA) or on click (A)

# Field flags (Ff) and their meaning.
REQUIRED, READ_ONLY, MULTILINE, COMB, DROP_DOWN, RADIO, PUSH_BUTTON = 2, 1, 4096, 16777216, 131072, 32768, 65536


class Writer:
    def __init__(self, layout, doc_script):
        self.layout, self.doc_script = layout, doc_script
        self.looks = {}   # drawings already made, by (width, height, drawing): see appearance()

    def write(self):
        """Builds and returns the pikepdf document."""
        layout, form = self.layout, self.layout.form
        pdf = self.pdf = pikepdf.new()

        # 1. The pages, each with its drawing and two fonts (F1 Helvetica, F2 Helvetica-Bold, built into every reader).
        helvetica = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding))
        helvetica_bold = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name("/Helvetica-Bold"), Encoding=Name.WinAnsiEncoding))
        for page in layout.pages:
            drawing = pdf.make_stream(zlib.compress(" ".join(page.ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)
            pdf.pages.append(pikepdf.Page(Dictionary(Type=Name.Page, MediaBox=[0, 0, PAGE_WIDTH, PAGE_HEIGHT],
                                                     Resources=Dictionary(Font=Dictionary(F1=helvetica, F2=helvetica_bold)),
                                                     Contents=drawing)))
        pages = [p.obj for p in pdf.pages]
        # The extra QR code page is a hidden page template, not in the page list: widgets refer to it as the page after the last.
        template = pdf.make_indirect(Dictionary(Type=Name.Template, MediaBox=[0, 0, PAGE_WIDTH, PAGE_HEIGHT],
                                                Resources=Dictionary(Font=Dictionary(F1=helvetica, F2=helvetica_bold)),
                                                Contents=pdf.make_stream(zlib.compress(" ".join(layout.qr_extra.ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)))
        pages.append(template)
        # Fonts the fields use: Helvetica for text, ZapfDingbats for the tick, radio dot and QR squares.
        zapf = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))
        self.fonts = Dictionary(Helvetica=helvetica, Helv=helvetica, ZaDb=zapf)

        # 2. Document information, and the form's description (FORM as JSON) for the workbench.
        pdf.docinfo[Name.Title] = String(safe(form["title"]))
        pdf.docinfo[Name.Creator] = String("PDF Template Studio")
        description = {**form, "uploaded": False}
        pdf.Root[Name.FormTemplate] = pdf.make_stream(zlib.compress(js_json(description).encode("utf-8")), Filter=Name.FlateDecode)

        def annotations(i):
            """The list of clickable things (links, widgets) on page i."""
            if Name.Annots not in pages[i]:
                pages[i][Name.Annots] = Array()
            return pages[i].Annots

        # 3. Page links ("< Previous page" / "Next page >").
        for i, area, target in layout.links:
            annotations(i).append(pdf.make_indirect(Dictionary(
                Type=Name.Annot, Subtype=Name.Link, Rect=area, Border=[0, 0, 0],
                A=Dictionary(S=Name.GoTo, D=[pages[target], Name.XYZ, None, None, None]))))

        # 4. The fields, in the order they were made.
        all_fields = []
        for field in layout.fields:
            all_fields.append(self.make_field(field, pages))
            for widget in field["widgets"]:
                annotations(widget["page"]).append(widget["obj"])
        acro_form = Dictionary(Fields=Array(all_fields), DR=Dictionary(Font=self.fonts), DA=String("/Helv 0 Tf 0 g"))
        acro_form[Name.CO] = Array([layout.by_name["__checks"]["obj"]])   # the hidden field that re-runs the rules
        pdf.Root[Name.AcroForm] = pdf.make_indirect(acro_form)

        # 5. The document script ("lcRules"), and the warning before saving (WS) or printing (WP) an incomplete form.
        stream = pdf.make_stream(zlib.compress(self.doc_script.encode("latin-1", "replace")), Filter=Name.FlateDecode)
        pdf.Root[Name.Names] = Dictionary(JavaScript=Dictionary(Names=[String("lcRules"), Dictionary(S=Name.JavaScript, JS=stream)]),
                                          Templates=Dictionary(Names=[String("qrx"), template]))
        pdf.Root[Name.AA] = Dictionary(WS=self.javascript(script("before-save")), WP=self.javascript(script("before-save")))
        return pdf

    # =========================================================================================== helpers
    def javascript(self, code):
        """A PDF action that runs JavaScript."""
        return Dictionary(S=Name.JavaScript, JS=String(code))

    def appearance(self, w, h, drawing):
        """A small drawing (form XObject) of how a box looks, w x h points. Boxes that look the same (the QR code's thousands
        of rows) share one drawing, which keeps the file small."""
        key = (num(w), num(h), drawing)
        if key not in self.looks:
            self.looks[key] = self.pdf.make_stream(drawing.encode("latin-1", "replace"), Type=Name.XObject, Subtype=Name.Form,
                                                   BBox=[0, 0, num(w), num(h)], Resources=Dictionary(Font=self.fonts))
        return self.looks[key]

    def frame(self, widget, w, h):
        """Drawing commands for a box's background and border."""
        out = ""
        if widget.get("bg"):
            out += "%s rg 0 0 %s %s re f " % (rgb(widget["bg"]), fmt(w), fmt(h))
        if widget.get("border") and widget.get("border_width"):
            b = widget["border_width"]
            out += "%s RG %s w %s %s %s %s re S " % (rgb(widget["border"]), fmt(b), fmt(b / 2), fmt(b / 2), fmt(w - b), fmt(h - b))
        return out

    # =========================================================================================== one field
    def make_field(self, field, pages):
        """The PDF objects for one field and its widgets."""
        pdf, field_type = self.pdf, field["type"]
        d = Dictionary(T=String(field["name"]))   # T = the field's name
        if field.get("tooltip"):
            d[Name.TU] = String(safe(field["tooltip"]))
        flags = REQUIRED if field.get("required") else 0
        size = field.get("size", TEXT)

        if field_type == "text":
            d[Name.FT] = Name.Tx
            if field.get("multiline"):
                flags |= MULTILINE
            if field.get("comb"):
                flags |= COMB | READ_ONLY
            if field.get("read_only"):
                flags |= READ_ONLY
            if field.get("max"):
                d[Name.MaxLen] = field["max"]
            if field.get("value"):
                d[Name.V] = String(field["value"])
            font_size = "0" if field["name"] in self.layout.shrink else fmt(size)   # 0 = shrink to fit
            d[Name.DA] = String(field.get("appearance") or "0 0 0 rg\n/Helvetica %s Tf" % font_size)
        elif field_type == "choice":      # a drop-down list
            d[Name.FT] = Name.Ch
            flags |= DROP_DOWN
            d[Name.Opt] = Array([Array([String(o), String(o)]) for o in field["options"]])
            if field.get("value") is not None:
                d[Name.V] = String(field["value"])
            d[Name.DA] = String("0 0 0 rg\n/Helvetica %s Tf" % fmt(size))
        elif field_type == "check":       # a tick box: on = /Yes, off = /Off
            d[Name.FT] = Name.Btn
            if field.get("value"):
                d[Name.V] = Name.Yes
            d[Name.DA] = String("/ZaDb 0 Tf 0 g")
        elif field_type == "radio":       # pick one: each option's widget has its own "on" name (/0, /1, ...)
            d[Name.FT] = Name.Btn
            flags |= RADIO
            d[Name.Opt] = Array([String(o) for o in field["options"]])   # so the answer reads as the option's wording
            if field.get("value") is not None:
                d[Name.V] = Name("/%d" % field["value"])
            d[Name.DA] = String("/ZaDb 0 Tf 0 g")
        elif field_type == "button":
            d[Name.FT] = Name.Btn
            flags |= PUSH_BUTTON
            d[Name.DA] = String("1 1 1 rg\n/Helvetica %s Tf" % fmt(size))

        if field.get("events"):
            d[Name.AA] = Dictionary({"/" + event: self.javascript(code) for event, code in field["events"].items()})
        if flags:
            d[Name.Ff] = flags
        if Name.V in d:   # DV = default value: "Reset form" goes back to the starting answer (e.g. Full Swift), not blank
            d[Name.DV] = d.V
        d = pdf.make_indirect(d)
        field["obj"] = d

        kids = Array()
        for widget in field["widgets"]:
            x1, y1, x2, y2 = widget["rect"]
            w, h = x2 - x1, y2 - y1
            k = Dictionary(Type=Name.Annot, Subtype=Name.Widget, Rect=[num(v) for v in widget["rect"]], P=pages[widget["page"]],
                           Parent=d, F=widget.get("flags", 2 if widget.get("hidden") else 4))
            look = Dictionary()
            if widget.get("border"):
                look.BC = list(widget["border"])
            if widget.get("bg"):
                look.BG = list(widget["bg"])
            if widget.get("caption"):
                look.CA = String(widget["caption"])
            if len(look):
                k.MK = look
            k.BS = Dictionary(W=num(widget.get("border_width", 0)) if widget.get("border") else 0)   # border width
            k.AP = self.widget_appearance(field, widget, w, h)
            if field_type in ("check", "radio"):   # AS = which appearance shows now (on or Off)
                on = widget.get("state", "Yes")
                lit = (field_type == "check" and field.get("value")) or \
                      (field_type == "radio" and field.get("value") is not None and str(field["value"]) == on)
                k.AS = Name("/" + on) if lit else Name.Off
            if widget.get("action"):
                k.A = self.javascript(widget["action"])
            if widget.get("events"):
                k.AA = Dictionary({"/" + event: self.javascript(code) for event, code in widget["events"].items()})
            widget["obj"] = pdf.make_indirect(k)
            kids.append(widget["obj"])
        d.Kids = kids
        return d

    def widget_appearance(self, field, widget, w, h):
        """How a widget looks: its frame plus, depending on the field, its text, tick, radio dot or caption.
        N = normal look, D = look while pressed. Tick boxes and radios have an "on" and an "Off" look."""
        field_type = field["type"]
        base = self.frame(widget, w, h)

        if field_type in ("text", "choice"):
            value, size, body = field.get("value") or "", field.get("size", TEXT), ""
            if value and not field.get("comb"):
                if field.get("multiline"):
                    text_y = h - 2 - size
                    for line in wrap(value, size, w - 4):
                        body += "BT /Helv %s Tf 0 g 2 %s Td (%s) Tj ET " % (fmt(size), fmt(text_y), pdf_string(line))
                        text_y -= size * 1.2
                else:
                    body = "BT /Helv %s Tf 0 g 2 %s Td (%s) Tj ET " % (fmt(size), fmt((h - size * 0.72) / 2), pdf_string(value))
            return Dictionary(N=self.appearance(w, h, "%s/Tx BMC q %sQ EMC" % (base, body)))

        if field_type == "check":   # ZapfDingbats "4" is a tick mark
            tick = "q 0 g BT /ZaDb %s Tf %s %s Td (4) Tj ET Q" % (fmt(h * 0.8), fmt(w * 0.15), fmt(h * 0.22))
            return Dictionary(N=Dictionary(Yes=self.appearance(w, h, base + tick), Off=self.appearance(w, h, base)),
                              D=Dictionary(Yes=self.appearance(w, h, base + tick), Off=self.appearance(w, h, base)))

        if field_type == "radio":   # a ring, and when on a dot inside it (circles drawn as 4 Bezier curves)
            ring_r, k, c = w / 2 - widget.get("border_width", 0.75) / 2, 0.5523, w / 2

            def circle(r):
                q = k * r
                return ("%s %s m %s %s %s %s %s %s c %s %s %s %s %s %s c %s %s %s %s %s %s c %s %s %s %s %s %s c" %
                        tuple(map(fmt, (c + r, c, c + r, c + q, c + q, c + r, c, c + r, c - q, c + r, c - r, c + q, c - r, c,
                                        c - r, c - q, c - q, c - r, c, c - r, c + q, c - r, c + r, c - q, c + r, c))))
            ring = ""
            if widget.get("bg"):
                ring += "%s rg %s f " % (rgb(widget["bg"]), circle(ring_r))
            ring += "%s RG %s w %s S " % (rgb(widget.get("border") or INK), fmt(widget.get("border_width", 0.75)), circle(ring_r))
            dot = ring + "0 g %s f" % circle(w * 0.21)
            on = widget["state"]
            return Dictionary(N=Dictionary({"/" + on: self.appearance(w, h, dot), "/Off": self.appearance(w, h, ring)}),
                              D=Dictionary({"/" + on: self.appearance(w, h, dot), "/Off": self.appearance(w, h, ring)}))

        if field_type == "button":  # white caption, centred
            caption, size = widget["caption"], field.get("size", 8)
            drawing = "%s/Tx BMC q BT /Helv %s Tf 1 g %s %s Td (%s) Tj ET Q EMC" % (
                base, fmt(size), fmt((w - width(caption, size)) / 2), fmt((h - size * 0.72) / 2), pdf_string(caption))
            look = self.appearance(w, h, drawing)
            return Dictionary(N=look, D=look)

        return Dictionary(N=self.appearance(w, h, ""))


# ====================================================================================================================
# 3. BUILD: RUN THE THREE STEPS
# ====================================================================================================================

def build(form, answers):
    """The finished PDF as bytes.

    The layout runs twice: the second time, the room left at the end of the last page of questions is shared out
    to the paragraph boxes on that page (Goods description, Additional conditions), so the form doesn't end with a
    blank gap. The second layout is kept only if it doesn't add a page.
    """
    def lay_out(extra_height):
        layout = Layout(form, answers, extra_height)
        layout.draw()
        return layout

    layout = lay_out({})                             # step 1
    last_paragraphs = [qid for qid, page in layout.paragraph_page.items() if page == layout.last_question_page]
    if last_paragraphs and layout.spare >= 20:
        each = min(90, int((layout.spare - 10) // len(last_paragraphs)))   # at most 90 points more per box
        taller = lay_out({qid: each for qid in last_paragraphs})
        if len(taller.pages) == len(layout.pages):
            layout = taller

    doc_script = add_scripts(layout)                 # step 2
    pdf = Writer(layout, doc_script).write()         # step 3
    out = io.BytesIO()
    pdf.save(out, deterministic_id=True)             # same input, same file (reproducible builds)
    return out.getvalue()


# ====================================================================================================================
# 4. SELF-CHECK: OPEN THE BUILT PDF AND CHECK IT
# ====================================================================================================================
# If something is wrong, the build stops here with the reason.

# Opens the finished PDF and checks that every question in the form file became the right fields, with their rules, limits
# and starting answers, and that the scripts, buttons and QR code rows are there. Stops with an error if not.
# (The scripts themselves run only inside Acrobat; test them there, see README "Testing in Acrobat".)

def self_check(pdf_bytes, spec):
    """spec: the form file (FORM, DEFAULTS, PAGES). Returns a one-line summary; stops with the reason if anything is wrong."""
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    fields = {str(f.T): f for f in pdf.Root.AcroForm.Fields}
    questions = [q for s in spec.FORM["sections"] for q in s["fields"]]
    problems = pdf.check_pdf_syntax()
    assert not problems, f"PDF structure problems: {problems}"
    if spec.PAGES:
        assert len(pdf.pages) == spec.PAGES, f"expected {spec.PAGES} pages (PAGES in the form file), got {len(pdf.pages)}"

    # Every question has its fields: dates a list + a calendar box, "tick any" one box per option.
    for q in questions:
        if q["kind"] == "checks":
            names = [f"{q['id']}__{i}" for i in range(len(q["options"]))]
        elif q["kind"] == "date":
            names = [q["id"], f"{q['id']}__list"]
        else:
            names = [q["id"]]
        for name in names:
            assert name in fields, f"missing field {name}"
        f = fields[names[0]]
        expected = REQUIRED if q.get("required") and q["kind"] != "date" else 0
        assert int(f.get("/Ff", 0)) & REQUIRED == expected, f"required flag wrong on {q['id']}"
        if q.get("max") and q["kind"] in ("text", "long"):
            assert int(f.MaxLen) == q["max"], f"max length wrong on {q['id']}"

    # Starting answers, kept as the values "Reset form" goes back to.
    for key, value in spec.DEFAULTS.items():
        f = fields[key]
        assert "/DV" in f, f"no reset value for {key}"
        if isinstance(value, str) and f.FT == "/Tx":
            assert str(f.V) == value, f"{key} starts as {f.V}"

    # The document script holds the rules table, the QR code's text and the QR encoder.
    doc_script = zlib.decompress(pdf.Root.Names.JavaScript.Names[1].JS.read_raw_bytes()).decode("latin-1")
    for name in ("function lcRules(", "function lcDates(", "function lcPayload(", "function lcQrMatrix(", "function lcDrawQr(",
                 "function lcExtra(", "function lcQrCheck(", "function lcLastPage("):
        assert name in doc_script, f"script lacks {name}"
    table = json.loads(re.search(r"var lcModel = (\{.*?\});\n", doc_script).group(1))
    assert "__DEPS__" not in doc_script, "the index of dependencies was not filled in"
    for q in questions:   # every rule in the form file reached the rules table unchanged
        if q.get("required") or q.get("requiredIf") or q.get("activeIf"):
            assert q["id"] in table, f"{q['id']} not in the rules table"
        assert table.get(q["id"], {}).get("always") == (1 if q.get("required") else None), f"'always' wrong on {q['id']}"
        rules = [[r["field"], [safe(v) for v in r["values"]], 1 if r.get("not") else 0] for r in q.get("requiredIf") or []]
        assert table.get(q["id"], {}).get("requiredIf") == (rules or None), f"requiredIf wrong on {q['id']}"

    # Buttons, the hidden re-check field, and the QR code rows.
    for name in ("__check_form", "__reset_form", "__generate_qr", "__print_form", "__checks", "__qr"):
        assert name in fields, f"missing {name}"
    assert len(fields["__check_form"].Kids) == len(pdf.pages), "Check form should be on every page"
    assert all(f"__qr{k}_{y}" in fields for k in (1, 2) for y in range(177)), "missing QR code rows"
    assert int(fields["__qr2_frame"].Kids[0].F) == 2, "the second QR frame should start hidden"
    # The extra QR code page: a hidden template "qrx" (not one of the pages) holding the rows, labels and frames of codes 3 and 4.
    templates = pdf.Root.Names.Templates.Names
    assert [str(templates[0])] == ["qrx"] and templates[1].Type == Name.Template, "the extra QR code page template is missing"
    assert not any(p.objgen == templates[1].objgen for p in pdf.pages), "the extra QR code page should not be one of the pages"
    for k in (1, 2):
        assert all(f"__qrx_{k}_{y}" in fields for y in range(177)) and f"__qrx_{k}_label" in fields, "missing the extra QR code rows"
        assert int(fields[f"__qrx_{k}_frame"].Kids[0].F) == 2, "the extra QR frames should start hidden"
        assert all(w.P.objgen == templates[1].objgen for y in (0, 176) for w in fields[f"__qrx_{k}_{y}"].Kids), "extra QR rows must sit on the template"
    assert "bRename: true" in doc_script and 'getTemplate("qrx")' in doc_script, "the script does not spawn the extra QR page"
    if spec.FORM.get("qrFormat") == "pipe":
        assert "function lcPipeRecords(" in doc_script and "__PIPE__" not in doc_script and "__GROUPS__" not in doc_script, "the pipe records script is missing or not filled in"
    assert "/WS" in pdf.Root.AA and "/WP" in pdf.Root.AA, "missing the warning before save / print"
    return f"PASS: {len(pdf.pages)} pages, {len(fields)} fields, rules table, scripts, buttons and QR rows OK"
