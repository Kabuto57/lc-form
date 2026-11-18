"""Clear, full-resolution crops of the scans for the Excel report.

    ../.venv/bin/python make_crops.py      -> screenshots/*.png, screenshots/index.json

Per sample: page 1 (whole, reduced) and a close-up of sections 3 and 7 (applicant and beneficiary) at scan
resolution; the QR page of every typed sample; and a close-up of every AI error, enlarged 2x.
"""
import glob
import io
import json
import os
import sys

from PIL import Image
import pikepdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "forms"))
sys.dont_write_bytecode = True
import lc_form                 # noqa: E402
from pdf_writer import build   # noqa: E402

OUT = os.path.join(HERE, "screenshots")
PAGE_W, PAGE_H = 595.28, 841.89


def field_rects():
    rects = {}
    pdf = pikepdf.open(io.BytesIO(build(lc_form.FORM, {})))
    for p, page in enumerate(pdf.pages):
        for a in page.get("/Annots", []):
            parent = a.get("/Parent")
            name = str(a.get("/T") or (parent.get("/T") if parent is not None else ""))
            if int(a.get("/F", 0)) & 2:
                continue   # hidden (the calendar box behind each date)
            base = name.split("__")[0]
            rects.setdefault(base, []).append((p, [float(x) for x in a.Rect]))
    return rects


def crop(path, box_pt, out, enlarge=1.0):
    """box_pt: (x1, y1, x2, y2) in PDF points (y from the bottom)."""
    with Image.open(path) as im:
        s = im.width / PAGE_W
        x1, y1, x2, y2 = box_pt
        c = im.crop((max(0, int(x1 * s)), max(0, int((PAGE_H - y2) * s)), min(im.width, int(x2 * s)), min(im.height, int((PAGE_H - y1) * s))))
        if enlarge != 1.0:
            c = c.resize((int(c.width * enlarge), int(c.height * enlarge)), Image.LANCZOS)
        c.save(out)
        return c.size


def main():
    os.makedirs(OUT, exist_ok=True)
    rects = field_rects()
    index = {"samples": {}, "errors": []}
    for folder in sorted(glob.glob(os.path.join(HERE, "samples", "*"))):
        name = os.path.basename(folder)
        entry = {}
        with Image.open(os.path.join(folder, "page-1.jpg")) as im:
            small = im.resize((900, int(900 * im.height / im.width)), Image.LANCZOS)
            small.save(os.path.join(OUT, f"{name}-page1.png"))
            entry["page1"] = [f"{name}-page1.png", small.size]
        # sections 3 (applicant) and the top of 7 (beneficiary): applicant_name down to beneficiary_tel
        top = rects["applicant_name"][0][1][3] + 22
        bottom = rects["beneficiary_tel"][0][1][1] - 8
        entry["closeup"] = [f"{name}-closeup.png", crop(os.path.join(folder, "page-1.jpg"), (36, bottom, 560, top), os.path.join(OUT, f"{name}-closeup.png"))]
        if "typed" in name:
            entry["qr"] = [f"{name}-qr.png", crop(os.path.join(folder, "page-4.jpg"), (36, 380, 560, 800), os.path.join(OUT, f"{name}-qr.png"), 0.8)]
        index["samples"][name] = entry
    # every AI error, from the scores
    scores = json.load(open(os.path.join(HERE, "results", "scores.json")))
    for reader, by_sample in scores.items():
        if reader == "QR code":
            continue
        for sample, s in by_sample.items():
            for kind, qid, true, read in s["problems"]:
                parts = rects[qid]
                page = parts[0][0]
                x1 = min(r[0] for p, r in parts if p == page) - 40; x2 = max(r[2] for p, r in parts if p == page) + 120
                y1 = min(r[1] for p, r in parts if p == page) - 12; y2 = max(r[3] for p, r in parts if p == page) + 28
                file = f"error-{sample}-{qid}.png"
                size = crop(os.path.join(HERE, "samples", sample, f"page-{page + 1}.jpg"), (max(36, x1), y1, min(560, x2), y2), os.path.join(OUT, file), 2.0)
                index["errors"].append({"reader": reader, "sample": sample, "field": qid, "kind": kind, "true": true, "read": read,
                                        "image": [file, size]})
    # per data field: [answers on forms, read right, invented on blank] for each reader (scored by score.py's rules)
    import score as scorer
    truth = {os.path.basename(f): json.load(open(os.path.join(f, "truth.json"))) for f in glob.glob(os.path.join(HERE, "samples", "*"))}
    index["fields"] = []
    for si, section in enumerate(lc_form.FORM["sections"], 1):
        for qi, q in enumerate(section["fields"], 1):
            row = {"number": f"{si}.{qi}", "sort": [si, qi], "id": q["id"], "label": q["label"], "kind": q.get("format") or q["kind"]}
            for reader, key in (("QR code", "qr"), (None, "ai")):
                counts = [0, 0, 0]
                for name, by in scores.items():
                    if (reader and name != reader) or (not reader and name == "QR code"):
                        continue
                    for sample, sc in by.items():
                        bad = {qid: k for k, qid, _, _ in sc["problems"]}
                        if scorer.norm(q, truth[sample].get(q["id"])) is not None:
                            counts[0] += 1
                            counts[1] += q["id"] not in bad
                        elif bad.get(q["id"]) == "invented":
                            counts[2] += 1
                row[key] = counts
            index["fields"].append(row)
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump(index, f, indent=1)
    print(len(index["samples"]), "samples,", len(index["errors"]), "error crops")


if __name__ == "__main__":
    main()
