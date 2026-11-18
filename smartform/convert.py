"""CONVERT: the vendor form's layout, styling and rules -> data/forms.json (what build_smartform.py draws).

    python smartform/convert.py [path/to/template.xml]

Reads data/raw/ (from harvest.py: where Acrobat drew everything, and the rules found by probing) and the XFA
template (from trade-smartform-extract, already anonymised: the fonts, borders, captions, lists and scripts).
Writes data/forms.json: for each section, its pages as simple drawing items (lines, fills, text lines) and its
fields (where, what kind, options, limits), plus each field's rules (mandatory / unlocked / shown when ...).

Coordinates in forms.json are PDF points from the TOP-left of the page (y grows downwards).
"""
import json
import os
import re
import sys
from collections import defaultdict

from xfa import MM, Template, child, kids, length, tag

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
TEMPLATE = os.path.expanduser("~/Documents/trade-smartform-extract/xfa/template.xml")
sys.path.insert(0, os.path.dirname(HERE))
from layout import width as text_width   # noqa: E402  Helvetica letter widths (Arial has the same widths)

AREA = {"Page1": (12 * MM, 28.325 * MM), "Page2": (3 * MM, 4 * MM)}   # where each page's content area starts
FORMS = ["LC", "LC_Amendment", "EBLC", "OBC", "DBRP", "EXPORT", "BG", "SBLC", "BGA", "SBLCA", "BEGeneric", "BEEBLC", "BEOBC"]
TERMS = {"LC": ["LCTermsAndConditions"], "EBLC": ["EBLCTermsAndConditions", "EBLCTermsAndConditions1"],
         "OBC": ["OBCTermsAndConditions"]}
# What each form is called (menu, titles) and its code in the QR code.
TITLES = {
    "LC": ("LC-01", "Irrevocable Documentary Credit Application"),
    "LC_Amendment": ("LCA-01", "Amendment to Original Documentary Credit"),
    "EBLC": ("EBLC-01", "Handling / Financing of Documents Under Export Documentary Credit"),
    "OBC": ("OBC-01", "Export Documentary Collection / Financing of Bills under Export Documentary Collection"),
    "DBRP": ("DBRP-01", "Import Financing"),
    "EXPORT": ("EXP-01", "Export Financing - Pre-shipment Financing on Open Account Basis / Sales Invoice Financing"),
    "BG": ("BG-01", "Banker's Guarantee Application"),
    "SBLC": ("SBLC-01", "Irrevocable Standby Letter of Credit Application"),
    "BGA": ("BGA-01", "Banker's Guarantee Amendment"),
    "SBLCA": ("SBLCA-01", "Standby Letter of Credit Amendment"),
    "BEGeneric": ("BE-01", "Bill of Exchange (Generic - free format)"),
    "BEEBLC": ("BEEBLC-01", "Bill of Exchange (Export Documentary Credit)"),
    "BEOBC": ("BEOBC-01", "Bill of Exchange (Export Documentary Collection)"),
}
SKIP_FIELD = re.compile(r"barcode|Bcode|Code128|Code3of9|^btn|Button|Dummy|FieldsList|HiddenField|CheckSum|^Pages$|"
                        r"CurrentPage|PageCount|txtPrint|Cif$", re.I)


def visible_text(s):
    """The anonymised template says "the Bank"; the new forms say "Demo Bank"."""
    s = s.replace("THE BANK LTD", "DEMO BANK LTD").replace("the Bank Ltd", "Demo Bank Ltd").replace("The Bank Ltd", "Demo Bank Ltd")
    return s.replace("–", "-").replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


# ==================================================================================================================
# STYLING READ FROM THE TEMPLATE
# ==================================================================================================================
def color(e, default=(0, 0, 0)):
    c = child(e, "color")
    if c is None or not c.get("value"):
        return default
    return tuple(int(v) / 255 for v in c.get("value").split(",")[:3])


def font_of(e, parent_font=None):
    """(size, bold, italic, colour) of a <font> under e, else the parent's, else 10pt black."""
    f = child(e, "font")
    base = parent_font or (10.0, False, False, (0, 0, 0))
    if f is None:
        return base
    size = length(f.get("size"), base[0])
    fill = child(f, "fill")
    return (size, f.get("weight") == "bold", f.get("posture") == "italic", color(fill, base[3]) if fill is not None else base[3])


def para_of(e):
    p = child(e, "para")
    g = (lambda k, d="": p.get(k, d)) if p is not None else (lambda k, d="": d)
    return {"h": g("hAlign", "left"), "v": g("vAlign", "top"), "ml": length(g("marginLeft")), "mr": length(g("marginRight")),
            "indent": length(g("textIndent")), "above": length(g("spaceAbove")), "below": length(g("spaceBelow"))}


def margin_of(e):
    m = child(e, "margin")
    if m is None:
        return (0, 0, 0, 0)
    return tuple(length(m.get(k)) for k in ("topInset", "rightInset", "bottomInset", "leftInset"))


def edges_of(border):
    """The 4 edges (top, right, bottom, left) of a <border>, each (thickness, colour, dashed) or None if hidden."""
    if border is None or border.get("presence") in ("hidden", "invisible", "inactive"):
        return [None] * 4
    es = kids(border, "edge") or [None]
    es = (es + [es[-1]] * 4)[:4]
    out = []
    for e in es:
        if e is not None and e.get("presence") in ("hidden", "invisible", "inactive"):
            out.append(None)
            continue
        stroke = e.get("stroke", "solid") if e is not None else "solid"
        grey = stroke in ("lowered", "raised", "etched", "embossed")
        out.append((length(e.get("thickness") if e is not None else None, 0.5), (0.5, 0.5, 0.5) if grey else color(e),
                    stroke in ("dashed", "dotted", "dashDot", "dashDotDot")))
    return out


def fill_of(border):
    if border is None or border.get("presence") in ("hidden", "invisible"):
        return None
    f = child(border, "fill")
    if f is None or child(f, "color") is None:
        return None
    c = color(f)
    return None if c == (1, 1, 1) else c


# ==================================================================================================================
# DRAWING ITEMS
# ==================================================================================================================
class Canvas:
    """Collects drawing items: lines, fills, ellipses and text lines (top-left coordinates)."""

    def __init__(self):
        self.items = []

    def box(self, x, y, w, h, border):
        fill = fill_of(border)
        if fill:
            self.items.append({"k": "fill", "x": x, "y": y, "w": w, "h": h, "c": fill})
        top, right, bottom, left = edges_of(border)
        for e, (x1, y1, x2, y2) in ((top, (x, y, x + w, y)), (right, (x + w, y, x + w, y + h)),
                                    (bottom, (x, y + h, x + w, y + h)), (left, (x, y, x, y + h))):
            if e and (x1 != x2 or y1 != y2):
                self.items.append({"k": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "w": e[0], "c": e[1], "dash": e[2]})

    def text(self, runs_by_line, x, y, w, h, para, valign=None):
        """Draws lines of runs [(text, size, bold, italic, colour)] inside the box, aligned like the template."""
        lines = [ln for ln in runs_by_line]
        heights = [max((r[1] for r in ln["runs"]), default=ln.get("size", 8)) * 1.15 for ln in lines]
        total = sum(heights) + sum(ln.get("above", 0) for ln in lines)
        v = valign or para["v"]
        top = y if v == "top" else y + (h - total) / 2 if v == "middle" else y + h - total
        for ln, lh in zip(lines, heights):
            top += ln.get("above", 0)
            line_w = sum(text_width(r[0], r[1], r[2]) for r in ln["runs"])
            left = x + ln.get("ml", 0)
            avail = w - ln.get("ml", 0) - ln.get("mr", 0)
            hal = ln.get("h", para["h"])
            cx = left + (avail - line_w) / 2 if hal == "center" else left + avail - line_w if hal == "right" else left + ln.get("indent", 0)
            base = top + lh * 0.82
            for t, size, bold, italic, c in ln["runs"]:
                if t:
                    self.items.append({"k": "text", "x": round(cx, 2), "y": round(base, 2), "s": size, "b": bold, "i": italic, "c": c, "t": t})
                cx += text_width(t, size, bold)
            top += lh


def wrap_runs(runs, max_w):
    """Breaks a paragraph's runs [(text, size, bold, italic, colour)] into lines no wider than max_w."""
    words = []
    for t, size, bold, italic, c in runs:
        for piece in re.findall(r"\S+\s*|\s+", t):
            words.append((piece, size, bold, italic, c))
    lines, cur, cur_w = [], [], 0
    for wd in words:
        ww = text_width(wd[0].rstrip(), wd[1], wd[2])
        if cur and cur_w + ww > max_w + 0.5:
            lines.append(cur)
            cur, cur_w = [], 0
            if not wd[0].strip():
                continue
        cur.append(wd)
        cur_w += text_width(wd[0], wd[1], wd[2])
    if cur:
        lines.append(cur)
    out = []
    for ln in lines or [[]]:   # merge neighbouring words of the same style into one run
        merged = []
        for wd in ln:
            if merged and merged[-1][1:] == wd[1:]:
                merged[-1] = (merged[-1][0] + wd[0],) + merged[-1][1:]
            else:
                merged.append(wd)
        if merged:
            merged[-1] = (merged[-1][0].rstrip(),) + merged[-1][1:]
        out.append(merged)
    return out


def plain_lines(text, font, para, max_w):
    lines = []
    for i, p in enumerate(visible_text(text).replace("\r", "\n").split("\n")):
        for ln in wrap_runs([(p, font[0], font[1], font[2], font[3])], max_w - para["ml"] - para["mr"]):
            lines.append({"runs": ln, "size": font[0], "h": para["h"], "ml": para["ml"], "mr": para["mr"],
                          "indent": para["indent"] if i == 0 else 0, "above": para["above"] if i == 0 else 0})
    return lines


CSS = re.compile(r"([\w-]+)\s*:\s*([^;]+)")


def xhtml_lines(exdata, font, para, max_w):
    """Rich text (<exData> XHTML): paragraphs with bold / italic / size runs, wrapped to max_w."""
    import xml.etree.ElementTree as ET
    body = exdata[0] if len(exdata) else None
    if body is None:
        return plain_lines(exdata.text or "", font, para, max_w)
    lines = []

    def style(e, st):
        st = dict(st)
        for k, v in CSS.findall(e.get("style", "")):
            st[k.strip()] = v.strip()
        t = tag(e)
        if t in ("b", "strong"):
            st["font-weight"] = "bold"
        if t in ("i", "em"):
            st["font-style"] = "italic"
        return st

    def run_font(st):
        size = length(st.get("font-size"), font[0]) if st.get("font-size") else font[0]
        return size, st.get("font-weight", "") in ("bold", "700"), st.get("font-style") == "italic"

    def paragraphs(e, st, out):
        st = style(e, st)
        if tag(e) in ("p", "li", "div") or e is body:
            runs = []
            collect(e, st, runs, out)
            if tag(e) in ("p", "li") or (e is body and runs):
                out.append((runs, st))
        else:
            for c in e:
                paragraphs(c, st, out)

    def collect(e, st, runs, out):
        if e.text:
            runs.append((e.text,) + run_font(st) + (font[3],))
        for c in e:
            cs = style(c, st)
            if tag(c) in ("p", "div", "li"):
                if runs:
                    out.append((list(runs), st))
                    runs.clear()
                paragraphs(c, st, out)
            elif tag(c) == "br":
                out.append((list(runs), st))
                runs.clear()
            else:
                collect(c, cs, runs, out)
            if c.tail:
                runs.append((c.tail,) + run_font(st) + (font[3],))

    out = []
    paragraphs(body, {}, out)
    for runs, st in out:
        runs = [(visible_text(re.sub(r"\s+", " ", r[0])),) + r[1:] for r in runs]
        if runs:
            runs[0] = (runs[0][0].lstrip(),) + runs[0][1:]
        ml = length(st.get("margin-left")) if st.get("margin-left") else para["ml"]
        mr = length(st.get("margin-right")) if st.get("margin-right") else para["mr"]
        indent = length(st.get("text-indent")) if st.get("text-indent") else para["indent"]
        above = length(st.get("margin-top")) if st.get("margin-top") else para["above"]
        hal = {"center": "center", "right": "right"}.get(st.get("text-align"), para["h"])
        size = run_font(st)[0]
        wrapped = wrap_runs(runs, max_w - ml - mr - max(indent, 0)) if any(r[0].strip() for r in runs) else [[]]
        for i, ln in enumerate(wrapped):
            lines.append({"runs": ln, "size": size, "h": hal, "ml": ml, "mr": mr, "indent": indent if i == 0 else 0,
                          "above": above if i == 0 else 0})
    return lines


def text_lines(value_parent, runtime_text, font, para, max_w):
    ex = child(value_parent, "value", "exData")
    if ex is not None and ex.get("contentType", "").endswith("html"):
        return xhtml_lines(ex, font, para, max_w)
    return plain_lines(runtime_text or "", font, para, max_w)


# ==================================================================================================================
# ONE SECTION
# ==================================================================================================================
def slug(name):
    name = re.sub(r"^(txt|drp|chk|rad|radio|subfrm|sufrm|sub|lbl|btn|num|dt|date)(?=[A-Z0-9_])", "", name)
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()
    return re.sub(r"[^a-z0-9]+", "_", name).strip("_") or "field"


def field_path(som, section):
    """The field's XFA path inside its section, without indices ([0]) and unnamed subforms."""
    parts = som.split(f".{section}[0].", 1)[-1].split(".")
    return ".".join(re.sub(r"\[0\]$", "", p) if p.endswith("[0]") else p for p in parts if not p.startswith("#"))


class Section:
    def __init__(self, T, name, layout):
        self.T, self.name, self.L = T, name, layout
        self.pages = [{"area": None, "draw": Canvas()} for _ in range(layout["pages"])]
        self.parts = {}      # hidden part som -> {"page", "draw": Canvas, "fields": [...]}
        self.fields = []
        self.seen = {}       # field som -> its entry (header fields repeat on every page: one field, one box per page)
        self.buttons, self.barcodes = [], []

    def origin(self, it):
        if it["master"]:
            return 0, 0
        return AREA[self.pages[it["page"] - 1]["area"] or "Page1"]

    def run(self):
        base = self.L["base"]
        for it in base:   # which master page each page uses (Page2 = the near full-bleed one for terms)
            if it["master"] and it["cls"] == "subform" and ".Page2[" in it["som"]:
                self.pages[it["page"] - 1]["area"] = "Page2"
        for p in self.pages:
            p["area"] = p["area"] or "Page1"
        for it in base:
            if it["vis"]:
                self.item(it, self.pages[it["page"] - 1]["draw"], None)
        for h in self.L["hidden"]:
            if h["shifted"]:
                continue   # measured shown already (harvest.py), so it is in base
            pages = sorted({it["page"] for it in h["items"]})
            part = self.parts[h["som"]] = {"page": pages[0] if pages else 1, "draw": Canvas(), "som": h["som"]}
            for it in h["items"]:
                if it["vis"]:
                    self.item(it, part["draw"], h["som"])
        return self

    # ---- one harvested item ----
    def item(self, it, canvas, part):
        e = self.T.find(it["som"])
        if e is None:
            return
        ox, oy = self.origin(it)
        x, y, w, h = it["x"] + ox, it["y"] + oy, it["w"], it["h"]
        kind = tag(e)
        if kind == "subform":
            canvas.box(x, y, w, h, child(e, "border"))
        elif kind == "draw":
            self.draw(e, it, x, y, w, h, canvas)
        elif kind == "field":
            self.field(e, it, x, y, w, h, canvas, part)

    def draw(self, e, it, x, y, w, h, canvas):
        value = child(e, "value")
        canvas.box(x, y, w, h, child(e, "border"))
        if value is None:
            return
        v = value[0] if len(value) else None
        if v is None:
            return
        vt = tag(v)
        if vt == "line":
            edge = child(v, "edge")
            th = length(edge.get("thickness") if edge is not None else None, 0.5)
            c = color(edge) if edge is not None else (0, 0, 0)
            if w < 1:
                pts = (x, y, x, y + h)
            elif h < 1:
                pts = (x, y, x + w, y)
            else:
                pts = (x, y + h, x + w, y) if v.get("slope") == "/" else (x, y, x + w, y + h)
            canvas.items.append({"k": "line", "x1": pts[0], "y1": pts[1], "x2": pts[2], "y2": pts[3], "w": th, "c": c, "dash": False})
        elif vt == "rectangle":
            canvas.box(x, y, w, h, v)
        elif vt == "arc":
            edge = child(v, "edge")
            canvas.items.append({"k": "ellipse", "x": x, "y": y, "w": w, "h": h, "lw": length(edge.get("thickness") if edge is not None else None, 0.5)})
        elif vt in ("text", "exData"):
            font = font_of(e)
            mt, mr, mb, ml = margin_of(e)
            para = para_of(e)
            lines = text_lines(e, it.get("text"), font, para, w - ml - mr)
            canvas.text(lines, x + ml, y + mt, w - ml - mr, h - mt - mb, para)

    def field(self, e, it, x, y, w, h, canvas, part):
        name = e.get("name") or ""
        ui = child(e, "ui")
        uik = tag(ui[0]) if ui is not None and len(ui) else "textEdit"
        canvas.box(x, y, w, h, child(e, "border"))
        if uik == "button" and part is None:
            self.buttons.append({"name": name, "caption": visible_text(it.get("caption") or ""), "page": it["page"], "rect": [x, y, w, h]})
            return
        if uik == "barcode" and part is None:
            bt = child(ui[0], "type") if False else ui[0].get("type")
            self.barcodes.append({"type": bt, "page": it["page"], "rect": [x, y, w, h], "value": it.get("value")})
            return
        if uik in ("barcode", "button", "imageEdit", "signature") or SKIP_FIELD.search(name):
            return
        mt, mr, mb, ml = margin_of(e)
        cx, cy, cw, ch = x + ml, y + mt, w - ml - mr, h - mt - mb
        font = font_of(e)
        skey = re.sub(r"\.(Page\d)\[\d+\]", r".\1[0]", it["som"])
        again = self.seen.get(skey)
        cap = child(e, "caption")
        cap_text = visible_text(it.get("caption") or "") if cap is not None else ""
        if cap is not None and cap.get("presence") not in ("hidden", "invisible"):
            place = cap.get("placement", "left")
            cfont = font_of(cap, font)
            cpara = para_of(cap)
            cmt, cmr, cmb, cml = margin_of(cap)
            reserve = cap.get("reserve")
            if place in ("left", "right"):
                r = length(reserve, -1) if reserve is not None else -1
                if r < 0:
                    r = max((text_width(ln, cfont[0], cfont[1]) for ln in (cap_text or " ").split("\n")), default=0) + cml + cmr + 2
                rx = cx if place == "left" else cx + cw - r
                if cap_text.strip():
                    lines = text_lines(cap, cap_text, cfont, cpara, r - cml - cmr + 40)   # captions don't wrap unless long
                    canvas.text(lines, rx + cml, cy + cmt, r - cml - cmr, ch - cmt - cmb, cpara)
                if place == "left":
                    cx, cw = cx + r, cw - r
                else:
                    cw -= r
            else:
                r = length(reserve, -1) if reserve is not None else -1
                if r < 0:
                    r = cfont[0] * 1.2 * max(1, len(cap_text.split("\n"))) + cmt + cmb
                ry = cy if place == "top" else cy + ch - r
                if cap_text.strip():
                    lines = text_lines(cap, cap_text, cfont, cpara, cw - cml - cmr)
                    canvas.text(lines, cx + cml, ry + cmt, cw - cml - cmr, r - cmt - cmb, cpara)
                if place == "top":
                    cy, ch = cy + r, ch - r
                else:
                    ch -= r
        widget_ui = ui[0] if ui is not None and len(ui) else None
        canvas.box(cx, cy, cw, ch, child(widget_ui, "border"))
        umt, umr, umb, uml = margin_of(widget_ui) if widget_ui is not None else (0, 0, 0, 0)
        wx, wy, ww, wh = cx + uml, cy + umt, max(cw - uml - umr, 4), max(ch - umt - umb, 4)
        para = para_of(e)
        f = {"som": it["som"], "xfa": field_path(it["som"], self.name), "page": it["page"], "part": part,
             "font": round(font[0], 2), "align": para["h"], "label": re.sub(r"\s*\*\s*$|:\s*\*?$", "", cap_text.strip()).strip(), "caption_raw": cap_text}
        value_el = child(e, "value")
        if uik == "checkButton":
            size = length(widget_ui.get("size"), 10)
            bx = wx if para["h"] in ("left", "justify") else wx + (ww - size) / 2 if para["h"] == "center" else wx + ww - size
            by = wy if para["v"] == "top" else wy + (wh - size) / 2 if para["v"] == "middle" else wy + wh - size
            f.update(kind="radio" if it.get("group") else "check", rect=[bx, by, size, size],
                     shape=widget_ui.get("shape", "square"), group=it.get("group"),
                     on=str((it.get("items") or [[None, "1"]])[0][1]) if it.get("items") else "1")
            items = child(e, "items")
            if items is not None and len(items):
                f["on"] = (items[0].text or "1").strip()
            if not f["label"]:
                f["label"] = cap_text.strip()
        else:
            text_el = child(value_el, "text") if value_el is not None else None
            f.update(rect=[wx, wy, ww, wh])
            if uik == "choiceList":
                f.update(kind="select", options=[[visible_text(str(d)), str(s)] for d, s in (it.get("items") or [])])
            elif uik == "dateTimeEdit":
                pic = child(e, "format", "picture")
                f.update(kind="date", picture=(pic.text or "").strip() if pic is not None else "")
            elif uik == "numericEdit":
                pic = child(e, "format", "picture")
                dec = child(value_el, "decimal") if value_el is not None else None
                frac = int(dec.get("fracDigits", "2")) if dec is not None and dec.get("fracDigits") not in (None, "-1") else (2 if pic is not None and ".9" in (pic.text or "") else 0)
                f.update(kind="number", decimals=frac, max=int(dec.get("leadDigits")) + (frac + 1 if frac else 0) if dec is not None and dec.get("leadDigits") else None)
            else:
                multi = widget_ui is not None and widget_ui.get("multiLine") == "1"
                f.update(kind="long" if multi else "text")
                comb = child(widget_ui, "comb") if widget_ui is not None else None
                if comb is not None:
                    f["comb"] = int(comb.get("numberOfCells", "0"))
                if text_el is not None and text_el.get("maxChars"):
                    f["max"] = int(text_el.get("maxChars"))
            if it.get("value") not in (None, "") and uik != "dateTimeEdit":
                f["default"] = visible_text(str(it["value"]))
            f["ks"] = self.keystrokes(e)
        if (e.get("access") or "") in ("protected", "readOnly") and not it.get("group"):
            f["readonly_at_open"] = e.get("access")
        if again:   # the same field again on another page (a header field): one more box
            again.setdefault("more", []).append([it["page"], f["rect"]])
            return
        self.seen[skey] = f
        f["som"] = skey
        self.fields.append(f)

    def keystrokes(self, e):
        """What the old form's change script does to each key: U upper case, S SWIFT characters only, D digits,
        N digits and '.', A letters and digits, T no '~'; plus a length limit."""
        spec, limit = "", None
        for ev in e.iter():
            if tag(ev) != "event" or ev.get("activity") != "change":
                continue
            s = "".join(x.text or "" for x in ev.iter() if tag(x) == "script")
            s = re.sub(r"//[^\n]*", "", s)
            if "changeUpper" in s or "toUpperCase" in s:
                spec += "U"
            if "AlphaNumericSwift" in s:
                spec += "S"
            if "forceNumberOnly" in s or "Number.value" in s or "validateRegularExpNumeric" in s:
                spec += "D"
            if "ForceNumberAndDecimalOnly" in s:
                spec += "N"
            if "forceAlphaNumericOnly" in s:
                spec += "A"
            if "specialCharacterCheck" in s:
                spec += "T"
            m = re.search(r"lengthLimit\(\s*(\d+)\s*\)", s)
            if m:
                limit = int(m.group(1))
        return {"spec": "".join(sorted(set(spec))), **({"limit": limit} if limit else {})}


# ==================================================================================================================
# RULES, FROM THE PROBES
# ==================================================================================================================
def rules_for(section, probe, fields_by_som, parts):
    """Turns the probe results into rules on field ids:
         always            mandatory from the start (and nothing turns it off)
         req  [[t, vals]]  mandatory when trigger t has one of vals (t "answered" when vals == ["*"])
         nreq [[t, vals]]  NOT mandatory when t has one of vals (mandatory otherwise)
         open [[t, vals]]  unlocked when ...   (otherwise locked: grey, cleared)
         lock [[t, vals]]  locked when ...
         show [[t, vals]]  shown when ...      (otherwise hidden and cleared)
         hide [[t, vals]]  hidden when ...
         set  [[t, val, value]] when t becomes val, this field is set to value
       Effects on a hidden part (its picture) are stored under the part's som."""
    base = probe["base"]
    trig_id = lambda som: fields_by_som.get(som, {}).get("id") or (fields_by_som.get(som + ".group") or {}).get("id")
    rules = defaultdict(lambda: defaultdict(list))
    for som, (m, a, vis, val) in base.items():
        f = fields_by_som.get(som)
        if f and m == "error":
            rules[f["id"]]["base_mandatory"] = True
        if f and a in ("readOnly", "protected"):
            rules[f["id"]]["base_locked"] = True
    for p in probe["probes"]:
        t = trig_id(p["som"])
        if not t:
            continue
        tf = fields_by_som.get(p["som"]) or fields_by_som.get(p["som"] + ".group")
        val = "*" if tf and tf["kind"] in ("text", "long", "number", "date") else ("on" if tf and tf["kind"] == "check" else str(p["value"]))
        for som, (before, after) in p["diff"].items():
            target = fields_by_som.get(som)
            key = target["id"] if target else (som if som in parts else None)
            if key is None or key == t:
                continue
            r = rules[key]
            if before[0] != after[0] and target:
                (r["req"] if after[0] == "error" else r["nreq"]).append((t, val))
            if before[1] != after[1] and target:
                (r["open"] if after[1] == "open" else r["lock"]).append((t, val))
            if before[2] != after[2]:
                (r["show"] if after[2] == 1 else r["hide"]).append((t, val))
            if before[3] != after[3] and target and after[3] not in (None, ""):
                r["set"].append((t, val, str(after[3])))
    out = {}
    for key, r in rules.items():
        o = {}
        for k in ("req", "nreq", "open", "lock", "show", "hide"):
            if r.get(k):
                by = defaultdict(list)
                for t, v in r[k]:
                    if v not in by[t]:
                        by[t].append(v)
                o[k] = [[t, vs] for t, vs in by.items()]
        if r.get("set"):
            o["set"] = sorted({tuple(s) for s in r["set"]})
        if r.get("base_mandatory") and "req" not in o:
            o["always"] = 1
        if r.get("base_mandatory") and "req" in o:
            o["always"] = 1   # mandatory from the start, and also switched by a choice
        if r.get("base_locked"):
            o["locked_at_open"] = 1
        if o:
            out[key] = o
    return out


# ==================================================================================================================
# ALL SECTIONS
# ==================================================================================================================
def main(template_path):
    T = Template(template_path)
    out = {"forms": [], "terms": {}, "menu": None}
    used_ids = set()

    def load(s, kind):
        p = os.path.join(RAW, f"{s}.{kind}.json")
        return json.load(open(p)) if os.path.exists(p) else None

    for name in ["MainPage"] + FORMS + [t for ts in TERMS.values() for t in ts]:
        layout = load(name, "layout")
        sec = Section(T, name, layout).run()
        prefix = TITLES.get(name, ("MENU",))[0].split("-")[0] if name != "MainPage" else "MENU"
        # field ids: the readable end of the XFA path, made unique
        groups = {}
        for f in sec.fields:
            path = f["xfa"].split(".")
            if f["kind"] == "radio":
                gpath = field_path(f["group"], name).split(".")
                key = f["group"]
                if key not in groups:
                    groups[key] = {"path": gpath, "options": [], "som": f["group"]}
                groups[key]["options"].append(f)
                continue
            f["path_parts"] = path
        named = [(f, f["path_parts"]) for f in sec.fields if f["kind"] != "radio"] + [(g, g["path"]) for g in groups.values()]
        # Containers most fields sit in (subfrmLC, subfrmAPF ...) and generic names (RadioButtonList) say nothing.
        from collections import Counter
        common = Counter(p for _, parts in named for p in set(parts[:-1]))
        generic = {"radio_button_list", "button_list", "radio_list", "list", "field", "group"}
        taken = {}
        for obj, parts in named:
            words = [slug(p) for i, p in enumerate(parts) if p and not (i < len(parts) - 1 and common[p] >= 0.25 * len(named))]
            words = [w for i, w in enumerate(words) if not (w in generic and i > 0 and i == len(words) - 1)] or words
            words = [w for i, w in enumerate(words) if i == 0 or w != words[i - 1]]   # "draft_draft" -> "draft"
            words = [w for w in words if not re.fullmatch(r"page\d+", w)] or words
            for n in range(min(2, len(words)), len(words) + 1):
                cand = "_".join(words[-n:])
                if cand not in taken:
                    break
            k = 2
            while cand in taken:
                cand = f"{'_'.join(words[-len(words):])}_{k}"
                k += 1
            obj["id"] = cand
            taken[cand] = obj
        for f in sec.fields:
            f.pop("path_parts", None)
        fields = [f for f in sec.fields if f["kind"] != "radio"]
        radios = []
        for g in groups.values():
            o0 = g["options"][0]
            radios.append({"id": g["id"], "kind": "radio", "xfa": ".".join(g["path"]), "som": g["som"], "page": o0["page"], "part": o0["part"],
                           "label": "", "options": [{"on": o["on"], "label": o["label"], "rect": o["rect"], "shape": o.get("shape"), "page": o["page"]} for o in g["options"]]})
        allf = fields + radios
        by_som = {f["som"]: f for f in fields}
        by_som.update({r["som"]: r for r in radios})
        for r in radios:
            by_som[r["som"] + ".group"] = r
        probe = load(name, "probe")
        rules = rules_for(name, probe, by_som, sec.parts) if probe else {}
        for g, r in zip(groups.values(), radios):   # the option ticked when the form opens
            for o in g["options"]:
                st = (probe or {}).get("base", {}).get(o["som"])
                if st and st[3] not in (None, "", "0", 0) and str(st[3]) == str(o["on"]):
                    r["default"] = o["on"]
        for f in allf:
            if ".pageSet[" in f.get("som", "") or "#pageSet" in f.get("som", ""):
                if "*" in (f.get("caption_raw") or ""):
                    rules.setdefault(f["id"], {})["always"] = 1
            if f["id"] in rules:
                f["rules"] = rules[f["id"]]
            f.pop("som", None)
            f.pop("caption_raw", None)
        parts = []
        for som, p in sec.parts.items():
            parts.append({"som": som, "xfa": field_path(som, name), "page": p["page"], "draw": p["draw"].items, "rules": rules.get(som, {})})
        pages = [{"area": p["area"], "draw": p["draw"].items} for p in sec.pages]
        entry = {"name": name, "pages": pages, "fields": allf, "parts": parts, "buttons": sec.buttons, "barcodes": sec.barcodes}
        if name in TITLES:
            entry["code"], entry["title"] = TITLES[name]
            entry["terms"] = TERMS.get(name, [])
        if name == "MainPage":
            out["menu"] = entry
        elif name in FORMS:
            out["forms"].append(entry)
        else:
            out["terms"][name] = entry
        nreq = sum(1 for f in allf if f.get("rules", {}).get("always"))
        print(f"{name}: {len(pages)} page(s), {len(allf)} questions ({nreq} always mandatory, "
              f"{sum(1 for f in allf if f.get('rules', {}).get('req'))} mandatory-when), {len(parts)} hidden parts")
    path = os.path.join(HERE, "data", "forms.json")
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print(f"Wrote {path} ({os.path.getsize(path) // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else TEMPLATE)
