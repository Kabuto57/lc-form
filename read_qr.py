#!/usr/bin/env python3
"""READ A FORM'S QR CODE(S):   python read_qr.py scan.png            (one image with one or both codes)
                               python read_qr.py page1.jpg page2.jpg  (codes in separate images)
                               python read_qr.py scanned.txt          (text typed in by a handheld scanner,
                                                                       one code per line)

Reads the code(s), joins them when there are two (in the right order), checks the answers against the form file
(engine/validate.py), prints the result, and saves it as JSON in out/  (e.g. out/LC-01-2026-11-17T10-30.json).
Exit status: 0 = the answers can be accepted, 1 = something is wrong (the reasons are printed and saved).

Images: PNG, JPG, TIFF (every page of a multi-page TIFF is read), BMP. Scan at 300 dpi or more, in grey or black
and white. A PDF from a scanner can't be read directly: save the scan as an image, or export the page as PNG.
QR codes are read by zxing-cpp (Apache-2.0), the C++ version of Google's open-source ZXing reader.
"""
import glob
import json
import os
import re
import sys

sys.dont_write_bytecode = True

import zxingcpp                                # noqa: E402
from PIL import Image, ImageSequence           # noqa: E402

from build import load_form                    # noqa: E402
from engine.validate import check_answers      # noqa: E402

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
    """The form file in forms/ whose form code (e.g. "LC-01") matches the QR code's."""
    for path in sorted(glob.glob(os.path.join(HERE, "forms", "*.py"))):
        spec = load_form(path)
        found = re.search(r"[A-Z]+-\d+", spec.FORM.get("formCode") or "")
        if found and found.group(0) == code:
            return spec
    raise SystemExit(f'The QR code is for form "{code}", but no form file in forms/ has that form code.')


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


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1:]))
