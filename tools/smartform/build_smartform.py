"""BUILD: data/forms.json -> out/Trade-Application-Forms.pdf, one PDF with the menu and all 13 forms.

    python tools/smartform/build_smartform.py [--only LC]

Each form looks like the vendor's (same layout, wording and page count, drawn from what Acrobat showed), but is an
ordinary fillable PDF (AcroForm) with Acrobat JavaScript: no XFA, no Reader Extensions, no barcode feature needed.
- The menu page links to each form; every form page has the old Main Menu / Reset buttons, and the last page
  Save and Confirm & Print Form.
- Rules (smartform_js.py): mandatory fields shade red when blank, locked fields grey, hidden parts appear when
  their choice is made, as in the old form (rules found by probing it, see convert.py).
- The 4 PDF417 barcodes are replaced by the form's QR code (one, or two when the answers are long), made from the
  answers when Confirm & Print Form is pressed.
"""
import io
import json
import os
import re
import sys
import zlib

import pikepdf
from pikepdf import Array, Dictionary, Name, String

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))   # lc-form
sys.path.insert(0, ROOT)
from layout import fmt, js_json, num, pdf_string, safe, width   # noqa: E402
from pdf_writer import Writer   # noqa: E402
from smartform_js import BUTTON_JS, DOCUMENT_JS   # noqa: E402

PAGE_W, PAGE_H = 595.28, 841.89
MM = 72 / 25.4
VERSION = "1.0"
OUT = os.path.join(ROOT, "out", "Trade-Application-Forms-old-look.pdf")   # build_all.py writes Trade-Application-Forms.pdf
# Page order: as the old menu lists the forms. A form's terms and its bill of exchange follow it.
ORDER = ["LC", "LC_Amendment", "EBLC", "OBC", "BEGeneric", "DBRP", "EXPORT", "BG", "SBLC", "BGA", "SBLCA"]
AFTER = {"EBLC": ["BEEBLC"], "OBC": ["BEOBC"]}
MENU_BUTTONS = {"btnLC": "LC", "btnLCA": "LC_Amendment", "btnEBLC": "EBLC", "btnOBC": "OBC", "btnBE": "BEGeneric",
                "btnDBRP": "DBRP", "btnEXPORT": "EXPORT", "btnBG": "BG", "btnSBLC": "SBLC", "btnBGA": "BGA", "btnSBLCA": "SBLCA"}
NO_QR = {"BEGeneric", "BEEBLC", "BEOBC"}   # bills of exchange: no barcode on the old form either
GREY_BUTTON = (0.83, 0.83, 0.83)
FONTS = {(False, False): "F1", (True, False): "F2", (False, True): "F3", (True, True): "F4"}


def rgb(c):
    return " ".join(fmt(v) for v in c)


# ==================================================================================================================
# CODE 128 (the static form-type barcode at the top right, e.g. "SG-LC")
# ==================================================================================================================
C128 = ("212222 222122 222221 121223 121322 131222 122213 122312 132212 221213 221312 231212 112232 122132 122231 113222 "
        "123122 123221 223211 221132 221231 213212 223112 312131 311222 321122 321221 312212 322112 322211 212123 212321 "
        "232121 111323 131123 131321 112313 132113 132311 211313 231113 231311 112133 112331 132131 113123 113321 133121 "
        "313121 211331 231131 213113 213311 213131 311123 311321 331121 312113 312311 332111 314111 221411 431111 111224 "
        "111422 121124 121421 141122 141221 112214 112412 122114 122411 142112 142211 241211 221114 413111 241112 134111 "
        "111242 121142 121241 114212 124112 124211 411212 421112 421211 212141 214121 412121 111143 111341 131141 114113 "
        "114311 411113 411311 113141 114131 311141 411131 211412 211214 211232 2331112").split()


def code128_ops(text, x, y, w, h):
    """Drawing commands for text as a Code 128 (set B) barcode filling the box (top-left x, y)."""
    codes = [104] + [ord(c) - 32 for c in text]
    check = (codes[0] + sum(i * c for i, c in enumerate(codes[1:], 1))) % 103
    widths = "".join(C128[c] for c in codes + [check]) + C128[106]
    modules = sum(int(c) for c in widths)
    unit = w / (modules + 20)   # 10 modules of white space each side
    cx, ops, bar = x + 10 * unit, [], True
    for c in widths:
        if bar:
            ops.append("%s %s %s %s re" % (fmt(cx), fmt(PAGE_H - y - h), fmt(int(c) * unit), fmt(h)))
        cx += int(c) * unit
        bar = not bar
    return "0 g " + " ".join(ops) + " f"


# ==================================================================================================================
# PAGES
# ==================================================================================================================
class Page:
    def __init__(self, section, index):
        self.section, self.index, self.ops = section, index, []


class Doc:
    """The whole PDF being built: pages (drawing commands) and fields, in the shape lc-form's Writer expects."""

    def __init__(self, data, only=None):
        self.data, self.pages, self.fields, self.by_name, self.links, self.shrink = data, [], [], {}, [], set()
        self.form = {"title": "Trade Application Forms"}
        self.forms = {f["name"]: f for f in data["forms"]}
        self.terms = data["terms"]
        self.model = {"forms": {}, "byCode": {}, "version": VERSION}
        self.only = only

    # ---- pages and drawing ----
    def add_section_pages(self, sec):
        first = len(self.pages)
        for i, p in enumerate(sec["pages"]):
            page = Page(sec["name"], i)
            page.ops.append(self.render(p["draw"]))
            self.pages.append(page)
        return first

    def render(self, items, dx=0, dy=0, height=PAGE_H):
        """Drawing commands for convert.py's items (top-left coordinates), shifted by (dx, dy) within a box of
        the given height (the page, or a hidden part's picture)."""
        ops = []
        Y = lambda y: height - (y - dy)
        for it in items:
            k = it["k"]
            if k == "fill":
                ops.append("%s rg %s %s %s %s re f" % (rgb(it["c"]), fmt(it["x"] - dx), fmt(Y(it["y"] + it["h"])), fmt(it["w"]), fmt(it["h"])))
            elif k == "line":
                dash = "[1.5 1.5] 0 d " if it.get("dash") else ""
                ops.append("q %s%s RG %s w %s %s m %s %s l S Q" % (dash, rgb(it["c"]), fmt(max(it["w"], 0.25)), fmt(it["x1"] - dx), fmt(Y(it["y1"])), fmt(it["x2"] - dx), fmt(Y(it["y2"]))))
            elif k == "ellipse":
                cx, cy, rx, ry, q = it["x"] - dx + it["w"] / 2, Y(it["y"] + it["h"] / 2), it["w"] / 2, it["h"] / 2, 0.5523
                ops.append("q 0 G %s w %s %s m %s %s %s %s %s %s c %s %s %s %s %s %s c %s %s %s %s %s %s c %s %s %s %s %s %s c S Q" % tuple(map(fmt, (
                    it["lw"], cx + rx, cy, cx + rx, cy + q * ry, cx + q * rx, cy + ry, cx, cy + ry, cx - q * rx, cy + ry, cx - rx, cy + q * ry, cx - rx, cy,
                    cx - rx, cy - q * ry, cx - q * rx, cy - ry, cx, cy - ry, cx + q * rx, cy - ry, cx + rx, cy - q * ry, cx + rx, cy))))
            elif k == "text":
                ops.append("BT /%s %s Tf %s rg %s %s Td (%s) Tj ET" % (FONTS[(it["b"], it["i"])], fmt(it["s"]), rgb(it["c"]),
                                                                     fmt(it["x"] - dx), fmt(Y(it["y"])), pdf_string(safe(it["t"]))))
        return " ".join(ops)

    # ---- fields ----
    def add_field(self, name, ftype, **kw):
        f = {"name": name, "type": ftype, "widgets": [], **kw}
        self.fields.append(f)
        self.by_name[name] = f
        return f

    def widget(self, field, page, x, y, w, h, **kw):
        """A box of field on page (index), at top-left (x, y), w x h points."""
        wd = {"page": page, "rect": [x, PAGE_H - y - h, x + w, PAGE_H - y], **kw}
        field["widgets"].append(wd)
        return wd


# ==================================================================================================================
# ONE FORM
# ==================================================================================================================
def code_of(sec):
    return re.sub(r"-\d+$", "", sec["code"]).replace("-", "")


def build_form(doc, sec, first_page):
    code = code_of(sec)
    prefix = code + "_"
    S = {"code": sec["code"], "prefix": prefix, "f": {}, "parts": {}, "order": [], "sets": {}, "first": first_page,
         "last": first_page + len(sec["pages"]) - 1}
    doc.model["forms"][sec["name"]] = S
    doc.model["byCode"][code] = sec["name"]

    # Hidden parts: their labels and lines as one picture (a read-only button), shown when their rule holds.
    part_ids = {}
    for i, p in enumerate(sec["parts"]):
        if not p["draw"]:
            continue
        pid = "part%d" % i
        part_ids[p["som"]] = pid
        xs = [v for it in p["draw"] for v in ((it["x"], it["x"] + it.get("w", 0)) if "x" in it else (it["x1"], it["x2"]))]
        ys = [v for it in p["draw"] for v in ((it["y"] - it.get("s", 0), it["y"] + it.get("h", 2)) if "y" in it else (it["y1"], it["y2"]))]
        x0, y0, x1, y1 = min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2
        name = "%sPART_%d" % (prefix, i)
        pic = doc.add_field(name, "picture", read_only=True)
        pic["picture"] = doc.render(p["draw"], dx=x0, dy=y0, height=y1 - y0)
        doc.widget(pic, first_page + p["page"] - 1, x0, y0, x1 - x0, y1 - y0, hidden=True)
        S["parts"][pid] = {"n": name, "r": clean_rules(p.get("rules"), sec)}

    # Questions.
    labels = {}
    for f in sec["fields"]:
        fid, kind = f["id"], f["kind"]
        name = prefix + fid
        label = f.get("label") or labels.get(fid) or fid.replace("_", " ").capitalize()
        m = {"k": kind, "l": label, "n": name}
        if f.get("part") in part_ids:
            m["p"] = part_ids[f["part"]]
        elif f.get("part"):
            m["p"] = None
        r = clean_rules(f.get("rules"), sec)
        if r:
            m["r"] = r
        if f.get("ks", {}).get("spec"):
            m["ks"] = f["ks"]["spec"]
        page = first_page + f["page"] - 1
        hidden = bool(f.get("part"))
        events = {}
        if kind == "radio":
            opts = f["options"]
            exports = [o["label"] or o["on"] for o in opts]
            if len(set(exports)) < len(exports):
                exports = [o["on"] for o in opts]
            m["values"] = dict(zip([o["on"] for o in opts], exports))
            default = exports[[o["on"] for o in opts].index(f["default"])] if f.get("default") in [o["on"] for o in opts] else None
            fld = doc.add_field(name, "radio", options=exports, value=[o["on"] for o in opts].index(f["default"]) if default else None, tooltip=label)
            for i, o in enumerate(opts):
                x, y, w, h = o["rect"]
                doc.widget(fld, first_page + o["page"] - 1, x, y, w, h, state=str(i), border=(0, 0, 0), border_width=0.6,
                           bg=(1, 1, 1), hidden=hidden, events={"U": "smChanged(this, event.target.name);"})
        elif kind == "check":
            x, y, w, h = f["rect"]
            fld = doc.add_field(name, "check", value=bool(f.get("default") and f["default"] not in ("0", "Off")), tooltip=label)
            doc.widget(fld, page, x, y, w, h, border=(0, 0, 0), border_width=0.6, bg=(1, 1, 1), hidden=hidden,
                       events={"U": "smChanged(this, event.target.name);"})
        else:
            x, y, w, h = f["rect"]
            size = min(f.get("font") or 8, max(h - 1, 5)) if kind != "long" else min(f.get("font") or 8, 8)
            ks = f.get("ks", {})
            if kind == "select":
                opts = [o[0] for o in f.get("options") or []]
                fld = doc.add_field(name, "choice", options=opts, value=f.get("default") if f.get("default") in opts else None, size=size, tooltip=label)
                events["U"] = "smChanged(this, event.target.name);"
                events["Bl"] = "smChanged(this, event.target.name);"
            else:
                fld = doc.add_field(name, "text", size=size, multiline=kind == "long", max=f.get("max") or (ks.get("limit")),
                                    value=f.get("default"), tooltip=label)
                if kind == "date":
                    pic = date_picture(f.get("picture"))
                    events["K"] = 'AFDate_KeystrokeEx("%s");' % pic
                    events["F"] = 'AFDate_FormatEx("%s");' % pic
                elif kind == "number":
                    d = f.get("decimals") or 0
                    events["K"] = "AFNumber_Keystroke(%d, 0, 0, 0, \"\", true);" % d
                    events["F"] = "AFNumber_Format(%d, 0, 0, 0, \"\", true);" % d
                elif ks.get("spec") or ks.get("limit"):
                    events["K"] = 'smKey("%s", %d);' % (ks.get("spec", ""), ks.get("limit") or 0)
                events["Bl"] = "smChanged(this, event.target.name);"
            boxes = [(page, f["rect"])] + [(first_page + pg - 1, rc) for pg, rc in f.get("more", [])]
            for pg, (x, y, w, h) in boxes:
                doc.widget(fld, pg, x, y, w, h, hidden=hidden)
            if f.get("readonly_at_open") and not (r or {}).get("open"):
                fld["read_only"] = True
            fld["events"] = events
        S["f"][fid] = m
        S["order"].append(fid)
        for t, val, value in (f.get("rules") or {}).get("set", []):
            S["sets"].setdefault(t, []).append([val, fid, value])
    # radio rule values: the old on-values -> the new export values
    for fid, m in S["f"].items():
        for key in ("req", "nreq", "open", "lock", "show", "hide"):
            for c in (m.get("r") or {}).get(key, []):
                tm = S["f"].get(c[0])
                if tm and tm["k"] == "radio":
                    c[1] = [tm["values"].get(v, v) for v in c[1]]
    for p in S["parts"].values():
        for key in ("show", "hide"):
            for c in (p.get("r") or {}).get(key, []):
                tm = S["f"].get(c[0])
                if tm and tm["k"] == "radio":
                    c[1] = [tm["values"].get(v, v) for v in c[1]]
    for t, lst in S["sets"].items():
        tm = S["f"].get(t)
        if tm and tm["k"] == "radio":
            for s in lst:
                s[0] = tm["values"].get(s[0], s[0])
        for s in lst:   # a radio target is set by its export value
            target = S["f"].get(s[1])
            if target and target["k"] == "radio":
                s[2] = target["values"].get(s[2], s[2])
            if target and target["k"] == "check":
                s[2] = "Yes" if s[2] not in ("0", "Off", "") else "Off"
    for m in S["f"].values():
        m.pop("values", None)
    return S


def clean_rules(r, sec):
    if not r:
        return {}
    out = {k: v for k, v in r.items() if k in ("always", "req", "nreq", "open", "lock", "show", "hide", "locked_at_open")}
    return out


def date_picture(pic):
    """The XFA date picture ("date{DD MMM, YYYY}") as Acrobat's date format ("dd mmm, yyyy")."""
    m = re.search(r"\{(.*?)\}", pic or "")
    p = m.group(1) if m else "DD/MM/YYYY"
    return p.replace("DD", "dd").replace("MMM", "mmm").replace("MM", "mm").replace("YYYY", "yyyy").replace("D", "d")


# ==================================================================================================================
# BUTTONS, MENU AND QR CODES
# ==================================================================================================================
def button(doc, name, caption, page, rect, js, size=8):
    x, y, w, h = rect
    b = doc.by_name.get(name) or doc.add_field(name, "button", size=size)
    doc.widget(b, page, x, y, w, h, caption=caption, border=(0.4, 0.4, 0.4), bg=GREY_BUTTON, border_width=0.75, action=js, flags=4 if False else 0)
    return b


def add_buttons(doc, sec, first_page, S, pages_of):
    code = code_of(sec)
    last = S["last"]
    terms_last = pages_of.get(sec["name"] + ":end", last)
    for i, b in enumerate(sec["buttons"]):
        cap, page = b["caption"], first_page + b["page"] - 1
        js = None
        if cap in ("Main Menu", "Main Page"):
            js = BUTTON_JS["menu"]
        elif cap == "Reset":
            js = BUTTON_JS["reset"].replace("__FORM__", sec["name"])
        elif cap.startswith("Confirm"):
            js = BUTTON_JS["print"].replace("__FORM__", sec["name"]).replace("__FIRST__", str(first_page)).replace("__LAST__", str(terms_last))
        elif cap == "Save":
            js = BUTTON_JS["save"]
        elif cap.startswith("BE(") and pages_of.get(cap):
            js = BUTTON_JS["goto"].replace("__PAGE__", str(pages_of[cap]))
        elif cap in ("EBLC", "OBC") and cap in pages_of:
            js = BUTTON_JS["goto"].replace("__PAGE__", str(pages_of[cap]))
        if js:
            button(doc, "%s_btn%d" % (code, i), cap, page, b["rect"], js)


def add_qr(doc, sec, first_page, S):
    """Two QR code slots side by side where the old PDF417 barcodes were (the first page that had them)."""
    pdf417 = [b for b in sec["barcodes"] if b["type"] == "pdf417"]
    code = code_of(sec)
    if not pdf417:
        return
    pg = min(b["page"] for b in pdf417)
    on = [b for b in pdf417 if b["page"] == pg]
    x0 = min(b["rect"][0] for b in on)
    x1 = max(b["rect"][0] + b["rect"][2] for b in on)
    y0 = min(b["rect"][1] for b in on)
    bottom = 28.325 * MM + 255.675 * MM   # the content area's bottom
    size = min((x1 - x0 - 12) / 2, bottom - y0 - 14, 100 * MM)
    page = first_page + pg - 1
    module = size / 185   # 177 squares and 4 white squares each side
    font = "/ZaDb %s Tf 0 g" % fmt(round(module / 0.692 * 1000) / 1000)
    for k in (1, 2):
        x = x0 + (k - 1) * (size + 12)
        label = doc.add_field("QR_%s_%d_label" % (sec["code"], k), "text", read_only=True, size=7, noqr=True)
        doc.widget(label, page, x, y0, size, 10)
        for row in range(177):
            f = doc.add_field("QR_%s_%d_%d" % (sec["code"], k, row), "text", max=177, comb=True, appearance=font, noqr=True)
            doc.widget(f, page, x + 4 * module, y0 + 12 + (4 + row) * module, 177 * module, module)
    S["qr"] = {"page": page}


def add_static_barcodes(doc, sec, first_page):
    for b in sec["barcodes"]:
        if b["type"] == "code128" and b.get("value"):
            x, y, w, h = b["rect"]
            doc.pages[first_page + b["page"] - 1].ops.append(code128_ops(b["value"].strip(), x, y, w, h - 8))
            doc.pages[first_page + b["page"] - 1].ops.append("BT /F1 7 Tf 0 g %s %s Td (%s) Tj ET" % (
                fmt(x + w / 2 - width(b["value"].strip(), 7) / 2), fmt(PAGE_H - y - h + 1), pdf_string(b["value"].strip())))


def build_menu(doc, menu, page_of_form):
    first = doc.add_section_pages(menu)
    for i, b in enumerate(menu["buttons"]):
        target = MENU_BUTTONS.get(b["name"])
        if target and target in page_of_form:
            x, y, w, h = b["rect"]
            # the old menu shows the form's name as the button's caption: draw it as text, link over it
            doc.pages[first].ops.append("BT /F1 %s Tf 0 g %s %s Td (%s) Tj ET" % (fmt(min(h * 0.75, 12)), fmt(x + 2), fmt(PAGE_H - y - h * 0.78), pdf_string(safe(b["caption"]))))
            btn = doc.add_field("MENU_btn%d" % i, "button", size=8)
            doc.widget(btn, first, x, y, w, h, action=BUTTON_JS["open-form"].replace("__PAGE__", str(page_of_form[target])), flags=4)
    for f in menu["fields"]:
        x, y, w, h = f["rect"]
        if f["kind"] == "check":
            fld = doc.add_field("MENU_agree", "check")
            doc.widget(fld, first, x, y, w, h, border=(0, 0, 0), border_width=0.6, bg=(1, 1, 1))
        else:
            fld = doc.add_field("MENU_" + f["id"], "text", size=min(f.get("font") or 9, h - 1), max=f.get("max"))
            doc.widget(fld, first, x, y, w, h, bg=(0.88, 0.9, 1))
    return first


# ==================================================================================================================
# WRITING
# ==================================================================================================================
class SmartWriter(Writer):
    def write(self):
        layout = self.layout
        pdf = self.pdf = pikepdf.new()
        fonts = {}
        for key, base in (("F1", "Helvetica"), ("F2", "Helvetica-Bold"), ("F3", "Helvetica-Oblique"), ("F4", "Helvetica-BoldOblique")):
            fonts[key] = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name("/" + base), Encoding=Name.WinAnsiEncoding))
        zapf = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))
        self.fonts = Dictionary(Helvetica=fonts["F1"], Helv=fonts["F1"], ZaDb=zapf, F1=fonts["F1"], F2=fonts["F2"], F3=fonts["F3"], F4=fonts["F4"])
        for page in layout.pages:
            drawing = pdf.make_stream(zlib.compress(" ".join(page.ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)
            pdf.pages.append(pikepdf.Page(Dictionary(Type=Name.Page, MediaBox=[0, 0, PAGE_W, PAGE_H],
                                                     Resources=Dictionary(Font=Dictionary(F1=fonts["F1"], F2=fonts["F2"], F3=fonts["F3"], F4=fonts["F4"])),
                                                     Contents=drawing)))
        pages = [p.obj for p in pdf.pages]
        pdf.docinfo[Name.Title] = String("Trade Application Forms")
        pdf.docinfo[Name.Creator] = String("lc-form smartform builder")
        all_fields = []
        for field in layout.fields:
            all_fields.append(self.make_field(field, pages))
            for widget in field["widgets"]:
                p = pages[widget["page"]]
                if Name.Annots not in p:
                    p[Name.Annots] = Array()
                p.Annots.append(widget["obj"])
        acro = Dictionary(Fields=Array(all_fields), DR=Dictionary(Font=self.fonts), DA=String("/Helv 0 Tf 0 g"))
        acro[Name.CO] = Array([layout.by_name["__checks"]["obj"]])
        pdf.Root[Name.AcroForm] = pdf.make_indirect(acro)
        stream = pdf.make_stream(zlib.compress(self.doc_script.encode("latin-1", "replace")), Filter=Name.FlateDecode)
        pdf.Root[Name.Names] = Dictionary(JavaScript=Dictionary(Names=[String("smRules"), Dictionary(S=Name.JavaScript, JS=stream)]))
        pdf.Root[Name.PageMode] = Name.UseNone
        return pdf

    def make_field(self, field, pages):
        if field["type"] == "picture":   # a hidden part: read-only push button whose look is the part's labels and lines
            d = self.pdf.make_indirect(Dictionary(T=String(field["name"]), FT=Name.Btn, Ff=65536 | 1))
            kids = Array()
            for wd in field["widgets"]:
                x1, y1, x2, y2 = wd["rect"]
                look = self.appearance(x2 - x1, y2 - y1, field["picture"])
                k = Dictionary(Type=Name.Annot, Subtype=Name.Widget, Rect=[num(v) for v in wd["rect"]], P=pages[wd["page"]],
                               Parent=d, F=6 if wd.get("hidden") else 4, AP=Dictionary(N=look), BS=Dictionary(W=0))
                wd["obj"] = self.pdf.make_indirect(k)
                kids.append(wd["obj"])
            d.Kids = kids
            field["obj"] = d
            return d
        d = super().make_field(field, pages)
        if field["type"] == "button":
            return d
        for wd in field["widgets"]:
            if wd.get("hidden"):
                wd["obj"].F = 6   # hidden + print (shown by the rules)
        return d

    def widget_appearance(self, field, widget, w, h):
        if field["type"] == "button":   # grey, black caption, like the old buttons
            caption, size = widget.get("caption"), field.get("size", 8)
            body = self.frame(widget, w, h)
            if caption:
                body += "/Tx BMC q BT /Helv %s Tf 0 g %s %s Td (%s) Tj ET Q EMC" % (fmt(size), fmt((w - width(caption, size)) / 2), fmt((h - size * 0.72) / 2), pdf_string(safe(caption)))
            look = self.appearance(w, h, body)
            return Dictionary(N=look, D=look)
        return super().widget_appearance(field, widget, w, h)


def build(only=None):
    data = json.load(open(os.path.join(HERE, "data", "forms.json")))
    doc = Doc(data, only)
    forms = doc.forms
    order = [only] if only else ORDER
    # Page numbers first (the menu and buttons link to them): menu, then each form, its terms, its bill of exchange.
    plan, n = [], 1
    page_of = {}
    for name in order:
        sec = forms[name]
        page_of[name] = n
        n += len(sec["pages"])
        for t in sec.get("terms", []):
            n += len(doc.terms[t]["pages"])
        page_of[name + ":end"] = n - 1
        for b in AFTER.get(name, []) if not only else []:
            page_of[b] = n
            page_of["BE(%s mapping)" % name] = n
            n += len(forms[b]["pages"])
    build_menu(doc, data["menu"], page_of)
    S_all = []
    for name in order:
        for sname in [name] + (AFTER.get(name, []) if not only else []):
            sec = forms[sname]
            first = doc.add_section_pages(sec)
            assert first == page_of[sname], (sname, first, page_of[sname])
            S = build_form(doc, sec, first)
            add_static_barcodes(doc, sec, first)
            if sname not in NO_QR:
                add_qr(doc, sec, first, S)
            add_buttons(doc, sec, first, S, page_of)
            S_all.append(S)
            if sname == name:
                for t in sec.get("terms", []):
                    doc.add_section_pages(doc.terms[t])
    # the hidden field that re-runs a form's rules after any change (Acrobat's calculate event)
    recalc = doc.add_field("__checks", "text", size=3, events={"C": "if (event.source) smRun(this, smForm(event.source.name));"})
    doc.widget(recalc, 0, -20, -20, 1, 1, hidden=True)
    script = DOCUMENT_JS.replace("__MODEL__", js_json(doc.model))
    script = script.encode("ascii", "replace").decode()
    pdf = SmartWriter(doc, script).write()
    out = io.BytesIO()
    pdf.save(out, deterministic_id=True)
    return out.getvalue(), doc


def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    data, doc = build(only)
    path = OUT if not only else OUT.replace(".pdf", "-%s.pdf" % only)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    print(f"Wrote {path}: {len(doc.pages)} pages, {len(doc.fields)} fields, {len(data) // 1024} KB")


if __name__ == "__main__":
    main()
