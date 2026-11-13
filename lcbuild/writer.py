"""STEP 3 OF 3: WRITE THE PDF (with pikepdf).

Turns the layout (pages, field descriptions, links) and the document script into a PDF:
  - each page with its drawing (its "content stream") and the fonts it uses
  - every field, with its settings and an "appearance" (a small drawing of how the box looks, so it shows
    correctly in any PDF reader before anyone types into it)
  - the page links, the document script, and the warnings before save / print
  - a copy of the form's description (JSON from lc.py) inside the PDF, for the bank's workbench to read

PDF terms used below:
  Dictionary   a PDF object with named entries, e.g. {/Type /Page, /MediaBox [...]}
  widget       the visible box of a field on a page (one field can have several, e.g. one per page)
  Ff           field flags: required (2), multiline (4096), comb (16777216), read-only (1), drop-down (131072),
               radio (32768), push button (65536)
  F            widget flags: 4 = print, 2 = hidden, 0 = on screen only
  DA           default appearance: font and colour Acrobat uses when it redraws the box
  MK           the box's border colour (BC), background (BG) and caption (CA)
  AA / A       actions: JavaScript run on events (AA) or on click (A)
"""
import zlib

import pikepdf
from pikepdf import Array, Dictionary, Name, String

from .scripts import script
from .style import INK, PAGE_HEIGHT, PAGE_WIDTH, TEXT
from .text import fmt, js_json, num, pdf_string, rgb, safe, width, wrap

# Field flags (Ff) and their meaning.
REQUIRED, READ_ONLY, MULTILINE, COMB, DROP_DOWN, RADIO, PUSH_BUTTON = 2, 1, 4096, 16777216, 131072, 32768, 65536


class Writer:
    def __init__(self, layout, doc_script):
        self.layout, self.doc_script = layout, doc_script

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
        # Fonts the fields use: Helvetica for text, ZapfDingbats for the tick, radio dot and QR squares.
        zapf = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))
        self.fonts = Dictionary(Helvetica=helvetica, Helv=helvetica, ZaDb=zapf)

        # 2. Document information, and the form's description (lc.py as JSON) for the workbench.
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
        pdf.Root[Name.Names] = Dictionary(JavaScript=Dictionary(Names=[String("lcRules"), Dictionary(S=Name.JavaScript, JS=stream)]))
        pdf.Root[Name.AA] = Dictionary(WS=self.javascript(script("before-save.js")), WP=self.javascript(script("before-save.js")))
        return pdf

    # =========================================================================================== helpers
    def javascript(self, code):
        """A PDF action that runs JavaScript."""
        return Dictionary(S=Name.JavaScript, JS=String(code))

    def appearance(self, w, h, drawing):
        """A small drawing (form XObject) of how a box looks, w x h points."""
        return self.pdf.make_stream(drawing.encode("latin-1", "replace"), Type=Name.XObject, Subtype=Name.Form,
                                    BBox=[0, 0, num(w), num(h)], Resources=Dictionary(Font=self.fonts))

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
