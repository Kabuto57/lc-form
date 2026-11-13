#!/usr/bin/env python3
"""BUILDS THE LC APPLICATION FORM (Form LC-01) AS A FILLABLE PDF, THEN CHECKS IT.

    python build_lc.py        -> out/LC-Application.pdf  (plus out/index.html for viewing it locally)

HOW IT FITS TOGETHER

    lc.py ──────────────┐  the form: every question, its options and rules
                        ▼
    build_lc.py    STEP 1  lay out the pages ─── where every section, question and box goes
                   STEP 2  add the scripts ───── the rules engine, buttons and QR code rows
                   STEP 3  write the PDF ─────── pikepdf turns it all into a real PDF
                   CHECK   open the result and check it question by question
                        ▼
    out/LC-Application.pdf
                        │  inside the PDF, Acrobat runs:
    js/document.js      │    the rules engine (red boxes, locking, checks), the QR code's text and the QR encoder
    js/buttons.js       │    Check form, Reset form, Generate QR Code, Print Form, and the warning before save/print

CONTENTS OF THIS FILE
    1. Settings: page size, colours, sizes, answer formats      (change the look here)
    2. Text helpers: safe characters, measuring, wrapping
    3. Rules and dates: "mandatory now?", "applies now?", the date list
    4. Step 1: lay out the pages                                 (class Layout)
    5. Step 2: add the scripts, buttons and QR code rows         (add_scripts)
    6. Step 3: write the PDF                                     (class Writer)
    7. Build: run the three steps                                (build)
    8. Self-check: open the built PDF and check it               (self_check)
    9. Run: build, check, save

The only library is pikepdf (MPL-2.0). Everything else is Python's standard library.
"""
import datetime
import io
import json
import os
import re
import zlib

import pikepdf
from pikepdf import Array, Dictionary, Name, String

from lc import DEFAULTS, LC

HERE = os.path.dirname(os.path.abspath(__file__))


# ====================================================================================================================
# 1. SETTINGS: PAGE, COLOURS, SIZES, ANSWER FORMATS
# ====================================================================================================================
# The look of the form: page size, colours, sizes and spacing, and the answer formats.
#
# Every measurement is in PDF points (1 point = 1/72 inch, about 0.35 mm). Coordinates follow the PDF itself:
# x is measured from the left edge, y from the BOTTOM edge of the page.

PAGE_WIDTH = 595.28
PAGE_HEIGHT = 841.89
MARGIN = 42                 # left and right margin
BOTTOM = 39                 # start a new page when content would go below this line (the footer sits under it)

# ---- Colours (red, green, blue; each 0 to 1)
RED = (0.8, 0, 0)           # mandatory boxes and the red * markers
INK = (0, 0, 0)             # text, lines, section outlines
GREY = (0.35, 0.35, 0.35)   # footer and secondary text
RULE = (0.75, 0.75, 0.75)   # thin lines between rows, footer line
WHITE = (1, 1, 1)
ACCENT = (0, 0, 0)          # header line, question numbers, buttons (black: an official form, no brand colour)
TINT = (0.88, 0.88, 0.88)   # grey band behind each section heading
BANK_SHADE = (0.95, 0.95, 0.95)  # background of the "For Bank Use Only" section

# ---- Text sizes
LABEL = 7.5                 # question labels
TEXT = 8.5                  # answers, options and tick-box wording

# ---- Boxes and spacing
BOX = 15                    # height of a one-line answer box
COLUMNS = 12                # each section is a grid of 12 columns; a question takes as many as it needs
COLUMN_GAP = 4              # gap between grid columns
PAD = 6                     # space inside a section's outline
BAND = 13                   # height of a section's grey heading band
SECTION_GAP = 5             # gap between sections
INDENT = 14                 # follow-up questions are indented under the tick box that switches them on
SIGN_OFF = 46               # height of the signature / date / company stamp lines

# 13.2 is the only question placed by hand, to match the approved 4-page copy of the form:
# its label sits beside a fixed-width box, this far after the label.
BESIDE_GAP = 14.7

# ---- Answer formats: (keys refused while typing, what a whole answer must look like, message if it doesn't)
# The first two are regular expressions used by the form's JavaScript in Acrobat.
FORMATS = {
    "number": ("[^0-9]", r"^\d+$", "should be a whole number"),
    "amount": ("[^0-9.,]", r"^\d{1,3}(,?\d{3})*(\.\d{1,2})?$", "is not an amount"),
    "phone": ("[^0-9+() -]", r"^\+?[\d ()-]*\d[\d ()-]*$", "is not a phone number (digits, spaces, + - ( ) only)"),
    "account": ("[^0-9-]", r"^\d[\d-]*\d$|^\d$", "is not an account number (digits and - only)"),
}

# Characters SWIFT messages can't carry (plus # & @ %, used in addresses and company names): refused while typing.
BAD_CHARS = "[^A-Za-z0-9 .,\\-/()':?+#&@%\\r\\n]"

W, H, M = PAGE_WIDTH, PAGE_HEIGHT, MARGIN   # short names for the page size and margin, used below

# ====================================================================================================================
# 2. TEXT HELPERS
# ====================================================================================================================
# Text helpers: making text safe for the PDF's built-in fonts, measuring it, and wrapping it into lines.
#
# The form uses only the fonts every PDF reader has built in (Helvetica, Helvetica-Bold and ZapfDingbats), so no
# font files are embedded. Those fonts cover Western European characters (the "WinAnsi" set).


# Characters outside WinAnsi that have a plain equivalent.
PLAIN = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."}


def read_file(name):
    """A file beside this script (js/*.js or helvetica-metrics.json)."""
    encoding = "latin-1" if name.endswith(".js") else "utf-8"
    with open(os.path.join(HERE, name), encoding=encoding) as f:
        return f.read()


def safe(s):
    """Text the built-in fonts can draw: curly quotes and dashes become plain ones; anything else unknown becomes '?'."""
    return re.sub(r"[^\n\x20-\x7e\xa0-\xff€]", lambda m: PLAIN.get(m.group(0), "?"), s or "")


# Adobe's own Helvetica measurements (each character's width and kerning, per 1000 units of font size), so text is
# measured exactly as Acrobat will draw it. Used to place labels, wrap text and size boxes.
METRICS = json.loads(read_file("helvetica-metrics.json"))


def width(text, size, bold=False):
    """How wide `text` is, in points, at font size `size`."""
    m = METRICS["bold" if bold else "helv"]
    units = sum(m["widths"].get(c, 0) for c in text) + sum(m["kern"].get(text[i:i + 2], 0) for i in range(len(text) - 1))
    return units * size / 1000


def wrap(text, size, max_width):
    """Splits text into lines no wider than max_width (breaking between words)."""
    lines = []
    for paragraph in safe(text).split("\n"):
        line = ""
        for word in re.split(r"\s+", paragraph):
            longer = f"{line} {word}" if line else word
            if line and width(longer, size) > max_width:
                lines.append(line)
                line = word
            else:
                line = longer
        lines.append(line)
    return lines


def fmt(n):
    """A number written into a PDF drawing command: at most 4 decimals, no trailing zeros (12.5, not 12.5000)."""
    return ("%.4f" % n).rstrip("0").rstrip(".")


def num(n):
    """A number stored in a PDF object: whole numbers as integers, others rounded to 4 decimals."""
    return int(n) if n == int(n) else round(n, 4)


def rgb(colour):
    """A colour (r, g, b) as PDF drawing-command text, e.g. '0.8 0 0'."""
    return " ".join(map(fmt, colour))


def pdf_string(s):
    """Text inside a PDF drawing command, with ( ) and backslash escaped."""
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def js_json(value):
    """JSON exactly as JavaScript's JSON.stringify writes it (no spaces, non-ASCII kept)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

# ====================================================================================================================
# 3. RULES AND DATES
# ====================================================================================================================
# The form's rules, evaluated in Python while building (the same rules also run in Acrobat, see js/document.js).
#
# A question's rules come from lc.py:
#   required=True            always mandatory
#   requiredIf=[rule, ...]   mandatory when any of these rules holds
#   activeIf=[rule, ...]     can only be answered when any of these rules holds (otherwise greyed out and locked)
# A rule is {"field": "drafts", "values": ["true"]} = "when Drafts is ticked". With "not": true it means
# "when that field is answered with anything else".

def holds(answers, rule):
    """Does this rule hold, given the answers so far?"""
    answer = answers.get(rule["field"])
    if isinstance(answer, list):   # a "tick any" question: one of the ticked options matches
        hit = any(option in rule["values"] for option in answer)
    else:                          # tick boxes count as "true" / "false"
        as_text = "true" if answer is True else "false" if answer is False else str(answer if answer is not None else "")
        hit = as_text in rule["values"]
    if rule.get("not"):
        return not hit and answer is not None and answer != ""
    return hit


def is_required(question, answers):
    """Is the question mandatory right now?"""
    return bool(question.get("required")) or any(holds(answers, r) for r in question.get("requiredIf") or [])


def active_rules(question):
    """The rules that switch a question on (locked until one holds). By default its "mandatory when" rules."""
    if "activeIf" in question:
        return question["activeIf"]
    return [r for r in question.get("requiredIf") or [] if not r.get("not")]


def has_options(kind):
    """Question kinds that offer a list of options."""
    return kind in ("radio", "checks", "select")


# ---- Dates. Each date question is a drop-down of real dates (works everywhere, even with JavaScript off), plus a
#      calendar box that Acrobat shows instead when JavaScript runs.
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def date_label(day):
    """A date as shown in the drop-down: '15 Mar 2026'."""
    return f"{day.day:02d} {MONTHS[day.month - 1]} {day.year}"


def date_options(today=None):
    """Every date from the 1st of this month a year ago to the end of this month two years ahead."""
    today = today or datetime.date.today()
    first = datetime.date(today.year - 1, today.month, 1)
    after_last = datetime.date(today.year + 2 + (today.month == 12), today.month % 12 + 1, 1)
    days, day = [], first
    while day < after_last:
        days.append(date_label(day))
        day += datetime.timedelta(days=1)
    return days

# ====================================================================================================================
# 4. STEP 1: LAY OUT THE PAGES
# ====================================================================================================================
# Walks through the form (lc.py) section by section and decides where everything goes. It produces:
#   - each page's drawing (text, lines, boxes) as PDF drawing commands, in Page.ops
#   - a description of every fillable field (text box, tick box, drop-down, button ...) and where its boxes
#     ("widgets") sit, in Layout.fields. Step 3 turns these into real PDF fields.
#
# How the page is organised:
#   - Each section is a box with a grey heading band. Its questions sit on a grid of 12 columns; each question
#     takes as many columns as it needs, and questions fill a row left to right.
#   - A tick box starts a new row, and the questions it switches on are indented under it.
#   - Two short sections that follow each other can sit side by side (e.g. 4 and 5).
#   - Labels sit beside their boxes ("Name: [    ]") when the whole row has room, otherwise above them.
#
# The cursor `self.top` is the y position (from the bottom of the page) where the next thing is drawn; it moves
# down the page as content is added.



class Page:
    """One page: its number (0 = first) and its drawing commands."""

    def __init__(self, number):
        self.number, self.ops = number, []


class Layout:
    def __init__(self, form, answers, extra_height):
        """form: the form from lc.py. answers: starting answers (lc.DEFAULTS).
        extra_height: extra points of height for paragraph boxes on the last page (see build.py)."""
        self.form, self.answers, self.extra_height = form, answers, extra_height
        self.pages = []
        self.fields = []           # every field, in the order made (the writer keeps this order)
        self.by_name = {}          # field name -> field
        self.links = []            # page links: (page number, clickable area, target page number)
        self.shrink = set()        # text boxes whose text should shrink to fit (Acrobat "auto" font size)
        self.paragraph_page = {}   # paragraph question id -> the page it landed on
        self.questions = [q for s in form["sections"] for q in s["fields"]]
        self.by_id = {q["id"]: q for q in self.questions}
        # Question numbers: "13.2" = section 13, question 2.
        self.numbers = {q["id"]: f"{si + 1}.{qi + 1}" for si, s in enumerate(form["sections"]) for qi, q in enumerate(s["fields"])}
        # Questions that other questions depend on (e.g. "Drafts" switches on 13.2 to 13.7).
        self.triggers = {r["field"] for q in self.questions for r in (q.get("requiredIf") or []) + (q.get("activeIf") or [])}

    # =========================================================================================== drawing primitives
    # Each adds PDF drawing commands to a page. Fonts: F1 = Helvetica, F2 = Helvetica-Bold. Text is placed by its
    # baseline. "q ... Q" saves and restores the drawing state, so a line's colour or width doesn't leak.

    def text(self, s, x, y, size, bold=False, color=INK, page=None):
        (page or self.page).ops.append("BT /%s %s Tf %s rg %s %s Td (%s) Tj ET" % (
            "F2" if bold else "F1", fmt(size), rgb(color), fmt(x), fmt(y), pdf_string(s)))

    def line(self, x1, y1, x2, y2, thickness, color, page=None):
        (page or self.page).ops.append("q %s RG %s w %s %s m %s %s l S Q" % (
            rgb(color), fmt(thickness), fmt(x1), fmt(y1), fmt(x2), fmt(y2)))

    def rect(self, x, y, w, h, fill=None, border=None, border_width=1, dashes=None, page=None):
        op = "q "
        if fill:
            op += f"{rgb(fill)} rg "
        if border:
            op += f"{rgb(border)} RG {fmt(border_width)} w "
        if dashes:
            op += f"{dashes} d "
        paint = "B" if fill and border else "f" if fill else "S"   # B = fill and outline, f = fill, S = outline
        (page or self.page).ops.append(op + "%s %s %s %s re %s Q" % (fmt(x), fmt(y), fmt(w), fmt(h), paint))

    def new_page(self, first=False):
        """Starts a page with the header: the issuer (and on later pages the form title) and a line under it."""
        self.page = Page(len(self.pages))
        self.pages.append(self.page)
        issuer = safe(self.form.get("issuer", "")).upper()
        if issuer:
            self.text(issuer, M, H - 22, 9 if first else 7, True, ACCENT)
        if not first:
            self.text(safe(self.form["title"]), M + (width(issuer, 7, True) + 8 if issuer else 0), H - 22, 7, False, GREY)
        self.line(M, H - 29, W - M, H - 29, 1.5 if first else 0.5, ACCENT)
        self.top = H - 34

    # =========================================================================================== fields
    # A field is described here as a plain dict; step 3 makes the PDF objects from it.
    #   field:  {"name", "type": text | choice | check | radio | button, "widgets": [...], plus its settings}
    #   widget: one clickable box of a field, on one page: {"page", "rect": [x1, y1, x2, y2], plus its look}

    def add_field(self, name, field_type, **settings):
        field = {"name": name, "type": field_type, "widgets": [], **settings}
        self.fields.append(field)
        self.by_name[name] = field
        return field

    def add_widget(self, field, x, y, w, h, **look):
        border = look.get("border_width", 0) if look.get("border") else 0   # the box grows by half its border on each side
        widget = {"page": self.page.number, "rect": [x - border / 2, y - border / 2, x + w + border / 2, y + h + border / 2], **look}
        field["widgets"].append(widget)
        return widget

    # =========================================================================================== one question
    def place_question(self, q, x, w, draw, labels_beside=False):
        """Places one question at (x, self.top) in width w. With draw=False it only measures.
        Returns the height it takes. labels_beside: the row has room for labels beside their boxes."""
        answer = self.answers.get(q["id"])
        required = is_required(q, self.answers)
        always_required = required and bool(q.get("required"))
        blank = answer is None or answer == "" or answer is False or (isinstance(answer, list) and not answer)
        # Mandatory and blank: a thicker red outline. Otherwise a thin black one.
        look = {"border": RED, "border_width": 1.25, "bg": WHITE} if required and blank else {"border": INK, "border_width": 0.75, "bg": WHITE}
        if active_rules(q):
            look = {**look, "bg": None}   # switchable questions are see-through, so a grey "not yet" shade shows
        top, number = self.top, self.numbers.get(q["id"], "")
        number_w = width(number, LABEL, True) + 4 if number else 0

        # A single tick box: the box, then its number and wording beside it (wrapping onto more lines).
        if q["kind"] == "check":
            lines = wrap(q["label"], TEXT, w - 14 - number_w)
            if draw:
                box = self.add_field(q["id"], "check", tooltip=q["label"], required=always_required, value=answer is True)
                self.add_widget(box, x, top - 10, 9, 9, **look)
                if required:
                    self.text("*", x + 14 + number_w + width(lines[0] if lines else "", TEXT) + 2, top - 8, 8.5, True, RED)
                if number:
                    self.text(number, x + 14, top - 8, LABEL, True, ACCENT)
                for i, line in enumerate(lines):
                    self.text(line, x + 14 + number_w, top - 8 - i * 10, TEXT)
            return max(11, len(lines) * 10)

        label = safe(q["label"])
        options = q.get("options") or []

        # Pick one / tick any, when all the options fit on one line beside the label: "Label: ( ) A  ( ) B".
        label_w = number_w + width(f"{label}:", TEXT) + (8 if required else 0) + 10
        if q["kind"] in ("radio", "checks") and label_w + sum(self.option_width(o) for o in options) <= w:
            if draw:
                if number:
                    self.text(number, x, top - 9, LABEL, True, ACCENT)
                self.text(f"{label}:", x + number_w, top - 9, TEXT)
                if required:
                    self.text("*", x + number_w + width(f"{label}:", TEXT) + 2, top - 9, 8.5, True, RED)
                self.place_options(q, options, answer, look, always_required, lambda i, cx: (cx, top - 10.5, top - 9), x + label_w)
            return 13

        # A one-line box with its label beside it: "Name: [          ]".
        # 13.2 uses `beside` (a fixed box width, set in lc.py) to match the approved 4-page copy.
        beside = q.get("beside")
        if beside or (labels_beside and self.can_label_beside(q, w)):
            label_w = self.inline_label_width(q)
            label_y = top - (9 if beside else 10.5)
            if draw:
                if number:
                    self.text(number, x, label_y, LABEL, True, ACCENT)
                self.text(f"{label}:", x + number_w, label_y, LABEL)
                if required:
                    self.text("*", x + number_w + width(f"{label}:", LABEL) + 2, label_y, 8.5, True, RED)
                box_x = x + label_w + (BESIDE_GAP if beside else 0)
                self.place_box(q, box_x, top - 1 - BOX, beside or w - label_w, BOX, answer, look, always_required)
            return BOX if beside else BOX + 2

        # Everything else: the label on top, the box(es) below.
        if draw:
            if number:
                self.text(number, x, top - 7, LABEL, True, ACCENT)
            self.text(label, x + number_w, top - 7, LABEL)
            if required:
                self.text("*", x + number_w + width(label, LABEL) + 2, top - 7, 8.5, True, RED)
        y = top - 10

        if q["kind"] == "select":   # a drop-down list
            if draw:
                self.place_box(q, x, y - BOX, w, BOX, answer, look, always_required)
            return 10 + BOX

        if has_options(q["kind"]):  # options under the label, wrapping onto more lines when needed
            cx, spots = x, []
            for o in options:
                span = self.option_width(o)
                if cx > x and cx + span > x + w:
                    cx = x
                    y -= 12
                spots.append((cx, y))
                cx += span
            if draw:
                self.place_options(q, options, answer, look, always_required, lambda i, _: (spots[i][0], spots[i][1] - 10.5, spots[i][1] - 9), x)
            return top - y + 12

        # A text box, a paragraph box (taller) or a date.
        h = 50 + self.extra_height.get(q["id"], 0) if q["kind"] == "long" else BOX
        if draw:
            if q["kind"] == "long":
                self.paragraph_page[q["id"]] = self.page.number
            self.place_box(q, x, y - h, w, h, answer, look, always_required)
        return 10 + h

    def place_options(self, q, options, answer, look, always_required, where, cx):
        """The option buttons of a question, each with its wording beside it.
        Pick one (radio) = one field with a widget per option. Tick any (checks) = one tick-box field per option,
        named id__0, id__1, ... where(i, cx) gives (box x, box y, text y) for option i."""
        group = None
        if q["kind"] == "radio":
            group = self.add_field(q["id"], "radio", tooltip=q["label"], required=always_required, options=[safe(o) for o in options],
                                   value=options.index(answer) if isinstance(answer, str) and answer in options else None)
        for i, o in enumerate(options):
            box_x, box_y, text_y = where(i, cx)
            if group:   # radio buttons always keep a white background
                self.add_widget(group, box_x, box_y, 9, 9, state=str(i), **{**look, "bg": look["bg"] or WHITE})
            else:
                box = self.add_field(f"{q['id']}__{i}", "check", tooltip=f"{q['label']}: {o}", value=isinstance(answer, list) and o in answer)
                self.add_widget(box, box_x, box_y, 9, 9, **look)
            self.text(safe(o), box_x + 12, text_y, TEXT)
            cx = box_x + self.option_width(o)
        return cx

    def place_box(self, q, x, y, w, h, answer, look, always_required):
        """The answer box of a text, paragraph, date or drop-down question, with its typing rules."""
        if q["kind"] == "select":
            options = [safe(o) for o in q.get("options") or []]
            value = safe(answer) if isinstance(answer, str) and answer in (q.get("options") or []) else None
            box = self.add_field(q["id"], "choice", tooltip=q["label"], required=always_required, options=options, value=value, size=TEXT)
            self.add_widget(box, x, y, w, h, **look)

        elif q["kind"] == "date":
            # A drop-down of real dates ("id__list"), shown by default; it works in any PDF reader.
            parts = answer.split("/") if isinstance(answer, str) and answer else []
            picked = date_label(datetime.date(int(parts[2]), int(parts[1]), int(parts[0]))) if len(parts) == 3 else ""
            dates = date_options()
            if picked and picked not in dates:
                dates.insert(0, picked)
            dropdown = self.add_field(f"{q['id']}__list", "choice", tooltip=safe(q["label"]), options=["Pick a date", *dates],
                                      value=picked or "Pick a date", size=TEXT)
            self.add_widget(dropdown, x, y, w, h, **look)
            # In the same place, a calendar box (Acrobat's built-in date picker), hidden until the form's
            # JavaScript shows it (lcDates in js/document.js). AFDate_* are Acrobat's own date functions.
            calendar = self.add_field(q["id"], "text", tooltip=f"{safe(q['label'])} (DD/MM/YYYY)", value=answer if isinstance(answer, str) else "",
                                      size=TEXT, events={"K": 'AFDate_KeystrokeEx("dd/mm/yyyy");', "F": 'AFDate_FormatEx("dd/mm/yyyy");'})
            self.add_widget(calendar, x, y, w, h, hidden=True, **look)

        else:
            text = safe(answer)[: q.get("max") or None] if isinstance(answer, str) and answer else ""
            box = self.add_field(q["id"], "text", tooltip=q["label"], required=always_required, multiline=q["kind"] == "long",
                                 max=q.get("max"), value=text, size=TEXT)
            # A starting answer too long for the box is drawn smaller.
            one_line = safe(answer).replace("\n", " ") if q["kind"] == "text" and isinstance(answer, str) else ""
            room = w - 6
            box["size"] = min(TEXT, TEXT * room / max(room, width(one_line, TEXT)) if one_line else TEXT)
            if q["kind"] == "text" and room < width("N" * (q.get("max") or 35), TEXT):
                self.shrink.add(q["id"])   # the longest allowed answer wouldn't fit: let Acrobat shrink the text
            # Typing rules, run by Acrobat. K = on every key press (refuse wrong keys); V = when leaving the box
            # (refuse a wrong whole answer, with a message). Boxes without a format get upper case + SWIFT characters.
            if q.get("format"):
                bad, ok, message = FORMATS[q["format"]]
                message = json.dumps(f"{safe(q['label'])} {message}.", ensure_ascii=False)
                box["events"] = {"K": f"if (!event.willCommit && /{bad}/.test(event.change)) {{ event.rc = false; app.beep(0); }}",
                                 "V": f'if (event.value !== "" && !/{ok}/.test(event.value)) {{ app.alert({message}); event.rc = false; }}'}
            else:
                box["events"] = {"K": f"if (!event.willCommit) {{ event.change = event.change.toUpperCase(); if (/{BAD_CHARS}/.test(event.change)) {{ event.rc = false; app.beep(0); }} }}"}
            self.add_widget(box, x, y, w, h, **look)

    # =========================================================================================== measuring
    def option_width(self, option):
        """Room for one option: its button, a gap, its wording, and space before the next."""
        return 12 + width(safe(option), TEXT) + 10

    def inline_label_width(self, q):
        """Room for "13.2 Label: *" when the label sits beside its box."""
        number_w = width(self.numbers[q["id"]], LABEL, True) + 4 if q["id"] in self.numbers else 0
        star = 7 if q.get("required") or q.get("requiredIf") else 0
        return number_w + width(f"{safe(q['label'])}:", LABEL) + star + 6

    def can_label_beside(self, q, w):
        """Whether the label fits beside the box at width w, leaving the box enough room."""
        return q["kind"] in ("text", "date", "select") and (q.get("max") or 35) <= 70 and \
            self.inline_label_width(q) <= w * 0.65 and w - self.inline_label_width(q) >= min(self.box_width_needed(q), 110)

    def box_width_needed(self, q):
        """How wide a question's box should be: enough for its longest allowed answer."""
        kind, max_chars = q["kind"], q.get("max")
        if kind == "long":
            return float("inf")
        if kind == "check":
            return 0
        if kind == "date":
            return 96
        if kind == "select":
            return max(width(safe(o), TEXT) for o in q.get("options") or [""]) + 24
        if has_options(kind):
            return sum(self.option_width(o) for o in q.get("options") or [])
        if q.get("format") == "number" or (max_chars or 99) <= 3:
            return 40
        m = max_chars or 35
        return 100 if m <= 20 else 165 if m <= 35 else 330 if (max_chars or 0) <= 70 else float("inf")

    # =========================================================================================== the grid
    def columns_needed(self, q, label_above=False):
        """How many of the 12 grid columns a question needs."""
        column_w = (W - 2 * M - (COLUMNS - 1) * COLUMN_GAP) / COLUMNS
        label = width(safe(q["label"]), TEXT if q["kind"] == "check" else LABEL) + (16 if q["kind"] == "check" else 10) + 18
        box = self.box_width_needed(q)
        # A tick box that switches on other questions takes at least a third of the row, so the questions after it
        # line up from one row to the next.
        least = COLUMNS // 3 if q["kind"] == "check" and q["id"] in self.triggers else 1
        if q["kind"] in ("radio", "checks"):
            need = label + box + 12
        elif q["kind"] == "long" or label_above:
            need = max(label, box)
        else:
            need = max(label, min(self.inline_label_width(q) + box, label + box))
        for n in range(least, COLUMNS):
            if n * column_w + (n - 1) * COLUMN_GAP >= need:
                return n
        return COLUMNS

    def is_follow_up(self, q, seen=None):
        """Whether a question is switched on (directly or through another question) by a tick box: it is then
        indented under that tick box."""
        seen = seen if seen is not None else set()
        for r in (q.get("requiredIf") or []) + (q.get("activeIf") or []):
            parent = self.by_id.get(r["field"])
            if not parent or parent["id"] in seen:
                continue
            seen.add(parent["id"])
            if parent["kind"] == "check" or self.is_follow_up(parent, seen):
                return True
        return False

    def inside(self, area):
        """The inside of a section's outline: (left x, width, width-of-n-columns function)."""
        w = area["w"] - 2 * PAD
        column_w = (w - (area["cols"] - 1) * COLUMN_GAP) / area["cols"]
        return area["x"] + PAD, w, lambda n: n * column_w + (n - 1) * COLUMN_GAP

    def rows_of(self, section, cols):
        """Groups a section's questions into rows. A new row starts when the next question doesn't fit, at a tick
        box, after a tick box, at a question others depend on, and where indentation changes."""
        rows, used, last = [], cols, None
        for q in section["fields"]:
            n = min(cols, self.columns_needed(q))
            if used + n > cols or q["id"] in self.triggers or q["kind"] == "check" or (last and last["kind"] == "check") or \
                    (last and self.is_follow_up(last) != self.is_follow_up(q)):
                rows.append([])
                used = 0
            rows[-1].append(q)
            used += n
            last = q
        return rows

    def cells(self, row, area):
        """Positions a row's questions: [(question, x, width), ...]. Columns left over at the end of the row go to
        its text boxes and lists (not to numbers or dates, which keep their short width)."""
        if self.is_follow_up(row[0]):
            area = {**area, "x": area["x"] + INDENT, "w": area["w"] - INDENT}
        x, _, span_width = self.inside(area)
        n = [min(area["cols"], self.columns_needed(q)) for q in row]
        grows = [q["kind"] in ("long", "select") or (q["kind"] == "text" and q.get("format") != "number" and (q.get("max") or 99) > 3) for q in row]
        growing, spare = sum(grows), area["cols"] - sum(n)
        if growing:
            for i in range(len(row)):
                if grows[i]:
                    add = -(-spare // growing)   # spare / growing, rounded up
                    growing -= 1
                    n[i] += add
                    spare -= add
        out = []
        for i, q in enumerate(row):
            w = span_width(n[i])
            out.append((q, x, w))
            x += w + COLUMN_GAP
        return out

    def labels_beside(self, row, area):
        """A row's labels go beside their boxes only when every question on it can be set that way."""
        return all(q["kind"] in ("radio", "checks") or self.can_label_beside(q, w) for q, _, w in self.cells(row, area))

    def row_height(self, row, area):
        beside = self.labels_beside(row, area)
        return max(self.place_question(q, x, w, False, beside) for q, x, w in self.cells(row, area))

    def note_lines(self, section, area):
        return wrap(section["note"], 7.5, self.inside(area)[1]) if section.get("note") else []

    def section_height(self, section, area):
        note = self.note_lines(section, area)
        rows = sum(self.row_height(r, area) + 4 for r in self.rows_of(section, area["cols"]))
        return BAND + 4 + len(note) * 9 + (4 if note else 0) + rows + (SIGN_OFF if section.get("signoff") else 0) + 1

    # =========================================================================================== one section
    def draw_section(self, section, index, area, may_break, bottom=None):
        """Draws a section: its heading band, note, rows of questions and outline.
        area: {"x", "w", "cols"} (full width or one half). may_break: may continue on the next page.
        bottom: for side-by-side sections, the y both must reach (so they're the same height)."""
        rows, note, whole = self.rows_of(section, area["cols"]), self.note_lines(section, area), self.section_height(section, area)
        inner_x, inner_w, _ = self.inside(area)
        # Start on a new page if not even the heading and first row fit. The bank-use panel and the declaration are
        # kept whole on one page.
        first_part = whole if section.get("signoff") or section.get("bankOnly") else BAND + 12 + (self.row_height(rows[0], area) if rows else 0)
        if may_break and self.top - first_part < BOTTOM:
            self.new_page()
        box_top = self.top

        def outline():
            self.rect(area["x"], self.top, area["w"], box_top - self.top, border=INK, border_width=0.6)

        if section.get("bankOnly"):   # the "For Bank Use Only" section is shaded
            fill = max(whole, self.top - bottom) if bottom is not None else whole
            self.rect(area["x"], self.top - fill, area["w"], fill, fill=BANK_SHADE)
        # Heading band: "3   APPLICANT" on grey, shrunk if it's too long for the box.
        self.rect(area["x"], self.top - BAND, area["w"], BAND, fill=TINT)
        self.line(area["x"], self.top - BAND, area["x"] + area["w"], self.top - BAND, 0.6, INK)
        heading = safe(f"{index + 1}   {section['title'].upper()}{'  (to be completed by the Bank)' if section.get('bankOnly') else ''}")
        self.text(heading, area["x"] + PAD, self.top - 9.3, min(7.5, 7.5 * (area["w"] - 2 * PAD) / width(heading, 7.5, True)), True)
        self.top -= BAND + 4
        for line in note:
            self.text(line, inner_x, self.top - 7.5, 7.5)
            self.top -= 9
        if note:
            self.top -= 4

        for i, row in enumerate(rows):
            h = self.row_height(row, area)
            if may_break and self.top - h < BOTTOM:   # the section carries on over the page
                self.top -= 1
                outline()
                self.new_page()
                box_top = self.top
                self.top -= 5
            if i > 0:
                self.line(inner_x, self.top + 3, inner_x + inner_w, self.top + 3, 0.4, RULE)   # thin line between rows
            beside = self.labels_beside(row, area)
            for q, x, w in self.cells(row, area):
                self.place_question(q, x, w, True, beside)
            self.top -= h + 4

        if section.get("signoff"):   # lines to sign on paper after printing
            for x, w, label in ((inner_x, 190, "Authorised signature(s)"), (inner_x + 210, 110, "Date")):
                self.line(x, self.top - 28, x + w, self.top - 28, 0.75, INK)
                self.text(label, x, self.top - 36, 7, color=GREY)
            self.rect(inner_x + inner_w - 150, self.top - 43, 150, 41, border=INK, border_width=0.75, dashes="[2 2] 0")
            self.text("Company stamp", inner_x + inner_w - 146, self.top - 39, 7, color=GREY)
            self.top -= SIGN_OFF

        # The approved 4-page copy ends the Drafts section (the one with 13.2) 3 points higher than the others.
        self.top -= -2 if any(q.get("beside") for q in section["fields"]) else 1
        if bottom is not None:
            self.top = min(self.top, bottom)
        outline()
        self.top -= SECTION_GAP

    # =========================================================================================== the whole form
    def draw(self):
        """Lays out the whole form: title, sections, QR code page, footers."""
        self.draw_title()
        self.draw_sections()
        self.last_question_page = self.page.number
        self.spare = self.top - BOTTOM   # room left on the last page of questions (build.py uses it)
        self.draw_qr_page()
        self.draw_footers()

    def draw_title(self):
        form = self.form
        self.new_page(first=True)
        self.text(safe(form["title"]), M, H - 48, 14, True)
        if form.get("formCode"):
            code = safe(form["formCode"])
            self.text(code, W - M - width(code, 7), H - 47, 7, color=GREY)
        self.top = H - 54
        note = f"{safe(form.get('note', ''))}  * Mandatory. Boxes outlined in red must be completed; a red note under a question says when it becomes mandatory."
        for line in wrap(note, 7, W - 2 * M):
            self.text(line, M, self.top - 7.5, 7, color=GREY)
            self.top -= 9
        self.top -= 5

    def draw_sections(self):
        """Draws the sections in order: full width, or two side by side when both are short and similar in height."""
        full = {"x": M, "w": W - 2 * M, "cols": COLUMNS}
        half_w = (W - 2 * M - SECTION_GAP) / 2
        left = {"x": M, "w": half_w, "cols": COLUMNS // 2}
        right = {**left, "x": M + half_w + SECTION_GAP}

        def fits_half(s):
            inner_w = self.inside(left)[1]
            return not s.get("note") and not s.get("signoff") and width(s["title"].upper(), 6, True) + 30 < half_w and \
                all(q["kind"] != "long" and (all(self.option_width(o) < inner_w for o in q.get("options") or []) if has_options(q["kind"])
                                             else q["kind"] == "check" or self.columns_needed(q, True) <= COLUMNS // 2) for q in s["fields"]) and \
                self.section_height(s, left) < 300

        sections, i = self.form["sections"], 0
        while i < len(sections):
            a = sections[i]
            b = sections[i + 1] if i + 1 < len(sections) else None
            height_a = self.section_height(a, left) if b else 0
            height_b = self.section_height(b, right) if b else 0
            side_by_side = b and fits_half(a) and fits_half(b) and min(height_a, height_b) >= 0.45 * max(height_a, height_b)
            pair_height = max(height_a, height_b) + SECTION_GAP
            # Full width when they can't pair, or when the pair doesn't fit here but the first section alone does.
            if not side_by_side or (self.top - pair_height < BOTTOM and self.top - self.section_height(a, full) - SECTION_GAP >= BOTTOM):
                self.draw_section(a, i, full, True)
                i += 1
                continue
            if self.top - pair_height < BOTTOM:
                self.new_page()
            start = self.top
            bottom = start - max(height_a, height_b)
            self.draw_section(a, i, left, False, bottom)
            self.top = start
            self.draw_section(b, i + 1, right, False, bottom)
            i += 2

    def draw_qr_page(self):
        """A last page with a frame for the QR code of the answers (js/document.js draws the code into it in Acrobat)."""
        self.new_page()
        self.text("APPLICATION QR CODE (FOR BANK USE)", M, H - 56, 11, True)
        y = H - 70
        for line in wrap("When the form is filled in, press Generate QR Code (under the code), then Print Form. The Bank scans the code to read the application (all the answers, as JSON). Do not write on or fold the code.", 8, W - 2 * M):
            self.text(line, M, y, 8, color=GREY)
            y -= 10
        size = 450
        self.qr = {"page": self.page.number, "x": (W - size) / 2, "y": y - 14 - size, "size": size,
                   "button": ((W - 312) / 2, y - 14 - size - 52)}
        self.rect(self.qr["x"], self.qr["y"], size, size, border=RULE, border_width=0.5)
        code = safe(self.form.get("formCode") or self.form["title"])
        self.text(code, (W - width(code, 7)) / 2, self.qr["y"] - 14, 7, color=GREY)

    def draw_footers(self):
        """Every page: form code, "Page n of N", and "< Previous page" / "Next page >" links (plain PDF links, so
        they work even with JavaScript off)."""
        count = len(self.pages)
        for i, page in enumerate(self.pages):
            self.line(M, 36, W - M, 36, 0.5, RULE, page=page)
            self.text(safe(self.form.get("formCode") or self.form["title"]), M, 24, 7, color=GREY, page=page)
            label = f"Page {i + 1} of {count}"
            self.text(label, W - M - width(label, 7.5), 24, 7.5, color=GREY, page=page)
            for text, target, x in (("< Previous page", i - 1, W / 2 - 90), ("Next page >", i + 1, W / 2 + 20)):
                if 0 <= target < count:
                    self.text(text, x, 23.5, 7.5, True, ACCENT, page=page)
                    self.links.append((i, [x - 4, 18, x + width(text, 7.5, True) + 4, 34], target))

# ====================================================================================================================
# 5. STEP 2: ADD THE SCRIPTS, BUTTONS AND QR CODE ROWS
# ====================================================================================================================
# Everything interactive in the PDF is Acrobat JavaScript, kept as plain files in js/. This step:
#   1. builds the "rules table" (which questions are mandatory, when, and their formats) from lc.py, and fills it
#      into js/document.js (the rules engine, the QR code's text and the QR encoder): the one document-level
#      script stored in the PDF, named "lcRules".
#   2. says when the rules run: when a tick box or option is clicked, and when the person leaves a box
#   3. adds the hidden helper fields, the 177 QR code rows, and the buttons (Check form, Reset form on every page;
#      Generate QR Code and Print Form on the QR page)
# It only adds field descriptions to the layout; step 3 makes the PDF objects.

RUN_RULES = "lcRules(this);"   # the call every event uses


# js/document.js is one script; js/buttons.js holds several, each after a "// ==== name ====" line.
# (Each file, and each section, ends with one newline that isn't part of the script.)
DOCUMENT_JS = read_file("js/document.js")[:-1]
_sections = re.split(r"(?m)^// ==== (\S+) ====\n", read_file("js/buttons.js"))
BUTTON_JS = {_sections[i]: _sections[i + 1][:-1] for i in range(1, len(_sections), 2)}


def script(name, **values):
    """A script ("document", or a button's name such as "check-form"), with its __PLACEHOLDERS__ filled in."""
    text = DOCUMENT_JS if name == "document" else BUTTON_JS[name]
    for key, value in values.items():
        text = text.replace(f"__{key}__", value)
    return text


def rules_table(layout):
    """What the rules engine (js/document.js) needs to know about each question, in form order (so Check form lists problems top to
    bottom). Short keys keep the script small:
      kind, label; hasRule (has a mandatory rule); always (always mandatory); requiredIf / activeIf as
      [field, values, not]; check: [pattern, message] for a format, or 1 for "allowed characters only";
      options for "tick any" questions."""
    layout_questions, by_id = layout.questions, layout.by_id

    def as_list(rules):
        return [[r["field"], [safe(v) for v in r["values"]], 1 if r.get("not") else 0] for r in rules]

    table = {}

    def entry(q):
        if q["id"] not in table:
            item = {"kind": q["kind"], "label": safe(q["label"])}
            if q["kind"] == "checks":
                item["options"] = [safe(o) for o in q.get("options") or []]
            table[q["id"]] = item
        return table[q["id"]]

    for q in [q for q in layout_questions if q.get("required") or q.get("requiredIf")]:   # mandatory questions
        item = entry(q)
        item["hasRule"] = 1
        if q.get("required"):
            item["always"] = 1
        if q.get("requiredIf"):
            item["requiredIf"] = as_list(q["requiredIf"])
        for r in q.get("requiredIf") or []:   # ... and the questions their rules look at
            if r["field"] in by_id:
                entry(by_id[r["field"]])
    for q in [q for q in layout_questions if active_rules(q)]:   # questions that are locked until switched on
        entry(q)["activeIf"] = as_list(active_rules(q))
        for r in active_rules(q):
            if r["field"] in by_id:
                entry(by_id[r["field"]])
    for q in [q for q in layout_questions if q["kind"] in ("text", "long", "date")]:   # typed answers are checked
        entry(q)["check"] = [FORMATS[q["format"]][1], FORMATS[q["format"]][2]] if q.get("format") else 1
    return {q["id"]: table[q["id"]] for q in layout_questions if q["id"] in table}


def document_script(layout, table):
    """The one document-level script (js/document.js), filled in for this form."""
    form, questions = layout.form, layout.questions
    tick_any = ", ".join(f"{json.dumps(q['id'])}: {js_json(q.get('options') or [])}" for q in questions if q["kind"] == "checks")
    code = re.search(r"[A-Z]+-\d+", form.get("formCode") or "")     # "LC-01"
    version = re.search(r"v([\d.]+)", form.get("formCode") or "")   # "1.0"
    return script("document", MODEL=js_json(table), DATES=js_json([q["id"] for q in questions if q["kind"] == "date"]),
                  GROUPS=tick_any, LONG=js_json([q["id"] for q in questions if q["kind"] == "long"]),
                  FORM=json.dumps(code.group(0) if code else safe(form["title"]), ensure_ascii=False),
                  VERSION=json.dumps(version.group(1) if version else "1"))


def add_scripts(layout):
    """Adds the events, helper fields, QR rows and buttons to the layout. Returns the document script."""
    table = rules_table(layout)
    doc_script = document_script(layout, table)

    # When the rules run: when a tick box, option or date list is clicked (U = mouse up), and when the person
    # leaves any other box (Bl = blur).
    for qid, item in table.items():
        if item["kind"] == "checks":
            names = [f"{qid}__{i}" for i in range(len(item.get("options") or []))]
        elif item["kind"] == "date" and f"{qid}__list" in layout.by_name:
            names = [f"{qid}__list", qid]
        else:
            names = [qid]
        for name in names:
            for widget in layout.by_name.get(name, {"widgets": []})["widgets"]:
                clicked = item["kind"] in ("check", "checks", "radio") or (item["kind"] == "date" and name != qid)
                widget.setdefault("events", {})["U" if clicked else "Bl"] = RUN_RULES

    # ... and after any value changes (Acrobat's "calculate" event), as a safety net: a hidden field off the page.
    layout.page = layout.pages[0]
    recalc = layout.add_field("__checks", "text", size=3, events={"C": RUN_RULES})
    layout.add_widget(recalc, -20, -20, 1, 1, hidden=True, border=INK, bg=WHITE)

    # The QR code: a hidden field "__qr" holds the answers as JSON; js/document.js draws the code into 177 read-only
    # "comb" text boxes, one per row of the code (a comb box spaces its characters evenly). Each dark square is
    # the letter "n" in the ZapfDingbats font, which prints as a solid black square. This avoids Acrobat's own
    # barcode feature, which some installations don't have.
    qr = layout.qr
    layout.page = layout.pages[qr["page"]]
    holder = layout.add_field("__qr", "text", size=3)
    layout.add_widget(holder, -20, -20, 1, 1, hidden=True, border=INK, bg=WHITE)
    module = qr["size"] / 185   # 177 squares + 4 squares of white margin on each side
    font_size = "/ZaDb %s Tf 0 g" % fmt(round(module / 0.692 * 1000) / 1000)   # the square is 0.692 of the font size
    for y in range(177):
        row = layout.add_field(f"__qr_{y}", "text", max=177, comb=True, appearance=font_size)
        layout.add_widget(row, qr["x"] + 4 * module, qr["y"] + qr["size"] - (5 + y) * module, 177 * module, module)

    # "Check form" and "Reset form" at the top right of every page (on screen only, never printed).
    buttons = [("__check_form", "Check form", script("check-form"), 64), ("__reset_form", "Reset form", script("reset-form"), 64)]
    for i, (name, caption, code, button_w) in enumerate(buttons):
        x = PAGE_WIDTH - MARGIN - sum(b[3] + 4 for b in buttons[i:]) + 4   # right-aligned, 4 points apart
        button = layout.add_field(name, "button", size=8)
        for page in layout.pages:
            layout.page = page
            layout.add_widget(button, x, PAGE_HEIGHT - 25, button_w, 13, caption=caption, border=ACCENT, bg=ACCENT,
                              border_width=0, action=code, flags=0)

    # "Generate QR Code" and "Print Form", under the QR code.
    layout.page = layout.pages[qr["page"]]
    for i, (name, caption, js_file) in enumerate((("__generate_qr", "Generate QR Code", "generate-qr"),
                                                  ("__print_form", "Print Form", "print-form"))):
        button = layout.add_field(name, "button", size=10)
        bx, by = qr["button"]
        layout.add_widget(button, bx + i * 162, by, 150, 22, caption=caption, border=ACCENT, bg=ACCENT, border_width=0,
                          action=script(js_file), flags=0)
    return doc_script

# ====================================================================================================================
# 6. STEP 3: WRITE THE PDF
# ====================================================================================================================
# Turns the layout (pages, field descriptions, links) and the document script into a PDF:
#   - each page with its drawing (its "content stream") and the fonts it uses
#   - every field, with its settings and an "appearance" (a small drawing of how the box looks, so it shows
#     correctly in any PDF reader before anyone types into it)
#   - the page links, the document script, and the warnings before save / print
#   - a copy of the form's description (JSON from lc.py) inside the PDF, for the bank's workbench to read
#
# PDF terms used below:
#   Dictionary   a PDF object with named entries, e.g. {/Type /Page, /MediaBox [...]}
#   widget       the visible box of a field on a page (one field can have several, e.g. one per page)
#   Ff           field flags: required (2), multiline (4096), comb (16777216), read-only (1), drop-down (131072),
#                radio (32768), push button (65536)
#   F            widget flags: 4 = print, 2 = hidden, 0 = on screen only
#   DA           default appearance: font and colour Acrobat uses when it redraws the box
#   MK           the box's border colour (BC), background (BG) and caption (CA)
#   AA / A       actions: JavaScript run on events (AA) or on click (A)

# Field flags (Ff) and their meaning.
REQUIRED, READ_ONLY, MULTILINE, COMB, DROP_DOWN, RADIO, PUSH_BUTTON = 2, 1, 4096, 16777216, 131072, 32768, 65536


class Writer:
    def __init__(self, layout, doc_script):
        self.layout, self.doc_script = layout, doc_script

    def write(self):
        """Builds and returns the pikepdf document."""
        layout, form = self.layout, self.layout.form
        pdf = self.pdf = pikepdf.new()

        # 1. The pages, each with its drawing and two fonts (F1 Helvetica, F2 Helvetica-Bold, built into every reader).
        helvetica = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica, Encoding=Name.WinAnsiEncoding))
        helvetica_bold = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name("/Helvetica-Bold"), Encoding=Name.WinAnsiEncoding))
        for page in layout.pages:
            drawing = pdf.make_stream(zlib.compress(" ".join(page.ops).encode("cp1252", "replace")), Filter=Name.FlateDecode)
            pdf.pages.append(pikepdf.Page(Dictionary(Type=Name.Page, MediaBox=[0, 0, PAGE_WIDTH, PAGE_HEIGHT],
                                                     Resources=Dictionary(Font=Dictionary(F1=helvetica, F2=helvetica_bold)),
                                                     Contents=drawing)))
        pages = [p.obj for p in pdf.pages]
        # Fonts the fields use: Helvetica for text, ZapfDingbats for the tick, radio dot and QR squares.
        zapf = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.ZapfDingbats))
        self.fonts = Dictionary(Helvetica=helvetica, Helv=helvetica, ZaDb=zapf)

        # 2. Document information, and the form's description (lc.py as JSON) for the workbench.
        pdf.docinfo[Name.Title] = String(safe(form["title"]))
        pdf.docinfo[Name.Creator] = String("PDF Template Studio")
        description = {**form, "uploaded": False}
        pdf.Root[Name.FormTemplate] = pdf.make_stream(zlib.compress(js_json(description).encode("utf-8")), Filter=Name.FlateDecode)

        def annotations(i):
            """The list of clickable things (links, widgets) on page i."""
            if Name.Annots not in pages[i]:
                pages[i][Name.Annots] = Array()
            return pages[i].Annots

        # 3. Page links ("< Previous page" / "Next page >").
        for i, area, target in layout.links:
            annotations(i).append(pdf.make_indirect(Dictionary(
                Type=Name.Annot, Subtype=Name.Link, Rect=area, Border=[0, 0, 0],
                A=Dictionary(S=Name.GoTo, D=[pages[target], Name.XYZ, None, None, None]))))

        # 4. The fields, in the order they were made.
        all_fields = []
        for field in layout.fields:
            all_fields.append(self.make_field(field, pages))
            for widget in field["widgets"]:
                annotations(widget["page"]).append(widget["obj"])
        acro_form = Dictionary(Fields=Array(all_fields), DR=Dictionary(Font=self.fonts), DA=String("/Helv 0 Tf 0 g"))
        acro_form[Name.CO] = Array([layout.by_name["__checks"]["obj"]])   # the hidden field that re-runs the rules
        pdf.Root[Name.AcroForm] = pdf.make_indirect(acro_form)

        # 5. The document script ("lcRules"), and the warning before saving (WS) or printing (WP) an incomplete form.
        stream = pdf.make_stream(zlib.compress(self.doc_script.encode("latin-1", "replace")), Filter=Name.FlateDecode)
        pdf.Root[Name.Names] = Dictionary(JavaScript=Dictionary(Names=[String("lcRules"), Dictionary(S=Name.JavaScript, JS=stream)]))
        pdf.Root[Name.AA] = Dictionary(WS=self.javascript(script("before-save")), WP=self.javascript(script("before-save")))
        return pdf

    # =========================================================================================== helpers
    def javascript(self, code):
        """A PDF action that runs JavaScript."""
        return Dictionary(S=Name.JavaScript, JS=String(code))

    def appearance(self, w, h, drawing):
        """A small drawing (form XObject) of how a box looks, w x h points."""
        return self.pdf.make_stream(drawing.encode("latin-1", "replace"), Type=Name.XObject, Subtype=Name.Form,
                                    BBox=[0, 0, num(w), num(h)], Resources=Dictionary(Font=self.fonts))

    def frame(self, widget, w, h):
        """Drawing commands for a box's background and border."""
        out = ""
        if widget.get("bg"):
            out += "%s rg 0 0 %s %s re f " % (rgb(widget["bg"]), fmt(w), fmt(h))
        if widget.get("border") and widget.get("border_width"):
            b = widget["border_width"]
            out += "%s RG %s w %s %s %s %s re S " % (rgb(widget["border"]), fmt(b), fmt(b / 2), fmt(b / 2), fmt(w - b), fmt(h - b))
        return out

    # =========================================================================================== one field
    def make_field(self, field, pages):
        """The PDF objects for one field and its widgets."""
        pdf, field_type = self.pdf, field["type"]
        d = Dictionary(T=String(field["name"]))   # T = the field's name
        if field.get("tooltip"):
            d[Name.TU] = String(safe(field["tooltip"]))
        flags = REQUIRED if field.get("required") else 0
        size = field.get("size", TEXT)

        if field_type == "text":
            d[Name.FT] = Name.Tx
            if field.get("multiline"):
                flags |= MULTILINE
            if field.get("comb"):
                flags |= COMB | READ_ONLY
            if field.get("max"):
                d[Name.MaxLen] = field["max"]
            if field.get("value"):
                d[Name.V] = String(field["value"])
            font_size = "0" if field["name"] in self.layout.shrink else fmt(size)   # 0 = shrink to fit
            d[Name.DA] = String(field.get("appearance") or "0 0 0 rg\n/Helvetica %s Tf" % font_size)
        elif field_type == "choice":      # a drop-down list
            d[Name.FT] = Name.Ch
            flags |= DROP_DOWN
            d[Name.Opt] = Array([Array([String(o), String(o)]) for o in field["options"]])
            if field.get("value") is not None:
                d[Name.V] = String(field["value"])
            d[Name.DA] = String("0 0 0 rg\n/Helvetica %s Tf" % fmt(size))
        elif field_type == "check":       # a tick box: on = /Yes, off = /Off
            d[Name.FT] = Name.Btn
            if field.get("value"):
                d[Name.V] = Name.Yes
            d[Name.DA] = String("/ZaDb 0 Tf 0 g")
        elif field_type == "radio":       # pick one: each option's widget has its own "on" name (/0, /1, ...)
            d[Name.FT] = Name.Btn
            flags |= RADIO
            d[Name.Opt] = Array([String(o) for o in field["options"]])   # so the answer reads as the option's wording
            if field.get("value") is not None:
                d[Name.V] = Name("/%d" % field["value"])
            d[Name.DA] = String("/ZaDb 0 Tf 0 g")
        elif field_type == "button":
            d[Name.FT] = Name.Btn
            flags |= PUSH_BUTTON
            d[Name.DA] = String("1 1 1 rg\n/Helvetica %s Tf" % fmt(size))

        if field.get("events"):
            d[Name.AA] = Dictionary({"/" + event: self.javascript(code) for event, code in field["events"].items()})
        if flags:
            d[Name.Ff] = flags
        if Name.V in d:   # DV = default value: "Reset form" goes back to the starting answer (e.g. Full Swift), not blank
            d[Name.DV] = d.V
        d = pdf.make_indirect(d)
        field["obj"] = d

        kids = Array()
        for widget in field["widgets"]:
            x1, y1, x2, y2 = widget["rect"]
            w, h = x2 - x1, y2 - y1
            k = Dictionary(Type=Name.Annot, Subtype=Name.Widget, Rect=[num(v) for v in widget["rect"]], P=pages[widget["page"]],
                           Parent=d, F=widget.get("flags", 2 if widget.get("hidden") else 4))
            look = Dictionary()
            if widget.get("border"):
                look.BC = list(widget["border"])
            if widget.get("bg"):
                look.BG = list(widget["bg"])
            if widget.get("caption"):
                look.CA = String(widget["caption"])
            if len(look):
                k.MK = look
            k.BS = Dictionary(W=num(widget.get("border_width", 0)) if widget.get("border") else 0)   # border width
            k.AP = self.widget_appearance(field, widget, w, h)
            if field_type in ("check", "radio"):   # AS = which appearance shows now (on or Off)
                on = widget.get("state", "Yes")
                lit = (field_type == "check" and field.get("value")) or \
                      (field_type == "radio" and field.get("value") is not None and str(field["value"]) == on)
                k.AS = Name("/" + on) if lit else Name.Off
            if widget.get("action"):
                k.A = self.javascript(widget["action"])
            if widget.get("events"):
                k.AA = Dictionary({"/" + event: self.javascript(code) for event, code in widget["events"].items()})
            widget["obj"] = pdf.make_indirect(k)
            kids.append(widget["obj"])
        d.Kids = kids
        return d

    def widget_appearance(self, field, widget, w, h):
        """How a widget looks: its frame plus, depending on the field, its text, tick, radio dot or caption.
        N = normal look, D = look while pressed. Tick boxes and radios have an "on" and an "Off" look."""
        field_type = field["type"]
        base = self.frame(widget, w, h)

        if field_type in ("text", "choice"):
            value, size, body = field.get("value") or "", field.get("size", TEXT), ""
            if value and not field.get("comb"):
                if field.get("multiline"):
                    text_y = h - 2 - size
                    for line in wrap(value, size, w - 4):
                        body += "BT /Helv %s Tf 0 g 2 %s Td (%s) Tj ET " % (fmt(size), fmt(text_y), pdf_string(line))
                        text_y -= size * 1.2
                else:
                    body = "BT /Helv %s Tf 0 g 2 %s Td (%s) Tj ET " % (fmt(size), fmt((h - size * 0.72) / 2), pdf_string(value))
            return Dictionary(N=self.appearance(w, h, "%s/Tx BMC q %sQ EMC" % (base, body)))

        if field_type == "check":   # ZapfDingbats "4" is a tick mark
            tick = "q 0 g BT /ZaDb %s Tf %s %s Td (4) Tj ET Q" % (fmt(h * 0.8), fmt(w * 0.15), fmt(h * 0.22))
            return Dictionary(N=Dictionary(Yes=self.appearance(w, h, base + tick), Off=self.appearance(w, h, base)),
                              D=Dictionary(Yes=self.appearance(w, h, base + tick), Off=self.appearance(w, h, base)))

        if field_type == "radio":   # a ring, and when on a dot inside it (circles drawn as 4 Bezier curves)
            ring_r, k, c = w / 2 - widget.get("border_width", 0.75) / 2, 0.5523, w / 2

            def circle(r):
                q = k * r
                return ("%s %s m %s %s %s %s %s %s c %s %s %s %s %s %s c %s %s %s %s %s %s c %s %s %s %s %s %s c" %
                        tuple(map(fmt, (c + r, c, c + r, c + q, c + q, c + r, c, c + r, c - q, c + r, c - r, c + q, c - r, c,
                                        c - r, c - q, c - q, c - r, c, c - r, c + q, c - r, c + r, c - q, c + r, c))))
            ring = ""
            if widget.get("bg"):
                ring += "%s rg %s f " % (rgb(widget["bg"]), circle(ring_r))
            ring += "%s RG %s w %s S " % (rgb(widget.get("border") or INK), fmt(widget.get("border_width", 0.75)), circle(ring_r))
            dot = ring + "0 g %s f" % circle(w * 0.21)
            on = widget["state"]
            return Dictionary(N=Dictionary({"/" + on: self.appearance(w, h, dot), "/Off": self.appearance(w, h, ring)}),
                              D=Dictionary({"/" + on: self.appearance(w, h, dot), "/Off": self.appearance(w, h, ring)}))

        if field_type == "button":  # white caption, centred
            caption, size = widget["caption"], field.get("size", 8)
            drawing = "%s/Tx BMC q BT /Helv %s Tf 1 g %s %s Td (%s) Tj ET Q EMC" % (
                base, fmt(size), fmt((w - width(caption, size)) / 2), fmt((h - size * 0.72) / 2), pdf_string(caption))
            look = self.appearance(w, h, drawing)
            return Dictionary(N=look, D=look)

        return Dictionary(N=self.appearance(w, h, ""))

# ====================================================================================================================
# 7. BUILD: RUN THE THREE STEPS
# ====================================================================================================================
# Puts the three steps together and produces the PDF bytes.

def build(form, answers):
    """The finished PDF as bytes.

    The layout runs twice: the second time, the room left at the end of the last page of questions is shared out
    to the paragraph boxes on that page (Goods description, Additional conditions), so the form doesn't end with a
    blank gap. The second layout is kept only if it doesn't add a page.
    """
    def lay_out(extra_height):
        layout = Layout(form, answers, extra_height)
        layout.draw()
        return layout

    layout = lay_out({})
    last_paragraphs = [qid for qid, page in layout.paragraph_page.items() if page == layout.last_question_page]
    if last_paragraphs and layout.spare >= 20:
        each = min(90, int((layout.spare - 10) // len(last_paragraphs)))   # at most 90 points more per box
        taller = lay_out({qid: each for qid in last_paragraphs})
        if len(taller.pages) == len(layout.pages):
            layout = taller

    doc_script = add_scripts(layout)                 # step 2
    pdf = Writer(layout, doc_script).write()         # step 3
    out = io.BytesIO()
    pdf.save(out, deterministic_id=True)             # same input, same file (reproducible builds)
    return out.getvalue()


# ====================================================================================================================
# 8. SELF-CHECK: OPEN THE BUILT PDF AND CHECK IT
# ====================================================================================================================
# Opens the finished PDF and checks that every question in lc.py became the right fields, with their rules, limits
# and starting answers, and that the scripts, buttons and QR code rows are there. Stops with an error if not.
# (The scripts themselves run only inside Acrobat; test them there, see README "Testing in Acrobat".)

def self_check(pdf_bytes):
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    fields = {str(f.T): f for f in pdf.Root.AcroForm.Fields}
    questions = [q for s in LC["sections"] for q in s["fields"]]
    problems = pdf.check_pdf_syntax()
    assert not problems, f"PDF structure problems: {problems}"
    assert len(pdf.pages) == 4, f"expected 4 pages, got {len(pdf.pages)}"
    assert len(fields) == 297, f"expected 297 fields, got {len(fields)} (update this number if you add or remove questions)"

    # Every question has its fields: dates a list + a calendar box, "tick any" one box per option.
    for q in questions:
        if q["kind"] == "checks":
            names = [f"{q['id']}__{i}" for i in range(len(q["options"]))]
        elif q["kind"] == "date":
            names = [q["id"], f"{q['id']}__list"]
        else:
            names = [q["id"]]
        for name in names:
            assert name in fields, f"missing field {name}"
        f = fields[names[0]]
        expected = REQUIRED if q.get("required") and q["kind"] != "date" else 0
        assert int(f.get("/Ff", 0)) & REQUIRED == expected, f"required flag wrong on {q['id']}"
        if q.get("max") and q["kind"] in ("text", "long"):
            assert int(f.MaxLen) == q["max"], f"max length wrong on {q['id']}"

    # Starting answers, kept as the values "Reset form" goes back to.
    for key, value in DEFAULTS.items():
        f = fields[key]
        assert "/DV" in f, f"no reset value for {key}"
        if isinstance(value, str) and f.FT == "/Tx":
            assert str(f.V) == value, f"{key} starts as {f.V}"

    # The document script holds the rules table, the QR code's text and the QR encoder.
    doc_script = zlib.decompress(pdf.Root.Names.JavaScript.Names[1].JS.read_raw_bytes()).decode("latin-1")
    for name in ("function lcRules(", "function lcDates(", "function lcPayload(", "function lcQrMatrix(", "function lcDrawQr("):
        assert name in doc_script, f"script lacks {name}"
    table = json.loads(re.search(r"var M = (\{.*?\});\n", doc_script).group(1))
    assert table["applicant_name"].get("always") == 1
    assert table["drafts_percent"]["requiredIf"] == [["drafts", ["true"], 0]]
    assert table["term_days"]["requiredIf"] == [["drafts_at", ["Term"], 0]]
    for q in questions:
        if q.get("required") or q.get("requiredIf") or q.get("activeIf"):
            assert q["id"] in table, f"{q['id']} not in the rules table"

    # Buttons, the hidden re-check field, and the QR code rows.
    for name in ("__check_form", "__reset_form", "__generate_qr", "__print_form", "__checks", "__qr"):
        assert name in fields, f"missing {name}"
    assert len(fields["__check_form"].Kids) == 4, "Check form should be on every page"
    assert all(f"__qr_{y}" in fields for y in range(177)), "missing QR code rows"
    assert "/WS" in pdf.Root.AA and "/WP" in pdf.Root.AA, "missing the warning before save / print"
    return "PASS: 4 pages, 297 fields, rules table, scripts, buttons and QR rows OK"


# ====================================================================================================================
# 9. RUN: BUILD, CHECK, SAVE
# ====================================================================================================================
# A small page for viewing the PDF locally:  python -m http.server 8090 -d out   ->  http://localhost:8090
INDEX_HTML = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>LC application (Form LC-01)</title>
<style>body { font: 15px Arial, sans-serif; margin: 0; } p { margin: 12px 16px; } iframe { border: 0; width: 100%; height: calc(100vh - 48px); }</style>
<p><a href="LC-Application.pdf" download>Download the form</a> (open it in Adobe Acrobat or Reader: the checks, red boxes and QR code need Acrobat's JavaScript).</p>
<iframe src="LC-Application.pdf" title="LC application form"></iframe>
</html>
"""

if __name__ == "__main__":
    pdf_bytes = build(LC, DEFAULTS)
    result = self_check(pdf_bytes)          # stops here, with the reason, if anything is wrong
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "LC-Application.pdf"), "wb") as f:
        f.write(pdf_bytes)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX_HTML)
    print("Wrote out/LC-Application.pdf")
    print(result)
