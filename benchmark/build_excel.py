"""Builds the Excel report: LC-QR-vs-AI.xlsx

    python3 build_excel.py        (any Python with openpyxl and Pillow; run make_crops.py first)

Raw counts (from score.py's results) are typed in (blue). Every rate, total, min / median / max / average and
"100% correct?" is an Excel formula (black), so the sheet recalculates if a count is corrected.
"""
import glob
import json
import os
import re
import statistics

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = "gemini-3.7-flash"
CROPS = os.path.join(HERE, "screenshots")
OUT = os.path.join(HERE, "LC-QR-vs-AI.xlsx")

ARIAL = "Arial"
F = lambda **k: Font(name=ARIAL, size=k.pop("size", 10), **k)
BLUE = F(color="0000FF")
BOLD = F(bold=True)
HEAD = F(bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor="1F2937")
SUB_FILL = PatternFill("solid", fgColor="E5E7EB")
GOOD = PatternFill("solid", fgColor="DCFCE7")
BAD = PatternFill("solid", fgColor="FEE2E2")
THIN = Border(bottom=Side(style="thin", color="D1D5DB"))
WRAP = Alignment(wrap_text=True, vertical="top")
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)


def header(ws, row, titles, widths=None):
    for i, t in enumerate(titles, 1):
        c = ws.cell(row, i, t)
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, CENTER
    ws.row_dimensions[row].height = 42
    for i, w in enumerate(widths or [], 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def title(ws, text, note):
    ws["A1"] = text
    ws["A1"].font = F(bold=True, size=16)
    ws["A2"] = note
    ws["A2"].font = F(color="4B5563")
    ws["A2"].alignment = Alignment(wrap_text=False)


def picture(ws, file, anchor, width_px):
    """Puts a picture at anchor, shown width_px wide (kept sharp: never shown larger than the file)."""
    img = XLImage(os.path.join(CROPS, file))
    scale = min(1.0, width_px / img.width)
    img.width, img.height = int(img.width * scale), int(img.height * scale)
    ws.add_image(img, anchor)
    return img.height


def rows_for(height_px, row_px=20):
    return int(height_px / row_px) + 2


def main():
    samples = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "samples", "*")))
    truth = {s: json.load(open(os.path.join(HERE, "samples", s, "truth.json"))) for s in samples}
    scores = json.load(open(os.path.join(HERE, "results", "scores.json")))
    qr, ai = scores["QR code"], scores[MODEL]
    raw = {s: json.load(open(os.path.join(HERE, "results", MODEL, s + ".json"))) for s in samples}
    crops = json.load(open(os.path.join(CROPS, "index.json")))
    fields = crops["fields"]   # per data field counts, made by make_crops.py (which can load the form file)

    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True   # Excel works out every formula when the file opens

    # ---------------------------------------------------------------- Each form (the data the rest is built on)
    ef = wb.active
    ef.title = "Each form"
    title(ef, "Each form: QR code vs AI (" + MODEL + ")", "Blue = counts from the test. Black = formulas. Accuracy = answers read exactly right / answers on the form.")
    cols = ["Form", "Filled", "Scan quality", "Answers on the form", "QR: correct", "QR: errors", "QR: accuracy", "QR: 100% correct?",
            "QR: seconds", "AI: correct", "AI: wrong answer", "AI: missed", "AI: invented", "AI: errors", "AI: accuracy",
            "AI: 100% correct?", "AI: seconds", "AI: tokens in", "AI: tokens out (incl. thinking)"]
    header(ef, 4, cols, [7, 13, 12, 11, 10, 9, 11, 11, 9, 10, 10, 9, 10, 9, 11, 11, 9, 10, 13])
    first = 5
    for i, s in enumerate(samples):
        r = first + i
        _, filled, quality = s.split("-")
        q, a, u = qr.get(s), ai[s], raw[s].get("usage", {})
        values = [s[:2], "typed" if filled == "typed" else "handwritten", quality, len(truth[s]),
                  q["correct"] if q else None, q["errors"] if q else None, None, None, q["seconds"] if q else None,
                  a["correct"], a["wrong"], a["missed"], a["invented"], None, None, None, a["seconds"],
                  u.get("promptTokenCount"), (u.get("candidatesTokenCount") or 0) + (u.get("thoughtsTokenCount") or 0)]
        for c, v in enumerate(values, 1):
            cell = ef.cell(r, c, v)
            cell.font = BLUE if c in (4, 5, 6, 9, 10, 11, 12, 13, 17, 18, 19) else F()
            cell.border = THIN
            cell.alignment = Alignment(horizontal="center")
        ef[f"G{r}"] = f'=IF(E{r}="","no QR code",E{r}/D{r})'
        ef[f"H{r}"] = f'=IF(E{r}="","-",IF(F{r}=0,"YES","no"))'
        ef[f"N{r}"] = f"=K{r}+L{r}+M{r}"
        ef[f"O{r}"] = f"=J{r}/D{r}"
        ef[f"P{r}"] = f'=IF(N{r}=0,"YES","no")'
        for c in ("G", "H", "N", "O", "P"):
            ef[f"{c}{r}"].font, ef[f"{c}{r}"].border, ef[f"{c}{r}"].alignment = F(), THIN, Alignment(horizontal="center")
        ef[f"G{r}"].number_format = ef[f"O{r}"].number_format = "0.0%"
        ef[f"I{r}"].number_format = "0.000"
        ef[f"Q{r}"].number_format = "0.0"
        ef[f"R{r}"].number_format = ef[f"S{r}"].number_format = "#,##0"
    last = first + len(samples) - 1
    t = last + 1
    ef[f"A{t}"] = "Total"
    ef[f"A{t}"].font = BOLD
    for c in "DEFJKLMN":
        ef[f"{c}{t}"] = f"=SUM({c}{first}:{c}{last})"
        ef[f"{c}{t}"].font = BOLD
    ef[f"G{t}"] = f"=E{t}/SUMPRODUCT((E{first}:E{last}<>\"\")*D{first}:D{last})"
    ef[f"O{t}"] = f"=J{t}/D{t}"
    for c in "GO":
        ef[f"{c}{t}"].number_format, ef[f"{c}{t}"].font = "0.0%", BOLD
    for c in range(1, len(cols) + 1):
        ef.cell(t, c).fill = SUB_FILL
    ef.freeze_panes = "B5"
    ef[f"A{t + 2}"] = ("QR codes exist only on forms filled on a computer (typed): a form filled by hand has no QR code. "
                       "'AI: tokens' are what Gemini reported; free tier, so no cost.")
    ef[f"A{t + 2}"].font = F(color="4B5563")
    R = lambda col: f"'Each form'!{col}{first}:{col}{last}"

    # ---------------------------------------------------------------- Summary
    sm = wb.create_sheet("Summary", 0)
    title(sm, "LC application: QR code vs AI reading", "10 fake filled-in LC applications, scanned; the answers read back by the form's QR code and by Google Gemini, compared with the true answers.")
    sm.column_dimensions["A"].width = 30
    for c in "BCDEFGHIJ":
        sm.column_dimensions[c].width = 13
    sm["A4"] = "Headline"
    sm["A4"].font = F(bold=True, size=12)
    heads = ["", "Forms read", "Forms 100% correct", "Accuracy: min", "median", "max", "Overall (all answers)",
             "Seconds per form: min", "median", "max", "average"]
    for i, h in enumerate(heads, 1):
        c = sm.cell(5, i, h)
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, CENTER
    sm.row_dimensions[5].height = 42
    sm.column_dimensions["K"].width = 13
    rows = [("QR code (typed forms only)", "E", "H", "G", "I", f"'Each form'!G{t}"),
            (f"AI: {MODEL} (all 10 forms)", "J", "P", "O", "Q", f"'Each form'!O{t}")]
    for i, (name, correct, ok, acc, sec, overall) in enumerate(rows):
        r = 6 + i
        sm.cell(r, 1, name).font = BOLD
        sm.cell(r, 2, f"=COUNT({R(correct)})")
        sm.cell(r, 3, f'=COUNTIF({R(ok)},"YES")&" of "&COUNT({R(correct)})')
        sm.cell(r, 4, f"=MIN({R(acc)})")
        sm.cell(r, 5, f"=MEDIAN({R(acc)})")
        sm.cell(r, 6, f"=MAX({R(acc)})")
        sm.cell(r, 7, f"={overall}")
        sm.cell(r, 8, f"=MIN({R(sec)})")
        sm.cell(r, 9, f"=MEDIAN({R(sec)})")
        sm.cell(r, 10, f"=MAX({R(sec)})")
        sm.cell(r, 11, f"=AVERAGE({R(sec)})")
        for c in range(2, 12):
            cell = sm.cell(r, c)
            cell.font, cell.alignment, cell.border = F(size=11), Alignment(horizontal="center"), THIN
            cell.number_format = "0.0%" if 4 <= c <= 7 else ("0.000" if i == 0 else "0.0") if c >= 8 else "General"

    sm["A9"] = "AI accuracy by form type and scan quality"
    sm["A9"].font = F(bold=True, size=12)
    for i, h in enumerate(["Filled", "Scan", "Forms", "Forms 100% correct", "Answers", "Correct", "Accuracy", "Errors", "Average seconds"], 1):
        c = sm.cell(10, i, h)
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, CENTER
    r = 11
    for filled in ("typed", "handwritten"):
        for quality in ("clean", "medium", "poor"):
            crit = f'{R("B")},"{filled}",{R("C")},"{quality}"'
            sm.cell(r, 1, filled); sm.cell(r, 2, quality)
            sm.cell(r, 3, f"=COUNTIFS({crit})")
            sm.cell(r, 4, f'=COUNTIFS({crit},{R("P")},"YES")')
            sm.cell(r, 5, f'=SUMIFS({R("D")},{crit})')
            sm.cell(r, 6, f'=SUMIFS({R("J")},{crit})')
            sm.cell(r, 7, f"=IF(E{r}=0,\"-\",F{r}/E{r})")
            sm.cell(r, 8, f'=SUMIFS({R("N")},{crit})')
            sm.cell(r, 9, f'=IF(C{r}=0,"-",SUMIFS({R("Q")},{crit})/C{r})')
            for c in range(1, 10):
                sm.cell(r, c).font, sm.cell(r, c).border = F(), THIN
                sm.cell(r, c).alignment = Alignment(horizontal="center")
            sm.cell(r, 7).number_format = "0.0%"
            sm.cell(r, 9).number_format = "0.0"
            r += 1

    sm["A18"] = "AI accuracy by data field (see the 'By field' sheet)"
    sm["A18"].font = F(bold=True, size=12)
    for i, h in enumerate(["Fields answered on at least one form", "Fields read right on every form", "Field accuracy: min", "median", "max", "average"], 1):
        c = sm.cell(19, i, h)
        c.font, c.fill, c.alignment = HEAD, HEAD_FILL, CENTER
    sm.row_dimensions[19].height = 42
    G = "'By field'!G5:G200"
    sm["A20"] = f'=COUNT({G})'
    sm["B20"] = f'=COUNTIF({G},1)'
    sm["C20"] = f"=MIN({G})"
    sm["D20"] = f"=MEDIAN({G})"
    sm["E20"] = f"=MAX({G})"
    sm["F20"] = f"=AVERAGE({G})"
    for c in "ABCDEF":
        sm[f"{c}20"].font, sm[f"{c}20"].alignment = F(size=11), Alignment(horizontal="center")
    for c in "CDEF":
        sm[f"{c}20"].number_format = "0.0%"

    findings = [
        "What this shows",
        "• QR code: every answer right on all 4 typed forms, including the poor scan and the form that needed two QR codes; about 0.04 seconds a form, on the computer, offline.",
        "• AI (Gemini 3.7 Flash): 8 of 10 forms fully right; 599 of 602 answers right (99.5%): 1 wrong option and 2 options missed, nothing invented. Typed and handwritten both read well; all 3 errors were on POOR scans, and all 3 were pick-one circles (a selected option read as another option, or not seen).",
        "• The AI gives no warning when it is wrong: a person must still check every form it reads. The QR code either reads perfectly or says it can't read the code.",
        "• AI time: 22 to 76 seconds a form (median about 31 s), plus free-tier limits (5 forms a minute, 20 a day for this model). Google sometimes answered 'model busy, try later' (3 times in this test).",
        "• Handwritten forms have no QR code, so for paper filled by hand the AI (or a person) is the only way to read them.",
        "",
        "How it was tested",
        "• 10 fake LC applications made from the real LC form (lc-form, Form LC-01). Typed = filled on a computer and printed with its QR code; handwritten = printed blank and filled by hand (handwriting fonts with random size, slant and drift).",
        "• Scans: clean = 300 dpi; medium = 200 dpi, slight tilt and blur, JPEG; poor = 150 dpi, tilt, blur, noise, uneven light, heavy JPEG. Pictures on the 'Scans' sheet.",
        "• QR: lc-form's own reader (read_qr.py). AI: Gemini 3.7 Flash (gemini-3.7-flash), one request per form with its 3 pages and the list of 108 questions, answers as JSON, temperature 0.",
        "• Scoring: an answer counts as right only if exactly the same; differences in formatting only (upper/lower case, spaces, 6/11/2026 vs 06/11/2026, 1,000.00 vs 1000.00) are not errors. All names and numbers are made up.",
        "• Limits: 10 forms is a small test; real scans (folds, stamps, signatures over boxes, real handwriting) are harder. Each AI form was read once.",
    ]
    r = 23
    for line in findings:
        sm.cell(r, 1, line).font = F(bold=True, size=12) if line in ("What this shows", "How it was tested") else F()
        sm.merge_cells(start_row=r, start_column=1, end_row=r, end_column=11)
        sm.cell(r, 1).alignment = WRAP
        sm.row_dimensions[r].height = 30 if len(line) > 140 else 16
        r += 1

    # ---------------------------------------------------------------- By field
    bf = wb.create_sheet("By field")
    title(bf, "AI accuracy by data field", "Every question that had an answer on at least one form. Blue = counts; black = formulas. Sorted worst first.")
    header(bf, 4, ["#", "Field (id)", "Question", "Kind", "AI: forms answered", "AI: correct", "AI: accuracy",
                   "AI: invented (blank on form, AI gave an answer)", "QR: forms answered", "QR: correct", "QR: accuracy"],
           [7, 26, 52, 10, 11, 10, 11, 16, 11, 10, 11])
    order = sorted((f for f in fields if f["ai"][0] or f["ai"][2]),
                   key=lambda f: (f["ai"][1] / f["ai"][0] if f["ai"][0] else 2, f["sort"]))
    for i, f in enumerate(order):
        r = 5 + i
        vals = [f["number"], f["id"], f["label"], f["kind"], f["ai"][0], f["ai"][1], None, f["ai"][2] or None,
                f["qr"][0] or None, f["qr"][1] if f["qr"][0] else None, None]
        for c, v in enumerate(vals, 1):
            cell = bf.cell(r, c, v)
            cell.font = BLUE if c in (5, 6, 8, 9, 10) else F()
            cell.border = THIN
        bf[f"G{r}"] = f'=IF(E{r}=0,"-",F{r}/E{r})'
        bf[f"K{r}"] = f'=IF(I{r}="","-",J{r}/I{r})'
        for c in "GK":
            bf[f"{c}{r}"].number_format, bf[f"{c}{r}"].font, bf[f"{c}{r}"].border = "0%", F(), THIN
        if f["ai"][1] < f["ai"][0]:
            for c in range(1, 12):
                bf.cell(r, c).fill = BAD
    bf.freeze_panes = "C5"

    # ---------------------------------------------------------------- By kind of answer
    bk = wb.create_sheet("By kind")
    title(bk, "AI accuracy by kind of answer", "Totals from the 'By field' sheet (formulas).")
    header(bk, 4, ["Kind", "What it is", "Answers", "Correct", "Accuracy"], [12, 46, 11, 11, 11])
    kinds = {"text": "one-line text (names, addresses ...)", "long": "paragraph (goods, conditions)", "date": "date",
             "radio": "pick one (circles)", "select": "drop-down", "check": "single tick box", "checks": "tick any",
             "number": "whole number", "amount": "money amount", "phone": "phone / fax", "account": "account number"}
    for i, (k, what) in enumerate(kinds.items()):
        r = 5 + i
        bk.cell(r, 1, k); bk.cell(r, 2, what)
        bk.cell(r, 3, f"=SUMIF('By field'!D:D,A{r},'By field'!E:E)")
        bk.cell(r, 4, f"=SUMIF('By field'!D:D,A{r},'By field'!F:F)")
        bk.cell(r, 5, f'=IF(C{r}=0,"-",D{r}/C{r})')
        bk.cell(r, 5).number_format = "0.0%"
        for c in range(1, 6):
            bk.cell(r, c).font, bk.cell(r, c).border = F(), THIN

    # ---------------------------------------------------------------- Errors, with pictures
    er = wb.create_sheet("AI errors")
    title(er, "Every AI error, with the scan", "Close-ups from the scanned page the AI was given, enlarged 2x. The mark is clearly visible in each.")
    header(er, 4, ["Form", "Field", "Error", "True answer", "AI read"], [16, 20, 12, 40, 40])
    r = 5
    for e in crops["errors"]:
        number = next(f["number"] for f in fields if f["id"] == e["field"])
        er.cell(r, 1, e["sample"]); er.cell(r, 2, f"{number} {e['field']}")
        er.cell(r, 3, {"wrong": "wrong answer", "missed": "missed", "invented": "invented"}[e["kind"]])
        er.cell(r, 4, json.dumps(e["true"]) if e["true"] is not None else "(blank)")
        er.cell(r, 5, json.dumps(e["read"]) if e["read"] is not None else "(nothing)")
        for c in range(1, 6):
            er.cell(r, c).font, er.cell(r, c).alignment, er.cell(r, c).fill = F(), WRAP, BAD
        er.row_dimensions[r].height = 30
        h = picture(er, e["image"][0], f"A{r + 1}", 1000)
        r += rows_for(h) + 1

    # ---------------------------------------------------------------- Scans gallery
    sc = wb.create_sheet("Scans")
    title(sc, "What the scans look like", "Each form: page 1 (left, reduced) and a close-up of sections 3 to 7 at scan resolution (right). Typed forms also show their QR code page.")
    sc.column_dimensions["A"].width = 3
    r = 4
    for s in samples:
        e = crops["samples"][s]
        _, filled, quality = s.split("-")
        res = ai[s]
        sc.cell(r, 2, f"Form {s[:2]}: {'typed' if filled == 'typed' else 'handwritten'}, {quality} scan.  "
                      f"AI: {res['correct']}/{len(truth[s])} right ({'100% correct' if res['errors'] == 0 else str(res['errors']) + ' error(s)'}), "
                      f"{res['seconds']:.0f} s." + (f"  QR: {qr[s]['correct']}/{len(truth[s])} right, {qr[s]['seconds']:.2f} s." if s in qr else "  No QR code (filled by hand)."))
        sc.cell(r, 2).font = F(bold=True, size=12)
        h1 = picture(sc, e["page1"][0], f"B{r + 1}", 450)
        h2 = picture(sc, e["closeup"][0], f"J{r + 1}", 1100)
        h = max(h1, h2)
        if "qr" in e:
            h3 = picture(sc, e["qr"][0], f"J{r + 1 + rows_for(h2)}", 520)
            h = max(h1, h2 + 20 * 2 + h3)
        r += rows_for(h) + 2

    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
