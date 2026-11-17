#!/usr/bin/env python3
"""BUILDS A FILLABLE PDF FORM FROM A FORM FILE, THEN CHECKS IT.

    python build_form.py lc.py     -> out/LC-Application.pdf  (plus out/index.html for viewing it locally)

TWO FILES
    lc.py          WHAT the form asks: its sections, questions, options and rules. One line per question.
                   To make a new form, copy lc.py, change the questions, and run  python build_form.py my_form.py
    build_form.py  HOW any form file becomes a PDF (this file). It contains everything else the PDF needs,
                   including the JavaScript Acrobat runs and the font measurements, so no other files are needed.

HOW IT FITS TOGETHER

    lc.py ──────────────┐  the form: every question, its options and rules
                        ▼
    build_form.py  STEP 1  lay out the pages ─── where every section, question and box goes
                   STEP 2  add the scripts ───── the rules engine, buttons and QR code rows
                   STEP 3  write the PDF ─────── pikepdf turns it all into a real PDF
                   CHECK   open the result and check it question by question
                        ▼
    out/LC-Application.pdf
                        │  inside the PDF, Acrobat runs (the scripts in Appendix A):
    DOCUMENT_JS         │    the rules engine (red boxes, locking, checks), the QR code's text and the QR encoder
    BUTTON_JS           │    Check form, Reset form, Generate QR Code, Print Form, and the warning before save/print

CONTENTS OF THIS FILE
    1. Question helpers: text, radio, date ... used by form files   (the options a question can have)
    2. Settings: page size, colours, sizes, answer formats          (change the look here)
    3. Text helpers: safe characters, measuring, wrapping
    4. Rules and dates: "mandatory now?", "applies now?", the date list
    5. Step 1: lay out the pages                                     (class Layout)
    6. Step 2: add the scripts, buttons and QR code rows             (add_scripts)
    7. Step 3: write the PDF                                         (class Writer)
    8. Build: run the three steps                                    (build)
    9. Self-check: open the built PDF and check it                   (self_check)
   10. Run: load the form file, build, check, save                   (main)
    Appendix A. The scripts that run inside Acrobat                  (DOCUMENT_JS, BUTTON_JS)
    Appendix B. Font measurements                                    (METRICS)

The only library is pikepdf (MPL-2.0). Everything else is Python's standard library.
"""
import datetime
import importlib.util
import io
import json
import os
import re
import sys
import zlib

import pikepdf
from pikepdf import Array, Dictionary, Name, String


# ====================================================================================================================
# 1. QUESTION HELPERS: HOW A FORM FILE DESCRIBES ITS QUESTIONS
# ====================================================================================================================
# A form file (lc.py is one) imports these and writes one line per question, for example
#     text("term_days", "Term: days", requiredIf=when("drafts_at", "Term"), format="number"),
# = a half-width text box named term_days, labelled "Term: days", mandatory (and unlocked) only when Drafts at is
# Term, digits only. The layout, numbering, scripts and QR code all follow from these lines.
#
# Question kinds:
#     text(id, label)              one-line text box (half width unless half=False)
#     long(id, label)              paragraph box
#     date(id, label)              date: a calendar box in Acrobat, a drop-down of dates elsewhere
#     radio(id, label, options)    pick one
#     checks(id, label, options=[...])   tick any
#     check(id, label)             one tick box
#     select(id, label, options=[...])   drop-down
# Options for any question:
#     required=True                    always mandatory (red *)
#     requiredIf=ticked("x")           mandatory, and unlocked, only when tick box x is ticked
#     requiredIf=when("x", "A", "B")   mandatory only when x is A or B
#     requiredIf=answered("x")         mandatory once x has any answer (never locked)
#     activeIf=ticked("x")             only applies (unlocked) when x is ticked, but optional
#     max=35                           at most 35 characters
#     format="amount"                  amount / number / phone / account (see FORMATS in section 2)
#     half=False / half=True           full or half width
#     beside=69.3                      label beside a box this wide, even when the label is long
# Sections:  section("Title", fields=[...]), plus note="..." (text under the heading), bankOnly=True (shaded,
# "For Bank Use Only"), signoff=True (signature, date and company stamp lines).

def question(kind):
    """A helper for one kind of question: question("long")("goods", "Goods") -> {"id": ..., "label": ..., "kind": "long"}."""
    def make(id, label, **more):
        return {"id": id, "label": label, "kind": kind, **more}
    return make


long, date, checks, select, check = question("long"), question("date"), question("checks"), question("select"), question("check")


def text(id, label, **more):
    return {"id": id, "label": label, "kind": "text", "half": True, **more}


def radio(id, label, options, **more):
    return {"id": id, "label": label, "kind": "radio", "options": options, **more}


def section(title, **more):
    return {"title": title, **more}


def when(field, *values):
    """Rule: field's answer is one of values."""
    return [{"field": field, "values": list(values)}]


def ticked(field):
    """Rule: tick box field is ticked."""
    return when(field, "true")


def answered(field):
    """Rule: field has any answer."""
    return [{"field": field, "values": [""], "not": True}]


# ====================================================================================================================
# 2. SETTINGS: PAGE, COLOURS, SIZES, ANSWER FORMATS
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
# 3. TEXT HELPERS
# ====================================================================================================================
# Text helpers: making text safe for the PDF's built-in fonts, measuring it, and wrapping it into lines.
#
# The form uses only the fonts every PDF reader has built in (Helvetica, Helvetica-Bold and ZapfDingbats), so no
# font files are embedded. Those fonts cover Western European characters (the "WinAnsi" set).


# Characters outside WinAnsi that have a plain equivalent.
PLAIN = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."}


def safe(s):
    """Text the built-in fonts can draw: curly quotes and dashes become plain ones; anything else unknown becomes '?'."""
    return re.sub(r"[^\n\x20-\x7e\xa0-\xff€]", lambda m: PLAIN.get(m.group(0), "?"), s or "")


# Text is measured with Adobe's own Helvetica widths (METRICS, in Appendix B at the end of this file), so it is
# placed exactly as Acrobat will draw it.


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
# 4. RULES AND DATES
# ====================================================================================================================
# The form's rules, evaluated in Python while building (the same rules also run in Acrobat, see DOCUMENT_JS in Appendix A).
#
# A question's rules come from the form file (section 1):
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
# 5. STEP 1: LAY OUT THE PAGES
# ====================================================================================================================
# Walks through the form (the form file's FORM) section by section and decides where everything goes. It produces:
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
        """form: FORM from the form file. answers: its starting answers (DEFAULTS).
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
        # 13.2 uses `beside` (a fixed box width, set in the form file) to match the approved 4-page copy.
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
            # JavaScript shows it (lcDates in DOCUMENT_JS). AFDate_* are Acrobat's own date functions.
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
        """A last page with room for two QR codes of the answers, one above the other, and the Generate QR Code and
        Print Form buttons at the bottom. DOCUMENT_JS draws the codes in Acrobat: usually one code fills the first
        frame; only when the answers are too long for one code does the second frame appear, with the rest."""
        self.new_page()
        self.text("APPLICATION QR CODE (FOR BANK USE)", M, H - 56, 11, True)
        y = H - 70
        for line in wrap("When the form is filled in, press Generate QR Code (at the bottom of this page), then Print Form. The Bank scans the code to read the application (all the answers, as JSON). If the answers are too long for one code, a second code appears under the first: the Bank scans both. Do not write on or fold the codes.", 8, W - 2 * M):
            self.text(line, M, y, 8, color=GREY)
            y -= 10
        buttons_y = 46                                         # the buttons sit just above the footer line
        label, gap = 12, 8                                     # room for "QR code 1 of 2" above each frame; gap between
        size = int((y - 4 - (buttons_y + 30) - 2 * label - gap) / 2)   # two equal frames fill the rest of the page
        x = (W - size) / 2
        first_y = y - 4 - label - size
        self.qr = {"page": self.page.number, "slots": [(x, first_y, size), (x, first_y - gap - label - size, size)],
                   "button": ((W - 312) / 2, buttons_y)}
        self.rect(x, first_y, size, size, border=RULE, border_width=0.5)   # the second frame is a field, shown when needed

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
# 6. STEP 2: ADD THE SCRIPTS, BUTTONS AND QR CODE ROWS
# ====================================================================================================================
# Everything interactive in the PDF is Acrobat JavaScript, kept as text in Appendix A. This step:
#   1. builds the "rules table" (which questions are mandatory, when, and their formats) from the form, and fills it
#      into DOCUMENT_JS (the rules engine, the QR code's text and the QR encoder): the one document-level
#      script stored in the PDF, named "lcRules".
#   2. says when the rules run: when a tick box or option is clicked, and when the person leaves a box
#   3. adds the hidden helper fields, the rows of the two QR codes, and the buttons (Check form, Reset form on every page;
#      Generate QR Code and Print Form on the QR page)
# It only adds field descriptions to the layout; step 3 makes the PDF objects.

RUN_RULES = "lcRules(this);"   # the call every event uses


def script(name, **values):
    """A script ("document", or a button's name such as "check-form"), with its __PLACEHOLDERS__ filled in."""
    text = DOCUMENT_JS if name == "document" else BUTTON_JS[name]
    for key, value in values.items():
        text = text.replace(f"__{key}__", value)
    return text


def rules_table(layout):
    """What the rules engine (DOCUMENT_JS) needs to know about each question, in form order (so Check form lists problems top to
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
    """The one document-level script (DOCUMENT_JS), filled in for this form."""
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

    # The QR codes: a hidden field "__qr" holds the answers as JSON; DOCUMENT_JS draws each code into 177 read-only
    # "comb" text boxes, one per row of the code (a comb box spaces its characters evenly). Each dark square is
    # the letter "n" in the ZapfDingbats font, which prints as a solid black square. This avoids Acrobat's own
    # barcode feature, which some installations don't have.
    # There are two codes' worth of rows: "__qr1_0" ... "__qr1_176" and "__qr2_0" ... "__qr2_176". The second code,
    # its frame ("__qr2_frame") and the labels ("__qr1_label", "__qr2_label") stay empty / hidden unless the
    # answers are too long for one code.
    qr = layout.qr
    layout.page = layout.pages[qr["page"]]
    holder = layout.add_field("__qr", "text", size=3)
    layout.add_widget(holder, -20, -20, 1, 1, hidden=True, border=INK, bg=WHITE)
    for k, (x, y0, size) in enumerate(qr["slots"], 1):
        label = layout.add_field(f"__qr{k}_label", "text", read_only=True, size=8)
        layout.add_widget(label, x, y0 + size + 1, size, 10)
        if k > 1:
            frame = layout.add_field(f"__qr{k}_frame", "text", read_only=True)
            layout.add_widget(frame, x, y0, size, size, hidden=True, border=RULE, border_width=0.5)
        module = size / 185   # 177 squares + 4 squares of white margin on each side
        font_size = "/ZaDb %s Tf 0 g" % fmt(round(module / 0.692 * 1000) / 1000)   # the square is 0.692 of the font size
        for y in range(177):
            row = layout.add_field(f"__qr{k}_{y}", "text", max=177, comb=True, appearance=font_size)
            layout.add_widget(row, x + 4 * module, y0 + size - (5 + y) * module, 177 * module, module)

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
# 7. STEP 3: WRITE THE PDF
# ====================================================================================================================
# Turns the layout (pages, field descriptions, links) and the document script into a PDF:
#   - each page with its drawing (its "content stream") and the fonts it uses
#   - every field, with its settings and an "appearance" (a small drawing of how the box looks, so it shows
#     correctly in any PDF reader before anyone types into it)
#   - the page links, the document script, and the warnings before save / print
#   - a copy of the form's description (JSON of FORM) inside the PDF, for the bank's workbench to read
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

        # 2. Document information, and the form's description (FORM as JSON) for the workbench.
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
            if field.get("read_only"):
                flags |= READ_ONLY
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
# 8. BUILD: RUN THE THREE STEPS
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
# 9. SELF-CHECK: OPEN THE BUILT PDF AND CHECK IT
# ====================================================================================================================
# Opens the finished PDF and checks that every question in the form file became the right fields, with their rules, limits
# and starting answers, and that the scripts, buttons and QR code rows are there. Stops with an error if not.
# (The scripts themselves run only inside Acrobat; test them there, see README "Testing in Acrobat".)

def self_check(pdf_bytes, spec):
    """spec: the form file (FORM, DEFAULTS, PAGES). Returns a one-line summary; stops with the reason if anything is wrong."""
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    fields = {str(f.T): f for f in pdf.Root.AcroForm.Fields}
    questions = [q for s in spec.FORM["sections"] for q in s["fields"]]
    problems = pdf.check_pdf_syntax()
    assert not problems, f"PDF structure problems: {problems}"
    if spec.PAGES:
        assert len(pdf.pages) == spec.PAGES, f"expected {spec.PAGES} pages (PAGES in the form file), got {len(pdf.pages)}"

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
    for key, value in spec.DEFAULTS.items():
        f = fields[key]
        assert "/DV" in f, f"no reset value for {key}"
        if isinstance(value, str) and f.FT == "/Tx":
            assert str(f.V) == value, f"{key} starts as {f.V}"

    # The document script holds the rules table, the QR code's text and the QR encoder.
    doc_script = zlib.decompress(pdf.Root.Names.JavaScript.Names[1].JS.read_raw_bytes()).decode("latin-1")
    for name in ("function lcRules(", "function lcDates(", "function lcPayload(", "function lcQrMatrix(", "function lcDrawQr("):
        assert name in doc_script, f"script lacks {name}"
    table = json.loads(re.search(r"var M = (\{.*?\});\n", doc_script).group(1))
    for q in questions:   # every rule in the form file reached the rules table unchanged
        if q.get("required") or q.get("requiredIf") or q.get("activeIf"):
            assert q["id"] in table, f"{q['id']} not in the rules table"
        assert table.get(q["id"], {}).get("always") == (1 if q.get("required") else None), f"'always' wrong on {q['id']}"
        rules = [[r["field"], [safe(v) for v in r["values"]], 1 if r.get("not") else 0] for r in q.get("requiredIf") or []]
        assert table.get(q["id"], {}).get("requiredIf") == (rules or None), f"requiredIf wrong on {q['id']}"

    # Buttons, the hidden re-check field, and the QR code rows.
    for name in ("__check_form", "__reset_form", "__generate_qr", "__print_form", "__checks", "__qr"):
        assert name in fields, f"missing {name}"
    assert len(fields["__check_form"].Kids) == len(pdf.pages), "Check form should be on every page"
    assert all(f"__qr{k}_{y}" in fields for k in (1, 2) for y in range(177)), "missing QR code rows"
    assert int(fields["__qr2_frame"].Kids[0].F) == 2, "the second QR frame should start hidden"
    assert "/WS" in pdf.Root.AA and "/WP" in pdf.Root.AA, "missing the warning before save / print"
    return f"PASS: {len(pdf.pages)} pages, {len(fields)} fields, rules table, scripts, buttons and QR rows OK"


# ====================================================================================================================
# 10. RUN: LOAD THE FORM FILE, BUILD, CHECK, SAVE
# ====================================================================================================================
# python build_form.py lc.py  reads these names from the form file:
#   FORM       the form: title, note, issuer, formCode, sections (required)
#   DEFAULTS   answers already filled in when the form opens (optional)
#   PDF_NAME   the file to write in out/ (optional; default: the title, e.g. "Irrevocable-Documentary-Credit.pdf")
#   PAGES      the number of pages the form must fit on; the build stops if it doesn't (optional)
# The PDF, and a small page for viewing it (out/index.html), go in out/ beside the form file.
# To view it in a browser:  python -m http.server 8090 -d out   ->  http://localhost:8090

def load_form(path):
    """The form file as a module, with the optional names filled in."""
    sys.dont_write_bytecode = True   # always read the form file fresh (no cached copy of an older version)
    loader = importlib.util.spec_from_file_location("form_file", path)
    spec = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(spec)
    assert hasattr(spec, "FORM"), f"{path} has no FORM"
    spec.DEFAULTS = getattr(spec, "DEFAULTS", {})
    spec.PDF_NAME = getattr(spec, "PDF_NAME", re.sub(r"\W+", "-", spec.FORM["title"]).strip("-") + ".pdf")
    spec.PAGES = getattr(spec, "PAGES", None)
    return spec


def index_html(title, pdf_name):
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>{title}</title>
<style>body {{ font: 15px Arial, sans-serif; margin: 0; }} p {{ margin: 12px 16px; }} iframe {{ border: 0; width: 100%; height: calc(100vh - 48px); }}</style>
<p><a href="{pdf_name}" download>Download the form</a> (open it in Adobe Acrobat or Reader: the checks, red boxes and QR code need Acrobat's JavaScript).</p>
<iframe src="{pdf_name}" title="{title}"></iframe>
</html>
"""


def main(form_path):
    spec = load_form(form_path)
    pdf_bytes = build(spec.FORM, spec.DEFAULTS)
    result = self_check(pdf_bytes, spec)          # stops here, with the reason, if anything is wrong
    out_dir = os.path.join(os.path.dirname(os.path.abspath(form_path)), "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, spec.PDF_NAME), "wb") as f:
        f.write(pdf_bytes)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html(spec.FORM["title"], spec.PDF_NAME))
    print(f"Wrote out/{spec.PDF_NAME}")
    print(result)


# ====================================================================================================================
# APPENDIX A. THE SCRIPTS THAT RUN INSIDE ACROBAT
# ====================================================================================================================
# The PDF's JavaScript, stored here as text and copied into the PDF by step 2 (add_scripts). Acrobat's JavaScript is
# old-style: var, no arrow functions, no let/const. The __NAMES__ in capitals are filled in for each form by
# document_script (step 2).

# The document script, stored in the PDF as "lcRules": the rules engine, the QR code's text and the QR encoder.
DOCUMENT_JS = r"""
// THE RULES ENGINE (runs inside Acrobat). Built into the PDF as the document script "lcRules".
// lcRules(doc) checks every question and colours its box:
//   blank or wrong mandatory answer -> red outline, pink fill, marked Required
//   answered and right              -> black outline, white fill
//   doesn't apply yet               -> greyed out, locked, and its answer cleared
// It returns the list of missing questions, plus .bad (wrong answers) and .first (where to put the cursor).
// lcDates(doc) shows each date's calendar box and hides its drop-down list (Acrobat only).
// __MODEL__ is filled in by document_script (step 2) with the rules table built from the form; __DATES__ with the date
// question ids. Acrobat's JavaScript is old-style: var, no arrow functions.
function lcRules(d) {
var M = __MODEL__;
function has(list, x) { for (var i = 0; i < list.length; i++) if (list[i] == x) return true; return false; }

// The answer to question id, read from the PDF's fields.
function val(id) {
  var m = M[id], f, a = [], i;
  if (m.kind == "checks") { for (i = 0; i < m.options.length; i++) { f = d.getField(id + "__" + i); if (f && f.value != "Off") a.push(m.options[i]); } return a; }
  if (m.kind == "date" && shown(id)) return d.getField(id).valueAsString;
  if (m.kind == "date" && d.getField(id + "__list")) { a = /^(\d\d) (\w{3}) (\d{4})$/.exec(d.getField(id + "__list").valueAsString);
    return a ? a[1] + "/" + ("0" + ("JanFebMarAprMayJunJulAugSepOctNovDec".indexOf(a[2]) / 3 + 1)).slice(-2) + "/" + a[3] : ""; }
  f = d.getField(id); if (!f) return "";
  if (m.kind == "check") return f.value != "Off" ? "true" : "false";
  return f.value == "Off" ? "" : String(f.value);
}
function shown(id) { var f = d.getField(id); return !!f && f.display != 1; } // 1 = display.hidden
function empty(x) { return typeof x == "object" ? !x.length : x === ""; }

// Does any of these rules hold?
function any(rules) {
  var i, j, x, hit;
  for (i = 0; i < rules.length; i++) {
    x = val(rules[i][0]); hit = false;
    if (typeof x == "object") { for (j = 0; j < x.length; j++) if (has(rules[i][1], x[j])) hit = true; } else hit = has(rules[i][1], x);
    if (rules[i][2] ? !hit && !empty(x) : hit) return true;
  }
  return false;
}
function mandatory(id) { var m = M[id]; return m.always ? true : any(m.requiredIf || []); }

// What is wrong with a typed answer, or "".
function wrong(id) {
  var m = M[id], f = d.getField(id), s = m.kind == "date" ? val(id) : f ? f.valueAsString : "", x, k;
  if (!m.check || !s) return "";
  x = s.match(new RegExp("[^A-Za-z0-9 .,\\-/()':?+#&@%\\r\\n]", "g"));
  if (x) { k = []; for (var i = 0; i < x.length; i++) if (!has(k, x[i])) k.push(x[i]); return "remove " + k.join(" ") + " (letters, digits and . , - / ( ) ' : ? + # & @ % only)"; }
  if (m.kind == "date") { x = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(s); k = x && new Date(+x[3], x[2] - 1, +x[1]); return k && k.getDate() == +x[1] && k.getMonth() == x[2] - 1 ? "" : "not a real date (DD/MM/YYYY)"; }
  return m.check.length && !new RegExp(m.check[0]).test(s) ? m.check[1] : "";
}

// A real DD/MM/YYYY date as a Date, or null.
function day(s) { var x = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(s), k = x && new Date(+x[3], x[2] - 1, +x[1]); return k && k.getDate() == +x[1] && k.getMonth() == x[2] - 1 ? k : null; }
function v(id) { return M[id] ? val(id) : ""; }

// Checks across answers (the same as cross-checks in form/validate.ts). Skipped when a form doesn't have the fields.
function across() {
  var X = {}, A = day(v("application_date")), S = day(v("latest_shipment_date")), E = day(v("expiry_date")), a = v("amount"), pb = v("price_basis");
  if (S && E && E < S) X.expiry_date = "is before the latest shipment date";
  else if (A && E && E < A) X.expiry_date = "is before the application date";
  if (A && S && S < A) X.latest_shipment_date = "is before the application date";
  if (A && A.getTime() > new Date().getTime()) X.application_date = "is in the future";
  if (/^[\d,]+(\.\d+)?$/.test(a) && !(Number(a.replace(/,/g, "")) > 0)) X.amount = "must be more than zero";
  if (v("insurance_arrangement") && (pb == "CIF" || pb == "CIP")) X.insurance_arrangement = "is only for FOB/CFR/FCA/CPT, but price basis is " + pb + " (the beneficiary insures)";
  return X;
}

// Clears a question's box, so an answer can't stay behind in a question that doesn't apply.
function clear(f, kind) {
  if (kind == "check" || kind == "checks" || kind == "radio") { if (f.value != "Off") f.value = "Off"; }
  else if (f.type == "combobox" && /__list$/.test(f["name"])) { if (f.currentValueIndices != 0) f.currentValueIndices = 0; } // a date list: back to "Pick a date"
  else if (f.value !== "" && f.value != null) f.value = "";
}

// Go through every question: work out its state, then colour (and lock) its boxes.
var missing = [], bad = [], first = "", id, m, applies, required, problem, whatsWrong, names, i, f, X;
try {
X = across();
for (id in M) {
  m = M[id]; if (!m.hasRule && !m.check && !m.activeIf) continue;
  applies = !m.activeIf || any(m.activeIf);
  required = m.hasRule && applies ? mandatory(id) : false;
  problem = required && (m.kind == "check" ? val(id) != "true" : empty(val(id)));
  if (problem) missing.push(m.label);
  whatsWrong = applies ? wrong(id) || X[id] || "" : ""; if (whatsWrong) { bad.push(m.label + ": " + whatsWrong); problem = true; }
  names = [id]; if (m.kind == "checks") { names = []; for (i = 0; i < m.options.length; i++) names.push(id + "__" + i); }
  if (m.kind == "date" && !shown(id) && d.getField(id + "__list")) names = [id + "__list"];
  if (problem && !first) first = names[0];
  for (i = 0; i < names.length; i++) {
    f = d.getField(names[i]); if (!f) continue;
    if (m.hasRule && m.kind != "checks") f.required = !!(required && problem); // only while blank or wrong: Acrobat outlines Required boxes in red even when filled
    if (m.activeIf) f.readonly = !applies;                                                   // locked until it applies
    if (!applies) { clear(f, m.kind); f.lineWidth = 1; f.strokeColor = ["G", 0.6]; f.fillColor = ["G", 0.86]; continue; } // grey, cleared
    f.lineWidth = problem || !m.underlined ? 1 : 0;
    f.strokeColor = problem ? color.red : m.underlined ? color.transparent : color.black;    // red when blank or wrong
    f.fillColor = problem ? ["RGB", 1, 0.88, 0.88] : m.underlined ? color.transparent : color.white;
  }
}
} catch (e) { console.println("lcRules: " + e); }
missing.bad = bad;
missing.first = first; // the field of the first problem, for "Check form" to go to
return missing;
}

// Acrobat only: show each date's calendar box and hide its drop-down list.
function lcDates(d) {
  var D = __DATES__, i, t, p;
  for (i = 0; i < D.length; i++) { t = d.getField(D[i]); if (!t) continue; t.display = display.visible;
    p = d.getField(D[i] + "__list"); if (p) p.display = display.hidden; }
}
// On opening in Acrobat: show the calendars, and set every box's colour and lock.
if (typeof app != "undefined" && /^(Exchange|Reader)/.test(app.viewerType)) { lcDates(this); lcRules(this); }
// THE QR CODE'S TEXT. lcPayload(doc) returns every answered question as JSON:
//   {"form": "LC-01", "version": "1.0", "saved": "...", "complete": true, "data": {field id: answer, ...}}
// Tick boxes become true; "tick any" questions become lists of the ticked options. One QR code holds 2,300
// characters of it; longer answers take two codes (lcDrawQr splits the text). The text is padded with spaces to
// 2,300 (or 4,600 for two codes). __GROUPS__, __LONG__, __FORM__ and __VERSION__ are filled in by document_script
// (step 2).
function lcPayload(d) {
var G = {__GROUPS__}, LONG = __LONG__, CAP = 2300;
var data = {}, i, n, f, k, v, g, m, out, cut = [], ok = true, t = new Date();
for (i = 0; i < d.numFields; i++) {
  n = d.getNthFieldName(i); if (/^__/.test(n) || /__list$/.test(n)) continue;
  f = d.getField(n); if (!f || f.type == "button" || f.type == "signature") continue;
  g = /^(.+)__(\d+)$/.exec(n);
  if (g && G[g[1]]) { if (f.value != "Off") { if (!data[g[1]]) data[g[1]] = []; data[g[1]].push(G[g[1]][+g[2]]); } continue; }
  if (f.type == "checkbox") { if (f.value != "Off") data[n] = true; continue; }
  v = f.type == "radiobutton" ? (f.value == "Off" ? "" : String(f.value)) : String(f.valueAsString).replace(/^\s+|\s+$/g, "");
  if (v !== "") data[n] = v;
}
if (typeof lcRules == "function") { m = lcRules(d); ok = !m.length && !(m.bad || []).length; }
function pad(x) { return ("0" + x).slice(-2); }
out = {"form": __FORM__, "version": __VERSION__, "saved": t.getFullYear() + "-" + pad(t.getMonth() + 1) + "-" + pad(t.getDate()) + "T" + pad(t.getHours()) + ":" + pad(t.getMinutes()), "complete": ok, "data": data};
// Two QR codes hold 4,600 characters: if the answers are longer still, shorten the two long paragraphs and say so.
for (i = 0; i < LONG.length && JSON.stringify(out).length > 2 * CAP; i++) {
  k = LONG[i]; if (!data[k]) continue;
  cut.push(k); out.truncated = cut;
  v = JSON.stringify(out).length - 2 * CAP + 3;
  data[k] = v < data[k].length ? data[k].slice(0, data[k].length - v) + "..." : "...";
}
// Padded with spaces to fill one code (2,300) or, when it doesn't fit in one, two codes (4,600).
v = JSON.stringify(out); n = v.length > CAP ? 2 * CAP : CAP; while (v.length < n) v += " ";
return v;
}
// THE QR CODE ENCODER AND DRAWING (standard QR code, no library needed).
// lcQrMatrix(bytes, part) returns the 177 x 177 grid of a version 40 QR code (true = dark square). bytes is the
// text as UTF-8 bytes (one character per byte). part is null for a single code, or [index, total, parity] for
// one of several codes ("structured append", part of the QR standard: each code says it is code 1 or 2 of 2,
// so a scanner that supports it joins them; any other scanner reads each code's text, and the two texts are
// joined in order). Version 40, error correction M, byte mode, mask 0; at most 2,329 bytes per code.
function lcQrMatrix(s, part) {
  var N = 177, i, j, x, y, m = [], f = [], bytes = [];
  for (i = 0; i < s.length; i++) bytes.push(s.charCodeAt(i) & 255);
  for (y = 0; y < N; y++) { m.push([]); f.push([]); for (x = 0; x < N; x++) { m[y].push(false); f[y].push(false); } }
  function set(x, y, dark) { m[y][x] = dark; f[y][x] = true; }
  function mul(a, b) { var z = 0; for (var k = 7; k >= 0; k--) { z = (z << 1) ^ ((z >>> 7) * 0x11D); z ^= ((b >>> k) & 1) * a; } return z; }
  // Function patterns: timing, finders, alignment, format area, version, dark module.
  for (i = 0; i < N; i++) { set(6, i, i % 2 == 0); set(i, 6, i % 2 == 0); }
  function finder(cx, cy) { for (var dy = -4; dy <= 4; dy++) for (var dx = -4; dx <= 4; dx++) {
    var d = Math.max(Math.abs(dx), Math.abs(dy)), xx = cx + dx, yy = cy + dy;
    if (xx >= 0 && xx < N && yy >= 0 && yy < N) set(xx, yy, d != 2 && d != 4); } }
  finder(3, 3); finder(N - 4, 3); finder(3, N - 4);
  var A = [6, 30, 58, 86, 114, 142, 170];
  for (i = 0; i < A.length; i++) for (j = 0; j < A.length; j++) {
    if ((i == 0 && j == 0) || (i == 0 && j == A.length - 1) || (i == A.length - 1 && j == 0)) continue;
    for (var dy = -2; dy <= 2; dy++) for (var dx = -2; dx <= 2; dx++) set(A[i] + dx, A[j] + dy, Math.max(Math.abs(dx), Math.abs(dy)) != 1);
  }
  var rem = 0, fmt; for (i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  fmt = ((0 << 10) | rem) ^ 0x5412; // error correction M (00), mask 0
  function bit(v, k) { return ((v >>> k) & 1) != 0; }
  for (i = 0; i <= 5; i++) set(8, i, bit(fmt, i));
  set(8, 7, bit(fmt, 6)); set(8, 8, bit(fmt, 7)); set(7, 8, bit(fmt, 8));
  for (i = 9; i < 15; i++) set(14 - i, 8, bit(fmt, i));
  for (i = 0; i < 8; i++) set(N - 1 - i, 8, bit(fmt, i));
  for (i = 8; i < 15; i++) set(8, N - 15 + i, bit(fmt, i));
  set(8, N - 8, true);
  rem = 40; for (i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1F25);
  var ver = (40 << 12) | rem;
  for (i = 0; i < 18; i++) { var a = N - 11 + i % 3, b = Math.floor(i / 3); set(a, b, bit(ver, i)); set(b, a, bit(ver, i)); }
  // Data: (for one of several codes: mode 0011, its index, the total - 1, the parity of all the text), then mode
  // 0100, 16-bit length, the bytes, terminator, padding to 2,334 data codewords.
  var bits = [], cap = 2334 * 8;
  function put(v, n) { for (var k = n - 1; k >= 0; k--) bits.push((v >>> k) & 1); }
  if (part) { put(3, 4); put(part[0], 4); put(part[1] - 1, 4); put(part[2], 8); }
  put(4, 4); put(bytes.length, 16); for (i = 0; i < bytes.length; i++) put(bytes[i], 8);
  if (bits.length > cap) throw new Error("too much text for one QR code (" + bytes.length + " bytes)");
  put(0, Math.min(4, cap - bits.length)); while (bits.length % 8) bits.push(0);
  var data = []; for (i = 0; i < bits.length; i += 8) { var v = 0; for (j = 0; j < 8; j++) v = (v << 1) | bits[i + j]; data.push(v); }
  for (i = 0; data.length < 2334; i++) data.push(i % 2 ? 0x11 : 0xEC);
  // Reed-Solomon: 49 blocks (18 of 47 + 31 of 48 data codewords), 28 error-correction codewords each.
  var div = [], root = 1; for (i = 0; i < 27; i++) div.push(0); div.push(1);
  for (i = 0; i < 28; i++) { for (j = 0; j < 28; j++) { div[j] = mul(div[j], root); if (j + 1 < 28) div[j] ^= div[j + 1]; } root = mul(root, 2); }
  var blocks = [], k = 0;
  for (i = 0; i < 49; i++) {
    var len = i < 18 ? 47 : 48, dat = data.slice(k, k + len), ecc = []; k += len;
    for (j = 0; j < 28; j++) ecc.push(0);
    for (j = 0; j < dat.length; j++) { var fct = dat[j] ^ ecc.shift(); ecc.push(0); for (var t = 0; t < 28; t++) ecc[t] ^= mul(div[t], fct); }
    if (i < 18) dat.push(-1);
    blocks.push(dat.concat(ecc));
  }
  var all = [];
  for (i = 0; i < blocks[0].length; i++) for (j = 0; j < 49; j++) if (blocks[j][i] != -1) all.push(blocks[j][i]);
  // Place the codewords in the zigzag, then mask 0 ((x + y) even flips).
  var n = 0;
  for (var right = N - 1; right >= 1; right -= 2) {
    if (right == 6) right = 5;
    for (var vert = 0; vert < N; vert++) for (j = 0; j < 2; j++) {
      x = right - j; var up = ((right + 1) & 2) == 0; y = up ? N - 1 - vert : vert;
      if (!f[y][x] && n < all.length * 8) { m[y][x] = ((all[n >>> 3] >>> (7 - (n & 7))) & 1) != 0; n++; }
    }
  }
  for (y = 0; y < N; y++) for (x = 0; x < N; x++) if (!f[y][x] && (x + y) % 2 == 0) m[y][x] = !m[y][x];
  return m;
}
// lcDrawQr(doc, text) draws text as one QR code, or as two when it is too long for one, and returns how many.
// Each code's rows go into the read-only text boxes "__qr1_0" ... "__qr1_176" (and "__qr2_..."), as the letter
// "n" in the ZapfDingbats font (which prints as a black square) for each dark square. The second code's frame
// and the "QR code 1 of 2" labels appear only when there are two. lcDrawQr(doc, "") clears both.
function lcDrawQr(d, text) {
  var ONE = 2329, s = unescape(encodeURIComponent(text)), parts = [], codes = [], parity = 0, i, k, y, x, row, calc = d.calculate;
  if (s.length > 2 * ONE) throw new Error("the answers are too long for two QR codes (" + s.length + " characters, at most " + 2 * ONE + ")");
  for (i = 0; i < s.length; i++) parity ^= s.charCodeAt(i) & 255;
  if (s.length > ONE) parts = [s.slice(0, Math.ceil(s.length / 2)), s.slice(Math.ceil(s.length / 2))];
  else if (s.length) parts = [s];
  for (k = 0; k < parts.length; k++) codes.push(lcQrMatrix(parts[k], parts.length > 1 ? [k, parts.length, parity] : null));
  d.calculate = false; // 354 rows: don't re-run the checks after each one
  try {
    for (k = 1; k <= 2; k++) {
      for (y = 0; y < 177; y++) { row = ""; if (codes[k - 1]) for (x = 0; x < 177; x++) row += codes[k - 1][y][x] ? "n" : " ";
        d.getField("__qr" + k + "_" + y).value = row; }
      d.getField("__qr" + k + "_label").value = codes.length > 1 ? "QR code " + k + " of 2" + (k == 1 ? " (scan both codes)" : "") : "";
    }
    d.getField("__qr2_frame").display = codes.length > 1 ? display.visible : display.hidden;
  } finally { d.calculate = calc; }
  return codes.length;
}
"""[1:-1]

# THE BUTTON AND EVENT SCRIPTS. Each section below, after its "// ==== name ====" line, is stored in the PDF
# as one action. The lines before the first marker (this header) are not stored.
#   check-form    the "Check form" button (top right of every page)
#   reset-form    the "Reset form" button (top right of every page)
#   generate-qr   the "Generate QR Code" button (QR page)
#   print-form    the "Print Form" button (QR page)
#   before-save   runs before the form is saved or printed
# They call the functions in DOCUMENT_JS (lcRules, lcPayload, lcDrawQr, lcDates).
BUTTON_JS = {
    "check-form": r"""
// "CHECK FORM" BUTTON: lists what is missing or wrong (at most 15 of each) and puts the cursor on the first
// problem; otherwise says the form is ready.
var m = typeof lcRules == "function" ? lcRules(this) : [], b = m.bad || [], t = [];
function list(a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("This form is not ready to send. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
  var g = m.first && this.getField(m.first); if (g) g.setFocus(); }
else app.alert("All mandatory questions are answered and every answer is in the right format. You can save the form and send it.", 3);
"""[1:-1],
    "reset-form": r"""
// "RESET FORM" BUTTON: asks first, then sets every answer back to how the form started, and re-checks.
if (app.alert("Are you sure you want to reset the form? All your answers will be cleared.", 2, 2) == 4) {
this.resetForm(); if (typeof lcDrawQr == "function") lcDrawQr(this, ""); if (typeof lcDates == "function") lcDates(this); if (typeof lcRules == "function") lcRules(this); }
"""[1:-1],
    "generate-qr": r"""
// "GENERATE QR CODE" BUTTON: refuses while anything is missing or wrong; otherwise makes the QR code from the
// answers (lcPayload, lcDrawQr), or two codes if the answers don't fit in one, and goes to the QR code page.
var m = typeof lcRules == "function" ? lcRules(this) : [], b = m.bad || [], t = [];
function list(a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("The QR code cannot be generated yet. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them, then press Generate QR Code again.", 1);
  var g = m.first && this.getField(m.first); if (g) g.setFocus(); }
else { try { var q = this.getField("__qr"); q.value = lcPayload(this); var n = lcDrawQr(this, q.value); this.pageNum = this.numPages - 1;
  if (n == 1) app.alert("The QR code has been generated from your answers (" + q.value.length + " characters). Press Print Form to print the form with the QR code.", 3);
  else app.alert("Your answers (" + q.value.length + " characters) are too long for one QR code, so two codes have been generated, one under the other. The Bank scans both. Press Print Form to print the form with the QR codes.", 3); }
  catch (e) { app.alert("The QR code could not be generated: " + e + "\nPlease send this message to the form's maintainer.", 1); } }
"""[1:-1],
    "print-form": r"""
// "PRINT FORM" BUTTON: prints only once the QR code exists and still matches the current answers, so the
// printed code always carries the answers on the paper.
var q = this.getField("__qr"), now = typeof lcPayload == "function" ? lcPayload(this) : "", same = false;
try { same = JSON.stringify(JSON.parse(q.value).data) == JSON.stringify(JSON.parse(now).data); } catch (e) {}
if (!/\S/.test(q.value)) app.alert("Please press Generate QR Code first, so the printed form carries the QR code.", 1);
else if (!same) app.alert("Your answers have changed since the QR code was generated. Please press Generate QR Code again, then Print Form.", 1);
else this.print(true, 0, this.numPages - 1, false, true);
"""[1:-1],
    "before-save": r"""
// BEFORE SAVING OR PRINTING: the same list as Check form, shown only if something is missing or wrong.
// It warns but doesn't stop the save or print.
var m = typeof lcRules == "function" ? lcRules(this) : [], b = m.bad || [], t = [];
function list(a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("This form is not ready to send. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
   }

"""[1:-1],
}


# ====================================================================================================================
# APPENDIX B. FONT MEASUREMENTS
# ====================================================================================================================
# Adobe's published Helvetica and Helvetica-Bold metrics: each character's width ("widths") and the kerning between
# pairs of characters ("kern"), in 1/1000 of the font size. Used by width() to place labels, wrap text and size boxes.
METRICS = {
    'helv': {
        'widths': {
            '0': 556, '1': 556, '2': 556, '3': 556, '4': 556, '5': 556, '6': 556, '7': 556, '8': 556, '9': 556, ' ':
            278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667, "'": 191, '(': 333, ')': 333, '*': 389,
            '+': 584, ',': 278, '-': 333, '.': 278, '/': 278, ':': 278, ';': 278, '<': 584, '=': 584, '>': 584, '?':
            556, '@': 1015, 'A': 667, 'B': 667, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278,
            'J': 500, 'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778, 'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T':
            611, 'U': 722, 'V': 667, 'W': 944, 'X': 667, 'Y': 667, 'Z': 611, '[': 278, '\\': 278, ']': 278, '^': 469,
            '_': 556, '`': 333, 'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556, 'f': 278, 'g': 556, 'h': 556, 'i':
            222, 'j': 222, 'k': 500, 'l': 222, 'm': 833, 'n': 556, 'o': 556, 'p': 556, 'q': 556, 'r': 333, 's': 500,
            't': 278, 'u': 556, 'v': 500, 'w': 722, 'x': 500, 'y': 500, 'z': 500, '{': 334, '|': 260, '}': 334, '~':
            584, '\xa0': 278, '¡': 333, '¢': 556, '£': 556, '¤': 556, '¥': 556, '¦': 260, '§': 556, '¨': 333, '©':
            737, 'ª': 370, '«': 556, '¬': 584, '\xad': 333, '®': 737, '¯': 333, '°': 400, '±': 584, '²': 333, '³':
            333, '´': 333, 'µ': 556, '¶': 537, '·': 278, '¸': 333, '¹': 333, 'º': 365, '»': 556, '¼': 834, '½': 834,
            '¾': 834, '¿': 611, 'À': 667, 'Á': 667, 'Â': 667, 'Ã': 667, 'Ä': 667, 'Å': 667, 'Æ': 1000, 'Ç': 722, 'È':
            667, 'É': 667, 'Ê': 667, 'Ë': 667, 'Ì': 278, 'Í': 278, 'Î': 278, 'Ï': 278, 'Ð': 722, 'Ñ': 722, 'Ò': 778,
            'Ó': 778, 'Ô': 778, 'Õ': 778, 'Ö': 778, '×': 584, 'Ø': 778, 'Ù': 722, 'Ú': 722, 'Û': 722, 'Ü': 722, 'Ý':
            667, 'Þ': 667, 'ß': 611, 'à': 556, 'á': 556, 'â': 556, 'ã': 556, 'ä': 556, 'å': 556, 'æ': 889, 'ç': 500,
            'è': 556, 'é': 556, 'ê': 556, 'ë': 556, 'ì': 278, 'í': 278, 'î': 278, 'ï': 278, 'ð': 556, 'ñ': 556, 'ò':
            556, 'ó': 556, 'ô': 556, 'õ': 556, 'ö': 556, '÷': 584, 'ø': 611, 'ù': 556, 'ú': 556, 'û': 556, 'ü': 556,
            'ý': 500, 'þ': 556, 'ÿ': 500, '€': 556
        },
        'kern': {
            ' T': -50, ' V': -50, ' W': -40, ' Y': -90, ' Ý': -90, '. ': -60, '.\xa0': -60, ': ': -50, ':\xa0': -50,
            '; ': -50, ';\xa0': -50, 'AC': -30, 'AG': -30, 'AO': -30, 'AQ': -30, 'AT': -120, 'AU': -50, 'AV': -70,
            'AW': -50, 'AY': -100, 'Au': -30, 'Av': -40, 'Aw': -40, 'Ay': -40, 'AÇ': -30, 'AÒ': -30, 'AÓ': -30, 'AÔ':
            -30, 'AÕ': -30, 'AÖ': -30, 'AØ': -30, 'AÙ': -50, 'AÚ': -50, 'AÛ': -50, 'AÜ': -50, 'AÝ': -100, 'Aù': -30,
            'Aú': -30, 'Aû': -30, 'Aü': -30, 'Aý': -40, 'Aÿ': -40, 'B,': -20, 'B.': -20, 'BU': -10, 'BÙ': -10, 'BÚ':
            -10, 'BÛ': -10, 'BÜ': -10, 'C,': -30, 'C.': -30, 'D,': -70, 'D.': -70, 'DA': -40, 'DV': -70, 'DW': -40,
            'DY': -90, 'DÀ': -40, 'DÁ': -40, 'DÂ': -40, 'DÃ': -40, 'DÄ': -40, 'DÅ': -40, 'DÝ': -90, 'F,': -150, 'F.':
            -150, 'FA': -80, 'Fa': -50, 'Fe': -30, 'Fo': -30, 'Fr': -45, 'FÀ': -80, 'FÁ': -80, 'FÂ': -80, 'FÃ': -80,
            'FÄ': -80, 'FÅ': -80, 'Fà': -50, 'Fá': -50, 'Fâ': -50, 'Fã': -50, 'Fä': -50, 'Få': -50, 'Fè': -30, 'Fé':
            -30, 'Fê': -30, 'Fë': -30, 'Fò': -30, 'Fó': -30, 'Fô': -30, 'Fõ': -30, 'Fö': -30, 'Fø': -30, 'J,': -30,
            'J.': -30, 'JA': -20, 'Ja': -20, 'Ju': -20, 'JÀ': -20, 'JÁ': -20, 'JÂ': -20, 'JÃ': -20, 'JÄ': -20, 'JÅ':
            -20, 'Jà': -20, 'Já': -20, 'Jâ': -20, 'Jã': -20, 'Jä': -20, 'Jå': -20, 'Jù': -20, 'Jú': -20, 'Jû': -20,
            'Jü': -20, 'KO': -50, 'Ke': -40, 'Ko': -40, 'Ku': -30, 'Ky': -50, 'KÒ': -50, 'KÓ': -50, 'KÔ': -50, 'KÕ':
            -50, 'KÖ': -50, 'KØ': -50, 'Kè': -40, 'Ké': -40, 'Kê': -40, 'Kë': -40, 'Kò': -40, 'Kó': -40, 'Kô': -40,
            'Kõ': -40, 'Kö': -40, 'Kø': -40, 'Kù': -30, 'Kú': -30, 'Kû': -30, 'Kü': -30, 'Ký': -50, 'Kÿ': -50, 'LT':
            -110, 'LV': -110, 'LW': -70, 'LY': -140, 'Ly': -30, 'LÝ': -140, 'Lý': -30, 'Lÿ': -30, 'O,': -40, 'O.':
            -40, 'OA': -20, 'OT': -40, 'OV': -50, 'OW': -30, 'OX': -60, 'OY': -70, 'OÀ': -20, 'OÁ': -20, 'OÂ': -20,
            'OÃ': -20, 'OÄ': -20, 'OÅ': -20, 'OÝ': -70, 'P,': -180, 'P.': -180, 'PA': -120, 'Pa': -40, 'Pe': -50,
            'Po': -50, 'PÀ': -120, 'PÁ': -120, 'PÂ': -120, 'PÃ': -120, 'PÄ': -120, 'PÅ': -120, 'Pà': -40, 'Pá': -40,
            'Pâ': -40, 'Pã': -40, 'Pä': -40, 'På': -40, 'Pè': -50, 'Pé': -50, 'Pê': -50, 'Pë': -50, 'Pò': -50, 'Pó':
            -50, 'Pô': -50, 'Põ': -50, 'Pö': -50, 'Pø': -50, 'QU': -10, 'QÙ': -10, 'QÚ': -10, 'QÛ': -10, 'QÜ': -10,
            'RO': -20, 'RT': -30, 'RU': -40, 'RV': -50, 'RW': -30, 'RY': -50, 'RÒ': -20, 'RÓ': -20, 'RÔ': -20, 'RÕ':
            -20, 'RÖ': -20, 'RØ': -20, 'RÙ': -40, 'RÚ': -40, 'RÛ': -40, 'RÜ': -40, 'RÝ': -50, 'S,': -20, 'S.': -20,
            'T,': -120, 'T-': -140, 'T.': -120, 'T:': -20, 'T;': -20, 'TA': -120, 'TO': -40, 'Ta': -120, 'Te': -120,
            'To': -120, 'Tr': -120, 'Tu': -120, 'Tw': -120, 'Ty': -120, 'T\xad': -140, 'TÀ': -120, 'TÁ': -120, 'TÂ':
            -120, 'TÃ': -120, 'TÄ': -120, 'TÅ': -120, 'TÒ': -40, 'TÓ': -40, 'TÔ': -40, 'TÕ': -40, 'TÖ': -40, 'TØ':
            -40, 'Tà': -120, 'Tá': -120, 'Tâ': -120, 'Tã': -60, 'Tä': -120, 'Tå': -120, 'Tè': -60, 'Té': -120, 'Tê':
            -120, 'Të': -120, 'Tò': -120, 'Tó': -120, 'Tô': -120, 'Tõ': -60, 'Tö': -120, 'Tø': -120, 'Tù': -120, 'Tú':
            -120, 'Tû': -120, 'Tü': -120, 'Tý': -120, 'Tÿ': -60, 'U,': -40, 'U.': -40, 'UA': -40, 'UÀ': -40, 'UÁ':
            -40, 'UÂ': -40, 'UÃ': -40, 'UÄ': -40, 'UÅ': -40, 'V,': -125, 'V-': -80, 'V.': -125, 'V:': -40, 'V;': -40,
            'VA': -80, 'VG': -40, 'VO': -40, 'Va': -70, 'Ve': -80, 'Vo': -80, 'Vu': -70, 'V\xad': -80, 'VÀ': -80,
            'VÁ': -80, 'VÂ': -80, 'VÃ': -80, 'VÄ': -80, 'VÅ': -80, 'VÒ': -40, 'VÓ': -40, 'VÔ': -40, 'VÕ': -40, 'VÖ':
            -40, 'VØ': -40, 'Và': -70, 'Vá': -70, 'Vâ': -70, 'Vã': -70, 'Vä': -70, 'Vå': -70, 'Vè': -80, 'Vé': -80,
            'Vê': -80, 'Vë': -80, 'Vò': -80, 'Vó': -80, 'Vô': -80, 'Võ': -80, 'Vö': -80, 'Vø': -80, 'Vù': -70, 'Vú':
            -70, 'Vû': -70, 'Vü': -70, 'W,': -80, 'W-': -40, 'W.': -80, 'WA': -50, 'WO': -20, 'Wa': -40, 'We': -30,
            'Wo': -30, 'Wu': -30, 'Wy': -20, 'W\xad': -40, 'WÀ': -50, 'WÁ': -50, 'WÂ': -50, 'WÃ': -50, 'WÄ': -50,
            'WÅ': -50, 'WÒ': -20, 'WÓ': -20, 'WÔ': -20, 'WÕ': -20, 'WÖ': -20, 'WØ': -20, 'Wà': -40, 'Wá': -40, 'Wâ':
            -40, 'Wã': -40, 'Wä': -40, 'Wå': -40, 'Wè': -30, 'Wé': -30, 'Wê': -30, 'Wë': -30, 'Wò': -30, 'Wó': -30,
            'Wô': -30, 'Wõ': -30, 'Wö': -30, 'Wø': -30, 'Wù': -30, 'Wú': -30, 'Wû': -30, 'Wü': -30, 'Wý': -20, 'Wÿ':
            -20, 'Y,': -140, 'Y-': -140, 'Y.': -140, 'Y:': -60, 'Y;': -60, 'YA': -110, 'YO': -85, 'Ya': -140, 'Ye':
            -140, 'Yi': -20, 'Yo': -140, 'Yu': -110, 'Y\xad': -140, 'YÀ': -110, 'YÁ': -110, 'YÂ': -110, 'YÃ': -110,
            'YÄ': -110, 'YÅ': -110, 'YÒ': -85, 'YÓ': -85, 'YÔ': -85, 'YÕ': -85, 'YÖ': -85, 'YØ': -85, 'Yà': -140,
            'Yá': -140, 'Yâ': -140, 'Yã': -140, 'Yä': -140, 'Yå': -140, 'Yè': -140, 'Yé': -140, 'Yê': -140, 'Yë':
            -140, 'Yí': -20, 'Yò': -140, 'Yó': -140, 'Yô': -140, 'Yõ': -140, 'Yö': -140, 'Yø': -140, 'Yù': -110, 'Yú':
            -110, 'Yû': -110, 'Yü': -110, 'av': -20, 'aw': -20, 'ay': -30, 'aý': -30, 'aÿ': -30, 'b,': -40, 'b.': -40,
            'bb': -10, 'bl': -20, 'bu': -20, 'bv': -20, 'by': -20, 'bù': -20, 'bú': -20, 'bû': -20, 'bü': -20, 'bý':
            -20, 'bÿ': -20, 'c,': -15, 'ck': -20, 'e,': -15, 'e.': -15, 'ev': -30, 'ew': -20, 'ex': -30, 'ey': -20,
            'eý': -20, 'eÿ': -20, 'f,': -30, 'f.': -30, 'fa': -30, 'fe': -30, 'fo': -30, 'fà': -30, 'fá': -30, 'fâ':
            -30, 'fã': -30, 'fä': -30, 'få': -30, 'fè': -30, 'fé': -30, 'fê': -30, 'fë': -30, 'fò': -30, 'fó': -30,
            'fô': -30, 'fõ': -30, 'fö': -30, 'fø': -30, 'gr': -10, 'hy': -30, 'hý': -30, 'hÿ': -30, 'ke': -20, 'ko':
            -20, 'kè': -20, 'ké': -20, 'kê': -20, 'kë': -20, 'kò': -20, 'kó': -20, 'kô': -20, 'kõ': -20, 'kö': -20,
            'kø': -20, 'mu': -10, 'my': -15, 'mù': -10, 'mú': -10, 'mû': -10, 'mü': -10, 'mý': -15, 'mÿ': -15, 'nu':
            -10, 'nv': -20, 'ny': -15, 'nù': -10, 'nú': -10, 'nû': -10, 'nü': -10, 'ný': -15, 'nÿ': -15, 'o,': -40,
            'o.': -40, 'ov': -15, 'ow': -15, 'ox': -30, 'oy': -30, 'oý': -30, 'oÿ': -30, 'p,': -35, 'p.': -35, 'py':
            -30, 'pý': -30, 'pÿ': -30, 'r,': -50, 'r.': -50, 'r:': 30, 'r;': 30, 'ra': -10, 'ri': 15, 'rk': 15, 'rl':
            15, 'rm': 25, 'rn': 25, 'rp': 30, 'rt': 40, 'ru': 15, 'rv': 30, 'ry': 30, 'rà': -10, 'rá': -10, 'râ': -10,
            'rã': -10, 'rä': -10, 'rå': -10, 'rì': 15, 'rí': 15, 'rî': 15, 'rï': 15, 'rñ': 25, 'rù': 15, 'rú': 15,
            'rû': 15, 'rü': 15, 'rý': 30, 'rÿ': 30, 's,': -15, 's.': -15, 'sw': -30, 'v,': -80, 'v.': -80, 'va': -25,
            've': -25, 'vo': -25, 'và': -25, 'vá': -25, 'vâ': -25, 'vã': -25, 'vä': -25, 'vå': -25, 'vè': -25, 'vé':
            -25, 'vê': -25, 'vë': -25, 'vò': -25, 'vó': -25, 'vô': -25, 'võ': -25, 'vö': -25, 'vø': -25, 'w,': -60,
            'w.': -60, 'wa': -15, 'we': -10, 'wo': -10, 'wà': -15, 'wá': -15, 'wâ': -15, 'wã': -15, 'wä': -15, 'wå':
            -15, 'wè': -10, 'wé': -10, 'wê': -10, 'wë': -10, 'wò': -10, 'wó': -10, 'wô': -10, 'wõ': -10, 'wö': -10,
            'wø': -10, 'xe': -30, 'xè': -30, 'xé': -30, 'xê': -30, 'xë': -30, 'y,': -100, 'y.': -100, 'ya': -20, 'ye':
            -20, 'yo': -20, 'yà': -20, 'yá': -20, 'yâ': -20, 'yã': -20, 'yä': -20, 'yå': -20, 'yè': -20, 'yé': -20,
            'yê': -20, 'yë': -20, 'yò': -20, 'yó': -20, 'yô': -20, 'yõ': -20, 'yö': -20, 'yø': -20, 'ze': -15, 'zo':
            -15, 'zè': -15, 'zé': -15, 'zê': -15, 'zë': -15, 'zò': -15, 'zó': -15, 'zô': -15, 'zõ': -15, 'zö': -15,
            'zø': -15, '\xa0T': -50, '\xa0V': -50, '\xa0W': -40, '\xa0Y': -90, '\xa0Ý': -90, 'ÀC': -30, 'ÀG': -30,
            'ÀO': -30, 'ÀQ': -30, 'ÀT': -120, 'ÀU': -50, 'ÀV': -70, 'ÀW': -50, 'ÀY': -100, 'Àu': -30, 'Àv': -40, 'Àw':
            -40, 'Ày': -40, 'ÀÇ': -30, 'ÀÒ': -30, 'ÀÓ': -30, 'ÀÔ': -30, 'ÀÕ': -30, 'ÀÖ': -30, 'ÀØ': -30, 'ÀÙ': -50,
            'ÀÚ': -50, 'ÀÛ': -50, 'ÀÜ': -50, 'ÀÝ': -100, 'Àù': -30, 'Àú': -30, 'Àû': -30, 'Àü': -30, 'Àý': -40, 'Àÿ':
            -40, 'ÁC': -30, 'ÁG': -30, 'ÁO': -30, 'ÁQ': -30, 'ÁT': -120, 'ÁU': -50, 'ÁV': -70, 'ÁW': -50, 'ÁY': -100,
            'Áu': -30, 'Áv': -40, 'Áw': -40, 'Áy': -40, 'ÁÇ': -30, 'ÁÒ': -30, 'ÁÓ': -30, 'ÁÔ': -30, 'ÁÕ': -30, 'ÁÖ':
            -30, 'ÁØ': -30, 'ÁÙ': -50, 'ÁÚ': -50, 'ÁÛ': -50, 'ÁÜ': -50, 'ÁÝ': -100, 'Áù': -30, 'Áú': -30, 'Áû': -30,
            'Áü': -30, 'Áý': -40, 'Áÿ': -40, 'ÂC': -30, 'ÂG': -30, 'ÂO': -30, 'ÂQ': -30, 'ÂT': -120, 'ÂU': -50, 'ÂV':
            -70, 'ÂW': -50, 'ÂY': -100, 'Âu': -30, 'Âv': -40, 'Âw': -40, 'Ây': -40, 'ÂÇ': -30, 'ÂÒ': -30, 'ÂÓ': -30,
            'ÂÔ': -30, 'ÂÕ': -30, 'ÂÖ': -30, 'ÂØ': -30, 'ÂÙ': -50, 'ÂÚ': -50, 'ÂÛ': -50, 'ÂÜ': -50, 'ÂÝ': -100, 'Âù':
            -30, 'Âú': -30, 'Âû': -30, 'Âü': -30, 'Âý': -40, 'Âÿ': -40, 'ÃC': -30, 'ÃG': -30, 'ÃO': -30, 'ÃQ': -30,
            'ÃT': -120, 'ÃU': -50, 'ÃV': -70, 'ÃW': -50, 'ÃY': -100, 'Ãu': -30, 'Ãv': -40, 'Ãw': -40, 'Ãy': -40, 'ÃÇ':
            -30, 'ÃÒ': -30, 'ÃÓ': -30, 'ÃÔ': -30, 'ÃÕ': -30, 'ÃÖ': -30, 'ÃØ': -30, 'ÃÙ': -50, 'ÃÚ': -50, 'ÃÛ': -50,
            'ÃÜ': -50, 'ÃÝ': -100, 'Ãù': -30, 'Ãú': -30, 'Ãû': -30, 'Ãü': -30, 'Ãý': -40, 'Ãÿ': -40, 'ÄC': -30, 'ÄG':
            -30, 'ÄO': -30, 'ÄQ': -30, 'ÄT': -120, 'ÄU': -50, 'ÄV': -70, 'ÄW': -50, 'ÄY': -100, 'Äu': -30, 'Äv': -40,
            'Äw': -40, 'Äy': -40, 'ÄÇ': -30, 'ÄÒ': -30, 'ÄÓ': -30, 'ÄÔ': -30, 'ÄÕ': -30, 'ÄÖ': -30, 'ÄØ': -30, 'ÄÙ':
            -50, 'ÄÚ': -50, 'ÄÛ': -50, 'ÄÜ': -50, 'ÄÝ': -100, 'Äù': -30, 'Äú': -30, 'Äû': -30, 'Äü': -30, 'Äý': -40,
            'Äÿ': -40, 'ÅC': -30, 'ÅG': -30, 'ÅO': -30, 'ÅQ': -30, 'ÅT': -120, 'ÅU': -50, 'ÅV': -70, 'ÅW': -50, 'ÅY':
            -100, 'Åu': -30, 'Åv': -40, 'Åw': -40, 'Åy': -40, 'ÅÇ': -30, 'ÅÒ': -30, 'ÅÓ': -30, 'ÅÔ': -30, 'ÅÕ': -30,
            'ÅÖ': -30, 'ÅØ': -30, 'ÅÙ': -50, 'ÅÚ': -50, 'ÅÛ': -50, 'ÅÜ': -50, 'ÅÝ': -100, 'Åù': -30, 'Åú': -30, 'Åû':
            -30, 'Åü': -30, 'Åý': -40, 'Åÿ': -40, 'Ç,': -30, 'Ç.': -30, 'Ò,': -40, 'Ò.': -40, 'ÒA': -20, 'ÒT': -40,
            'ÒV': -50, 'ÒW': -30, 'ÒX': -60, 'ÒY': -70, 'ÒÀ': -20, 'ÒÁ': -20, 'ÒÂ': -20, 'ÒÃ': -20, 'ÒÄ': -20, 'ÒÅ':
            -20, 'ÒÝ': -70, 'Ó,': -40, 'Ó.': -40, 'ÓA': -20, 'ÓT': -40, 'ÓV': -50, 'ÓW': -30, 'ÓX': -60, 'ÓY': -70,
            'ÓÀ': -20, 'ÓÁ': -20, 'ÓÂ': -20, 'ÓÃ': -20, 'ÓÄ': -20, 'ÓÅ': -20, 'ÓÝ': -70, 'Ô,': -40, 'Ô.': -40, 'ÔA':
            -20, 'ÔT': -40, 'ÔV': -50, 'ÔW': -30, 'ÔX': -60, 'ÔY': -70, 'ÔÀ': -20, 'ÔÁ': -20, 'ÔÂ': -20, 'ÔÃ': -20,
            'ÔÄ': -20, 'ÔÅ': -20, 'ÔÝ': -70, 'Õ,': -40, 'Õ.': -40, 'ÕA': -20, 'ÕT': -40, 'ÕV': -50, 'ÕW': -30, 'ÕX':
            -60, 'ÕY': -70, 'ÕÀ': -20, 'ÕÁ': -20, 'ÕÂ': -20, 'ÕÃ': -20, 'ÕÄ': -20, 'ÕÅ': -20, 'ÕÝ': -70, 'Ö,': -40,
            'Ö.': -40, 'ÖA': -20, 'ÖT': -40, 'ÖV': -50, 'ÖW': -30, 'ÖX': -60, 'ÖY': -70, 'ÖÀ': -20, 'ÖÁ': -20, 'ÖÂ':
            -20, 'ÖÃ': -20, 'ÖÄ': -20, 'ÖÅ': -20, 'ÖÝ': -70, 'Ø,': -40, 'Ø.': -40, 'ØA': -20, 'ØT': -40, 'ØV': -50,
            'ØW': -30, 'ØX': -60, 'ØY': -70, 'ØÀ': -20, 'ØÁ': -20, 'ØÂ': -20, 'ØÃ': -20, 'ØÄ': -20, 'ØÅ': -20, 'ØÝ':
            -70, 'Ù,': -40, 'Ù.': -40, 'ÙA': -40, 'ÙÀ': -40, 'ÙÁ': -40, 'ÙÂ': -40, 'ÙÃ': -40, 'ÙÄ': -40, 'ÙÅ': -40,
            'Ú,': -40, 'Ú.': -40, 'ÚA': -40, 'ÚÀ': -40, 'ÚÁ': -40, 'ÚÂ': -40, 'ÚÃ': -40, 'ÚÄ': -40, 'ÚÅ': -40, 'Û,':
            -40, 'Û.': -40, 'ÛA': -40, 'ÛÀ': -40, 'ÛÁ': -40, 'ÛÂ': -40, 'ÛÃ': -40, 'ÛÄ': -40, 'ÛÅ': -40, 'Ü,': -40,
            'Ü.': -40, 'ÜA': -40, 'ÜÀ': -40, 'ÜÁ': -40, 'ÜÂ': -40, 'ÜÃ': -40, 'ÜÄ': -40, 'ÜÅ': -40, 'Ý,': -140, 'Ý-':
            -140, 'Ý.': -140, 'Ý:': -60, 'Ý;': -60, 'ÝA': -110, 'ÝO': -85, 'Ýa': -140, 'Ýe': -140, 'Ýi': -20, 'Ýo':
            -140, 'Ýu': -110, 'Ý\xad': -140, 'ÝÀ': -110, 'ÝÁ': -110, 'ÝÂ': -110, 'ÝÃ': -110, 'ÝÄ': -110, 'ÝÅ': -110,
            'ÝÒ': -85, 'ÝÓ': -85, 'ÝÔ': -85, 'ÝÕ': -85, 'ÝÖ': -85, 'ÝØ': -85, 'Ýà': -140, 'Ýá': -140, 'Ýâ': -140,
            'Ýã': -70, 'Ýä': -140, 'Ýå': -140, 'Ýè': -140, 'Ýé': -140, 'Ýê': -140, 'Ýë': -140, 'Ýí': -20, 'Ýò': -140,
            'Ýó': -140, 'Ýô': -140, 'Ýõ': -140, 'Ýö': -140, 'Ýø': -140, 'Ýù': -110, 'Ýú': -110, 'Ýû': -110, 'Ýü':
            -110, 'àv': -20, 'àw': -20, 'ày': -30, 'àý': -30, 'àÿ': -30, 'áv': -20, 'áw': -20, 'áy': -30, 'áý': -30,
            'áÿ': -30, 'âv': -20, 'âw': -20, 'ây': -30, 'âý': -30, 'âÿ': -30, 'ãv': -20, 'ãw': -20, 'ãy': -30, 'ãý':
            -30, 'ãÿ': -30, 'äv': -20, 'äw': -20, 'äy': -30, 'äý': -30, 'äÿ': -30, 'åv': -20, 'åw': -20, 'åy': -30,
            'åý': -30, 'åÿ': -30, 'ç,': -15, 'çk': -20, 'è,': -15, 'è.': -15, 'èv': -30, 'èw': -20, 'èx': -30, 'èy':
            -20, 'èý': -20, 'èÿ': -20, 'é,': -15, 'é.': -15, 'év': -30, 'éw': -20, 'éx': -30, 'éy': -20, 'éý': -20,
            'éÿ': -20, 'ê,': -15, 'ê.': -15, 'êv': -30, 'êw': -20, 'êx': -30, 'êy': -20, 'êý': -20, 'êÿ': -20, 'ë,':
            -15, 'ë.': -15, 'ëv': -30, 'ëw': -20, 'ëx': -30, 'ëy': -20, 'ëý': -20, 'ëÿ': -20, 'ñu': -10, 'ñv': -20,
            'ñy': -15, 'ñù': -10, 'ñú': -10, 'ñû': -10, 'ñü': -10, 'ñý': -15, 'ñÿ': -15, 'ò,': -40, 'ò.': -40, 'òv':
            -15, 'òw': -15, 'òx': -30, 'òy': -30, 'òý': -30, 'òÿ': -30, 'ó,': -40, 'ó.': -40, 'óv': -15, 'ów': -15,
            'óx': -30, 'óy': -30, 'óý': -30, 'óÿ': -30, 'ô,': -40, 'ô.': -40, 'ôv': -15, 'ôw': -15, 'ôx': -30, 'ôy':
            -30, 'ôý': -30, 'ôÿ': -30, 'õ,': -40, 'õ.': -40, 'õv': -15, 'õw': -15, 'õx': -30, 'õy': -30, 'õý': -30,
            'õÿ': -30, 'ö,': -40, 'ö.': -40, 'öv': -15, 'öw': -15, 'öx': -30, 'öy': -30, 'öý': -30, 'öÿ': -30, 'ø,':
            -95, 'ø.': -95, 'øa': -55, 'øb': -55, 'øc': -55, 'ød': -55, 'øe': -55, 'øf': -55, 'øg': -55, 'øh': -55,
            'øi': -55, 'øj': -55, 'øk': -55, 'øl': -55, 'øm': -55, 'øn': -55, 'øo': -55, 'øp': -55, 'øq': -55, 'ør':
            -55, 'øs': -55, 'øt': -55, 'øu': -55, 'øv': -70, 'øw': -70, 'øx': -85, 'øy': -70, 'øz': -55, 'øà': -55,
            'øá': -55, 'øâ': -55, 'øã': -55, 'øä': -55, 'øå': -55, 'øç': -55, 'øè': -55, 'øé': -55, 'øê': -55, 'øë':
            -55, 'øì': -55, 'øí': -55, 'øî': -55, 'øï': -55, 'øñ': -55, 'øò': -55, 'øó': -55, 'øô': -55, 'øõ': -55,
            'øö': -55, 'øø': -55, 'øù': -55, 'øú': -55, 'øû': -55, 'øü': -55, 'øý': -70, 'øÿ': -70, 'ý,': -100, 'ý.':
            -100, 'ýa': -20, 'ýe': -20, 'ýo': -20, 'ýà': -20, 'ýá': -20, 'ýâ': -20, 'ýã': -20, 'ýä': -20, 'ýå': -20,
            'ýè': -20, 'ýé': -20, 'ýê': -20, 'ýë': -20, 'ýò': -20, 'ýó': -20, 'ýô': -20, 'ýõ': -20, 'ýö': -20, 'ýø':
            -20, 'ÿ,': -100, 'ÿ.': -100, 'ÿa': -20, 'ÿe': -20, 'ÿo': -20, 'ÿà': -20, 'ÿá': -20, 'ÿâ': -20, 'ÿã': -20,
            'ÿä': -20, 'ÿå': -20, 'ÿè': -20, 'ÿé': -20, 'ÿê': -20, 'ÿë': -20, 'ÿò': -20, 'ÿó': -20, 'ÿô': -20, 'ÿõ':
            -20, 'ÿö': -20, 'ÿø': -20
        },
    },
    'bold': {
        'widths': {
            '0': 556, '1': 556, '2': 556, '3': 556, '4': 556, '5': 556, '6': 556, '7': 556, '8': 556, '9': 556, ' ':
            278, '!': 333, '"': 474, '#': 556, '$': 556, '%': 889, '&': 722, "'": 238, '(': 333, ')': 333, '*': 389,
            '+': 584, ',': 278, '-': 333, '.': 278, '/': 278, ':': 333, ';': 333, '<': 584, '=': 584, '>': 584, '?':
            611, '@': 975, 'A': 722, 'B': 722, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778, 'H': 722, 'I': 278,
            'J': 556, 'K': 722, 'L': 611, 'M': 833, 'N': 722, 'O': 778, 'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T':
            611, 'U': 722, 'V': 667, 'W': 944, 'X': 667, 'Y': 667, 'Z': 611, '[': 333, '\\': 278, ']': 333, '^': 584,
            '_': 556, '`': 333, 'a': 556, 'b': 611, 'c': 556, 'd': 611, 'e': 556, 'f': 333, 'g': 611, 'h': 611, 'i':
            278, 'j': 278, 'k': 556, 'l': 278, 'm': 889, 'n': 611, 'o': 611, 'p': 611, 'q': 611, 'r': 389, 's': 556,
            't': 333, 'u': 611, 'v': 556, 'w': 778, 'x': 556, 'y': 556, 'z': 500, '{': 389, '|': 280, '}': 389, '~':
            584, '\xa0': 278, '¡': 333, '¢': 556, '£': 556, '¤': 556, '¥': 556, '¦': 280, '§': 556, '¨': 333, '©':
            737, 'ª': 370, '«': 556, '¬': 584, '\xad': 333, '®': 737, '¯': 333, '°': 400, '±': 584, '²': 333, '³':
            333, '´': 333, 'µ': 611, '¶': 556, '·': 278, '¸': 333, '¹': 333, 'º': 365, '»': 556, '¼': 834, '½': 834,
            '¾': 834, '¿': 611, 'À': 722, 'Á': 722, 'Â': 722, 'Ã': 722, 'Ä': 722, 'Å': 722, 'Æ': 1000, 'Ç': 722, 'È':
            667, 'É': 667, 'Ê': 667, 'Ë': 667, 'Ì': 278, 'Í': 278, 'Î': 278, 'Ï': 278, 'Ð': 722, 'Ñ': 722, 'Ò': 778,
            'Ó': 778, 'Ô': 778, 'Õ': 778, 'Ö': 778, '×': 584, 'Ø': 778, 'Ù': 722, 'Ú': 722, 'Û': 722, 'Ü': 722, 'Ý':
            667, 'Þ': 667, 'ß': 611, 'à': 556, 'á': 556, 'â': 556, 'ã': 556, 'ä': 556, 'å': 556, 'æ': 889, 'ç': 556,
            'è': 556, 'é': 556, 'ê': 556, 'ë': 556, 'ì': 278, 'í': 278, 'î': 278, 'ï': 278, 'ð': 611, 'ñ': 611, 'ò':
            611, 'ó': 611, 'ô': 611, 'õ': 611, 'ö': 611, '÷': 584, 'ø': 611, 'ù': 611, 'ú': 611, 'û': 611, 'ü': 611,
            'ý': 556, 'þ': 611, 'ÿ': 556, '€': 556
        },
        'kern': {
            ' T': -100, ' V': -80, ' W': -80, ' Y': -120, ' Ý': -120, ', ': -40, ',\xa0': -40, '. ': -40, '.\xa0':
            -40, ': ': -40, ':\xa0': -40, '; ': -40, ';\xa0': -40, 'AC': -40, 'AG': -50, 'AO': -40, 'AQ': -40, 'AT':
            -90, 'AU': -50, 'AV': -80, 'AW': -60, 'AY': -110, 'Au': -30, 'Av': -40, 'Aw': -30, 'Ay': -30, 'AÇ': -40,
            'AÒ': -40, 'AÓ': -40, 'AÔ': -40, 'AÕ': -40, 'AÖ': -40, 'AØ': -40, 'AÙ': -50, 'AÚ': -50, 'AÛ': -50, 'AÜ':
            -50, 'AÝ': -110, 'Aù': -30, 'Aú': -30, 'Aû': -30, 'Aü': -30, 'Aý': -30, 'Aÿ': -30, 'BA': -30, 'BU': -10,
            'BÀ': -30, 'BÁ': -30, 'BÂ': -30, 'BÃ': -30, 'BÄ': -30, 'BÅ': -30, 'BÙ': -10, 'BÚ': -10, 'BÛ': -10, 'BÜ':
            -10, 'D,': -30, 'D.': -30, 'DA': -40, 'DV': -40, 'DW': -40, 'DY': -70, 'DÀ': -40, 'DÁ': -40, 'DÂ': -40,
            'DÃ': -40, 'DÄ': -40, 'DÅ': -40, 'DÝ': -70, 'F,': -100, 'F.': -100, 'FA': -80, 'Fa': -20, 'FÀ': -80, 'FÁ':
            -80, 'FÂ': -80, 'FÃ': -80, 'FÄ': -80, 'FÅ': -80, 'Fà': -20, 'Fá': -20, 'Fâ': -20, 'Fã': -20, 'Fä': -20,
            'Få': -20, 'J,': -20, 'J.': -20, 'JA': -20, 'Ju': -20, 'JÀ': -20, 'JÁ': -20, 'JÂ': -20, 'JÃ': -20, 'JÄ':
            -20, 'JÅ': -20, 'Jù': -20, 'Jú': -20, 'Jû': -20, 'Jü': -20, 'KO': -30, 'Ke': -15, 'Ko': -35, 'Ku': -30,
            'Ky': -40, 'KÒ': -30, 'KÓ': -30, 'KÔ': -30, 'KÕ': -30, 'KÖ': -30, 'KØ': -30, 'Kè': -15, 'Ké': -15, 'Kê':
            -15, 'Kë': -15, 'Kò': -35, 'Kó': -35, 'Kô': -35, 'Kõ': -35, 'Kö': -35, 'Kø': -35, 'Kù': -30, 'Kú': -30,
            'Kû': -30, 'Kü': -30, 'Ký': -40, 'Kÿ': -40, 'LT': -90, 'LV': -110, 'LW': -80, 'LY': -120, 'Ly': -30, 'LÝ':
            -120, 'Lý': -30, 'Lÿ': -30, 'O,': -40, 'O.': -40, 'OA': -50, 'OT': -40, 'OV': -50, 'OW': -50, 'OX': -50,
            'OY': -70, 'OÀ': -50, 'OÁ': -50, 'OÂ': -50, 'OÃ': -50, 'OÄ': -50, 'OÅ': -50, 'OÝ': -70, 'P,': -120, 'P.':
            -120, 'PA': -100, 'Pa': -30, 'Pe': -30, 'Po': -40, 'PÀ': -100, 'PÁ': -100, 'PÂ': -100, 'PÃ': -100, 'PÄ':
            -100, 'PÅ': -100, 'Pà': -30, 'Pá': -30, 'Pâ': -30, 'Pã': -30, 'Pä': -30, 'På': -30, 'Pè': -30, 'Pé': -30,
            'Pê': -30, 'Pë': -30, 'Pò': -40, 'Pó': -40, 'Pô': -40, 'Põ': -40, 'Pö': -40, 'Pø': -40, 'Q,': 20, 'Q.':
            20, 'QU': -10, 'QÙ': -10, 'QÚ': -10, 'QÛ': -10, 'QÜ': -10, 'RO': -20, 'RT': -20, 'RU': -20, 'RV': -50,
            'RW': -40, 'RY': -50, 'RÒ': -20, 'RÓ': -20, 'RÔ': -20, 'RÕ': -20, 'RÖ': -20, 'RØ': -20, 'RÙ': -20, 'RÚ':
            -20, 'RÛ': -20, 'RÜ': -20, 'RÝ': -50, 'T,': -80, 'T-': -120, 'T.': -80, 'T:': -40, 'T;': -40, 'TA': -90,
            'TO': -40, 'Ta': -80, 'Te': -60, 'To': -80, 'Tr': -80, 'Tu': -90, 'Tw': -60, 'Ty': -60, 'T\xad': -120,
            'TÀ': -90, 'TÁ': -90, 'TÂ': -90, 'TÃ': -90, 'TÄ': -90, 'TÅ': -90, 'TÒ': -40, 'TÓ': -40, 'TÔ': -40, 'TÕ':
            -40, 'TÖ': -40, 'TØ': -40, 'Tà': -80, 'Tá': -80, 'Tâ': -80, 'Tã': -80, 'Tä': -80, 'Tå': -80, 'Tè': -60,
            'Té': -60, 'Tê': -60, 'Të': -60, 'Tò': -80, 'Tó': -80, 'Tô': -80, 'Tõ': -80, 'Tö': -80, 'Tø': -80, 'Tù':
            -90, 'Tú': -90, 'Tû': -90, 'Tü': -90, 'Tý': -60, 'Tÿ': -60, 'U,': -30, 'U.': -30, 'UA': -50, 'UÀ': -50,
            'UÁ': -50, 'UÂ': -50, 'UÃ': -50, 'UÄ': -50, 'UÅ': -50, 'V,': -120, 'V-': -80, 'V.': -120, 'V:': -40, 'V;':
            -40, 'VA': -80, 'VG': -50, 'VO': -50, 'Va': -60, 'Ve': -50, 'Vo': -90, 'Vu': -60, 'V\xad': -80, 'VÀ': -80,
            'VÁ': -80, 'VÂ': -80, 'VÃ': -80, 'VÄ': -80, 'VÅ': -80, 'VÒ': -50, 'VÓ': -50, 'VÔ': -50, 'VÕ': -50, 'VÖ':
            -50, 'VØ': -50, 'Và': -60, 'Vá': -60, 'Vâ': -60, 'Vã': -60, 'Vä': -60, 'Vå': -60, 'Vè': -50, 'Vé': -50,
            'Vê': -50, 'Vë': -50, 'Vò': -90, 'Vó': -90, 'Vô': -90, 'Võ': -90, 'Vö': -90, 'Vø': -90, 'Vù': -60, 'Vú':
            -60, 'Vû': -60, 'Vü': -60, 'W,': -80, 'W-': -40, 'W.': -80, 'W:': -10, 'W;': -10, 'WA': -60, 'WO': -20,
            'Wa': -40, 'We': -35, 'Wo': -60, 'Wu': -45, 'Wy': -20, 'W\xad': -40, 'WÀ': -60, 'WÁ': -60, 'WÂ': -60,
            'WÃ': -60, 'WÄ': -60, 'WÅ': -60, 'WÒ': -20, 'WÓ': -20, 'WÔ': -20, 'WÕ': -20, 'WÖ': -20, 'WØ': -20, 'Wà':
            -40, 'Wá': -40, 'Wâ': -40, 'Wã': -40, 'Wä': -40, 'Wå': -40, 'Wè': -35, 'Wé': -35, 'Wê': -35, 'Wë': -35,
            'Wò': -60, 'Wó': -60, 'Wô': -60, 'Wõ': -60, 'Wö': -60, 'Wø': -60, 'Wù': -45, 'Wú': -45, 'Wû': -45, 'Wü':
            -45, 'Wý': -20, 'Wÿ': -20, 'Y,': -100, 'Y.': -100, 'Y:': -50, 'Y;': -50, 'YA': -110, 'YO': -70, 'Ya': -90,
            'Ye': -80, 'Yo': -100, 'Yu': -100, 'YÀ': -110, 'YÁ': -110, 'YÂ': -110, 'YÃ': -110, 'YÄ': -110, 'YÅ': -110,
            'YÒ': -70, 'YÓ': -70, 'YÔ': -70, 'YÕ': -70, 'YÖ': -70, 'YØ': -70, 'Yà': -90, 'Yá': -90, 'Yâ': -90, 'Yã':
            -90, 'Yä': -90, 'Yå': -90, 'Yè': -80, 'Yé': -80, 'Yê': -80, 'Yë': -80, 'Yò': -100, 'Yó': -100, 'Yô': -100,
            'Yõ': -100, 'Yö': -100, 'Yø': -100, 'Yù': -100, 'Yú': -100, 'Yû': -100, 'Yü': -100, 'ag': -10, 'av': -15,
            'aw': -15, 'ay': -20, 'aý': -20, 'aÿ': -20, 'bl': -10, 'bu': -20, 'bv': -20, 'by': -20, 'bù': -20, 'bú':
            -20, 'bû': -20, 'bü': -20, 'bý': -20, 'bÿ': -20, 'ch': -10, 'ck': -20, 'cl': -20, 'cy': -10, 'cý': -10,
            'cÿ': -10, 'dd': -10, 'dv': -15, 'dw': -15, 'dy': -15, 'dý': -15, 'dÿ': -15, 'e,': 10, 'e.': 20, 'ev':
            -15, 'ew': -15, 'ex': -15, 'ey': -15, 'eý': -15, 'eÿ': -15, 'f,': -10, 'f.': -10, 'fe': -10, 'fo': -20,
            'fè': -10, 'fé': -10, 'fê': -10, 'fë': -10, 'fò': -20, 'fó': -20, 'fô': -20, 'fõ': -20, 'fö': -20, 'fø':
            -20, 'ge': 10, 'gg': -10, 'gè': 10, 'gé': 10, 'gê': 10, 'gë': 10, 'hy': -20, 'hý': -20, 'hÿ': -20, 'ko':
            -15, 'kò': -15, 'kó': -15, 'kô': -15, 'kõ': -15, 'kö': -15, 'kø': -15, 'lw': -15, 'ly': -15, 'lý': -15,
            'lÿ': -15, 'mu': -20, 'my': -30, 'mù': -20, 'mú': -20, 'mû': -20, 'mü': -20, 'mý': -30, 'mÿ': -30, 'nu':
            -10, 'nv': -40, 'ny': -20, 'nù': -10, 'nú': -10, 'nû': -10, 'nü': -10, 'ný': -20, 'nÿ': -20, 'ov': -20,
            'ow': -15, 'ox': -30, 'oy': -20, 'oý': -20, 'oÿ': -20, 'py': -15, 'pý': -15, 'pÿ': -15, 'r,': -60, 'r-':
            -20, 'r.': -60, 'rc': -20, 'rd': -20, 'rg': -15, 'ro': -20, 'rq': -20, 'rs': -15, 'rt': 20, 'rv': 10,
            'ry': 10, 'r\xad': -20, 'rç': -20, 'rò': -20, 'ró': -20, 'rô': -20, 'rõ': -20, 'rö': -20, 'rø': -20, 'rý':
            10, 'rÿ': 10, 'sw': -15, 'v,': -80, 'v.': -80, 'va': -20, 'vo': -30, 'và': -20, 'vá': -20, 'vâ': -20,
            'vã': -20, 'vä': -20, 'vå': -20, 'vò': -30, 'vó': -30, 'vô': -30, 'võ': -30, 'vö': -30, 'vø': -30, 'w,':
            -40, 'w.': -40, 'wo': -20, 'wò': -20, 'wó': -20, 'wô': -20, 'wõ': -20, 'wö': -20, 'wø': -20, 'xe': -10,
            'xè': -10, 'xé': -10, 'xê': -10, 'xë': -10, 'y,': -80, 'y.': -80, 'ya': -30, 'ye': -10, 'yo': -25, 'yà':
            -30, 'yá': -30, 'yâ': -30, 'yã': -30, 'yä': -30, 'yå': -30, 'yè': -10, 'yé': -10, 'yê': -10, 'yë': -10,
            'yò': -25, 'yó': -25, 'yô': -25, 'yõ': -25, 'yö': -25, 'yø': -25, 'ze': 10, 'zè': 10, 'zé': 10, 'zê': 10,
            'zë': 10, '\xa0T': -100, '\xa0V': -80, '\xa0W': -80, '\xa0Y': -120, '\xa0Ý': -120, 'ÀC': -40, 'ÀG': -50,
            'ÀO': -40, 'ÀQ': -40, 'ÀT': -90, 'ÀU': -50, 'ÀV': -80, 'ÀW': -60, 'ÀY': -110, 'Àu': -30, 'Àv': -40, 'Àw':
            -30, 'Ày': -30, 'ÀÇ': -40, 'ÀÒ': -40, 'ÀÓ': -40, 'ÀÔ': -40, 'ÀÕ': -40, 'ÀÖ': -40, 'ÀØ': -40, 'ÀÙ': -50,
            'ÀÚ': -50, 'ÀÛ': -50, 'ÀÜ': -50, 'ÀÝ': -110, 'Àù': -30, 'Àú': -30, 'Àû': -30, 'Àü': -30, 'Àý': -30, 'Àÿ':
            -30, 'ÁC': -40, 'ÁG': -50, 'ÁO': -40, 'ÁQ': -40, 'ÁT': -90, 'ÁU': -50, 'ÁV': -80, 'ÁW': -60, 'ÁY': -110,
            'Áu': -30, 'Áv': -40, 'Áw': -30, 'Áy': -30, 'ÁÇ': -40, 'ÁÒ': -40, 'ÁÓ': -40, 'ÁÔ': -40, 'ÁÕ': -40, 'ÁÖ':
            -40, 'ÁØ': -40, 'ÁÙ': -50, 'ÁÚ': -50, 'ÁÛ': -50, 'ÁÜ': -50, 'ÁÝ': -110, 'Áù': -30, 'Áú': -30, 'Áû': -30,
            'Áü': -30, 'Áý': -30, 'Áÿ': -30, 'ÂC': -40, 'ÂG': -50, 'ÂO': -40, 'ÂQ': -40, 'ÂT': -90, 'ÂU': -50, 'ÂV':
            -80, 'ÂW': -60, 'ÂY': -110, 'Âu': -30, 'Âv': -40, 'Âw': -30, 'Ây': -30, 'ÂÇ': -40, 'ÂÒ': -40, 'ÂÓ': -40,
            'ÂÔ': -40, 'ÂÕ': -40, 'ÂÖ': -40, 'ÂØ': -40, 'ÂÙ': -50, 'ÂÚ': -50, 'ÂÛ': -50, 'ÂÜ': -50, 'ÂÝ': -110, 'Âù':
            -30, 'Âú': -30, 'Âû': -30, 'Âü': -30, 'Âý': -30, 'Âÿ': -30, 'ÃC': -40, 'ÃG': -50, 'ÃO': -40, 'ÃQ': -40,
            'ÃT': -90, 'ÃU': -50, 'ÃV': -80, 'ÃW': -60, 'ÃY': -110, 'Ãu': -30, 'Ãv': -40, 'Ãw': -30, 'Ãy': -30, 'ÃÇ':
            -40, 'ÃÒ': -40, 'ÃÓ': -40, 'ÃÔ': -40, 'ÃÕ': -40, 'ÃÖ': -40, 'ÃØ': -40, 'ÃÙ': -50, 'ÃÚ': -50, 'ÃÛ': -50,
            'ÃÜ': -50, 'ÃÝ': -110, 'Ãù': -30, 'Ãú': -30, 'Ãû': -30, 'Ãü': -30, 'Ãý': -30, 'Ãÿ': -30, 'ÄC': -40, 'ÄG':
            -50, 'ÄO': -40, 'ÄQ': -40, 'ÄT': -90, 'ÄU': -50, 'ÄV': -80, 'ÄW': -60, 'ÄY': -110, 'Äu': -30, 'Äv': -40,
            'Äw': -30, 'Äy': -30, 'ÄÇ': -40, 'ÄÒ': -40, 'ÄÓ': -40, 'ÄÔ': -40, 'ÄÕ': -40, 'ÄÖ': -40, 'ÄØ': -40, 'ÄÙ':
            -50, 'ÄÚ': -50, 'ÄÛ': -50, 'ÄÜ': -50, 'ÄÝ': -110, 'Äù': -30, 'Äú': -30, 'Äû': -30, 'Äü': -30, 'Äý': -30,
            'Äÿ': -30, 'ÅC': -40, 'ÅG': -50, 'ÅO': -40, 'ÅQ': -40, 'ÅT': -90, 'ÅU': -50, 'ÅV': -80, 'ÅW': -60, 'ÅY':
            -110, 'Åu': -30, 'Åv': -40, 'Åw': -30, 'Åy': -30, 'ÅÇ': -40, 'ÅÒ': -40, 'ÅÓ': -40, 'ÅÔ': -40, 'ÅÕ': -40,
            'ÅÖ': -40, 'ÅØ': -40, 'ÅÙ': -50, 'ÅÚ': -50, 'ÅÛ': -50, 'ÅÜ': -50, 'ÅÝ': -110, 'Åù': -30, 'Åú': -30, 'Åû':
            -30, 'Åü': -30, 'Åý': -30, 'Åÿ': -30, 'Ò,': -40, 'Ò.': -40, 'ÒA': -50, 'ÒT': -40, 'ÒV': -50, 'ÒW': -50,
            'ÒX': -50, 'ÒY': -70, 'ÒÀ': -50, 'ÒÁ': -50, 'ÒÂ': -50, 'ÒÃ': -50, 'ÒÄ': -50, 'ÒÅ': -50, 'ÒÝ': -70, 'Ó,':
            -40, 'Ó.': -40, 'ÓA': -50, 'ÓT': -40, 'ÓV': -50, 'ÓW': -50, 'ÓX': -50, 'ÓY': -70, 'ÓÀ': -50, 'ÓÁ': -50,
            'ÓÂ': -50, 'ÓÃ': -50, 'ÓÄ': -50, 'ÓÅ': -50, 'ÓÝ': -70, 'Ô,': -40, 'Ô.': -40, 'ÔA': -50, 'ÔT': -40, 'ÔV':
            -50, 'ÔW': -50, 'ÔX': -50, 'ÔY': -70, 'ÔÀ': -50, 'ÔÁ': -50, 'ÔÂ': -50, 'ÔÃ': -50, 'ÔÄ': -50, 'ÔÅ': -50,
            'ÔÝ': -70, 'Õ,': -40, 'Õ.': -40, 'ÕA': -50, 'ÕT': -40, 'ÕV': -50, 'ÕW': -50, 'ÕX': -50, 'ÕY': -70, 'ÕÀ':
            -50, 'ÕÁ': -50, 'ÕÂ': -50, 'ÕÃ': -50, 'ÕÄ': -50, 'ÕÅ': -50, 'ÕÝ': -70, 'Ö,': -40, 'Ö.': -40, 'ÖA': -50,
            'ÖT': -40, 'ÖV': -50, 'ÖW': -50, 'ÖX': -50, 'ÖY': -70, 'ÖÀ': -50, 'ÖÁ': -50, 'ÖÂ': -50, 'ÖÃ': -50, 'ÖÄ':
            -50, 'ÖÅ': -50, 'ÖÝ': -70, 'Ø,': -40, 'Ø.': -40, 'ØA': -50, 'ØT': -40, 'ØV': -50, 'ØW': -50, 'ØX': -50,
            'ØY': -70, 'ØÀ': -50, 'ØÁ': -50, 'ØÂ': -50, 'ØÃ': -50, 'ØÄ': -50, 'ØÅ': -50, 'ØÝ': -70, 'Ù,': -30, 'Ù.':
            -30, 'ÙA': -50, 'ÙÀ': -50, 'ÙÁ': -50, 'ÙÂ': -50, 'ÙÃ': -50, 'ÙÄ': -50, 'ÙÅ': -50, 'Ú,': -30, 'Ú.': -30,
            'ÚA': -50, 'ÚÀ': -50, 'ÚÁ': -50, 'ÚÂ': -50, 'ÚÃ': -50, 'ÚÄ': -50, 'ÚÅ': -50, 'Û,': -30, 'Û.': -30, 'ÛA':
            -50, 'ÛÀ': -50, 'ÛÁ': -50, 'ÛÂ': -50, 'ÛÃ': -50, 'ÛÄ': -50, 'ÛÅ': -50, 'Ü,': -30, 'Ü.': -30, 'ÜA': -50,
            'ÜÀ': -50, 'ÜÁ': -50, 'ÜÂ': -50, 'ÜÃ': -50, 'ÜÄ': -50, 'ÜÅ': -50, 'Ý,': -100, 'Ý.': -100, 'Ý:': -50, 'Ý;':
            -50, 'ÝA': -110, 'ÝO': -70, 'Ýa': -90, 'Ýe': -80, 'Ýo': -100, 'Ýu': -100, 'ÝÀ': -110, 'ÝÁ': -110, 'ÝÂ':
            -110, 'ÝÃ': -110, 'ÝÄ': -110, 'ÝÅ': -110, 'ÝÒ': -70, 'ÝÓ': -70, 'ÝÔ': -70, 'ÝÕ': -70, 'ÝÖ': -70, 'ÝØ':
            -70, 'Ýà': -90, 'Ýá': -90, 'Ýâ': -90, 'Ýã': -90, 'Ýä': -90, 'Ýå': -90, 'Ýè': -80, 'Ýé': -80, 'Ýê': -80,
            'Ýë': -80, 'Ýò': -100, 'Ýó': -100, 'Ýô': -100, 'Ýõ': -100, 'Ýö': -100, 'Ýø': -100, 'Ýù': -100, 'Ýú': -100,
            'Ýû': -100, 'Ýü': -100, 'àg': -10, 'àv': -15, 'àw': -15, 'ày': -20, 'àý': -20, 'àÿ': -20, 'ág': -10, 'áv':
            -15, 'áw': -15, 'áy': -20, 'áý': -20, 'áÿ': -20, 'âg': -10, 'âv': -15, 'âw': -15, 'ây': -20, 'âý': -20,
            'âÿ': -20, 'ãg': -10, 'ãv': -15, 'ãw': -15, 'ãy': -20, 'ãý': -20, 'ãÿ': -20, 'äg': -10, 'äv': -15, 'äw':
            -15, 'äy': -20, 'äý': -20, 'äÿ': -20, 'åg': -10, 'åv': -15, 'åw': -15, 'åy': -20, 'åý': -20, 'åÿ': -20,
            'çh': -10, 'çk': -20, 'çl': -20, 'çy': -10, 'çý': -10, 'çÿ': -10, 'è,': 10, 'è.': 20, 'èv': -15, 'èw':
            -15, 'èx': -15, 'èy': -15, 'èý': -15, 'èÿ': -15, 'é,': 10, 'é.': 20, 'év': -15, 'éw': -15, 'éx': -15,
            'éy': -15, 'éý': -15, 'éÿ': -15, 'ê,': 10, 'ê.': 20, 'êv': -15, 'êw': -15, 'êx': -15, 'êy': -15, 'êý':
            -15, 'êÿ': -15, 'ë,': 10, 'ë.': 20, 'ëv': -15, 'ëw': -15, 'ëx': -15, 'ëy': -15, 'ëý': -15, 'ëÿ': -15,
            'ñu': -10, 'ñv': -40, 'ñy': -20, 'ñù': -10, 'ñú': -10, 'ñû': -10, 'ñü': -10, 'ñý': -20, 'ñÿ': -20, 'òv':
            -20, 'òw': -15, 'òx': -30, 'òy': -20, 'òý': -20, 'òÿ': -20, 'óv': -20, 'ów': -15, 'óx': -30, 'óy': -20,
            'óý': -20, 'óÿ': -20, 'ôv': -20, 'ôw': -15, 'ôx': -30, 'ôy': -20, 'ôý': -20, 'ôÿ': -20, 'õv': -20, 'õw':
            -15, 'õx': -30, 'õy': -20, 'õý': -20, 'õÿ': -20, 'öv': -20, 'öw': -15, 'öx': -30, 'öy': -20, 'öý': -20,
            'öÿ': -20, 'øv': -20, 'øw': -15, 'øx': -30, 'øy': -20, 'øý': -20, 'øÿ': -20, 'ý,': -80, 'ý.': -80, 'ýa':
            -30, 'ýe': -10, 'ýo': -25, 'ýà': -30, 'ýá': -30, 'ýâ': -30, 'ýã': -30, 'ýä': -30, 'ýå': -30, 'ýè': -10,
            'ýé': -10, 'ýê': -10, 'ýë': -10, 'ýò': -25, 'ýó': -25, 'ýô': -25, 'ýõ': -25, 'ýö': -25, 'ýø': -25, 'ÿ,':
            -80, 'ÿ.': -80, 'ÿa': -30, 'ÿe': -10, 'ÿo': -25, 'ÿà': -30, 'ÿá': -30, 'ÿâ': -30, 'ÿã': -30, 'ÿä': -30,
            'ÿå': -30, 'ÿè': -10, 'ÿé': -10, 'ÿê': -10, 'ÿë': -10, 'ÿò': -25, 'ÿó': -25, 'ÿô': -25, 'ÿõ': -25, 'ÿö':
            -25, 'ÿø': -25
        },
    },
}

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "lc.py")
