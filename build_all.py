"""BUILD ALL: one PDF with a main menu and every trade form, like the old smart form.

    python build_all.py          -> out/Trade-Application-Forms.pdf

Builds each form file (the same way as build.py), then joins them into one PDF:
  - page 1: the main menu (Import / Export / Loans / Guarantees). Click a form's name to open it.
  - each form, as built on its own (questions, rules, Check form / Reset form, QR code page), plus a
    "Main menu" button on every page.
  - bookmarks for every form.
Like the old smart form, only the chosen form is shown: every form's pages are stored as hidden page templates
(named "LC_0", "LC_1" ...), and clicking a form on the menu (or its bookmark) hides the open form and shows that one
(showForm, in the document script "00 menu"). This needs Acrobat (not the free Reader, which may not show or hide
pages) with JavaScript on; without JavaScript only the menu page is visible.
Each form keeps its own rules and QR code: Check form, Reset form, Generate QR Code and Print Form work on that form
only (its fields are renamed "LC.applicant_name", "BG.applicant_name" ..., and its scripts are made to match).
Needs the form files below (in forms/) and the engine files in this folder. No terms and conditions pages: the old form has them
but every one of its scripts keeps them hidden, so users never saw them.
"""
import io
import json
import warnings
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

# The menu, as the old smart form grouped it: (group, [(form file, code used in field names)]).
MENU = [
    ("Import", [("lc_form.py", "LC"), ("lc_amendment_form.py", "LCA")]),
    ("Export", [("eblc_form.py", "EBLC"), ("bill_of_exchange_eblc_form.py", "BEEBLC"),
                ("obc_form.py", "OBC"), ("bill_of_exchange_obc_form.py", "BEOBC"),
                ("bill_of_exchange_form.py", "BE")]),
    ("Loans", [("import_financing_form.py", "DBRP"), ("export_financing_form.py", "EXP")]),
    ("Guarantees", [("bg_form.py", "BG"), ("sblc_form.py", "SBLC"),
                    ("bg_amendment_form.py", "BGA"), ("sblc_amendment_form.py", "SBLCA")]),
]
W, H, M = PAGE_WIDTH, PAGE_HEIGHT, MARGIN
FUNCTIONS = ("lcRules", "lcDates", "lcPayload", "lcQrMatrix", "lcDrawQr", "lcWords")


# ==================================================================================================================
# ONE FORM'S SCRIPTS, MADE TO WORK BESIDE THE OTHERS
# ==================================================================================================================
def scoped(js, code):
    """A form's JavaScript, rewritten for the joined PDF: its fields are "CODE.name", its functions "lcRules_CODE"
    ..., Reset form clears only this form, and Print Form leaves out the menu page (page 0). Only one form is shown
    at a time, so the QR code page is still the last page."""
    js = js.replace("getField(", 'getField("%s." + ' % code)
    js = js.replace("n = d.getNthFieldName(i);", 'n = d.getNthFieldName(i); if (n.indexOf("%s.") != 0) continue; n = n.slice(%d);' % (code, len(code) + 1))
    js = re.sub(r"\b(%s)\b" % "|".join(FUNCTIONS), lambda m: m.group(1) + "_" + code, js)
    js = js.replace("this.resetForm();", 'this.resetForm(["%s"]);' % code)
    js = js.replace("this.print(true, 0, this.numPages - 1, false, true)", "this.print(true, 1, this.numPages - 1, false, true)")
    return js


def rewrite_scripts(pdf, code):
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
                new = scoped(text, code)
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
# PAGES OF OUR OWN: THE MENU
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


def link(page, rect, action):
    annots = page.obj.get(Name.Annots) or Array()
    annots.append(Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=rect, Border=[0, 0, 0], A=action))
    page.obj.Annots = annots


def goto(page):
    return Dictionary(S=Name.GoTo, D=[page.obj, Name.Fit])


def show(code):
    """The action that opens one form (showForm is in the document script "00 menu")."""
    return Dictionary(S=Name.JavaScript, JS=String('showForm(this, "%s");' % code))


# The document script "00 menu": hides the open form's pages and shows the chosen form's (they are page templates
# CODE_0, CODE_1 ...; showing a template adds its page at the end, so the chosen form follows the menu page).
MENU_JS = """var FORMS = __FORMS__;
function showForm(d, code) {
  var c, k;
  for (c in FORMS) if (c != code) for (k = 0; k < FORMS[c]; k++) d.getTemplate(c + "_" + k).hidden = true;
  for (k = 0; k < FORMS[code]; k++) d.getTemplate(code + "_" + k).hidden = false;
  d.pageNum = 1;
}
"""


# ==================================================================================================================
# JOINING
# ==================================================================================================================
def main():
    warnings.filterwarnings("ignore", message="Copying pages")   # the fields are joined by hand below
    out = pikepdf.new()
    menu_page = new_page(out, [])
    entries, fields, recalcs, scripts, pages_of = [], [], [], [], {}
    for group, forms in MENU:
        for file, code in forms:
            spec = load_form(file)   # from the forms folder
            check_form(spec.FORM, spec.DEFAULTS, FORMATS)
            src = pikepdf.open(io.BytesIO(build(spec.FORM, spec.DEFAULTS)))
            first = len(out.pages)
            last = first + len(src.pages) - 1
            rewrite_scripts(src, code)
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
                link(page, [x, H - 25, x + 64, H - 12], goto(menu_page))
            title = spec.FORM["title"]
            entries.append((group, title, re.search(r"[A-Z]+-\d+", spec.FORM["formCode"]).group(0), code))
            pages_of[code] = [out.pages[i].obj for i in range(first, last + 1)]

    # the menu page
    ops = header("Trade Application Forms") + [text_op("Please select the form that you require. Only that form is shown; Main menu brings you back here.", M, H - 76, 9)]
    y, links = H - 104, []
    for group in [g for g, _ in MENU]:
        ops.append(text_op(group, M, y, 12, True))
        y -= 18
        for g, title, form_code, code in entries:
            if g != group:
                continue
            lines = wrap(title, 9.5, W - 2 * M - 18 - 130)
            for k, ln in enumerate(lines):
                ops.append(text_op(ln, M + 18, y - k * 11.5, 9.5))
            ops.append(text_op(f"Form {form_code}", W - M - width(f"Form {form_code}", 8), y, 8, False, (0.35, 0.35, 0.35)))
            links.append(([M + 14, y - 4 - 11.5 * (len(lines) - 1), W - M, y + 11], code))
            y -= 17 + 11.5 * (len(lines) - 1)
        y -= 10
    ops.append(text_op("Open this PDF in Adobe Acrobat with JavaScript on: the forms open, and are checked, only with JavaScript.", M, 50, 8, False, (0.35, 0.35, 0.35)))
    menu_page.obj.Contents = out.make_stream(zlib.compress(" ".join(ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)
    menu_page.obj.Resources = Dictionary(Font=Dictionary(
        F1=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding)),
        F2=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name("/Helvetica-Bold"), Encoding=Name.WinAnsiEncoding))))
    for rect, code in links:
        link(menu_page, rect, show(code))

    # every form's pages become hidden page templates: taken out of the page list, named in /Templates
    templates = Array()
    for name, page in sorted((f"{code}_{k}", page) for code, pages in pages_of.items() for k, page in enumerate(pages)):
        templates.append(String(name))   # a name tree: names in sorted order
        templates.append(page)
    del out.pages[1:]
    for page in pages_of.values():
        for p in page:
            del p.Parent
            p.Type = Name.Template   # a hidden template's page is /Type /Template (PDF spec, "Named pages")

    # one AcroForm for all, every form's document script, bookmarks
    dr = Dictionary(Font=Dictionary(
        Helv=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding)),
        ZaDb=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))))
    dr.Font.Helvetica = dr.Font.Helv
    out.Root.AcroForm = out.make_indirect(Dictionary(Fields=Array(fields), DR=dr, DA=String("/Helv 0 Tf 0 g"), CO=Array(recalcs)))
    scripts.append(("00 menu", out.make_indirect(Dictionary(S=Name.JavaScript, JS=String(
        MENU_JS.replace("__FORMS__", json.dumps({c: len(p) for c, p in pages_of.items()})))))))
    names = Array()
    for name, action in sorted(scripts):
        names.append(String(name))
        names.append(action)
    out.Root.Names = Dictionary(JavaScript=Dictionary(Names=names), Templates=Dictionary(Names=templates))
    with out.open_outline() as o:
        o.root.append(pikepdf.OutlineItem("Main menu", 0))
        for group, title, form_code, code in entries:
            o.root.append(pikepdf.OutlineItem(title, action=show(code)))
    out.docinfo[Name.Title] = String("Trade Application Forms")
    out.Root.PageMode = Name.UseOutlines
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.save(OUT, deterministic_id=True)
    check = pikepdf.open(OUT)
    problems = check.check_pdf_syntax()
    assert not problems, problems
    tops = [str(f.T) for f in check.Root.AcroForm.Fields]
    assert len(tops) == len(set(tops)) == len(entries), tops
    assert len(check.pages) == 1 and len(check.Root.Names.Templates.Names) == 2 * sum(map(len, pages_of.values()))
    print(f"Wrote out/Trade-Application-Forms.pdf: menu page + {len(entries)} forms "
          f"({sum(map(len, pages_of.values()))} pages, hidden until chosen)")


if __name__ == "__main__":
    main()
