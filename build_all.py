"""BUILD ALL: one PDF with a main menu and every trade form, like the old smart form.

    python build_all.py          -> out/Trade-Application-Forms.pdf

Builds each form file (the same way as build.py), then joins them into one PDF:
  - page 1: the main menu (Import / Export / Loans / Guarantees). Click a form's name to go to it.
  - each form, as built on its own (questions, rules, Check form / Reset form, QR code page), plus a
    "Main menu" button on every page; the terms and conditions pages follow the LC, EBLC and OBC forms.
  - bookmarks for every form.
Each form keeps its own rules and QR code: Check form, Reset form, Generate QR Code and Print Form work on that form
only (its fields are renamed "LC.applicant_name", "BG.applicant_name" ..., and its scripts are made to match).
Needs the form files below and the 5 engine files in this folder. The terms text is in TERMS (read from the old form).
"""
import io
import warnings
import json
import os
import re
import sys
import zlib

import pikepdf
from pikepdf import Array, Dictionary, Name, String

from build import check_form, load_form
from layout import ACCENT, FORMATS, MARGIN, PAGE_HEIGHT, PAGE_WIDTH, fmt, pdf_string, safe, width, wrap
from pdf_writer import build

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "Trade-Application-Forms.pdf")

# The menu, as the old smart form grouped it: (group, [(form file, code used in field names, terms pages)]).
MENU = [
    ("Import", [("lc_form.py", "LC", "LC"), ("lc_amendment_form.py", "LCA", None)]),
    ("Export", [("eblc_form.py", "EBLC", "EBLC"), ("bill_of_exchange_eblc_form.py", "BEEBLC", None),
                ("obc_form.py", "OBC", "OBC"), ("bill_of_exchange_obc_form.py", "BEOBC", None),
                ("bill_of_exchange_form.py", "BE", None)]),
    ("Loans", [("import_financing_form.py", "DBRP", None), ("export_financing_form.py", "EXP", None)]),
    ("Guarantees", [("bg_form.py", "BG", None), ("sblc_form.py", "SBLC", None),
                    ("bg_amendment_form.py", "BGA", None), ("sblc_amendment_form.py", "SBLCA", None)]),
]
TERMS_FILE = os.path.join(HERE, "terms.json")   # {"LC": {"title": ..., "paragraphs": [...]}, ...}
W, H, M = PAGE_WIDTH, PAGE_HEIGHT, MARGIN
FUNCTIONS = ("lcRules", "lcDates", "lcPayload", "lcQrMatrix", "lcDrawQr", "lcWords")


# ==================================================================================================================
# ONE FORM'S SCRIPTS, MADE TO WORK BESIDE THE OTHERS
# ==================================================================================================================
def scoped(js, code, first, last):
    """A form's JavaScript, rewritten for the joined PDF: its fields are "CODE.name", its functions "lcRules_CODE"
    ..., Reset form clears only this form, and Generate QR Code / Print Form use this form's pages (first..last,
    0-based; the QR code page is the last)."""
    js = js.replace("getField(", 'getField("%s." + ' % code)
    js = js.replace("n = d.getNthFieldName(i);", 'n = d.getNthFieldName(i); if (n.indexOf("%s.") != 0) continue; n = n.slice(%d);' % (code, len(code) + 1))
    js = re.sub(r"\b(%s)\b" % "|".join(FUNCTIONS), lambda m: m.group(1) + "_" + code, js)
    js = js.replace("this.resetForm();", 'this.resetForm(["%s"]);' % code)
    js = js.replace("this.pageNum = this.numPages - 1;", "this.pageNum = %d;" % last)
    js = js.replace("this.print(true, 0, this.numPages - 1, false, true)", "this.print(true, %d, %d, false, true)" % (first, last))
    return js


def rewrite_scripts(pdf, code, first, last):
    """Every script in one form's PDF (document script, field events, button actions), scoped to the form. Scripts
    sit in actions (dictionaries with /JS), which can be objects of their own or inside other dictionaries."""
    seen = set()

    def visit(obj):
        if isinstance(obj, (Dictionary, pikepdf.Stream)):
            if obj.is_indirect:
                if obj.objgen in seen:
                    return
                seen.add(obj.objgen)
            if isinstance(obj, Dictionary) and Name.JS in obj:
                js = obj.JS
                text = js.read_bytes().decode("latin-1") if isinstance(js, pikepdf.Stream) else str(js)
                new = scoped(text, code, first, last)
                obj.JS = pdf.make_stream(zlib.compress(new.encode("latin-1")), Filter=Name.FlateDecode) if isinstance(js, pikepdf.Stream) else String(new)
            for key in list(obj.keys()):
                if key not in ("/Parent", "/P", "/Kids") or key == "/Kids":
                    visit(obj[key])
        elif isinstance(obj, Array):
            for item in obj:
                visit(item)

    visit(pdf.Root)
    for page in pdf.pages:
        visit(page.obj)


# ==================================================================================================================
# PAGES OF OUR OWN: THE MENU AND THE TERMS
# ==================================================================================================================
def text_op(s, x, y, size, bold=False, colour=(0, 0, 0)):
    return "BT /%s %s Tf %s rg %s %s Td (%s) Tj ET" % ("F2" if bold else "F1", fmt(size), " ".join(fmt(c) for c in colour),
                                                    fmt(x), fmt(y), pdf_string(safe(s)))


def new_page(out, ops):
    helv = Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding)
    bold = Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name("/Helvetica-Bold"), Encoding=Name.WinAnsiEncoding)
    page = pikepdf.Page(Dictionary(Type=Name.Page, MediaBox=[0, 0, W, H],
                                   Resources=Dictionary(Font=Dictionary(F1=out.make_indirect(helv), F2=out.make_indirect(bold))),
                                   Contents=out.make_stream(zlib.compress(" ".join(ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)))
    out.pages.append(page)
    return out.pages[-1]


def header(title):
    """The same header as the forms: issuer, a rule, the page title."""
    return [text_op("DEMO BANK · TRADE SERVICES", M, H - 28, 9, True), "0 G 0.8 w %s %s m %s %s l S" % (fmt(M), fmt(H - 34), fmt(W - M), fmt(H - 34)),
            text_op(title, M, H - 58, 15, True)]


def link(page, rect, target_page):
    annots = page.obj.get(Name.Annots) or Array()
    annots.append(Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=rect, Border=[0, 0, 0],
                             A=Dictionary(S=Name.GoTo, D=[target_page.obj, Name.Fit])))
    page.obj.Annots = annots


def terms_pages(out, terms):
    """The terms and conditions in two columns of small text, as many pages as they need."""
    size, lead, gap = 6.6, 7.9, 18
    col_w = (W - 2 * M - gap) / 2
    lines = []
    for p in terms["paragraphs"]:
        bold = p.isupper() and len(p) < 120
        for i, ln in enumerate(wrap(p, size, col_w)):
            lines.append((ln, bold))
        lines.append(("", False))
    pages, top, bottom = [], H - 72, 46
    per_col = int((top - bottom) / lead)
    while lines:
        ops = header(terms["title"])
        for col in range(2):
            chunk, lines = lines[:per_col], lines[per_col:]
            x = M + col * (col_w + gap)
            for k, (ln, bold) in enumerate(chunk):
                if ln:
                    ops.append(text_op(ln, x, top - k * lead, size, bold))
        pages.append(new_page(out, ops))
    return pages


# ==================================================================================================================
# JOINING
# ==================================================================================================================
def main():
    warnings.filterwarnings("ignore", message="Copying pages")   # the fields are joined by hand below
    terms = json.load(open(TERMS_FILE)) if os.path.exists(TERMS_FILE) else {}
    out = pikepdf.new()
    menu_page = new_page(out, [])
    entries, fields, recalcs, scripts, outline = [], [], [], [], []
    for group, forms in MENU:
        for file, code, terms_key in forms:
            spec = load_form(os.path.join(HERE, file))
            check_form(spec.FORM, spec.DEFAULTS, FORMATS)
            src = pikepdf.open(io.BytesIO(build(spec.FORM, spec.DEFAULTS)))
            first = len(out.pages)
            last = first + len(src.pages) - 1
            rewrite_scripts(src, code, first, last)
            # the form's fields go under one parent field named after the form ("BG" -> "BG.applicant_name")
            parent = src.make_indirect(Dictionary(T=String(code), Kids=Array()))
            for f in src.Root.AcroForm.Fields:
                f.Parent = parent
                parent.Kids.append(f)
            doc_js = src.make_indirect(src.Root.Names.JavaScript.Names[1])
            calc = [f for f in src.Root.AcroForm.Fields if str(f.T) == "__checks"]
            out.pages.extend(src.pages)
            fields.append(out.copy_foreign(parent))
            recalcs += [out.copy_foreign(c) for c in calc]
            scripts.append((f"{len(scripts):02d} {code}", out.copy_foreign(doc_js)))
            for i in range(first, last + 1):   # a "Main menu" button beside Check form / Reset form
                page = out.pages[i]
                x = W - M - 3 * 68 + 4
                page.contents_add(out.make_stream(("q %s rg %s %s 64 13 re f Q " % (" ".join(map(fmt, ACCENT)), fmt(x), fmt(H - 25)) +
                                                   text_op("Main menu", x + (64 - width("Main menu", 8)) / 2, H - 21.5, 8, False, (1, 1, 1))).encode("cp1252")))
                if Name.F1 not in page.Resources.Font:
                    page.Resources.Font.F1 = out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding))
                link(page, [x, H - 25, x + 64, H - 12], menu_page)
            title = spec.FORM["title"]
            entries.append((group, title, re.search(r"[A-Z]+-\d+", spec.FORM["formCode"]).group(0), first))
            outline.append((title, first))
            if terms_key and terms_key in terms:
                tp = terms_pages(out, terms[terms_key])
                outline.append((terms[terms_key]["title"], out.pages.index(tp[0])))

    # the menu page
    ops = header("Trade Application Forms") + [text_op("Please select the form that you require. Each form has its own Check form, QR code and Print Form buttons.", M, H - 76, 9)]
    y, links = H - 104, []
    for group in [g for g, _ in MENU]:
        ops.append(text_op(group, M, y, 12, True))
        y -= 18
        for g, title, code, page_index in entries:
            if g != group:
                continue
            lines = wrap(title, 9.5, W - 2 * M - 18 - 130)
            for k, ln in enumerate(lines):
                ops.append(text_op(ln, M + 18, y - k * 11.5, 9.5))
            ops.append(text_op(f"Form {code}  ·  page {page_index + 1}", W - M - width(f"Form {code}  ·  page {page_index + 1}", 8), y, 8, False, (0.35, 0.35, 0.35)))
            links.append(([M + 14, y - 4 - 11.5 * (len(lines) - 1), W - M, y + 11], page_index))
            y -= 17 + 11.5 * (len(lines) - 1)
        y -= 10
    ops.append(text_op("Open this PDF in Adobe Acrobat or Reader and allow JavaScript: the checks, red boxes and QR codes need it.", M, 50, 8, False, (0.35, 0.35, 0.35)))
    menu_page.obj.Contents = out.make_stream(zlib.compress(" ".join(ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)
    menu_page.obj.Resources = Dictionary(Font=Dictionary(
        F1=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding)),
        F2=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name("/Helvetica-Bold"), Encoding=Name.WinAnsiEncoding))))
    for rect, page_index in links:
        link(menu_page, rect, out.pages[page_index])

    # one AcroForm for all, every form's document script, bookmarks
    dr = Dictionary(Font=Dictionary(
        Helv=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding)),
        ZaDb=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))))
    dr.Font.Helvetica = dr.Font.Helv
    out.Root.AcroForm = out.make_indirect(Dictionary(Fields=Array(fields), DR=dr, DA=String("/Helv 0 Tf 0 g"), CO=Array(recalcs)))
    names = Array()
    for name, action in sorted(scripts):
        names.append(String(name))
        names.append(action)
    out.Root.Names = Dictionary(JavaScript=Dictionary(Names=names))
    with out.open_outline() as o:
        o.root.append(pikepdf.OutlineItem("Main menu", 0))
        for title, page_index in outline:
            o.root.append(pikepdf.OutlineItem(title, page_index))
    out.docinfo[Name.Title] = String("Trade Application Forms")
    out.Root.PageMode = Name.UseOutlines
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.save(OUT, deterministic_id=True)
    check = pikepdf.open(OUT)
    problems = check.check_pdf_syntax()
    assert not problems, problems
    tops = [str(f.T) for f in check.Root.AcroForm.Fields]
    assert len(tops) == len(set(tops)) == len(entries), tops
    os.makedirs(os.path.join(HERE, "dist"), exist_ok=True)
    with open(OUT, "rb") as src_file, open(os.path.join(HERE, "dist", "Trade-Application-Forms.pdf"), "wb") as copy:
        copy.write(src_file.read())   # a copy that is kept in the repository (out/ is not)
    print(f"Wrote out/Trade-Application-Forms.pdf: {len(check.pages)} pages, {len(entries)} forms, menu + terms pages")


if __name__ == "__main__":
    main()
