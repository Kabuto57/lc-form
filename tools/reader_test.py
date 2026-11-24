"""READER TEST: one-page PDF that checks which page tricks the free Adobe Acrobat Reader allows.

    python tools/reader_test.py     -> out/Reader-Test.pdf

Open it in Acrobat Reader (JavaScript on), click "Run all tests", and read the result box. Each test is tried on its
own and reported OK or BLOCKED with the error. It decides how build_all.py's menu can work in the free Reader:
show/hide templates (fails in Reader, the control), spawn a copy, delete a spawned copy, delete an original page,
switch a layer off, hide a field, reset a field.
"""
import os
import zlib

import pikepdf
from pikepdf import Array, Dictionary, Name, String

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out", "Reader-Test.pdf")
W, H = 595, 842

JS = r"""
var d = this, r = [], n0 = d.numPages;
function t(name, f) { try { r.push("OK       " + name + (f() || "")); } catch (e) { r.push("BLOCKED  " + name + "  (" + e.name + ": " + e.message + ")"); } }
r.push("Viewer: " + app.viewerType + " " + app.viewerVersion + " (" + app.viewerVariation + ")");
t("1 hide a field", function () { d.getField("T1").display = display.hidden; d.getField("T1").display = display.visible; });
t("2 reset a field", function () { d.getField("T1").value = "x"; d.resetForm(["T1"]); });
t("3 switch a layer off/on", function () { var o = d.getOCGs(); o[0].state = false; o[0].state = true; return "  (" + o.length + " layer)"; });
t("4 spawn a template copy", function () { d.getTemplate("TPL").spawn({nPage: d.numPages, bRename: false, bOverlay: false}); return "  (pages " + n0 + " -> " + d.numPages + ")"; });
t("5 delete the spawned copy", function () { if (d.numPages == n0) throw new Error("nothing spawned"); d.deletePages(d.numPages - 1); return "  (pages now " + d.numPages + ")"; });
t("6 show a hidden template (old way)", function () { d.getTemplate("TPL").hidden = false; d.getTemplate("TPL").hidden = true; });
t("7 delete an original page", function () { d.getTemplate("TPL").spawn({nPage: d.numPages, bRename: false, bOverlay: false}); d.deletePages(0); return "  (pages now " + d.numPages + ")"; });
app.alert(r.join("\n"), 3);
"""


def stream(pdf, text):
    return pdf.make_stream(zlib.compress(text.encode("latin-1")), Filter=Name.FlateDecode)


def main():
    pdf = pikepdf.new()
    font = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding))
    ocg = pdf.make_indirect(Dictionary(Type=Name.OCG, Name=String("Test layer")))
    pdf.Root.OCProperties = Dictionary(OCGs=Array([ocg]), D=Dictionary(ON=Array([ocg]), Order=Array([ocg])))

    def page(ops, props=None):
        res = Dictionary(Font=Dictionary(F1=font))
        if props:
            res.Properties = props
        p = pikepdf.Page(Dictionary(Type=Name.Page, MediaBox=[0, 0, W, H], Resources=res, Contents=stream(pdf, ops)))
        pdf.pages.append(p)
        return pdf.pages[-1]

    def txt(s, y, size=11):
        return "BT /F1 %d Tf 50 %d Td (%s) Tj ET " % (size, y, s)

    main_page = page(txt("Reader test", 790, 18) + txt("Click the button. A box lists each test as OK or BLOCKED.", 765)
                     + txt("Send the box's text (or a screenshot) to the developer.", 748)
                     + "/OC /L1 BDC " + txt("This line is on a layer (test 3 switches it off and on).", 700) + "EMC "
                     + txt("Field for tests 1 and 2:", 660), Dictionary(L1=ocg))
    tpl = page(txt("Spawned test page (a copy of a hidden template).", 790, 14))

    btn = pdf.make_indirect(Dictionary(Type=Name.Annot, Subtype=Name.Widget, FT=Name.Btn, Ff=65536, T=String("RUN"),
                                       Rect=[50, 560, 250, 600], F=4, P=main_page.obj,
                                       MK=Dictionary(BG=[0.78, 0.06, 0.18], CA=String("Run all tests")),
                                       DA=String("/Helv 12 Tf 1 g"),
                                       A=Dictionary(S=Name.JavaScript, JS=String(JS))))
    fld = pdf.make_indirect(Dictionary(Type=Name.Annot, Subtype=Name.Widget, FT=Name.Tx, T=String("T1"),
                                       Rect=[200, 650, 400, 670], F=4, P=main_page.obj, DA=String("/Helv 10 Tf 0 g"),
                                       MK=Dictionary(BC=[0, 0, 0])))
    main_page.obj.Annots = Array([btn, fld])
    helv = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding))
    pdf.Root.AcroForm = Dictionary(Fields=Array([btn, fld]), DR=Dictionary(Font=Dictionary(Helv=helv)),
                                   DA=String("/Helv 0 Tf 0 g"), NeedAppearances=True)

    # the second page becomes a hidden template "TPL"
    t = tpl.obj
    del pdf.pages[1]
    del t.Parent
    t.Type = Name.Template
    pdf.Root.Names = Dictionary(Templates=Dictionary(Names=Array([String("TPL"), t])))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    pdf.save(OUT, deterministic_id=True)
    check = pikepdf.open(OUT)
    assert len(check.pages) == 1 and not check.check_pdf_syntax()
    print("Wrote out/Reader-Test.pdf")


if __name__ == "__main__":
    main()
