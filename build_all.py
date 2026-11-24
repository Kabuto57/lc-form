"""BUILD ALL: one PDF with a main menu and every trade form, like the old smart form.

    python build_all.py          -> out/Trade-Application-Forms.pdf

Builds each form file (the same way as build.py), then joins them into one PDF:
  - the main menu page (Import / Export / Loans / Guarantees) with a tick box for the Bank's terms (TERMS_TEXT).
    Click a form's name to open it; if the box is not ticked an alert asks the user to tick it first.
  - each form, as built on its own (questions, rules, Check form / Reset form, QR code page), plus a
    "Main menu" button on every page.
  - bookmarks for every form.
The menu is the ordinary page 0 and always stays; every form's pages are hidden page templates ("LC_0", "LC_1" ...).
Clicking a form on the menu (or its bookmark) copies that form's pages in after the menu with Template.spawn, and deletes
the copies of the form that was open (showForm, in the document script "00 menu"; it asks first, because the open form's
answers are cleared). The "Main menu" button and bookmark (showMenu) ask the same, then delete the form's pages and clear its
answers, so the PDF is just the menu page again (if the viewer refuses deletePages it only goes to page 0). The open form's
code is kept in the hidden field "OPEN". The tick box (field "ACCEPT") is on the menu page. Needs JavaScript on (written
for the free Acrobat Reader too, but untested there); without JavaScript only the menu page is visible. If the viewer
refuses a step, the menu shows a message with the step, the error and the viewer's name (failed(), in "00 menu").
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
# The wording beside the tick box on the menu page (change it here).
TERMS_TEXT = "I have read and agree to the Bank's terms and conditions for trade applications."
W, H, M = PAGE_WIDTH, PAGE_HEIGHT, MARGIN
FUNCTIONS = ("lcRules", "lcDates", "lcPayload", "lcQrMatrix", "lcDrawQr", "lcWords")


# ==================================================================================================================
# ONE FORM'S SCRIPTS, MADE TO WORK BESIDE THE OTHERS
# ==================================================================================================================
def scoped(js, code):
    """A form's JavaScript, rewritten for the joined PDF: its fields are "CODE.name", its functions "lcRules_CODE"
    ..., and Reset form clears only this form, and Print Form leaves out the menu (page 0). Only one form's pages follow
    the menu, so the QR code page is still the last page."""
    js = js.replace("getField(", 'getField("%s." + ' % code)
    js = js.replace("n = d.getNthFieldName(i);", 'n = d.getNthFieldName(i); if (n.indexOf("%s.") != 0) continue; n = n.slice(%d);' % (code, len(code) + 1))
    js = re.sub(r"\b(%s)\b" % "|".join(FUNCTIONS), lambda m: m.group(1) + "_" + code, js)
    js = js.replace("this.print(true, 0, this.numPages - 1, false, true)", "this.print(true, 1, this.numPages - 1, false, true)")
    js = js.replace("this.resetForm();", 'this.resetForm(["%s"]);' % code)
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


def show(code):
    """The action that opens one form (showForm is in the document script "00 menu")."""
    return Dictionary(S=Name.JavaScript, JS=String('showForm(this, "%s");' % code))


def to_menu():
    """The action of every Main menu button and the Main menu bookmark."""
    return Dictionary(S=Name.JavaScript, JS=String("showMenu(this);"))


def open_field(out, page):
    """The hidden read-only text field "OPEN": the code of the form whose pages are open (empty = none)."""
    field = out.make_indirect(Dictionary(Type=Name.Annot, Subtype=Name.Widget, FT=Name.Tx, T=String("OPEN"), V=String(""),
                                         Rect=[0, 0, 1, 1], F=2, Ff=1, P=page.obj, DA=String("/Helv 0 Tf 0 g")))
    page.obj.Annots.append(field)
    return field


def tick_box(out, page, rect):
    """The terms tick box (field "ACCEPT"): black outline, white, a tick when on; off = /Off, on = /Yes."""
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    box = "1 g 0 0 %s %s re f 0 G 0.75 w 0.375 0.375 %s %s re S " % (fmt(w), fmt(h), fmt(w - 0.75), fmt(h - 0.75))
    zapf = out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))

    def ap(body):
        return out.make_stream(body.encode("latin-1"), Type=Name.XObject, Subtype=Name.Form, BBox=[0, 0, w, h],
                               Resources=Dictionary(Font=Dictionary(ZaDb=zapf)))
    on, off = ap(box + "q 0 g BT /ZaDb %s Tf %s %s Td (4) Tj ET Q" % (fmt(h * 0.8), fmt(w * 0.15), fmt(h * 0.22))), ap(box)
    field = out.make_indirect(Dictionary(
        Type=Name.Annot, Subtype=Name.Widget, FT=Name.Btn, T=String("ACCEPT"), TU=String(TERMS_TEXT), V=Name.Off, AS=Name.Off,
        Rect=rect, F=4, P=page.obj, DA=String("/ZaDb 0 Tf 0 g"), MK=Dictionary(CA=String("4")),
        AP=Dictionary(N=Dictionary(Yes=on, Off=off), D=Dictionary(Yes=on, Off=off))))
    annots = page.obj.get(Name.Annots) or Array()
    annots.append(field)
    page.obj.Annots = annots
    return field


# The document script "00 menu". The menu is the ordinary page 0 and always stays. Each form's pages are hidden page
# templates CODE_0, CODE_1 ... showForm copies them in with Template.spawn (bRename false: the fields keep their names,
# "LC.applicant_name") after the menu page, and deletes the copies of the form that was open before. Which form is open
# is kept in the hidden read-only field "OPEN" (the form's code, or empty), so it is still right after the PDF is saved
# and opened again. showMenu asks, then deletes the open form's pages and clears its answers, so the PDF is the menu page
# again (if the viewer refuses deletePages it just goes to page 0 and the form stays). Spawn drops the click action of the
# tick boxes, radio buttons and lists (setAction cannot put it back: measured; a field-level /V action and a direct call of
# the rules both risk re-entry, "too much recursion"). The hidden __checks calculation, which spawn keeps, runs the rules
# after every change, and showForm asks for one calculation (calculateNow) once the pages are in. Going to a page (goPage) never shows an error: if the viewer refuses it inside the click it is retried
# 100 ms later, else the user just stays where they are. The free Acrobat Reader may refuse spawn or deletePages (not tested): failed() names the step.
MENU_JS = """var FORMS = __FORMS__;
var TITLES = __TITLES__;
function openForm(d) {
  var f = d.getField("OPEN");
  return f ? String(f.value) : "";
}
function showForm(d, code) {
  var step = "start";
  try {
    if (d.getField("ACCEPT").value == "Off") {
      app.alert("Please tick the box to agree to the Bank's terms and conditions before opening a form.", 3);
      return;
    }
    var was = openForm(d);
    if (was == code && d.numPages > 1) { goPage(d, 1); return; }
    step = "ask";
    if (was != "" && d.numPages > 1 && app.alert("Open " + TITLES[code] + "? The answers in " + TITLES[was] + " will be cleared.", 2, 2) != 4) return;
    step = "deletePages";
    if (d.numPages > 1) d.deletePages({nStart: 1, nEnd: d.numPages - 1});
    step = "OPEN";
    d.getField("OPEN").value = "";   // the pages are gone: the old form is not open any more, whatever happens next
    if (was != "") {
      try { d.resetForm([was]); } catch (e) { failed(e, "resetForm"); }
    }
    for (var k = 0; k < FORMS[code]; k++) {
      step = "spawn " + code + "_" + k;
      d.getTemplate(code + "_" + k).spawn({nPage: d.numPages, bRename: false, bOverlay: false});
    }
    step = "OPEN";
    d.getField("OPEN").value = code;
    // the copies lose their click action; the hidden __checks calculation still runs the rules, so ask for one calculation
    // (never call the rules here: they set fields, which fires the calculation, which calls the rules again: too much recursion)
    try { d.calculateNow(); } catch (e) {}
    goPage(d, 1);
  } catch (e) { failed(e, step); }
}
function showMenu(d) {
  var step = "main menu";
  try {
    var was = openForm(d);
    if (was != "" && d.numPages > 1) {
      if (app.alert("Go back to the main menu? The answers in " + TITLES[was] + " will be cleared.", 2, 2) != 4) return;
      try { d.deletePages({nStart: 1, nEnd: d.numPages - 1}); } catch (e) { goPage(d, 0); return; }   // viewer refuses: just go to the menu, the form stays
      d.getField("OPEN").value = "";
      try { d.resetForm([was]); } catch (e) { failed(e, "resetForm"); }
    }
    goPage(d, 0);
  } catch (e) { failed(e, step); }
}
// Going to a page is the last step and never an error: a viewer may refuse it inside the click that just added or
// deleted pages (InvalidSetError), so it is tried again a moment later; if that fails too, the user stays where they are.
var GO = {d: null, n: 0};
function goPage(d, n) {
  try { d.pageNum = n; } catch (e) {
    GO.d = d; GO.n = n;
    try { app.setTimeOut("goLater()", 100); } catch (e2) {}
  }
}
function goLater() {
  try { GO.d.pageNum = GO.n; } catch (e) {}
}
function failed(e, step) {
  var viewer = app.viewerType + " " + app.viewerVersion;
  var why = (step.indexOf("spawn") == 0 || step == "deletePages") && app.viewerType == "Reader"
    ? "The free Acrobat Reader may not let a form add or delete pages: try Adobe Acrobat Pro or Standard."
    : "This looks like a problem in the form's script: please send this message to the form's developer.";
  app.alert("This PDF viewer would not open the form (step " + step + ", " + e.name + ": " + e.message + "). Viewer: " + viewer + ". " + why, 1);
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
                link(page, [x, H - 25, x + 64, H - 12], to_menu())
                for a in page.obj.Annots:   # spawn drops GoTo links: make them JavaScript ("Next page" = pageNum += 1)
                    if a.get(Name.Subtype) == Name.Link and a.get(Name.A, {}).get(Name.S) == Name.GoTo:
                        gap = [p.objgen for p in out.pages[first:last + 1]].index(a.A.D[0].objgen) - (i - first)
                        a.A = Dictionary(S=Name.JavaScript, JS=String("this.pageNum %s= %d;" % ("+" if gap > 0 else "-", abs(gap))))
            title = spec.FORM["title"]
            entries.append((group, title, re.search(r"[A-Z]+-\d+", spec.FORM["formCode"]).group(0), code))
            pages_of[code] = [out.pages[i].obj for i in range(first, last + 1)]

    # the menu page
    ops = header("Trade Application Forms") + [text_op("Please select the form that you require. The form opens after this page; Main menu brings you back here and clears the form.", M, H - 76, 9)]
    terms = wrap(TERMS_TEXT, 9, W - 2 * M - 24)
    for k, ln in enumerate(terms):
        ops.append(text_op(ln, M + 24, H - 98 - k * 11, 9))
    box_rect = [M, H - 100, M + 12, H - 88]
    y, links = H - 128 - 11 * (len(terms) - 1), []
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
    ops.append(text_op("Open this PDF in Adobe Acrobat or Reader with JavaScript on: the forms open, and are checked, only with JavaScript.", M, 50, 8, False, (0.35, 0.35, 0.35)))
    menu_page.obj.Contents = out.make_stream(zlib.compress(" ".join(ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)
    menu_page.obj.Resources = Dictionary(Font=Dictionary(
        F1=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding)),
        F2=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name("/Helvetica-Bold"), Encoding=Name.WinAnsiEncoding))))
    for rect, code in links:
        link(menu_page, rect, show(code))
    accept = tick_box(out, menu_page, box_rect)
    opened = open_field(out, menu_page)
    assert y > 70, "menu text runs into the footer"

    # every form's pages become hidden page templates: taken out of the page list, named in /Templates
    templates = Array()
    for name, page in sorted((f"{code}_{k}", page) for code, pages in pages_of.items() for k, page in enumerate(pages)):
        templates.append(String(name))   # a name tree: names in sorted order
        templates.append(page)
    del out.pages[1:]   # the menu stays: it is the one page at open
    for page in pages_of.values():
        for p in page:
            del p.Parent
            p.Type = Name.Template   # a hidden template's page is /Type /Template (PDF spec, "Named pages")

    # one AcroForm for all, every form's document script, bookmarks
    dr = Dictionary(Font=Dictionary(
        Helv=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding)),
        ZaDb=out.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))))
    dr.Font.Helvetica = dr.Font.Helv
    out.Root.AcroForm = out.make_indirect(Dictionary(Fields=Array(fields + [accept, opened]), DR=dr, DA=String("/Helv 0 Tf 0 g"), CO=Array(recalcs)))
    scripts.append(("00 menu", out.make_indirect(Dictionary(S=Name.JavaScript, JS=String(
        MENU_JS.replace("__FORMS__", json.dumps({c: len(p) for c, p in pages_of.items()}))
        .replace("__TITLES__", json.dumps({c: t for _, t, _, c in entries})))))))
    names = Array()
    for name, action in sorted(scripts):
        names.append(String(name))
        names.append(action)
    out.Root.Names = Dictionary(JavaScript=Dictionary(Names=names), Templates=Dictionary(Names=templates))
    with out.open_outline() as o:
        o.root.append(pikepdf.OutlineItem("Main menu", action=to_menu()))
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
    assert len(tops) == len(set(tops)) == len(entries) + 2 and "ACCEPT" in tops and "OPEN" in tops, tops
    assert len(check.pages) == 1 and len(check.Root.Names.Templates.Names) == 2 * sum(map(len, pages_of.values()))
    assert Name.Pages not in check.Root.Names
    open_w = [a for a in check.pages[0].obj.Annots if str(a.get("/T")) == "OPEN"]
    assert len(open_w) == 1 and open_w[0].F == 2 and open_w[0].Ff == 1, "OPEN field wrong"
    js = next(str(x.JS) for n, x in zip(*[iter(check.Root.Names.JavaScript.Names)] * 2) if str(n) == "00 menu")
    assert "__FORMS__" not in js and "__TITLES__" not in js and "spawn" in js
    assert any(str(a.get("/T")) == "ACCEPT" for a in check.pages[0].obj.Annots), "tick box missing"
    print(f"Wrote out/Trade-Application-Forms.pdf: menu page + {len(entries)} forms "
          f"({sum(map(len, pages_of.values()))} pages, hidden until chosen)")


if __name__ == "__main__":
    main()
