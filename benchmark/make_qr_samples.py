"""Makes 10 NEW poor-quality LC applications (numbers 21 to 30), all typed forms with the QR code. The point is to show
how the QR code survives (or not) each kind of bad copy: phone photo, tiny scan, blur, folds and punches, stains,
a torn corner, a cropped edge, a damaged fax, a faded halftone print and a shrunk, skewed scan.
    ../.venv/bin/python make_qr_samples.py            (about 3 minutes: it draws and damages every page)
    ../.venv/bin/python make_qr_samples.py readme     (only rewrites README.md, using results already measured)

Output: out/samples-qr-quality/
    LC-Poor-NN-<kind>.pdf                 4 scanned pages each
    qr-closeups/LC-Poor-NN-<kind>-qr.png  the QR area of page 4, as it arrived
    LC-Samples-21-30-answers.json         the answer key (keyed by PDF name)
    qr-check.txt, results.json            what the Python reader (zxing-cpp, as read_qr.py) finds on page 4
    README.md                             the table; it also shows web-check.json (the workbench's reader), when present
Each sample gets page-level damage on all 4 pages; the QR-specific damage is only on page 4, where the code is.
Uses make_samples.py for the filled pages, the QR code and the scanner.
"""
import io
import json
import math
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
import pikepdf
import zxingcpp

import make_samples as m

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "out", "samples-qr-quality")
SCALE = m.RENDER_DPI / 72        # PDF points -> pixels at 300 dpi
W, H = 2480, 3508                # an A4 page at 300 dpi

# sample number -> (kind, problem, what was done to the image, two codes?)
KINDS = {
    21: ("phone-photo", "Photographed with a phone",
         "Taken at an angle (keystone), a shadow across the code, uneven light, phone blur, JPEG.", True),
    22: ("scan-75dpi", "Scanned at only 75 dpi",
         "Whole page shrunk to 75 dpi: each QR square is under 2 pixels. Slight tilt, JPEG.", False),
    23: ("blurred", "Out of focus and motion blur",
         "Soft focus plus a horizontal smear (camera moved), then a medium scan.", False),
    24: ("crease-and-punch", "Folded, punched and stapled",
         "Letter folds at thirds (one runs through the code), two punch holes in the margin, a staple beside the code.", False),
    25: ("stain-and-pen", "Coffee ring and pen scribble",
         "A brown coffee ring and a pen scribble over about 6 percent of the code (2.6 percent of its pixels visibly darkened, since black squares cannot get darker).", False),
    26: ("torn-corner", "Torn corner",
         "The top-left corner of the code is torn off, taking one of the three corner squares with it.", False),
    27: ("cropped-edge", "Page shifted on the scanner",
         "The page sat 4.8 cm too far up on the glass, so the top of the code is cut off at the edge.", False),
    28: ("two-codes-fax", "Two-code form sent by fax, one code damaged",
         "Standard fax (204 x 98 dpi, black and white) and a jammed roll: a smeared band and a dirty streak across the second code.", True),
    29: ("faded-halftone", "Faded low-toner print with a halftone screen",
         "Grey, washed-out ink printed as a halftone dot pattern (moire against the scan), then a medium scan.", False),
    30: ("shrunk-and-skewed", "Printed 'fit to page' at 60 percent and scanned skewed",
         "Page shrunk to 60 percent, rotated about 6 degrees, scanned at 150 dpi.", True),
}


# ---- Page-level damage (every page) --------------------------------------------------------------------------------
def fax_header(img, page, rng):
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", int(img.width / 95))
    d.text((int(img.width * 0.03), 6), f"18/11/2026 {rng.randint(9, 17):02d}:{rng.randint(0, 59):02d}  FROM:+65 6{rng.randint(100, 999)} {rng.randint(1000, 9999)}"
           f"      TO:TRADE OPS        P.{page}/4", font=f, fill=0)


def fax(img, page, rng):
    """A standard fax: 204 dpi across, 98 dpi down, pure black and white, specks and a streak (copied from make_poor_samples)."""
    g = img.convert("L").rotate(rng.uniform(-1.5, 1.5), resample=Image.BICUBIC, fillcolor=255)
    w, h = g.size
    g = g.resize((int(w * 204 / 300), int(h * 98 / 300)), Image.BILINEAR)
    g = g.point(lambda v: 255 if v > rng.randint(150, 175) else 0).convert("1", dither=Image.NONE).convert("L")
    g = g.resize((g.width, g.height * 2), Image.NEAREST)              # each line printed twice: the blocky look
    d = ImageDraw.Draw(g)
    for _ in range(rng.randint(150, 500)):                            # dust specks
        x, y = rng.randrange(g.width), rng.randrange(g.height); r = rng.choice([0, 1, 1, 2])
        d.ellipse([x, y, x + r, y + r], fill=0)
    fax_header(g, page, rng)
    return g.convert("1"), 204


def low_dpi(img, dpi, rng):
    g = img.convert("L").rotate(rng.uniform(-1, 1), resample=Image.BICUBIC, fillcolor=255)
    g = g.resize((int(g.width * dpi / 300), int(g.height * dpi / 300)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.3))
    out = io.BytesIO(); g.save(out, "JPEG", quality=50)
    return Image.open(io.BytesIO(out.getvalue())).convert("L"), dpi


def smear(img, length):
    """Motion blur: the picture averaged with copies of itself moved a few pixels sideways."""
    acc = img
    for i in range(1, length):
        acc = Image.blend(acc, ImageChops.offset(img, i, 0), 1 / (i + 1))
    return acc


def blurred(img, rng):
    g = img.convert("L").filter(ImageFilter.GaussianBlur(1.6))
    return m.scan(smear(g, 5).convert("RGB"), "medium", rng)


def shadow(size, box, strength):
    """A soft dark band across `box` (a hand or a lamp getting in the way): white = no shadow."""
    mask = Image.new("L", size, 0)
    x0, y0, x1, y1 = box
    ImageDraw.Draw(mask).polygon([(x0 - 300, y0 + (y1 - y0) * 0.55), (x1 + 300, y0 - 100), (x1 + 300, y0 + 150), (x0 - 300, y0 + (y1 - y0) * 0.95)], fill=int(255 * strength))
    return ImageChops.invert(mask.filter(ImageFilter.GaussianBlur(70)))


def phone_photo(img, box, rng):
    """A phone photo taken from low and to one side: the page is a trapezoid on a desk, with a shadow and uneven light."""
    g = img.convert("RGB")
    g = ImageChops.multiply(g, Image.merge("RGB", [shadow(g.size, box, 0.5)] * 3))      # shadow across the code
    pad = 180
    desk = Image.new("RGB", (g.width + 2 * pad, g.height + 2 * pad), (96, 84, 72))
    desk.paste(g, (pad, pad))
    light = Image.radial_gradient("L").resize(desk.size).point(lambda v: 255 - int(v * 0.30))   # brighter on one side
    light = ImageChops.offset(light, int(desk.width * 0.25), 0)
    desk = ImageChops.multiply(desk, Image.merge("RGB", [light] * 3))
    w, h = desk.size
    # the output rectangle samples a wider strip of the desk at the top than at the bottom: the page looks keystoned
    quad = (-0.10 * w, -0.03 * h,   0.03 * w, 1.0 * h,   0.98 * w, 1.0 * h,   1.12 * w, 0.02 * h)
    out = desk.transform((int(w * 0.62), int(h * 0.62)), Image.QUAD, quad, Image.BICUBIC, fillcolor=(96, 84, 72))
    out = out.rotate(rng.uniform(-3, 3), resample=Image.BICUBIC, fillcolor=(96, 84, 72))
    out = out.filter(ImageFilter.GaussianBlur(1.0))
    out = Image.blend(out, Image.effect_noise(out.size, 12).convert("RGB"), 0.07)
    buf = io.BytesIO(); out.save(buf, "JPEG", quality=55)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB"), 185


def folds_and_punches(img, rng):
    """Letter folds at one third and two thirds of the page, and a two-hole punch in the left margin."""
    g = img.convert("L"); d = ImageDraw.Draw(g)
    for y in (H // 3, 2 * H // 3):
        d.line([(0, y - 3), (g.width, y - 3)], fill=170, width=3)     # shadow beside the crease
        d.line([(0, y), (g.width, y)], fill=255, width=4)             # the crease itself: toner cracked off
        d.line([(0, y + 4), (g.width, y + 4)], fill=190, width=2)
    for y in (H // 2 - 470, H // 2 + 470):                             # punch holes, 8 cm apart
        d.ellipse([110, y - 45, 200, y + 45], fill=45)
        d.arc([110, y - 45, 200, y + 45], 200, 340, fill=120, width=4)
    return m.scan(g.convert("RGB"), "medium", rng)


def faded_halftone(img, rng):
    """Low toner: ink only 50 to 60 percent dark, printed as a dot screen at 30 degrees (moire when scanned)."""
    g = img.convert("L").point(lambda v: int(255 - (255 - v) * rng.uniform(0.5, 0.6)))
    pitch = 4
    cell = Image.radial_gradient("L").resize((pitch, pitch), Image.BILINEAR)
    screen = Image.new("L", (int(W * 1.3), int(H * 1.3)))
    for y in range(0, screen.height, pitch):
        for x in range(0, screen.width, pitch):
            screen.paste(cell, (x, y))
    screen = screen.rotate(30, resample=Image.BILINEAR).crop((200, 200, 200 + g.width, 200 + g.height))
    dots = ImageChops.subtract(g, screen, 1, 128).point(lambda v: 255 if v > 128 else 0)   # white where the paper beats the dot
    return m.scan(dots.convert("RGB"), "medium", rng)


def shrunk_and_skewed(img, rng):
    """'Fit to page' at 60 percent (small page in the middle of a white sheet), crooked on the glass, scanned at 150 dpi."""
    small = img.resize((int(img.width * 0.6), int(img.height * 0.6)), Image.LANCZOS)
    sheet = Image.new("RGB", img.size, (255, 255, 255))
    sheet.paste(small, ((img.width - small.width) // 2, (img.height - small.height) // 2))
    g = sheet.convert("L").rotate(6, resample=Image.BICUBIC, fillcolor=255)
    g = g.resize((g.width // 2, g.height // 2), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.5))   # 150 dpi
    g = Image.blend(g, Image.effect_noise(g.size, 14), 0.06)
    buf = io.BytesIO(); g.save(buf, "JPEG", quality=60)
    return Image.open(io.BytesIO(buf.getvalue())).convert("L"), 150


# ---- QR-specific damage (page 4 only; boxes are the code(s) in pixels) -----------------------------------------------
def staple(img, box):
    """A staple beside the code, overlapping its left edge a little."""
    x0, y0, x1, y1 = box
    layer = Image.new("L", (160, 60), 255)
    d = ImageDraw.Draw(layer)
    d.rectangle([20, 22, 140, 36], fill=50)                          # the bar
    d.rectangle([20, 18, 30, 42], fill=20); d.rectangle([130, 18, 140, 42], fill=20)   # the two legs
    layer = layer.rotate(30, expand=True, fillcolor=255)
    img.paste(ImageChops.multiply(img.crop((x0 - 10, y0 + 300, x0 - 10 + layer.width, y0 + 300 + layer.height)), layer.convert(img.mode)), (x0 - 10, y0 + 300))


def stain_and_pen(img, box, rng):
    x0, y0, x1, y1 = box; s = x1 - x0
    # coffee ring: a wobbly brown ring with a faint tint inside, multiplied onto the page
    cx, cy, r = x0 + int(s * 0.62), y0 + int(s * 0.38), 230
    ring, tint = Image.new("L", img.size, 0), Image.new("L", img.size, 0)
    pts = [(cx + r * (1 + rng.uniform(-0.04, 0.04)) * math.cos(a / 40 * 2 * math.pi), cy + r * (1 + rng.uniform(-0.04, 0.04)) * math.sin(a / 40 * 2 * math.pi)) for a in range(41)]
    ImageDraw.Draw(ring).line(pts, fill=215, width=34, joint="curve")
    ImageDraw.Draw(tint).ellipse([cx - r, cy - r, cx + r, cy + r], fill=45)
    mask = ImageChops.lighter(ring.filter(ImageFilter.GaussianBlur(5)), tint.filter(ImageFilter.GaussianBlur(9)))
    img = ImageChops.multiply(img.convert("RGB"), Image.composite(Image.new("RGB", img.size, (140, 98, 60)), Image.new("RGB", img.size, (255, 255, 255)), mask))
    # pen scribble: a random walk of black ink in a box near the bottom right of the code
    d = ImageDraw.Draw(img); sx, sy = x0 + int(s * 0.62), y0 + int(s * 0.70); p = (sx, sy)
    for _ in range(90):
        q = (min(max(p[0] + rng.randint(-110, 110), sx - 120), sx + 190), min(max(p[1] + rng.randint(-90, 90), sy - 90), sy + 150))
        d.line([p, q], fill=(25, 25, 40), width=9); p = q
    return img


def torn_corner(img, box, rng):
    """The top-left corner of the code is gone: a ragged tear takes the corner square with it."""
    x0, y0 = box[0], box[1]
    edge = [(x0 - 80 + (340 * i / 14), y0 + 260 - (340 * i / 14) + rng.randint(-14, 14)) for i in range(15)]
    d = ImageDraw.Draw(img)
    d.polygon([(x0 - 80, y0 - 80)] + edge, fill=(250, 250, 250))      # missing paper: the scanner lid shows
    d.line(edge, fill=(190, 190, 190), width=3)                      # the torn edge's shadow
    return img


def fax_jam(img, box, rng):
    """A jammed fax roll: one line repeated down a band across the code, and a dirty-roller streak beside it."""
    x0, y0, x1, y1 = box
    yc = y0 + int((y1 - y0) * 0.42)
    row = img.crop((x0 - 40, yc, x1 + 40, yc + 1)).resize((x1 - x0 + 80, 160), Image.NEAREST)
    img.paste(row, (x0 - 40, yc))
    ImageDraw.Draw(img).rectangle([x0 + int((x1 - x0) * 0.2), y0 - 30, x0 + int((x1 - x0) * 0.2) + 90, y1 + 30], fill=(0, 0, 0))
    return img


# ---- Putting a sample together ------------------------------------------------------------------------------------------
def make_answers(n):
    """Fake answers for sample n. Samples with two codes get a long goods description (the form allows 6,500 characters)."""
    a = m.fake_answers(random.Random(5000 + n), n - 21)                 # n - 21: the company, person, ... lists hold 10
    if KINDS[n][3]:
        extra = " ".join(m.GOODS[:5]) + " " + " ".join(m.CONDITIONS)
        a["goods_description"] = (a["goods_description"] + " ALSO: " + extra)
    a = m.within_limits(a)
    assert len(m.qr_text(a)) == (2 if KINDS[n][3] else 1), f"sample {n}: wrong number of QR codes"
    return a


def qr_boxes(answers):
    """Where each QR code is printed on page 4, in pixels: (left, top, right, bottom)."""
    return [tuple(int(v) for v in m.to_px([x, y, x + s, y + s], SCALE, 841.89)) for x, y, s in m.qr_slot()][: len(m.qr_text(answers))]


def build_pages(n, a):
    """The four filled pages (page 4 with the QR code(s) pasted in), and the damage that depends on the QR position."""
    pages = m.typed_pages(a)
    boxes = qr_boxes(a)
    for box, text in zip(boxes, m.qr_text(a)):
        pages[3].paste(m.qr_image(text, box[2] - box[0]).convert("RGB"), box[:2])
    return pages, boxes


def damage(n, pages, boxes, rng):
    """Returns the 4 damaged pages as (image, dpi)."""
    p4, b = pages[3].convert("RGB"), boxes[0]
    kind = KINDS[n][0]
    if kind == "torn-corner":
        p4 = torn_corner(p4, b, rng)
    elif kind == "crease-and-punch":
        staple(p4, b)
    elif kind == "stain-and-pen":
        p4 = stain_and_pen(p4, b, rng)
    elif kind == "two-codes-fax":
        p4 = fax_jam(p4, boxes[1], rng)
    pages = pages[:3] + [p4]
    shift = 0
    if kind == "cropped-edge":                                         # every page sat too high on the glass; page 4 decides how far
        shift = b[1] + int((b[3] - b[1]) * 0.15)
        pages = [cropped_edge_by(p.convert("RGB"), shift) for p in pages]
    out = []
    for i, p in enumerate(pages):
        box = b if i == 3 else (700, 900, 1900, 2200)
        if kind == "phone-photo":
            out.append(phone_photo(p, box, rng))
        elif kind == "scan-75dpi":
            out.append(low_dpi(p, 75, rng))
        elif kind == "blurred":
            out.append(blurred(p, rng))
        elif kind == "crease-and-punch":
            out.append(folds_and_punches(p, rng))
        elif kind == "two-codes-fax":
            out.append(fax(p, i + 1, rng))
        elif kind == "faded-halftone":
            out.append(faded_halftone(p, rng))
        elif kind == "shrunk-and-skewed":
            out.append(shrunk_and_skewed(p, rng))
        else:                                                         # stain, torn corner, cropped edge: an ordinary medium scan
            out.append(m.scan(p, "medium", rng))
    return out


def cropped_edge_by(img, dy):
    """The page was put on the glass too far up: the scan starts dy pixels down the page."""
    out = Image.new("RGB", img.size, (255, 255, 255))
    out.paste(img, (0, -dy))
    return out


def page4_image(pdf_path):
    """Page 4 as it is stored in the PDF (what the Bank would extract and read)."""
    with pikepdf.open(pdf_path) as pdf:
        return pikepdf.PdfImage(list(pdf.pages[3].Resources.XObject.values())[0]).as_pil_image().convert("L")


def read_codes(img):
    return [r.text for r in zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.QRCode)]


def check(texts, want, answers):
    """(codes found, answers match exactly?)"""
    try:
        joined = json.loads("".join(sorted(texts, key=lambda t: not t.startswith("{"))))
        return len(texts), joined.get("data") == answers and len(texts) == want
    except ValueError:
        return len(texts), False


def closeup(img, boxes, n, name):
    """The QR area of page 4 (all codes, with a margin) cut from the delivered page, scaled to its size."""
    sx, sy = img.width / W, img.height / H
    x0, y0 = min(b[0] for b in boxes) - 150, min(b[1] for b in boxes) - 150
    x1, y1 = max(b[2] for b in boxes) + 150, max(b[3] for b in boxes) + 150
    if KINDS[n][0] == "shrunk-and-skewed":                            # the page is 60 percent size, around the centre
        x0, y0, x1, y1 = [(v - c) * 0.6 + c for v, c in ((x0, W / 2), (y0, H / 2), (x1, W / 2), (y1, H / 2))]
        x0, y0, x1, y1 = x0 - 200, y0 - 200, x1 + 200, y1 + 200       # the 6 degree tilt moves the corners
    img.crop((max(0, int(x0 * sx)), max(0, int(y0 * sy)), min(img.width, int(x1 * sx)), min(img.height, int(y1 * sy)))).save(
        os.path.join(OUT, "qr-closeups", f"{name[:-4]}-qr.png"))


# ---- README -------------------------------------------------------------------------------------------------------------
def write_readme():
    results = json.load(open(os.path.join(OUT, "results.json")))
    web_path = os.path.join(OUT, "web-check.json")
    web = json.load(open(web_path)) if os.path.exists(web_path) else {}
    rows = []
    for n, (kind, problem, what, _) in KINDS.items():
        name = f"LC-Poor-{n:02d}-{kind}.pdf"
        r, w = results[name], web.get(name)
        py = f"{r['found']} of {r['want']} codes; " + ("answers match" if r["match"] else "answers NOT recovered")
        wb = "not run" if w is None else f"{w['found']} of {r['want']} codes; " + ("answers match" if w["match"] else "answers NOT recovered")
        rows.append(f"| {n} | {kind} | {problem} | {what} | {py} | {wb} |")
    text = ("# Poor-quality LC applications 21 to 30: how the QR code survives\n\n"
            "Ten typed LC applications (no handwriting), each with one kind of bad copy. Every sample has the same four pages as the\n"
            "samples20-poor set; the QR code is on page 4. `qr-closeups/` shows the QR area of page 4 as it arrived. The answer key is\n"
            "`LC-Samples-21-30-answers.json` (keyed by PDF name). Made by `benchmark/make_qr_samples.py` in lc-form.\n\n"
            "Results are measured, not assumed: the Python reader is zxing-cpp on page 4 as stored in the PDF (what `read_qr.py` does);\n"
            "the web reader is the workbench's `codesIn()` + `joinCodes()` (`src/qr-read.ts`) on the same page 4 image.\n"
            "\"Answers match\" means the joined JSON data equals the answer key exactly.\n\n"
            "| No. | Kind | Problem | What was done to the image | Python reader | Web reader |\n|---|---|---|---|---|---|\n"
            + "\n".join(rows) + "\n\n"
            "Samples 21, 28 and 30 carry two QR codes (a long goods description); the other seven carry one.\n")
    open(os.path.join(OUT, "README.md"), "w").write(text)


def main():
    os.makedirs(os.path.join(OUT, "qr-closeups"), exist_ok=True); os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    if sys.argv[1:] == ["readme"]:
        return write_readme()
    answers_all, results, report = {}, {}, []
    for n, (kind, *_rest) in KINDS.items():
        rng = random.Random(9100 + n)
        a = make_answers(n)
        name = f"LC-Poor-{n:02d}-{kind}.pdf"
        answers_all[name] = a
        pages, boxes = build_pages(n, a)
        done = damage(n, pages, boxes, rng)
        first, dpi = done[0]
        first.save(os.path.join(OUT, name), "PDF", resolution=dpi, **({} if first.mode == "1" else {"quality": 60}), save_all=True, append_images=[p for p, _ in done[1:]])
        img = page4_image(os.path.join(OUT, name))
        found, ok = check(read_codes(img), len(boxes), a)
        results[name] = {"found": found, "want": len(boxes), "match": ok}
        closeup(img, boxes, n, name)
        img.save(os.path.join(HERE, "work", f"{name[:-4]}-page4.png"))   # for the web reader check (not published)
        report.append(f"{name}: {found} of {len(boxes)} codes found; answers {'match the key exactly' if ok else 'NOT recovered'}")
        print(report[-1], f"({os.path.getsize(os.path.join(OUT, name)) / 1e6:.2f} MB)", flush=True)
    open(os.path.join(OUT, "qr-check.txt"), "w").write("\n".join(report) + "\n")
    json.dump(results, open(os.path.join(OUT, "results.json"), "w"), indent=1)
    json.dump(answers_all, open(os.path.join(OUT, "LC-Samples-21-30-answers.json"), "w"), indent=1, ensure_ascii=False)
    write_readme()


if __name__ == "__main__":
    main()
