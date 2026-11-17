#!/usr/bin/env python3
"""READ A FORM'S QR CODE(S):   python read_qr.py scan.png            (one image with one or both codes)
                               python read_qr.py page1.jpg page2.jpg  (codes in separate images)
                               python read_qr.py scanned.txt          (text typed in by a handheld scanner,
                                                                       one code per line)

Reads the code(s), joins them when there are two (in the right order), checks the answers against the form file
(check_answers, at the end of this file), prints the result, and saves it as JSON in out/  (e.g. out/LC-01-2026-11-17T10-30.json).
Exit status: 0 = the answers can be accepted, 1 = something is wrong (the reasons are printed and saved).

Images: PNG, JPG, TIFF (every page of a multi-page TIFF is read), BMP. Scan at 300 dpi or more, in grey or black
and white. A PDF from a scanner can't be read directly: save the scan as an image, or export the page as PNG.
QR codes are read by zxing-cpp (Apache-2.0), the C++ version of Google's open-source ZXing reader.
"""
import datetime
import glob
import json
import os
import re
import sys

sys.dont_write_bytecode = True

import zxingcpp                                # noqa: E402
from PIL import Image, ImageSequence           # noqa: E402

from build import load_form                    # noqa: E402
from layout import BAD_CHARS, FORMATS, active_rules, holds, is_required   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MAX_BYTES = 2 * 2329        # two version-40 QR codes: anything longer didn't come from one of these forms
Image.MAX_IMAGE_PIXELS = 200_000_000   # refuse absurdly large images (a 600 dpi A4 page is about 35 million)


def codes_in(path):
    """The text of every QR code in one file."""
    if path.lower().endswith(".txt"):
        with open(path, encoding="utf-8") as f:
            return [line.rstrip("\r\n") for line in f if line.strip()]
    texts = []
    with Image.open(path) as image:
        for page in ImageSequence.Iterator(image):
            for code in zxingcpp.read_barcodes(page.convert("L"), formats=zxingcpp.BarcodeFormat.QRCode):
                texts.append(code.text)
    return texts


def join(texts):
    """The full text from one code, or from two codes in either order. The order is the one that makes valid JSON
    (code 1 of 2 always starts the JSON). Stops with a clear message if the codes don't make a whole application."""
    texts = list(dict.fromkeys(texts))                       # the same code scanned twice counts once
    if not texts:
        raise SystemExit("No QR code found. Scan at 300 dpi or more, keep the page flat, and include the whole code.")
    if len(texts) > 2:
        raise SystemExit(f"Found {len(texts)} different QR codes; an application has one or two. Scan one form at a time.")
    for order in ([texts] if len(texts) == 1 else [texts, texts[::-1]]):
        whole = "".join(order)
        if len(whole.encode("utf-8")) > MAX_BYTES:
            raise SystemExit("The QR text is longer than two codes can hold: it didn't come from this form.")
        try:
            return json.loads(whole), len(texts)
        except ValueError:
            continue
    if len(texts) == 1:
        raise SystemExit("Found one QR code, but it is only part of an application: this form printed two codes "
                         "(\"QR code 1 of 2\" and \"2 of 2\"). Scan both.")
    raise SystemExit("The two QR codes don't belong together (they don't join into one application).")


def find_form(code):
    """The form file (*_form.py, beside this file) whose form code (e.g. "LC-01") matches the QR code's."""
    for path in sorted(glob.glob(os.path.join(HERE, "*_form.py"))):
        spec = load_form(path)
        found = re.search(r"[A-Z]+-\d+", spec.FORM.get("formCode") or "")
        if found and found.group(0) == code:
            return spec
    raise SystemExit(f'The QR code is for form "{code}", but no form file (*_form.py) beside read_qr.py has that form code.')


def main(paths):
    texts = [t for p in paths for t in codes_in(p)]
    payload, count = join(texts)
    if not isinstance(payload, dict) or "form" not in payload:
        raise SystemExit("The QR code holds JSON, but not an application from these forms.")
    spec = find_form(str(payload["form"]))
    problems, warnings = check_answers(spec.FORM, payload)
    version = re.search(r"v([\d.]+)", spec.FORM.get("formCode") or "")
    if version and str(payload.get("version")) != version.group(1):
        warnings.append(f"made with version {payload.get('version')} of the form; the form file is version {version.group(1)}")

    result = {"form": payload["form"], "version": payload.get("version"), "saved": payload.get("saved"), "codes": count,
              "accepted": not problems, "problems": problems, "warnings": warnings, "data": payload["data"]}
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    out_name = re.sub(r"[^\w.-]+", "-", f"{payload['form']}-{payload.get('saved', 'unknown')}") + ".json"
    with open(os.path.join(out_dir, out_name), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Form {payload['form']} v{payload.get('version')}, made {payload.get('saved')}, "
          f"from {count} QR code{'s' if count > 1 else ''}: {len(payload['data'])} answers.")
    for w in warnings:
        print("  WARNING:", w)
    for p in problems:
        print("  PROBLEM:", p)
    print(("ACCEPTED" if not problems else f"NOT ACCEPTED ({len(problems)} problem{'s' if len(problems) > 1 else ''})")
          + f". Saved out/{out_name}")
    return 0 if not problems else 1



# ====================================================================================================================
# RE-CHECKING THE SCANNED ANSWERS AGAINST THE FORM FILE
# ====================================================================================================================
DATE = re.compile(r"^(\d\d)/(\d\d)/(\d{4})$")


def to_date(text):
    """A DD/MM/YYYY answer as a date, or None if it isn't a real date."""
    m = DATE.match(text or "")
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        return None


def check_answers(form, payload):
    """Returns (problems, warnings): lists of plain-English sentences. No problems = the answers can be accepted."""
    problems, warnings = [], []
    data = payload.get("data")
    if not isinstance(data, dict):
        return ["the QR code has no answers (no \"data\")"], warnings
    questions = {q["id"]: q for s in form["sections"] for q in s["fields"]}
    numbers = {q["id"]: f"{si}.{qi}" for si, s in enumerate(form["sections"], 1) for qi, q in enumerate(s["fields"], 1)}

    def name(qid):
        return f'{numbers[qid]} {questions[qid]["label"]}'

    for qid in data:
        if qid not in questions:
            problems.append(f'unknown answer "{qid}" (no such question in this form)')

    for qid, q in questions.items():
        answer, kind = data.get(qid), q["kind"]
        if answer is None:
            if is_required(q, data):
                problems.append(f"{name(qid)}: mandatory, but not answered")
            continue
        rules = active_rules(q)
        if rules and not any(holds(data, r) for r in rules):
            problems.append(f"{name(qid)}: answered, but the question doesn't apply to these answers (it is locked)")
        if kind == "check":
            if answer is not True:
                problems.append(f"{name(qid)}: should be a tick (true)")
        elif kind == "checks":
            if not isinstance(answer, list) or any(a not in q["options"] for a in answer):
                problems.append(f"{name(qid)}: not a list of its options")
        elif not isinstance(answer, str):
            problems.append(f"{name(qid)}: should be text")
        elif kind in ("radio", "select"):
            if answer not in q["options"]:
                problems.append(f'{name(qid)}: "{answer}" is not one of its options')
        else:
            if q.get("max") and len(answer) > q["max"]:
                problems.append(f"{name(qid)}: {len(answer)} characters, more than its {q['max']}")
            if kind == "date":
                if not to_date(answer):
                    problems.append(f'{name(qid)}: "{answer}" is not a real DD/MM/YYYY date')
            elif q.get("format"):
                if not re.search(FORMATS[q["format"]][1], answer):
                    problems.append(f"{name(qid)}: {FORMATS[q['format']][2]}")
            elif re.search(BAD_CHARS, answer):
                problems.append(f"{name(qid)}: has characters the form doesn't allow")

    problems += checks_across(data, payload.get("saved", ""), questions, name)
    if payload.get("truncated"):
        warnings.append("shortened to fit the QR codes (the full text is only in the PDF): "
                        + ", ".join(name(k) for k in payload["truncated"] if k in questions))
    if payload.get("complete") is not True:
        warnings.append('the form itself said it was not complete ("complete": false)')
    return problems, warnings


def checks_across(data, saved, questions, name):
    """The same checks across answers as the form makes in Acrobat (acrobat_js.py, across()). Each is skipped
    when the form doesn't have those questions. "In the future" is measured from when the QR code was made."""
    out = []
    a, s, e = (to_date(data.get(k)) for k in ("application_date", "latest_shipment_date", "expiry_date"))
    made = to_date(f"{saved[8:10]}/{saved[5:7]}/{saved[0:4]}") if len(saved) >= 10 else None
    if s and e and e < s:
        out.append(f"{name('expiry_date')}: is before the latest shipment date")
    elif a and e and e < a:
        out.append(f"{name('expiry_date')}: is before the application date")
    if a and s and s < a:
        out.append(f"{name('latest_shipment_date')}: is before the application date")
    if a and made and a > made:
        out.append(f"{name('application_date')}: is after the day the QR code was made")
    amount = data.get("amount")
    if isinstance(amount, str) and re.fullmatch(r"[\d,]+(\.\d+)?", amount) and not float(amount.replace(",", "")) > 0:
        out.append(f"{name('amount')}: must be more than zero")
    if data.get("insurance_arrangement") and data.get("price_basis") in ("CIF", "CIP") and "insurance_arrangement" in questions:
        out.append(f"{name('insurance_arrangement')}: is only for FOB/CFR/FCA/CPT, but price basis is {data['price_basis']}")
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1:]))
