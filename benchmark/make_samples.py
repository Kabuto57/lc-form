"""Makes 10 fake, filled-in LC application scans plus their true answers.

    ../.venv/bin/python make_samples.py      -> samples/<id>/page-1..4.png, truth.json, (qr.txt)

Typed samples: the real LC PDF filled electronically (lc-form's own build), printed with its real QR code.
Handwritten samples: the blank LC PDF, filled by "hand" (handwriting fonts with random size, slant and drift).
A hand-filled form has no QR code: the code is only made when the form is filled on a computer.
Scan quality: clean (300 dpi), medium (200 dpi, slight blur and tilt, JPEG), poor (150 dpi, blur, noise, tilt,
uneven light, heavy JPEG). All names, companies and numbers are made up.
"""
import datetime
import io
import json
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont
import pikepdf
import zxingcpp

HERE = os.path.dirname(os.path.abspath(__file__))
LC = os.path.join(HERE, "..")
sys.path.insert(0, LC)
sys.path.insert(0, os.path.join(LC, "forms"))
sys.dont_write_bytecode = True
import lc_form                          # noqa: E402
from layout import Layout, active_rules, holds  # noqa: E402
from pdf_writer import build            # noqa: E402

SAMPLES = [  # id, filled by, scan quality
    ("01", "typed", "clean"), ("02", "typed", "clean"), ("03", "typed", "medium"), ("04", "typed", "poor"),
    ("05", "hand", "clean"), ("06", "hand", "clean"), ("07", "hand", "medium"), ("08", "hand", "medium"),
    ("09", "hand", "poor"), ("10", "hand", "poor"),
]
RENDER_DPI = 300
FONTS = "/System/Library/Fonts/Supplemental/"
HAND_FONTS = [FONTS + "Bradley Hand Bold.ttf", FONTS + "Chalkboard.ttc", FONTS + "ChalkboardSE.ttc"]

# ---- Fake data -------------------------------------------------------------------------------------------------
COMPANIES = ["SUNRISE ELECTRONICS PTE LTD", "ORCHID MARINE SUPPLIES PTE LTD", "TAN BROTHERS TRADING PTE LTD",
             "PACIFIC RIM FOODS PTE LTD", "LIONGATE INDUSTRIAL PTE LTD", "MERLION TEXTILES PTE LTD",
             "KALLANG PRECISION ENGINEERING PTE LTD", "EASTWIND CHEMICALS PTE LTD", "GREENLEAF AGRI PTE LTD",
             "HARBOURFRONT LOGISTICS PTE LTD"]
SUPPLIERS = ["SHENZHEN BRIGHTWAY CO LTD", "OSAKA KOGYO CO LTD", "HAMBURG MASCHINEN GMBH", "BANGKOK RICE MILLS CO LTD",
             "PENANG COMPONENTS SDN BHD", "SURABAYA TIMBER PT", "GUJARAT COTTON EXPORTS PVT LTD",
             "BUSAN STEEL CO LTD", "MELBOURNE DAIRY PTY LTD", "HO CHI MINH GARMENT JSC"]
SG_STREETS = ["21 UBI ROAD 1", "8 KAKI BUKIT AVENUE 4", "15 TUAS SOUTH STREET 3", "50 RAFFLES PLACE #20-01",
              "3 JURONG PORT ROAD", "101 CECIL STREET #12-05", "6 CHANGI SOUTH LANE", "27 WOODLANDS LOOP"]
FOREIGN = [("88 HUAQIANG NORTH ROAD", "FUTIAN DISTRICT", "SHENZHEN 518031", "CHINA"),
           ("2-4-1 NAKANOSHIMA", "KITA-KU", "OSAKA 530-0005", "JAPAN"),
           ("HAFENSTRASSE 12", "20457 HAMBURG", "GERMANY", ""), ("199 RAMA IV ROAD", "BANGKOK 10500", "THAILAND", ""),
           ("PLOT 45 BAYAN LEPAS FIZ", "11900 PENANG", "MALAYSIA", ""), ("JL RAYA RUNGKUT 18", "SURABAYA 60293", "INDONESIA", ""),
           ("12 ASHRAM ROAD", "AHMEDABAD 380009", "INDIA", ""), ("77 JUNGANG-DAERO", "JUNG-GU", "BUSAN 48939", "KOREA")]
PEOPLE = ["TAN WEI MING", "LIM SU LING", "RAJESH KUMAR", "NUR AISYAH BTE AHMAD", "CHONG KAH HOE", "SARAH NG",
          "MUHAMMAD FAIZAL", "KELLY ONG", "DAVID LEE", "PRIYA MENON"]
BANKS = [("BANK OF CHINA SHENZHEN BRANCH", "2 SHENNAN ROAD", "SHENZHEN, CHINA"), ("MUFG BANK OSAKA", "3-5-6 FUSHIMIMACHI", "OSAKA, JAPAN"),
         ("COMMERZBANK AG HAMBURG", "NESS 7-9", "HAMBURG, GERMANY"), ("BANGKOK BANK PCL", "333 SILOM ROAD", "BANGKOK, THAILAND")]
GOODS = ["500 UNITS LED DISPLAY PANELS MODEL LD-55X AS PER PROFORMA INVOICE NO PI-2026-118",
         "20 MT FROZEN CHICKEN WINGS GRADE A, PACKED IN 10KG CARTONS",
         "2 SETS CNC MILLING MACHINE MODEL HM-800 WITH STANDARD ACCESSORIES",
         "1,200 BAGS THAI JASMINE RICE 25KG EACH, CROP 2026",
         "40,000 PCS PRINTED CIRCUIT BOARDS PART NO PCB-7731-R2",
         "350 CBM KILN DRIED MERANTI TIMBER, SIZES AS PER CONTRACT 77/26",
         "18,000 METRES 100 PCT COTTON DENIM FABRIC 12OZ INDIGO",
         "150 MT HOT ROLLED STEEL COILS SPEC SS400 2.0MM X 1219MM"]
CONDITIONS = ["ALL DOCUMENTS MUST INDICATE THE DC NUMBER.", "THIRD PARTY DOCUMENTS ACCEPTABLE EXCEPT DRAFTS AND INVOICE.",
              "SHORT FORM BILL OF LADING NOT ACCEPTABLE. CHARTER PARTY B/L NOT ACCEPTABLE.",
              "A DISCREPANCY FEE OF USD 75 WILL BE DEDUCTED FROM PROCEEDS FOR EACH DISCREPANT PRESENTATION.", ""]
PORTS = ["SHENZHEN, CHINA", "OSAKA, JAPAN", "HAMBURG, GERMANY", "LAEM CHABANG, THAILAND", "PENANG, MALAYSIA",
         "SURABAYA, INDONESIA", "MUNDRA, INDIA", "BUSAN, KOREA"]


def fake_answers(rng, n):
    """One filled-in LC application that follows the form's rules (only answers the form would accept)."""
    today = datetime.date(2026, 11, 17)
    app_date = today - datetime.timedelta(days=rng.randint(0, 20))
    ship = app_date + datetime.timedelta(days=rng.randint(30, 90))
    expiry = ship + datetime.timedelta(days=rng.randint(15, 30))
    supplier, addr = SUPPLIERS[n % len(SUPPLIERS)], FOREIGN[n % len(FOREIGN)]
    bank = BANKS[n % len(BANKS)]
    d = lambda day: day.strftime("%d/%m/%Y")
    picks = {  # answers for free-text questions; anything else is chosen from its options
        "application_date": d(app_date),
        "applicant_name": COMPANIES[n], "applicant_address_1": SG_STREETS[n % len(SG_STREETS)],
        "applicant_address_2": "SINGAPORE " + str(rng.randint(100000, 829999)),
        "contact_name": PEOPLE[n], "contact_tel": f"+65 6{rng.randint(100, 999)} {rng.randint(1000, 9999)}",
        "contact_fax": f"+65 6{rng.randint(100, 999)} {rng.randint(1000, 9999)}",
        "advising_bank_name": bank[0], "advising_bank_address_1": bank[1], "advising_bank_address_2": bank[2],
        "beneficiary_name": supplier, "beneficiary_address_1": addr[0], "beneficiary_address_2": addr[1],
        "beneficiary_address_3": addr[2], "beneficiary_address_4": addr[3],
        "beneficiary_contact": rng.choice(["MR CHEN JIANHUA", "MS YUKI TANAKA", "MR KLAUS WEBER", "MS SOMCHAI P"]),
        "beneficiary_tel": f"+{rng.choice([86, 81, 49, 66, 60])} {rng.randint(10, 99)} {rng.randint(1000, 9999)} {rng.randint(1000, 9999)}",
        "amount": f"{rng.randint(12, 980)},{rng.randint(0, 999):03d}.{rng.choice(['00', '50', '25'])}",
        "tolerance_plus": str(rng.choice([5, 10])), "tolerance_minus": str(rng.choice([5, 10])),
        "price_basis_other": "EXW SHENZHEN FACTORY",
        "shipment_from_place": PORTS[n % len(PORTS)], "shipment_to_place": "SINGAPORE",
        "latest_shipment_date": d(ship), "expiry_date": d(expiry), "presentation_days": str(rng.choice([14, 21])),
        "master_dc_no": f"MDC{rng.randint(100000, 999999)}", "master_dc_issued_by": "OVERSEA BANKING CORP SINGAPORE",
        "drafts_percent": "100", "term_days": str(rng.choice([30, 60, 90])), "term_after": "BILL OF LADING DATE",
        "draft_date": d(ship + datetime.timedelta(days=60)),
        "bl_made_out_to_other": "ORDER OF SHIPPER", "bl_notify_party": COMPANIES[n] + ", SINGAPORE",
        "awb_notify_party": COMPANIES[n] + ", SINGAPORE",
        "do_originals": "1", "do_copies": "2", "insurance_cover_no": f"OC-{rng.randint(1000, 9999)}",
        "insurance_cover_with": "GREAT EASTERN GENERAL INSURANCE", "bencert_days": str(rng.choice([3, 5, 7])),
        "invoice_originals": "3", "invoice_copies": "2", "packing_list_originals": "1", "packing_list_copies": "2",
        "weight_note_originals": "1", "weight_note_copies": "1", "origin_originals": "1", "origin_copies": "1",
        "origin_country": addr[3] or addr[2], "other_documents_1": "INSPECTION CERTIFICATE ISSUED BY SGS",
        "goods_description": GOODS[n % len(GOODS)], "additional_conditions": CONDITIONS[n % len(CONDITIONS)],
        "forward_contract_no": f"FC{rng.randint(10000, 99999)}",
        "advance_payment_account": f"{rng.randint(100, 999)}-{rng.randint(100000, 999999)}-{rng.randint(0, 9)}",
        "issuance_charges_account": f"{rng.randint(100, 999)}-{rng.randint(100000, 999999)}-{rng.randint(0, 9)}",
        "authorised_person": PEOPLE[n] + ", DIRECTOR",
        "dc_no": "", "bank_code": "",   # For Bank Use Only: left blank by the customer
    }
    answers = {}
    for section in lc_form.FORM["sections"]:
        for q in section["fields"]:
            rules = active_rules(q)
            if rules and not any(holds(answers, r) for r in rules):
                continue                                    # locked: the customer can't fill it in
            required = q.get("required") or any(holds(answers, r) for r in q.get("requiredIf") or [])
            if q["id"] in ("dc_no", "bank_code"):
                continue
            kind = q["kind"]
            if kind == "check":
                if required or rng.random() < 0.45:
                    answers[q["id"]] = True
            elif kind in ("radio", "select"):
                if required or rng.random() < 0.6:
                    options = q["options"]
                    if q["id"] == "price_basis":
                        options = [o for o in options if o != "Others"] if rng.random() < 0.8 else options
                    answers[q["id"]] = rng.choice(options)
            elif kind == "checks":
                if required or rng.random() < 0.5:
                    answers[q["id"]] = sorted(rng.sample(q["options"], rng.randint(1, len(q["options"]))), key=q["options"].index)
            else:
                value = picks.get(q["id"])
                if value and (required or rng.random() < 0.7):
                    answers[q["id"]] = value
    return answers


# ---- The QR code (the same text the form's own "Generate QR Code" button makes) ---------------------------------
def qr_text(answers):
    payload = {"form": "LC-01", "version": "1.0", "saved": "2026-11-17T10:30", "complete": True, "data": answers}
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Like the form: padded with spaces to one code (2,300 characters) or two (4,600), cut into codes of 2,300.
    text = text.ljust(2300 if len(text) <= 2300 else 4600)
    return [text[i:i + 2300] for i in range(0, len(text), 2300)]


def qr_image(text, size_px):
    # version 40, error correction M: the same kind of code the form's own button draws
    code = zxingcpp.create_barcode(text, zxingcpp.BarcodeFormat.QRCode, ec_level="M", version=40)
    view = memoryview(zxingcpp.write_barcode_to_image(code, scale=1, add_quiet_zones=False))
    return Image.frombytes("L", (view.shape[1], view.shape[0]), view.tobytes()).resize((size_px, size_px), Image.NEAREST)


# ---- Drawing handwriting on the blank form ---------------------------------------------------------------------
def widgets(pdf_bytes):
    """Every widget: (page, field name, rect in PDF points, appearance state names)."""
    out = []
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    for p, page in enumerate(pdf.pages):
        for a in page.get("/Annots", []):
            if a.get("/Subtype") != "/Widget":
                continue
            parent = a.get("/Parent")
            name = str(a.get("/T") or (parent.get("/T") if parent is not None else ""))
            states = [str(k)[1:] for k in a.AP.N.keys()] if "/AP" in a and isinstance(a.AP.get("/N"), pikepdf.Dictionary) else []
            out.append((p, name, [float(x) for x in a.Rect], states, int(a.get("/F", 0))))
    return out


def to_px(rect, scale, page_h):
    x1, y1, x2, y2 = rect
    return x1 * scale, (page_h - y2) * scale, x2 * scale, (page_h - y1) * scale


def hand_text(img, box, text, rng, font_path, multiline=False):
    """Writes text in a box like a person would: varying size, slant, baseline drift; mostly block capitals."""
    x1, y1, x2, y2 = box
    h = y2 - y1
    size = int(min(h * 0.72, 42) * rng.uniform(0.85, 1.1)) if not multiline else int(rng.uniform(30, 38))
    font = ImageFont.truetype(font_path, size)
    lines = [text]
    if multiline or font.getlength(text) > (x2 - x1) - 20:
        words, lines, line = text.split(), [], ""
        for w in words:
            if font.getlength(line + " " + w) > (x2 - x1) - 30 and line:
                lines.append(line); line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        if not multiline:   # a person squeezes a long answer into one line: smaller writing
            while font.getlength(text) > (x2 - x1) - 20 and size > 14:
                size -= 2; font = ImageFont.truetype(font_path, size)
            lines = [text]
    layer = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(layer)
    y = y1 + (h - size * 1.1) / 2 if not multiline else y1 + 10
    for line in lines:
        x = x1 + rng.uniform(6, 18)
        for ch in line:   # letter by letter, each a little off
            draw.text((x, y + rng.uniform(-2.5, 2.5)), ch, font=font, fill=255)
            x += font.getlength(ch) * rng.uniform(0.95, 1.08)
        y += size * 1.25
    angle = rng.uniform(-1.2, 1.2)
    layer = layer.rotate(angle, center=((x1 + x2) / 2, (y1 + y2) / 2), resample=Image.BICUBIC)
    ink = Image.new("RGB", img.size, rng.choice([(20, 30, 120), (15, 15, 25), (25, 40, 140)]))   # blue or black pen
    img.paste(ink, (0, 0), layer)


def hand_mark(img, box, rng, kind):
    """A tick or cross in a tick box, or a filled/circled radio button."""
    x1, y1, x2, y2 = box
    cx, cy, r = (x1 + x2) / 2, (y1 + y2) / 2, (x2 - x1) / 2
    draw = ImageDraw.Draw(img)
    pen = rng.choice([(20, 30, 120), (15, 15, 25)])
    wd = rng.randint(4, 7)
    if kind == "radio" and rng.random() < 0.5:
        draw.ellipse([cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55], fill=pen)
    elif rng.random() < 0.5:   # a tick
        pts = [(cx - r * 0.8 + rng.uniform(-3, 3), cy), (cx - r * 0.15, cy + r * 0.8), (cx + r * 1.1, cy - r * 1.1 + rng.uniform(-3, 3))]
        draw.line(pts, fill=pen, width=wd, joint="curve")
    else:                      # a cross
        draw.line([(cx - r * 0.8, cy - r * 0.8), (cx + r * 0.8, cy + r * 0.8)], fill=pen, width=wd)
        draw.line([(cx - r * 0.8, cy + r * 0.8), (cx + r * 0.8, cy - r * 0.8)], fill=pen, width=wd)


def handwritten_pages(answers, rng):
    blank = build(lc_form.FORM, {})
    pages = render(blank)
    font_path = rng.choice(HAND_FONTS)
    questions = {q["id"]: q for s in lc_form.FORM["sections"] for q in s["fields"]}
    scale = RENDER_DPI / 72
    page_h = 841.89
    by_name = {}
    for p, name, rect, states, flags in widgets(blank):
        by_name.setdefault(name, []).append((p, rect, states, flags))
    for qid, value in answers.items():
        q = questions[qid]
        kind = q["kind"]
        if kind == "check":
            p, rect, _, _ = by_name[qid][0]
            hand_mark(pages[p], to_px(rect, scale, page_h), rng, "check")
        elif kind == "radio":
            i = q["options"].index(value)
            for p, rect, states, _ in by_name[qid]:
                if str(i) in states:
                    hand_mark(pages[p], to_px(rect, scale, page_h), rng, "radio")
        elif kind == "checks":
            for o in value:
                p, rect, _, _ = by_name[f"{qid}__{q['options'].index(o)}"][0]
                hand_mark(pages[p], to_px(rect, scale, page_h), rng, "check")
        else:
            name = f"{qid}__list" if kind == "date" else qid
            p, rect, _, _ = by_name[name][0]
            box = to_px(rect, scale, page_h)
            if kind in ("date", "select"):   # cover the printed "Pick a date" / drop-down arrow area's text
                ImageDraw.Draw(pages[p]).rectangle([box[0] + 4, box[1] + 4, box[2] - 4, box[3] - 4], fill="white")
            if kind == "date":
                day, month, year = value.split("/")
                value = rng.choice([value, f"{int(day)}/{int(month)}/{year}",
                                    f"{int(day)} {['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'][int(month)-1]} {year}"])
            hand_text(pages[p], box, value, rng, font_path, multiline=kind == "long")
    return pages


def typed_pages(answers):
    """The filled PDF as printed: each field's own saved look (what Acrobat prints) is stamped onto the page first,
    because macOS's renderer would otherwise redraw auto-size boxes itself and clip long answers."""
    pdf = pikepdf.open(io.BytesIO(build(lc_form.FORM, answers)))
    pdf.flatten_annotations("print")
    out = io.BytesIO()
    pdf.save(out)
    return render(out.getvalue())


def within_limits(answers):
    """Typed answers as the form accepts them: no longer than each box's max (the form refuses more)."""
    questions = {q["id"]: q for s in lc_form.FORM["sections"] for q in s["fields"]}
    return {k: v[: questions[k]["max"]] if isinstance(v, str) and questions[k].get("max") else v for k, v in answers.items()}


def render(pdf_bytes):
    path = os.path.join(HERE, "work", "tmp.pdf")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    prefix = os.path.join(HERE, "work", "tmp")
    subprocess.run(["swift", os.path.join(HERE, "render.swift"), path, prefix, str(RENDER_DPI)], check=True, capture_output=True)
    pages = []
    for i in range(1, 5):
        with Image.open(f"{prefix}-{i}.png") as im:
            pages.append(im.convert("RGB"))
    return pages


# ---- Scanning ---------------------------------------------------------------------------------------------------
def scan(img, quality, rng):
    """What a scanner or phone gives back: lower resolution, tilt, blur, noise, uneven light, JPEG."""
    if quality == "clean":
        return img.convert("L").convert("RGB"), 300
    dpi, blur, tilt, noise, jpeg = ((200, 0.6, 0.6, 6, 70) if quality == "medium" else (150, 1.1, 1.8, 16, 30))
    img = img.convert("L")
    img = img.rotate(rng.uniform(-tilt, tilt), resample=Image.BICUBIC, fillcolor=255, expand=False)
    img = img.resize((int(img.width * dpi / RENDER_DPI), int(img.height * dpi / RENDER_DPI)), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(blur))
    w, h = img.size
    light = Image.linear_gradient("L").resize((w, h)).point(lambda v: 255 - int(v * (0.25 if quality == "poor" else 0.08)))
    img = ImageChops.multiply(img, light)                                   # uneven light: darker towards the bottom
    img = Image.blend(img, Image.effect_noise((w, h), noise), 0.06 if quality == "medium" else 0.14)   # sensor noise
    out = io.BytesIO()
    img.save(out, "JPEG", quality=jpeg)
    return Image.open(io.BytesIO(out.getvalue())).convert("RGB"), dpi


def qr_slot():
    layout = Layout(lc_form.FORM, {}, {})
    layout.draw()
    return layout.qr["slots"]


QR_SLOTS = None
ONLY = sys.argv[1:]   # e.g. "typed": remake only those samples


def main():
    global QR_SLOTS
    QR_SLOTS = qr_slot()
    rng = random.Random(2026)
    os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    for n, (sid, filled_by, quality) in enumerate(SAMPLES):
        answers = fake_answers(random.Random(1000 + n), n)
        if filled_by == "typed":
            answers = within_limits(answers)
        if ONLY and filled_by not in ONLY:
            continue
        folder = os.path.join(HERE, "samples", f"{sid}-{filled_by}-{quality}")
        os.makedirs(folder, exist_ok=True)
        pages = typed_pages(answers) if filled_by == "typed" else handwritten_pages(answers, random.Random(2000 + n))
        has_qr = False
        if filled_by == "typed":
            codes = qr_text(answers)
            for (x, y, size), text in zip(QR_SLOTS, codes):   # the QR frames on the last page, as the form draws them
                box = to_px([x, y, x + size, y + size], RENDER_DPI / 72, 841.89)
                pages[3].paste(qr_image(text, int(box[2] - box[0])).convert("RGB"), (int(box[0]), int(box[1])))
            with open(os.path.join(folder, "qr.txt"), "w") as f:
                f.write("".join(codes))
            has_qr = len(codes)
        for i, page in enumerate(pages, 1):
            scanned, dpi = scan(page, quality, rng)
            scanned.save(os.path.join(folder, f"page-{i}.jpg"), "JPEG", quality=92, dpi=(dpi, dpi))
        with open(os.path.join(folder, "truth.json"), "w") as f:
            json.dump(answers, f, indent=1, ensure_ascii=False)
        print(folder, len(answers), "answers", f"{has_qr} QR code(s)" if has_qr else "no QR")


if __name__ == "__main__":
    main()
