"""STEP 1. LAY OUT THE PAGES: where every section, question and box goes.

Also holds what the layout needs: the settings (page size, colours, sizes, answer formats; change the look of
every form in section 1), text helpers, the rules ("mandatory now?"), and Adobe's Helvetica letter widths.
You don't need to open this file to change or make a form.

CONTENTS
    1. Settings: page, colours, sizes, answer formats      (change the look here)
    2. Text helpers: safe characters, measuring, wrapping
    3. Rules and dates
    4. Step 1: lay out the pages                           (class Layout)
    5. Font measurements (data)
"""
import datetime
import json
import re


# ====================================================================================================================
# 1. SETTINGS: PAGE, COLOURS, SIZES, ANSWER FORMATS
# ====================================================================================================================
# Change a number here to change it on every form (then rebuild and check the result).

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

# A question with beside=<width> in the form file: its label sits beside a box of that width, this far after the label.
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
# You shouldn't need to change this file.

# Text helpers: making text safe for the PDF's built-in fonts, measuring it, and wrapping it into lines.
#
# The form uses only the fonts every PDF reader has built in (Helvetica, Helvetica-Bold and ZapfDingbats), so no
# font files are embedded. Those fonts cover Western European characters (the "WinAnsi" set).


# Characters outside WinAnsi that have a plain equivalent.
PLAIN = {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-", "\u2026": "..."}  # curly quotes, dashes, ...


def safe(s):
    """Text the built-in fonts can draw: curly quotes and dashes become plain ones; anything else unknown becomes '?'."""
    return re.sub(r"[^\n\x20-\x7e\xa0-\xff\u20ac]", lambda m: PLAIN.get(m.group(0), "?"), s or "")


# Text is measured with Adobe's own Helvetica widths (METRICS, section 5 below), so it is
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
# 3. RULES AND DATES
# ====================================================================================================================
# You shouldn't need to change this file.

# The form's rules, evaluated in Python while building (the same rules also run in Acrobat, see acrobat_js.py).
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
# 4. STEP 1: LAY OUT THE PAGES
# ====================================================================================================================
# Change this file only to change how questions are arranged on the page.


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
        # beside=<width> in the form file fixes the box width and keeps the label beside it.
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
            # JavaScript shows it (lcDates in acrobat_js.py). AFDate_* are Acrobat's own date functions.
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
        """How many of the 12 grid columns a question needs (cols=N in the form file decides it instead)."""
        if q.get("cols"):
            return q["cols"]
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
        grows = [not q.get("cols") and (q["kind"] in ("long", "select") or (q["kind"] == "text" and q.get("format") != "number" and (q.get("max") or 99) > 3)) for q in row]
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

        # A section with a beside= question ends 3 points higher than the others (keeps its row spacing even).
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
        """Draws the sections in order: full width, or two side by side when both are short and similar in height.
        A section's width="full" / width="half" (in the form file) decides instead; new_page=True starts a new page."""
        full = {"x": M, "w": W - 2 * M, "cols": COLUMNS}
        half_w = (W - 2 * M - SECTION_GAP) / 2
        left = {"x": M, "w": half_w, "cols": COLUMNS // 2}
        right = {**left, "x": M + half_w + SECTION_GAP}

        def options_fit(s):   # every radio / tick-any option fits in half the page
            inner_w = self.inside(left)[1]
            return all(self.option_width(o) < inner_w for q in s["fields"] if has_options(q["kind"]) for o in q.get("options") or [])

        def can_half(s):
            return s.get("width") != "full" and (s.get("width") == "half" and options_fit(s) or s.get("width") is None and fits_half(s))

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
            if b and b.get("new_page"):
                b = None   # the next section starts a new page, so it can't sit beside this one
            if a.get("new_page") and i > 0:
                self.new_page()
            height_a = self.section_height(a, left) if b else 0
            height_b = self.section_height(b, right) if b else 0
            both_half = b and a.get("width") == "half" and b.get("width") == "half"
            side_by_side = b and can_half(a) and can_half(b) and (both_half or min(height_a, height_b) >= 0.45 * max(height_a, height_b))
            pair_height = max(height_a, height_b) + SECTION_GAP
            # Full width when they can't pair, or when the pair doesn't fit here but the first section alone does.
            if not side_by_side and a.get("width") == "half" and options_fit(a):   # a half section with no half partner
                if self.top - self.section_height(a, left) < BOTTOM:
                    self.new_page()
                self.draw_section(a, i, left, False)
                i += 1
                continue
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
        """A last page with room for two QR codes of the answers, one above the other. The Generate QR Code and Print
        Form buttons sit right under the first code, where they always were. acrobat_js.py draws the codes in
        Acrobat: usually one code fills the first frame; only when the answers are too long for one code does the
        second frame (under the buttons) appear, with the rest."""
        self.new_page()
        self.text("APPLICATION QR CODE (FOR BANK USE)", M, H - 56, 11, True)
        y = H - 70
        for line in wrap("When the form is filled in, press Generate QR Code (under the code), then Print Form. The Bank scans the code to read the application (all the answers, as JSON). If the answers are too long for one code, a second code appears under the buttons: the Bank scans both. Do not write on or fold the codes.", 8, W - 2 * M):
            self.text(line, M, y, 8, color=GREY)
            y -= 10
        label, gap, button_h = 12, 10, 22   # room for "QR code 1 of 2" above each frame; space around the buttons
        size = int((y - 4 - 46 - 2 * label - button_h - 2 * gap) / 2)   # two equal frames fill the page above the footer
        x = (W - size) / 2
        first_y = y - 4 - label - size
        buttons_y = first_y - gap - button_h
        self.qr = {"page": self.page.number, "slots": [(x, first_y, size), (x, buttons_y - gap - label - size, size)],
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
# 5. FONT MEASUREMENTS
# ====================================================================================================================
# Each character's width ("widths") and the kerning between pairs of characters ("kern"), in 1/1000 of
# the font size. Used by width() in section 2 to place labels, wrap text and size boxes.

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
            584, '\xa0': 278, '\xa1': 333, '\xa2': 556, '\xa3': 556, '\xa4': 556, '\xa5': 556, '\xa6': 260, '\xa7':
            556, '\xa8': 333, '\xa9': 737, '\xaa': 370, '\xab': 556, '\xac': 584, '\xad': 333, '\xae': 737, '\xaf':
            333, '\xb0': 400, '\xb1': 584, '\xb2': 333, '\xb3': 333, '\xb4': 333, '\xb5': 556, '\xb6': 537, '\xb7':
            278, '\xb8': 333, '\xb9': 333, '\xba': 365, '\xbb': 556, '\xbc': 834, '\xbd': 834, '\xbe': 834, '\xbf':
            611, '\xc0': 667, '\xc1': 667, '\xc2': 667, '\xc3': 667, '\xc4': 667, '\xc5': 667, '\xc6': 1000, '\xc7':
            722, '\xc8': 667, '\xc9': 667, '\xca': 667, '\xcb': 667, '\xcc': 278, '\xcd': 278, '\xce': 278, '\xcf':
            278, '\xd0': 722, '\xd1': 722, '\xd2': 778, '\xd3': 778, '\xd4': 778, '\xd5': 778, '\xd6': 778, '\xd7':
            584, '\xd8': 778, '\xd9': 722, '\xda': 722, '\xdb': 722, '\xdc': 722, '\xdd': 667, '\xde': 667, '\xdf':
            611, '\xe0': 556, '\xe1': 556, '\xe2': 556, '\xe3': 556, '\xe4': 556, '\xe5': 556, '\xe6': 889, '\xe7':
            500, '\xe8': 556, '\xe9': 556, '\xea': 556, '\xeb': 556, '\xec': 278, '\xed': 278, '\xee': 278, '\xef':
            278, '\xf0': 556, '\xf1': 556, '\xf2': 556, '\xf3': 556, '\xf4': 556, '\xf5': 556, '\xf6': 556, '\xf7':
            584, '\xf8': 611, '\xf9': 556, '\xfa': 556, '\xfb': 556, '\xfc': 556, '\xfd': 500, '\xfe': 556, '\xff':
            500, '\u20ac': 556
        },
        'kern': {
            ' T': -50, ' V': -50, ' W': -40, ' Y': -90, ' \xdd': -90, '. ': -60, '.\xa0': -60, ': ': -50, ':\xa0':
            -50, '; ': -50, ';\xa0': -50, 'AC': -30, 'AG': -30, 'AO': -30, 'AQ': -30, 'AT': -120, 'AU': -50, 'AV':
            -70, 'AW': -50, 'AY': -100, 'Au': -30, 'Av': -40, 'Aw': -40, 'Ay': -40, 'A\xc7': -30, 'A\xd2': -30,
            'A\xd3': -30, 'A\xd4': -30, 'A\xd5': -30, 'A\xd6': -30, 'A\xd8': -30, 'A\xd9': -50, 'A\xda': -50, 'A\xdb':
            -50, 'A\xdc': -50, 'A\xdd': -100, 'A\xf9': -30, 'A\xfa': -30, 'A\xfb': -30, 'A\xfc': -30, 'A\xfd': -40,
            'A\xff': -40, 'B,': -20, 'B.': -20, 'BU': -10, 'B\xd9': -10, 'B\xda': -10, 'B\xdb': -10, 'B\xdc': -10,
            'C,': -30, 'C.': -30, 'D,': -70, 'D.': -70, 'DA': -40, 'DV': -70, 'DW': -40, 'DY': -90, 'D\xc0': -40,
            'D\xc1': -40, 'D\xc2': -40, 'D\xc3': -40, 'D\xc4': -40, 'D\xc5': -40, 'D\xdd': -90, 'F,': -150, 'F.':
            -150, 'FA': -80, 'Fa': -50, 'Fe': -30, 'Fo': -30, 'Fr': -45, 'F\xc0': -80, 'F\xc1': -80, 'F\xc2': -80,
            'F\xc3': -80, 'F\xc4': -80, 'F\xc5': -80, 'F\xe0': -50, 'F\xe1': -50, 'F\xe2': -50, 'F\xe3': -50, 'F\xe4':
            -50, 'F\xe5': -50, 'F\xe8': -30, 'F\xe9': -30, 'F\xea': -30, 'F\xeb': -30, 'F\xf2': -30, 'F\xf3': -30,
            'F\xf4': -30, 'F\xf5': -30, 'F\xf6': -30, 'F\xf8': -30, 'J,': -30, 'J.': -30, 'JA': -20, 'Ja': -20, 'Ju':
            -20, 'J\xc0': -20, 'J\xc1': -20, 'J\xc2': -20, 'J\xc3': -20, 'J\xc4': -20, 'J\xc5': -20, 'J\xe0': -20,
            'J\xe1': -20, 'J\xe2': -20, 'J\xe3': -20, 'J\xe4': -20, 'J\xe5': -20, 'J\xf9': -20, 'J\xfa': -20, 'J\xfb':
            -20, 'J\xfc': -20, 'KO': -50, 'Ke': -40, 'Ko': -40, 'Ku': -30, 'Ky': -50, 'K\xd2': -50, 'K\xd3': -50,
            'K\xd4': -50, 'K\xd5': -50, 'K\xd6': -50, 'K\xd8': -50, 'K\xe8': -40, 'K\xe9': -40, 'K\xea': -40, 'K\xeb':
            -40, 'K\xf2': -40, 'K\xf3': -40, 'K\xf4': -40, 'K\xf5': -40, 'K\xf6': -40, 'K\xf8': -40, 'K\xf9': -30,
            'K\xfa': -30, 'K\xfb': -30, 'K\xfc': -30, 'K\xfd': -50, 'K\xff': -50, 'LT': -110, 'LV': -110, 'LW': -70,
            'LY': -140, 'Ly': -30, 'L\xdd': -140, 'L\xfd': -30, 'L\xff': -30, 'O,': -40, 'O.': -40, 'OA': -20, 'OT':
            -40, 'OV': -50, 'OW': -30, 'OX': -60, 'OY': -70, 'O\xc0': -20, 'O\xc1': -20, 'O\xc2': -20, 'O\xc3': -20,
            'O\xc4': -20, 'O\xc5': -20, 'O\xdd': -70, 'P,': -180, 'P.': -180, 'PA': -120, 'Pa': -40, 'Pe': -50, 'Po':
            -50, 'P\xc0': -120, 'P\xc1': -120, 'P\xc2': -120, 'P\xc3': -120, 'P\xc4': -120, 'P\xc5': -120, 'P\xe0':
            -40, 'P\xe1': -40, 'P\xe2': -40, 'P\xe3': -40, 'P\xe4': -40, 'P\xe5': -40, 'P\xe8': -50, 'P\xe9': -50,
            'P\xea': -50, 'P\xeb': -50, 'P\xf2': -50, 'P\xf3': -50, 'P\xf4': -50, 'P\xf5': -50, 'P\xf6': -50, 'P\xf8':
            -50, 'QU': -10, 'Q\xd9': -10, 'Q\xda': -10, 'Q\xdb': -10, 'Q\xdc': -10, 'RO': -20, 'RT': -30, 'RU': -40,
            'RV': -50, 'RW': -30, 'RY': -50, 'R\xd2': -20, 'R\xd3': -20, 'R\xd4': -20, 'R\xd5': -20, 'R\xd6': -20,
            'R\xd8': -20, 'R\xd9': -40, 'R\xda': -40, 'R\xdb': -40, 'R\xdc': -40, 'R\xdd': -50, 'S,': -20, 'S.': -20,
            'T,': -120, 'T-': -140, 'T.': -120, 'T:': -20, 'T;': -20, 'TA': -120, 'TO': -40, 'Ta': -120, 'Te': -120,
            'To': -120, 'Tr': -120, 'Tu': -120, 'Tw': -120, 'Ty': -120, 'T\xad': -140, 'T\xc0': -120, 'T\xc1': -120,
            'T\xc2': -120, 'T\xc3': -120, 'T\xc4': -120, 'T\xc5': -120, 'T\xd2': -40, 'T\xd3': -40, 'T\xd4': -40,
            'T\xd5': -40, 'T\xd6': -40, 'T\xd8': -40, 'T\xe0': -120, 'T\xe1': -120, 'T\xe2': -120, 'T\xe3': -60,
            'T\xe4': -120, 'T\xe5': -120, 'T\xe8': -60, 'T\xe9': -120, 'T\xea': -120, 'T\xeb': -120, 'T\xf2': -120,
            'T\xf3': -120, 'T\xf4': -120, 'T\xf5': -60, 'T\xf6': -120, 'T\xf8': -120, 'T\xf9': -120, 'T\xfa': -120,
            'T\xfb': -120, 'T\xfc': -120, 'T\xfd': -120, 'T\xff': -60, 'U,': -40, 'U.': -40, 'UA': -40, 'U\xc0': -40,
            'U\xc1': -40, 'U\xc2': -40, 'U\xc3': -40, 'U\xc4': -40, 'U\xc5': -40, 'V,': -125, 'V-': -80, 'V.': -125,
            'V:': -40, 'V;': -40, 'VA': -80, 'VG': -40, 'VO': -40, 'Va': -70, 'Ve': -80, 'Vo': -80, 'Vu': -70,
            'V\xad': -80, 'V\xc0': -80, 'V\xc1': -80, 'V\xc2': -80, 'V\xc3': -80, 'V\xc4': -80, 'V\xc5': -80, 'V\xd2':
            -40, 'V\xd3': -40, 'V\xd4': -40, 'V\xd5': -40, 'V\xd6': -40, 'V\xd8': -40, 'V\xe0': -70, 'V\xe1': -70,
            'V\xe2': -70, 'V\xe3': -70, 'V\xe4': -70, 'V\xe5': -70, 'V\xe8': -80, 'V\xe9': -80, 'V\xea': -80, 'V\xeb':
            -80, 'V\xf2': -80, 'V\xf3': -80, 'V\xf4': -80, 'V\xf5': -80, 'V\xf6': -80, 'V\xf8': -80, 'V\xf9': -70,
            'V\xfa': -70, 'V\xfb': -70, 'V\xfc': -70, 'W,': -80, 'W-': -40, 'W.': -80, 'WA': -50, 'WO': -20, 'Wa':
            -40, 'We': -30, 'Wo': -30, 'Wu': -30, 'Wy': -20, 'W\xad': -40, 'W\xc0': -50, 'W\xc1': -50, 'W\xc2': -50,
            'W\xc3': -50, 'W\xc4': -50, 'W\xc5': -50, 'W\xd2': -20, 'W\xd3': -20, 'W\xd4': -20, 'W\xd5': -20, 'W\xd6':
            -20, 'W\xd8': -20, 'W\xe0': -40, 'W\xe1': -40, 'W\xe2': -40, 'W\xe3': -40, 'W\xe4': -40, 'W\xe5': -40,
            'W\xe8': -30, 'W\xe9': -30, 'W\xea': -30, 'W\xeb': -30, 'W\xf2': -30, 'W\xf3': -30, 'W\xf4': -30, 'W\xf5':
            -30, 'W\xf6': -30, 'W\xf8': -30, 'W\xf9': -30, 'W\xfa': -30, 'W\xfb': -30, 'W\xfc': -30, 'W\xfd': -20,
            'W\xff': -20, 'Y,': -140, 'Y-': -140, 'Y.': -140, 'Y:': -60, 'Y;': -60, 'YA': -110, 'YO': -85, 'Ya': -140,
            'Ye': -140, 'Yi': -20, 'Yo': -140, 'Yu': -110, 'Y\xad': -140, 'Y\xc0': -110, 'Y\xc1': -110, 'Y\xc2': -110,
            'Y\xc3': -110, 'Y\xc4': -110, 'Y\xc5': -110, 'Y\xd2': -85, 'Y\xd3': -85, 'Y\xd4': -85, 'Y\xd5': -85,
            'Y\xd6': -85, 'Y\xd8': -85, 'Y\xe0': -140, 'Y\xe1': -140, 'Y\xe2': -140, 'Y\xe3': -140, 'Y\xe4': -140,
            'Y\xe5': -140, 'Y\xe8': -140, 'Y\xe9': -140, 'Y\xea': -140, 'Y\xeb': -140, 'Y\xed': -20, 'Y\xf2': -140,
            'Y\xf3': -140, 'Y\xf4': -140, 'Y\xf5': -140, 'Y\xf6': -140, 'Y\xf8': -140, 'Y\xf9': -110, 'Y\xfa': -110,
            'Y\xfb': -110, 'Y\xfc': -110, 'av': -20, 'aw': -20, 'ay': -30, 'a\xfd': -30, 'a\xff': -30, 'b,': -40,
            'b.': -40, 'bb': -10, 'bl': -20, 'bu': -20, 'bv': -20, 'by': -20, 'b\xf9': -20, 'b\xfa': -20, 'b\xfb':
            -20, 'b\xfc': -20, 'b\xfd': -20, 'b\xff': -20, 'c,': -15, 'ck': -20, 'e,': -15, 'e.': -15, 'ev': -30,
            'ew': -20, 'ex': -30, 'ey': -20, 'e\xfd': -20, 'e\xff': -20, 'f,': -30, 'f.': -30, 'fa': -30, 'fe': -30,
            'fo': -30, 'f\xe0': -30, 'f\xe1': -30, 'f\xe2': -30, 'f\xe3': -30, 'f\xe4': -30, 'f\xe5': -30, 'f\xe8':
            -30, 'f\xe9': -30, 'f\xea': -30, 'f\xeb': -30, 'f\xf2': -30, 'f\xf3': -30, 'f\xf4': -30, 'f\xf5': -30,
            'f\xf6': -30, 'f\xf8': -30, 'gr': -10, 'hy': -30, 'h\xfd': -30, 'h\xff': -30, 'ke': -20, 'ko': -20,
            'k\xe8': -20, 'k\xe9': -20, 'k\xea': -20, 'k\xeb': -20, 'k\xf2': -20, 'k\xf3': -20, 'k\xf4': -20, 'k\xf5':
            -20, 'k\xf6': -20, 'k\xf8': -20, 'mu': -10, 'my': -15, 'm\xf9': -10, 'm\xfa': -10, 'm\xfb': -10, 'm\xfc':
            -10, 'm\xfd': -15, 'm\xff': -15, 'nu': -10, 'nv': -20, 'ny': -15, 'n\xf9': -10, 'n\xfa': -10, 'n\xfb':
            -10, 'n\xfc': -10, 'n\xfd': -15, 'n\xff': -15, 'o,': -40, 'o.': -40, 'ov': -15, 'ow': -15, 'ox': -30,
            'oy': -30, 'o\xfd': -30, 'o\xff': -30, 'p,': -35, 'p.': -35, 'py': -30, 'p\xfd': -30, 'p\xff': -30, 'r,':
            -50, 'r.': -50, 'r:': 30, 'r;': 30, 'ra': -10, 'ri': 15, 'rk': 15, 'rl': 15, 'rm': 25, 'rn': 25, 'rp': 30,
            'rt': 40, 'ru': 15, 'rv': 30, 'ry': 30, 'r\xe0': -10, 'r\xe1': -10, 'r\xe2': -10, 'r\xe3': -10, 'r\xe4':
            -10, 'r\xe5': -10, 'r\xec': 15, 'r\xed': 15, 'r\xee': 15, 'r\xef': 15, 'r\xf1': 25, 'r\xf9': 15, 'r\xfa':
            15, 'r\xfb': 15, 'r\xfc': 15, 'r\xfd': 30, 'r\xff': 30, 's,': -15, 's.': -15, 'sw': -30, 'v,': -80, 'v.':
            -80, 'va': -25, 've': -25, 'vo': -25, 'v\xe0': -25, 'v\xe1': -25, 'v\xe2': -25, 'v\xe3': -25, 'v\xe4':
            -25, 'v\xe5': -25, 'v\xe8': -25, 'v\xe9': -25, 'v\xea': -25, 'v\xeb': -25, 'v\xf2': -25, 'v\xf3': -25,
            'v\xf4': -25, 'v\xf5': -25, 'v\xf6': -25, 'v\xf8': -25, 'w,': -60, 'w.': -60, 'wa': -15, 'we': -10, 'wo':
            -10, 'w\xe0': -15, 'w\xe1': -15, 'w\xe2': -15, 'w\xe3': -15, 'w\xe4': -15, 'w\xe5': -15, 'w\xe8': -10,
            'w\xe9': -10, 'w\xea': -10, 'w\xeb': -10, 'w\xf2': -10, 'w\xf3': -10, 'w\xf4': -10, 'w\xf5': -10, 'w\xf6':
            -10, 'w\xf8': -10, 'xe': -30, 'x\xe8': -30, 'x\xe9': -30, 'x\xea': -30, 'x\xeb': -30, 'y,': -100, 'y.':
            -100, 'ya': -20, 'ye': -20, 'yo': -20, 'y\xe0': -20, 'y\xe1': -20, 'y\xe2': -20, 'y\xe3': -20, 'y\xe4':
            -20, 'y\xe5': -20, 'y\xe8': -20, 'y\xe9': -20, 'y\xea': -20, 'y\xeb': -20, 'y\xf2': -20, 'y\xf3': -20,
            'y\xf4': -20, 'y\xf5': -20, 'y\xf6': -20, 'y\xf8': -20, 'ze': -15, 'zo': -15, 'z\xe8': -15, 'z\xe9': -15,
            'z\xea': -15, 'z\xeb': -15, 'z\xf2': -15, 'z\xf3': -15, 'z\xf4': -15, 'z\xf5': -15, 'z\xf6': -15, 'z\xf8':
            -15, '\xa0T': -50, '\xa0V': -50, '\xa0W': -40, '\xa0Y': -90, '\xa0\xdd': -90, '\xc0C': -30, '\xc0G': -30,
            '\xc0O': -30, '\xc0Q': -30, '\xc0T': -120, '\xc0U': -50, '\xc0V': -70, '\xc0W': -50, '\xc0Y': -100,
            '\xc0u': -30, '\xc0v': -40, '\xc0w': -40, '\xc0y': -40, '\xc0\xc7': -30, '\xc0\xd2': -30, '\xc0\xd3': -30,
            '\xc0\xd4': -30, '\xc0\xd5': -30, '\xc0\xd6': -30, '\xc0\xd8': -30, '\xc0\xd9': -50, '\xc0\xda': -50,
            '\xc0\xdb': -50, '\xc0\xdc': -50, '\xc0\xdd': -100, '\xc0\xf9': -30, '\xc0\xfa': -30, '\xc0\xfb': -30,
            '\xc0\xfc': -30, '\xc0\xfd': -40, '\xc0\xff': -40, '\xc1C': -30, '\xc1G': -30, '\xc1O': -30, '\xc1Q': -30,
            '\xc1T': -120, '\xc1U': -50, '\xc1V': -70, '\xc1W': -50, '\xc1Y': -100, '\xc1u': -30, '\xc1v': -40,
            '\xc1w': -40, '\xc1y': -40, '\xc1\xc7': -30, '\xc1\xd2': -30, '\xc1\xd3': -30, '\xc1\xd4': -30,
            '\xc1\xd5': -30, '\xc1\xd6': -30, '\xc1\xd8': -30, '\xc1\xd9': -50, '\xc1\xda': -50, '\xc1\xdb': -50,
            '\xc1\xdc': -50, '\xc1\xdd': -100, '\xc1\xf9': -30, '\xc1\xfa': -30, '\xc1\xfb': -30, '\xc1\xfc': -30,
            '\xc1\xfd': -40, '\xc1\xff': -40, '\xc2C': -30, '\xc2G': -30, '\xc2O': -30, '\xc2Q': -30, '\xc2T': -120,
            '\xc2U': -50, '\xc2V': -70, '\xc2W': -50, '\xc2Y': -100, '\xc2u': -30, '\xc2v': -40, '\xc2w': -40,
            '\xc2y': -40, '\xc2\xc7': -30, '\xc2\xd2': -30, '\xc2\xd3': -30, '\xc2\xd4': -30, '\xc2\xd5': -30,
            '\xc2\xd6': -30, '\xc2\xd8': -30, '\xc2\xd9': -50, '\xc2\xda': -50, '\xc2\xdb': -50, '\xc2\xdc': -50,
            '\xc2\xdd': -100, '\xc2\xf9': -30, '\xc2\xfa': -30, '\xc2\xfb': -30, '\xc2\xfc': -30, '\xc2\xfd': -40,
            '\xc2\xff': -40, '\xc3C': -30, '\xc3G': -30, '\xc3O': -30, '\xc3Q': -30, '\xc3T': -120, '\xc3U': -50,
            '\xc3V': -70, '\xc3W': -50, '\xc3Y': -100, '\xc3u': -30, '\xc3v': -40, '\xc3w': -40, '\xc3y': -40,
            '\xc3\xc7': -30, '\xc3\xd2': -30, '\xc3\xd3': -30, '\xc3\xd4': -30, '\xc3\xd5': -30, '\xc3\xd6': -30,
            '\xc3\xd8': -30, '\xc3\xd9': -50, '\xc3\xda': -50, '\xc3\xdb': -50, '\xc3\xdc': -50, '\xc3\xdd': -100,
            '\xc3\xf9': -30, '\xc3\xfa': -30, '\xc3\xfb': -30, '\xc3\xfc': -30, '\xc3\xfd': -40, '\xc3\xff': -40,
            '\xc4C': -30, '\xc4G': -30, '\xc4O': -30, '\xc4Q': -30, '\xc4T': -120, '\xc4U': -50, '\xc4V': -70,
            '\xc4W': -50, '\xc4Y': -100, '\xc4u': -30, '\xc4v': -40, '\xc4w': -40, '\xc4y': -40, '\xc4\xc7': -30,
            '\xc4\xd2': -30, '\xc4\xd3': -30, '\xc4\xd4': -30, '\xc4\xd5': -30, '\xc4\xd6': -30, '\xc4\xd8': -30,
            '\xc4\xd9': -50, '\xc4\xda': -50, '\xc4\xdb': -50, '\xc4\xdc': -50, '\xc4\xdd': -100, '\xc4\xf9': -30,
            '\xc4\xfa': -30, '\xc4\xfb': -30, '\xc4\xfc': -30, '\xc4\xfd': -40, '\xc4\xff': -40, '\xc5C': -30,
            '\xc5G': -30, '\xc5O': -30, '\xc5Q': -30, '\xc5T': -120, '\xc5U': -50, '\xc5V': -70, '\xc5W': -50,
            '\xc5Y': -100, '\xc5u': -30, '\xc5v': -40, '\xc5w': -40, '\xc5y': -40, '\xc5\xc7': -30, '\xc5\xd2': -30,
            '\xc5\xd3': -30, '\xc5\xd4': -30, '\xc5\xd5': -30, '\xc5\xd6': -30, '\xc5\xd8': -30, '\xc5\xd9': -50,
            '\xc5\xda': -50, '\xc5\xdb': -50, '\xc5\xdc': -50, '\xc5\xdd': -100, '\xc5\xf9': -30, '\xc5\xfa': -30,
            '\xc5\xfb': -30, '\xc5\xfc': -30, '\xc5\xfd': -40, '\xc5\xff': -40, '\xc7,': -30, '\xc7.': -30, '\xd2,':
            -40, '\xd2.': -40, '\xd2A': -20, '\xd2T': -40, '\xd2V': -50, '\xd2W': -30, '\xd2X': -60, '\xd2Y': -70,
            '\xd2\xc0': -20, '\xd2\xc1': -20, '\xd2\xc2': -20, '\xd2\xc3': -20, '\xd2\xc4': -20, '\xd2\xc5': -20,
            '\xd2\xdd': -70, '\xd3,': -40, '\xd3.': -40, '\xd3A': -20, '\xd3T': -40, '\xd3V': -50, '\xd3W': -30,
            '\xd3X': -60, '\xd3Y': -70, '\xd3\xc0': -20, '\xd3\xc1': -20, '\xd3\xc2': -20, '\xd3\xc3': -20,
            '\xd3\xc4': -20, '\xd3\xc5': -20, '\xd3\xdd': -70, '\xd4,': -40, '\xd4.': -40, '\xd4A': -20, '\xd4T': -40,
            '\xd4V': -50, '\xd4W': -30, '\xd4X': -60, '\xd4Y': -70, '\xd4\xc0': -20, '\xd4\xc1': -20, '\xd4\xc2': -20,
            '\xd4\xc3': -20, '\xd4\xc4': -20, '\xd4\xc5': -20, '\xd4\xdd': -70, '\xd5,': -40, '\xd5.': -40, '\xd5A':
            -20, '\xd5T': -40, '\xd5V': -50, '\xd5W': -30, '\xd5X': -60, '\xd5Y': -70, '\xd5\xc0': -20, '\xd5\xc1':
            -20, '\xd5\xc2': -20, '\xd5\xc3': -20, '\xd5\xc4': -20, '\xd5\xc5': -20, '\xd5\xdd': -70, '\xd6,': -40,
            '\xd6.': -40, '\xd6A': -20, '\xd6T': -40, '\xd6V': -50, '\xd6W': -30, '\xd6X': -60, '\xd6Y': -70,
            '\xd6\xc0': -20, '\xd6\xc1': -20, '\xd6\xc2': -20, '\xd6\xc3': -20, '\xd6\xc4': -20, '\xd6\xc5': -20,
            '\xd6\xdd': -70, '\xd8,': -40, '\xd8.': -40, '\xd8A': -20, '\xd8T': -40, '\xd8V': -50, '\xd8W': -30,
            '\xd8X': -60, '\xd8Y': -70, '\xd8\xc0': -20, '\xd8\xc1': -20, '\xd8\xc2': -20, '\xd8\xc3': -20,
            '\xd8\xc4': -20, '\xd8\xc5': -20, '\xd8\xdd': -70, '\xd9,': -40, '\xd9.': -40, '\xd9A': -40, '\xd9\xc0':
            -40, '\xd9\xc1': -40, '\xd9\xc2': -40, '\xd9\xc3': -40, '\xd9\xc4': -40, '\xd9\xc5': -40, '\xda,': -40,
            '\xda.': -40, '\xdaA': -40, '\xda\xc0': -40, '\xda\xc1': -40, '\xda\xc2': -40, '\xda\xc3': -40,
            '\xda\xc4': -40, '\xda\xc5': -40, '\xdb,': -40, '\xdb.': -40, '\xdbA': -40, '\xdb\xc0': -40, '\xdb\xc1':
            -40, '\xdb\xc2': -40, '\xdb\xc3': -40, '\xdb\xc4': -40, '\xdb\xc5': -40, '\xdc,': -40, '\xdc.': -40,
            '\xdcA': -40, '\xdc\xc0': -40, '\xdc\xc1': -40, '\xdc\xc2': -40, '\xdc\xc3': -40, '\xdc\xc4': -40,
            '\xdc\xc5': -40, '\xdd,': -140, '\xdd-': -140, '\xdd.': -140, '\xdd:': -60, '\xdd;': -60, '\xddA': -110,
            '\xddO': -85, '\xdda': -140, '\xdde': -140, '\xddi': -20, '\xddo': -140, '\xddu': -110, '\xdd\xad': -140,
            '\xdd\xc0': -110, '\xdd\xc1': -110, '\xdd\xc2': -110, '\xdd\xc3': -110, '\xdd\xc4': -110, '\xdd\xc5':
            -110, '\xdd\xd2': -85, '\xdd\xd3': -85, '\xdd\xd4': -85, '\xdd\xd5': -85, '\xdd\xd6': -85, '\xdd\xd8':
            -85, '\xdd\xe0': -140, '\xdd\xe1': -140, '\xdd\xe2': -140, '\xdd\xe3': -70, '\xdd\xe4': -140, '\xdd\xe5':
            -140, '\xdd\xe8': -140, '\xdd\xe9': -140, '\xdd\xea': -140, '\xdd\xeb': -140, '\xdd\xed': -20, '\xdd\xf2':
            -140, '\xdd\xf3': -140, '\xdd\xf4': -140, '\xdd\xf5': -140, '\xdd\xf6': -140, '\xdd\xf8': -140,
            '\xdd\xf9': -110, '\xdd\xfa': -110, '\xdd\xfb': -110, '\xdd\xfc': -110, '\xe0v': -20, '\xe0w': -20,
            '\xe0y': -30, '\xe0\xfd': -30, '\xe0\xff': -30, '\xe1v': -20, '\xe1w': -20, '\xe1y': -30, '\xe1\xfd': -30,
            '\xe1\xff': -30, '\xe2v': -20, '\xe2w': -20, '\xe2y': -30, '\xe2\xfd': -30, '\xe2\xff': -30, '\xe3v': -20,
            '\xe3w': -20, '\xe3y': -30, '\xe3\xfd': -30, '\xe3\xff': -30, '\xe4v': -20, '\xe4w': -20, '\xe4y': -30,
            '\xe4\xfd': -30, '\xe4\xff': -30, '\xe5v': -20, '\xe5w': -20, '\xe5y': -30, '\xe5\xfd': -30, '\xe5\xff':
            -30, '\xe7,': -15, '\xe7k': -20, '\xe8,': -15, '\xe8.': -15, '\xe8v': -30, '\xe8w': -20, '\xe8x': -30,
            '\xe8y': -20, '\xe8\xfd': -20, '\xe8\xff': -20, '\xe9,': -15, '\xe9.': -15, '\xe9v': -30, '\xe9w': -20,
            '\xe9x': -30, '\xe9y': -20, '\xe9\xfd': -20, '\xe9\xff': -20, '\xea,': -15, '\xea.': -15, '\xeav': -30,
            '\xeaw': -20, '\xeax': -30, '\xeay': -20, '\xea\xfd': -20, '\xea\xff': -20, '\xeb,': -15, '\xeb.': -15,
            '\xebv': -30, '\xebw': -20, '\xebx': -30, '\xeby': -20, '\xeb\xfd': -20, '\xeb\xff': -20, '\xf1u': -10,
            '\xf1v': -20, '\xf1y': -15, '\xf1\xf9': -10, '\xf1\xfa': -10, '\xf1\xfb': -10, '\xf1\xfc': -10,
            '\xf1\xfd': -15, '\xf1\xff': -15, '\xf2,': -40, '\xf2.': -40, '\xf2v': -15, '\xf2w': -15, '\xf2x': -30,
            '\xf2y': -30, '\xf2\xfd': -30, '\xf2\xff': -30, '\xf3,': -40, '\xf3.': -40, '\xf3v': -15, '\xf3w': -15,
            '\xf3x': -30, '\xf3y': -30, '\xf3\xfd': -30, '\xf3\xff': -30, '\xf4,': -40, '\xf4.': -40, '\xf4v': -15,
            '\xf4w': -15, '\xf4x': -30, '\xf4y': -30, '\xf4\xfd': -30, '\xf4\xff': -30, '\xf5,': -40, '\xf5.': -40,
            '\xf5v': -15, '\xf5w': -15, '\xf5x': -30, '\xf5y': -30, '\xf5\xfd': -30, '\xf5\xff': -30, '\xf6,': -40,
            '\xf6.': -40, '\xf6v': -15, '\xf6w': -15, '\xf6x': -30, '\xf6y': -30, '\xf6\xfd': -30, '\xf6\xff': -30,
            '\xf8,': -95, '\xf8.': -95, '\xf8a': -55, '\xf8b': -55, '\xf8c': -55, '\xf8d': -55, '\xf8e': -55, '\xf8f':
            -55, '\xf8g': -55, '\xf8h': -55, '\xf8i': -55, '\xf8j': -55, '\xf8k': -55, '\xf8l': -55, '\xf8m': -55,
            '\xf8n': -55, '\xf8o': -55, '\xf8p': -55, '\xf8q': -55, '\xf8r': -55, '\xf8s': -55, '\xf8t': -55, '\xf8u':
            -55, '\xf8v': -70, '\xf8w': -70, '\xf8x': -85, '\xf8y': -70, '\xf8z': -55, '\xf8\xe0': -55, '\xf8\xe1':
            -55, '\xf8\xe2': -55, '\xf8\xe3': -55, '\xf8\xe4': -55, '\xf8\xe5': -55, '\xf8\xe7': -55, '\xf8\xe8': -55,
            '\xf8\xe9': -55, '\xf8\xea': -55, '\xf8\xeb': -55, '\xf8\xec': -55, '\xf8\xed': -55, '\xf8\xee': -55,
            '\xf8\xef': -55, '\xf8\xf1': -55, '\xf8\xf2': -55, '\xf8\xf3': -55, '\xf8\xf4': -55, '\xf8\xf5': -55,
            '\xf8\xf6': -55, '\xf8\xf8': -55, '\xf8\xf9': -55, '\xf8\xfa': -55, '\xf8\xfb': -55, '\xf8\xfc': -55,
            '\xf8\xfd': -70, '\xf8\xff': -70, '\xfd,': -100, '\xfd.': -100, '\xfda': -20, '\xfde': -20, '\xfdo': -20,
            '\xfd\xe0': -20, '\xfd\xe1': -20, '\xfd\xe2': -20, '\xfd\xe3': -20, '\xfd\xe4': -20, '\xfd\xe5': -20,
            '\xfd\xe8': -20, '\xfd\xe9': -20, '\xfd\xea': -20, '\xfd\xeb': -20, '\xfd\xf2': -20, '\xfd\xf3': -20,
            '\xfd\xf4': -20, '\xfd\xf5': -20, '\xfd\xf6': -20, '\xfd\xf8': -20, '\xff,': -100, '\xff.': -100, '\xffa':
            -20, '\xffe': -20, '\xffo': -20, '\xff\xe0': -20, '\xff\xe1': -20, '\xff\xe2': -20, '\xff\xe3': -20,
            '\xff\xe4': -20, '\xff\xe5': -20, '\xff\xe8': -20, '\xff\xe9': -20, '\xff\xea': -20, '\xff\xeb': -20,
            '\xff\xf2': -20, '\xff\xf3': -20, '\xff\xf4': -20, '\xff\xf5': -20, '\xff\xf6': -20, '\xff\xf8': -20
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
            584, '\xa0': 278, '\xa1': 333, '\xa2': 556, '\xa3': 556, '\xa4': 556, '\xa5': 556, '\xa6': 280, '\xa7':
            556, '\xa8': 333, '\xa9': 737, '\xaa': 370, '\xab': 556, '\xac': 584, '\xad': 333, '\xae': 737, '\xaf':
            333, '\xb0': 400, '\xb1': 584, '\xb2': 333, '\xb3': 333, '\xb4': 333, '\xb5': 611, '\xb6': 556, '\xb7':
            278, '\xb8': 333, '\xb9': 333, '\xba': 365, '\xbb': 556, '\xbc': 834, '\xbd': 834, '\xbe': 834, '\xbf':
            611, '\xc0': 722, '\xc1': 722, '\xc2': 722, '\xc3': 722, '\xc4': 722, '\xc5': 722, '\xc6': 1000, '\xc7':
            722, '\xc8': 667, '\xc9': 667, '\xca': 667, '\xcb': 667, '\xcc': 278, '\xcd': 278, '\xce': 278, '\xcf':
            278, '\xd0': 722, '\xd1': 722, '\xd2': 778, '\xd3': 778, '\xd4': 778, '\xd5': 778, '\xd6': 778, '\xd7':
            584, '\xd8': 778, '\xd9': 722, '\xda': 722, '\xdb': 722, '\xdc': 722, '\xdd': 667, '\xde': 667, '\xdf':
            611, '\xe0': 556, '\xe1': 556, '\xe2': 556, '\xe3': 556, '\xe4': 556, '\xe5': 556, '\xe6': 889, '\xe7':
            556, '\xe8': 556, '\xe9': 556, '\xea': 556, '\xeb': 556, '\xec': 278, '\xed': 278, '\xee': 278, '\xef':
            278, '\xf0': 611, '\xf1': 611, '\xf2': 611, '\xf3': 611, '\xf4': 611, '\xf5': 611, '\xf6': 611, '\xf7':
            584, '\xf8': 611, '\xf9': 611, '\xfa': 611, '\xfb': 611, '\xfc': 611, '\xfd': 556, '\xfe': 611, '\xff':
            556, '\u20ac': 556
        },
        'kern': {
            ' T': -100, ' V': -80, ' W': -80, ' Y': -120, ' \xdd': -120, ', ': -40, ',\xa0': -40, '. ': -40, '.\xa0':
            -40, ': ': -40, ':\xa0': -40, '; ': -40, ';\xa0': -40, 'AC': -40, 'AG': -50, 'AO': -40, 'AQ': -40, 'AT':
            -90, 'AU': -50, 'AV': -80, 'AW': -60, 'AY': -110, 'Au': -30, 'Av': -40, 'Aw': -30, 'Ay': -30, 'A\xc7':
            -40, 'A\xd2': -40, 'A\xd3': -40, 'A\xd4': -40, 'A\xd5': -40, 'A\xd6': -40, 'A\xd8': -40, 'A\xd9': -50,
            'A\xda': -50, 'A\xdb': -50, 'A\xdc': -50, 'A\xdd': -110, 'A\xf9': -30, 'A\xfa': -30, 'A\xfb': -30,
            'A\xfc': -30, 'A\xfd': -30, 'A\xff': -30, 'BA': -30, 'BU': -10, 'B\xc0': -30, 'B\xc1': -30, 'B\xc2': -30,
            'B\xc3': -30, 'B\xc4': -30, 'B\xc5': -30, 'B\xd9': -10, 'B\xda': -10, 'B\xdb': -10, 'B\xdc': -10, 'D,':
            -30, 'D.': -30, 'DA': -40, 'DV': -40, 'DW': -40, 'DY': -70, 'D\xc0': -40, 'D\xc1': -40, 'D\xc2': -40,
            'D\xc3': -40, 'D\xc4': -40, 'D\xc5': -40, 'D\xdd': -70, 'F,': -100, 'F.': -100, 'FA': -80, 'Fa': -20,
            'F\xc0': -80, 'F\xc1': -80, 'F\xc2': -80, 'F\xc3': -80, 'F\xc4': -80, 'F\xc5': -80, 'F\xe0': -20, 'F\xe1':
            -20, 'F\xe2': -20, 'F\xe3': -20, 'F\xe4': -20, 'F\xe5': -20, 'J,': -20, 'J.': -20, 'JA': -20, 'Ju': -20,
            'J\xc0': -20, 'J\xc1': -20, 'J\xc2': -20, 'J\xc3': -20, 'J\xc4': -20, 'J\xc5': -20, 'J\xf9': -20, 'J\xfa':
            -20, 'J\xfb': -20, 'J\xfc': -20, 'KO': -30, 'Ke': -15, 'Ko': -35, 'Ku': -30, 'Ky': -40, 'K\xd2': -30,
            'K\xd3': -30, 'K\xd4': -30, 'K\xd5': -30, 'K\xd6': -30, 'K\xd8': -30, 'K\xe8': -15, 'K\xe9': -15, 'K\xea':
            -15, 'K\xeb': -15, 'K\xf2': -35, 'K\xf3': -35, 'K\xf4': -35, 'K\xf5': -35, 'K\xf6': -35, 'K\xf8': -35,
            'K\xf9': -30, 'K\xfa': -30, 'K\xfb': -30, 'K\xfc': -30, 'K\xfd': -40, 'K\xff': -40, 'LT': -90, 'LV': -110,
            'LW': -80, 'LY': -120, 'Ly': -30, 'L\xdd': -120, 'L\xfd': -30, 'L\xff': -30, 'O,': -40, 'O.': -40, 'OA':
            -50, 'OT': -40, 'OV': -50, 'OW': -50, 'OX': -50, 'OY': -70, 'O\xc0': -50, 'O\xc1': -50, 'O\xc2': -50,
            'O\xc3': -50, 'O\xc4': -50, 'O\xc5': -50, 'O\xdd': -70, 'P,': -120, 'P.': -120, 'PA': -100, 'Pa': -30,
            'Pe': -30, 'Po': -40, 'P\xc0': -100, 'P\xc1': -100, 'P\xc2': -100, 'P\xc3': -100, 'P\xc4': -100, 'P\xc5':
            -100, 'P\xe0': -30, 'P\xe1': -30, 'P\xe2': -30, 'P\xe3': -30, 'P\xe4': -30, 'P\xe5': -30, 'P\xe8': -30,
            'P\xe9': -30, 'P\xea': -30, 'P\xeb': -30, 'P\xf2': -40, 'P\xf3': -40, 'P\xf4': -40, 'P\xf5': -40, 'P\xf6':
            -40, 'P\xf8': -40, 'Q,': 20, 'Q.': 20, 'QU': -10, 'Q\xd9': -10, 'Q\xda': -10, 'Q\xdb': -10, 'Q\xdc': -10,
            'RO': -20, 'RT': -20, 'RU': -20, 'RV': -50, 'RW': -40, 'RY': -50, 'R\xd2': -20, 'R\xd3': -20, 'R\xd4':
            -20, 'R\xd5': -20, 'R\xd6': -20, 'R\xd8': -20, 'R\xd9': -20, 'R\xda': -20, 'R\xdb': -20, 'R\xdc': -20,
            'R\xdd': -50, 'T,': -80, 'T-': -120, 'T.': -80, 'T:': -40, 'T;': -40, 'TA': -90, 'TO': -40, 'Ta': -80,
            'Te': -60, 'To': -80, 'Tr': -80, 'Tu': -90, 'Tw': -60, 'Ty': -60, 'T\xad': -120, 'T\xc0': -90, 'T\xc1':
            -90, 'T\xc2': -90, 'T\xc3': -90, 'T\xc4': -90, 'T\xc5': -90, 'T\xd2': -40, 'T\xd3': -40, 'T\xd4': -40,
            'T\xd5': -40, 'T\xd6': -40, 'T\xd8': -40, 'T\xe0': -80, 'T\xe1': -80, 'T\xe2': -80, 'T\xe3': -80, 'T\xe4':
            -80, 'T\xe5': -80, 'T\xe8': -60, 'T\xe9': -60, 'T\xea': -60, 'T\xeb': -60, 'T\xf2': -80, 'T\xf3': -80,
            'T\xf4': -80, 'T\xf5': -80, 'T\xf6': -80, 'T\xf8': -80, 'T\xf9': -90, 'T\xfa': -90, 'T\xfb': -90, 'T\xfc':
            -90, 'T\xfd': -60, 'T\xff': -60, 'U,': -30, 'U.': -30, 'UA': -50, 'U\xc0': -50, 'U\xc1': -50, 'U\xc2':
            -50, 'U\xc3': -50, 'U\xc4': -50, 'U\xc5': -50, 'V,': -120, 'V-': -80, 'V.': -120, 'V:': -40, 'V;': -40,
            'VA': -80, 'VG': -50, 'VO': -50, 'Va': -60, 'Ve': -50, 'Vo': -90, 'Vu': -60, 'V\xad': -80, 'V\xc0': -80,
            'V\xc1': -80, 'V\xc2': -80, 'V\xc3': -80, 'V\xc4': -80, 'V\xc5': -80, 'V\xd2': -50, 'V\xd3': -50, 'V\xd4':
            -50, 'V\xd5': -50, 'V\xd6': -50, 'V\xd8': -50, 'V\xe0': -60, 'V\xe1': -60, 'V\xe2': -60, 'V\xe3': -60,
            'V\xe4': -60, 'V\xe5': -60, 'V\xe8': -50, 'V\xe9': -50, 'V\xea': -50, 'V\xeb': -50, 'V\xf2': -90, 'V\xf3':
            -90, 'V\xf4': -90, 'V\xf5': -90, 'V\xf6': -90, 'V\xf8': -90, 'V\xf9': -60, 'V\xfa': -60, 'V\xfb': -60,
            'V\xfc': -60, 'W,': -80, 'W-': -40, 'W.': -80, 'W:': -10, 'W;': -10, 'WA': -60, 'WO': -20, 'Wa': -40,
            'We': -35, 'Wo': -60, 'Wu': -45, 'Wy': -20, 'W\xad': -40, 'W\xc0': -60, 'W\xc1': -60, 'W\xc2': -60,
            'W\xc3': -60, 'W\xc4': -60, 'W\xc5': -60, 'W\xd2': -20, 'W\xd3': -20, 'W\xd4': -20, 'W\xd5': -20, 'W\xd6':
            -20, 'W\xd8': -20, 'W\xe0': -40, 'W\xe1': -40, 'W\xe2': -40, 'W\xe3': -40, 'W\xe4': -40, 'W\xe5': -40,
            'W\xe8': -35, 'W\xe9': -35, 'W\xea': -35, 'W\xeb': -35, 'W\xf2': -60, 'W\xf3': -60, 'W\xf4': -60, 'W\xf5':
            -60, 'W\xf6': -60, 'W\xf8': -60, 'W\xf9': -45, 'W\xfa': -45, 'W\xfb': -45, 'W\xfc': -45, 'W\xfd': -20,
            'W\xff': -20, 'Y,': -100, 'Y.': -100, 'Y:': -50, 'Y;': -50, 'YA': -110, 'YO': -70, 'Ya': -90, 'Ye': -80,
            'Yo': -100, 'Yu': -100, 'Y\xc0': -110, 'Y\xc1': -110, 'Y\xc2': -110, 'Y\xc3': -110, 'Y\xc4': -110,
            'Y\xc5': -110, 'Y\xd2': -70, 'Y\xd3': -70, 'Y\xd4': -70, 'Y\xd5': -70, 'Y\xd6': -70, 'Y\xd8': -70,
            'Y\xe0': -90, 'Y\xe1': -90, 'Y\xe2': -90, 'Y\xe3': -90, 'Y\xe4': -90, 'Y\xe5': -90, 'Y\xe8': -80, 'Y\xe9':
            -80, 'Y\xea': -80, 'Y\xeb': -80, 'Y\xf2': -100, 'Y\xf3': -100, 'Y\xf4': -100, 'Y\xf5': -100, 'Y\xf6':
            -100, 'Y\xf8': -100, 'Y\xf9': -100, 'Y\xfa': -100, 'Y\xfb': -100, 'Y\xfc': -100, 'ag': -10, 'av': -15,
            'aw': -15, 'ay': -20, 'a\xfd': -20, 'a\xff': -20, 'bl': -10, 'bu': -20, 'bv': -20, 'by': -20, 'b\xf9':
            -20, 'b\xfa': -20, 'b\xfb': -20, 'b\xfc': -20, 'b\xfd': -20, 'b\xff': -20, 'ch': -10, 'ck': -20, 'cl':
            -20, 'cy': -10, 'c\xfd': -10, 'c\xff': -10, 'dd': -10, 'dv': -15, 'dw': -15, 'dy': -15, 'd\xfd': -15,
            'd\xff': -15, 'e,': 10, 'e.': 20, 'ev': -15, 'ew': -15, 'ex': -15, 'ey': -15, 'e\xfd': -15, 'e\xff': -15,
            'f,': -10, 'f.': -10, 'fe': -10, 'fo': -20, 'f\xe8': -10, 'f\xe9': -10, 'f\xea': -10, 'f\xeb': -10,
            'f\xf2': -20, 'f\xf3': -20, 'f\xf4': -20, 'f\xf5': -20, 'f\xf6': -20, 'f\xf8': -20, 'ge': 10, 'gg': -10,
            'g\xe8': 10, 'g\xe9': 10, 'g\xea': 10, 'g\xeb': 10, 'hy': -20, 'h\xfd': -20, 'h\xff': -20, 'ko': -15,
            'k\xf2': -15, 'k\xf3': -15, 'k\xf4': -15, 'k\xf5': -15, 'k\xf6': -15, 'k\xf8': -15, 'lw': -15, 'ly': -15,
            'l\xfd': -15, 'l\xff': -15, 'mu': -20, 'my': -30, 'm\xf9': -20, 'm\xfa': -20, 'm\xfb': -20, 'm\xfc': -20,
            'm\xfd': -30, 'm\xff': -30, 'nu': -10, 'nv': -40, 'ny': -20, 'n\xf9': -10, 'n\xfa': -10, 'n\xfb': -10,
            'n\xfc': -10, 'n\xfd': -20, 'n\xff': -20, 'ov': -20, 'ow': -15, 'ox': -30, 'oy': -20, 'o\xfd': -20,
            'o\xff': -20, 'py': -15, 'p\xfd': -15, 'p\xff': -15, 'r,': -60, 'r-': -20, 'r.': -60, 'rc': -20, 'rd':
            -20, 'rg': -15, 'ro': -20, 'rq': -20, 'rs': -15, 'rt': 20, 'rv': 10, 'ry': 10, 'r\xad': -20, 'r\xe7': -20,
            'r\xf2': -20, 'r\xf3': -20, 'r\xf4': -20, 'r\xf5': -20, 'r\xf6': -20, 'r\xf8': -20, 'r\xfd': 10, 'r\xff':
            10, 'sw': -15, 'v,': -80, 'v.': -80, 'va': -20, 'vo': -30, 'v\xe0': -20, 'v\xe1': -20, 'v\xe2': -20,
            'v\xe3': -20, 'v\xe4': -20, 'v\xe5': -20, 'v\xf2': -30, 'v\xf3': -30, 'v\xf4': -30, 'v\xf5': -30, 'v\xf6':
            -30, 'v\xf8': -30, 'w,': -40, 'w.': -40, 'wo': -20, 'w\xf2': -20, 'w\xf3': -20, 'w\xf4': -20, 'w\xf5':
            -20, 'w\xf6': -20, 'w\xf8': -20, 'xe': -10, 'x\xe8': -10, 'x\xe9': -10, 'x\xea': -10, 'x\xeb': -10, 'y,':
            -80, 'y.': -80, 'ya': -30, 'ye': -10, 'yo': -25, 'y\xe0': -30, 'y\xe1': -30, 'y\xe2': -30, 'y\xe3': -30,
            'y\xe4': -30, 'y\xe5': -30, 'y\xe8': -10, 'y\xe9': -10, 'y\xea': -10, 'y\xeb': -10, 'y\xf2': -25, 'y\xf3':
            -25, 'y\xf4': -25, 'y\xf5': -25, 'y\xf6': -25, 'y\xf8': -25, 'ze': 10, 'z\xe8': 10, 'z\xe9': 10, 'z\xea':
            10, 'z\xeb': 10, '\xa0T': -100, '\xa0V': -80, '\xa0W': -80, '\xa0Y': -120, '\xa0\xdd': -120, '\xc0C': -40,
            '\xc0G': -50, '\xc0O': -40, '\xc0Q': -40, '\xc0T': -90, '\xc0U': -50, '\xc0V': -80, '\xc0W': -60, '\xc0Y':
            -110, '\xc0u': -30, '\xc0v': -40, '\xc0w': -30, '\xc0y': -30, '\xc0\xc7': -40, '\xc0\xd2': -40,
            '\xc0\xd3': -40, '\xc0\xd4': -40, '\xc0\xd5': -40, '\xc0\xd6': -40, '\xc0\xd8': -40, '\xc0\xd9': -50,
            '\xc0\xda': -50, '\xc0\xdb': -50, '\xc0\xdc': -50, '\xc0\xdd': -110, '\xc0\xf9': -30, '\xc0\xfa': -30,
            '\xc0\xfb': -30, '\xc0\xfc': -30, '\xc0\xfd': -30, '\xc0\xff': -30, '\xc1C': -40, '\xc1G': -50, '\xc1O':
            -40, '\xc1Q': -40, '\xc1T': -90, '\xc1U': -50, '\xc1V': -80, '\xc1W': -60, '\xc1Y': -110, '\xc1u': -30,
            '\xc1v': -40, '\xc1w': -30, '\xc1y': -30, '\xc1\xc7': -40, '\xc1\xd2': -40, '\xc1\xd3': -40, '\xc1\xd4':
            -40, '\xc1\xd5': -40, '\xc1\xd6': -40, '\xc1\xd8': -40, '\xc1\xd9': -50, '\xc1\xda': -50, '\xc1\xdb': -50,
            '\xc1\xdc': -50, '\xc1\xdd': -110, '\xc1\xf9': -30, '\xc1\xfa': -30, '\xc1\xfb': -30, '\xc1\xfc': -30,
            '\xc1\xfd': -30, '\xc1\xff': -30, '\xc2C': -40, '\xc2G': -50, '\xc2O': -40, '\xc2Q': -40, '\xc2T': -90,
            '\xc2U': -50, '\xc2V': -80, '\xc2W': -60, '\xc2Y': -110, '\xc2u': -30, '\xc2v': -40, '\xc2w': -30,
            '\xc2y': -30, '\xc2\xc7': -40, '\xc2\xd2': -40, '\xc2\xd3': -40, '\xc2\xd4': -40, '\xc2\xd5': -40,
            '\xc2\xd6': -40, '\xc2\xd8': -40, '\xc2\xd9': -50, '\xc2\xda': -50, '\xc2\xdb': -50, '\xc2\xdc': -50,
            '\xc2\xdd': -110, '\xc2\xf9': -30, '\xc2\xfa': -30, '\xc2\xfb': -30, '\xc2\xfc': -30, '\xc2\xfd': -30,
            '\xc2\xff': -30, '\xc3C': -40, '\xc3G': -50, '\xc3O': -40, '\xc3Q': -40, '\xc3T': -90, '\xc3U': -50,
            '\xc3V': -80, '\xc3W': -60, '\xc3Y': -110, '\xc3u': -30, '\xc3v': -40, '\xc3w': -30, '\xc3y': -30,
            '\xc3\xc7': -40, '\xc3\xd2': -40, '\xc3\xd3': -40, '\xc3\xd4': -40, '\xc3\xd5': -40, '\xc3\xd6': -40,
            '\xc3\xd8': -40, '\xc3\xd9': -50, '\xc3\xda': -50, '\xc3\xdb': -50, '\xc3\xdc': -50, '\xc3\xdd': -110,
            '\xc3\xf9': -30, '\xc3\xfa': -30, '\xc3\xfb': -30, '\xc3\xfc': -30, '\xc3\xfd': -30, '\xc3\xff': -30,
            '\xc4C': -40, '\xc4G': -50, '\xc4O': -40, '\xc4Q': -40, '\xc4T': -90, '\xc4U': -50, '\xc4V': -80, '\xc4W':
            -60, '\xc4Y': -110, '\xc4u': -30, '\xc4v': -40, '\xc4w': -30, '\xc4y': -30, '\xc4\xc7': -40, '\xc4\xd2':
            -40, '\xc4\xd3': -40, '\xc4\xd4': -40, '\xc4\xd5': -40, '\xc4\xd6': -40, '\xc4\xd8': -40, '\xc4\xd9': -50,
            '\xc4\xda': -50, '\xc4\xdb': -50, '\xc4\xdc': -50, '\xc4\xdd': -110, '\xc4\xf9': -30, '\xc4\xfa': -30,
            '\xc4\xfb': -30, '\xc4\xfc': -30, '\xc4\xfd': -30, '\xc4\xff': -30, '\xc5C': -40, '\xc5G': -50, '\xc5O':
            -40, '\xc5Q': -40, '\xc5T': -90, '\xc5U': -50, '\xc5V': -80, '\xc5W': -60, '\xc5Y': -110, '\xc5u': -30,
            '\xc5v': -40, '\xc5w': -30, '\xc5y': -30, '\xc5\xc7': -40, '\xc5\xd2': -40, '\xc5\xd3': -40, '\xc5\xd4':
            -40, '\xc5\xd5': -40, '\xc5\xd6': -40, '\xc5\xd8': -40, '\xc5\xd9': -50, '\xc5\xda': -50, '\xc5\xdb': -50,
            '\xc5\xdc': -50, '\xc5\xdd': -110, '\xc5\xf9': -30, '\xc5\xfa': -30, '\xc5\xfb': -30, '\xc5\xfc': -30,
            '\xc5\xfd': -30, '\xc5\xff': -30, '\xd2,': -40, '\xd2.': -40, '\xd2A': -50, '\xd2T': -40, '\xd2V': -50,
            '\xd2W': -50, '\xd2X': -50, '\xd2Y': -70, '\xd2\xc0': -50, '\xd2\xc1': -50, '\xd2\xc2': -50, '\xd2\xc3':
            -50, '\xd2\xc4': -50, '\xd2\xc5': -50, '\xd2\xdd': -70, '\xd3,': -40, '\xd3.': -40, '\xd3A': -50, '\xd3T':
            -40, '\xd3V': -50, '\xd3W': -50, '\xd3X': -50, '\xd3Y': -70, '\xd3\xc0': -50, '\xd3\xc1': -50, '\xd3\xc2':
            -50, '\xd3\xc3': -50, '\xd3\xc4': -50, '\xd3\xc5': -50, '\xd3\xdd': -70, '\xd4,': -40, '\xd4.': -40,
            '\xd4A': -50, '\xd4T': -40, '\xd4V': -50, '\xd4W': -50, '\xd4X': -50, '\xd4Y': -70, '\xd4\xc0': -50,
            '\xd4\xc1': -50, '\xd4\xc2': -50, '\xd4\xc3': -50, '\xd4\xc4': -50, '\xd4\xc5': -50, '\xd4\xdd': -70,
            '\xd5,': -40, '\xd5.': -40, '\xd5A': -50, '\xd5T': -40, '\xd5V': -50, '\xd5W': -50, '\xd5X': -50, '\xd5Y':
            -70, '\xd5\xc0': -50, '\xd5\xc1': -50, '\xd5\xc2': -50, '\xd5\xc3': -50, '\xd5\xc4': -50, '\xd5\xc5': -50,
            '\xd5\xdd': -70, '\xd6,': -40, '\xd6.': -40, '\xd6A': -50, '\xd6T': -40, '\xd6V': -50, '\xd6W': -50,
            '\xd6X': -50, '\xd6Y': -70, '\xd6\xc0': -50, '\xd6\xc1': -50, '\xd6\xc2': -50, '\xd6\xc3': -50,
            '\xd6\xc4': -50, '\xd6\xc5': -50, '\xd6\xdd': -70, '\xd8,': -40, '\xd8.': -40, '\xd8A': -50, '\xd8T': -40,
            '\xd8V': -50, '\xd8W': -50, '\xd8X': -50, '\xd8Y': -70, '\xd8\xc0': -50, '\xd8\xc1': -50, '\xd8\xc2': -50,
            '\xd8\xc3': -50, '\xd8\xc4': -50, '\xd8\xc5': -50, '\xd8\xdd': -70, '\xd9,': -30, '\xd9.': -30, '\xd9A':
            -50, '\xd9\xc0': -50, '\xd9\xc1': -50, '\xd9\xc2': -50, '\xd9\xc3': -50, '\xd9\xc4': -50, '\xd9\xc5': -50,
            '\xda,': -30, '\xda.': -30, '\xdaA': -50, '\xda\xc0': -50, '\xda\xc1': -50, '\xda\xc2': -50, '\xda\xc3':
            -50, '\xda\xc4': -50, '\xda\xc5': -50, '\xdb,': -30, '\xdb.': -30, '\xdbA': -50, '\xdb\xc0': -50,
            '\xdb\xc1': -50, '\xdb\xc2': -50, '\xdb\xc3': -50, '\xdb\xc4': -50, '\xdb\xc5': -50, '\xdc,': -30,
            '\xdc.': -30, '\xdcA': -50, '\xdc\xc0': -50, '\xdc\xc1': -50, '\xdc\xc2': -50, '\xdc\xc3': -50,
            '\xdc\xc4': -50, '\xdc\xc5': -50, '\xdd,': -100, '\xdd.': -100, '\xdd:': -50, '\xdd;': -50, '\xddA': -110,
            '\xddO': -70, '\xdda': -90, '\xdde': -80, '\xddo': -100, '\xddu': -100, '\xdd\xc0': -110, '\xdd\xc1':
            -110, '\xdd\xc2': -110, '\xdd\xc3': -110, '\xdd\xc4': -110, '\xdd\xc5': -110, '\xdd\xd2': -70, '\xdd\xd3':
            -70, '\xdd\xd4': -70, '\xdd\xd5': -70, '\xdd\xd6': -70, '\xdd\xd8': -70, '\xdd\xe0': -90, '\xdd\xe1': -90,
            '\xdd\xe2': -90, '\xdd\xe3': -90, '\xdd\xe4': -90, '\xdd\xe5': -90, '\xdd\xe8': -80, '\xdd\xe9': -80,
            '\xdd\xea': -80, '\xdd\xeb': -80, '\xdd\xf2': -100, '\xdd\xf3': -100, '\xdd\xf4': -100, '\xdd\xf5': -100,
            '\xdd\xf6': -100, '\xdd\xf8': -100, '\xdd\xf9': -100, '\xdd\xfa': -100, '\xdd\xfb': -100, '\xdd\xfc':
            -100, '\xe0g': -10, '\xe0v': -15, '\xe0w': -15, '\xe0y': -20, '\xe0\xfd': -20, '\xe0\xff': -20, '\xe1g':
            -10, '\xe1v': -15, '\xe1w': -15, '\xe1y': -20, '\xe1\xfd': -20, '\xe1\xff': -20, '\xe2g': -10, '\xe2v':
            -15, '\xe2w': -15, '\xe2y': -20, '\xe2\xfd': -20, '\xe2\xff': -20, '\xe3g': -10, '\xe3v': -15, '\xe3w':
            -15, '\xe3y': -20, '\xe3\xfd': -20, '\xe3\xff': -20, '\xe4g': -10, '\xe4v': -15, '\xe4w': -15, '\xe4y':
            -20, '\xe4\xfd': -20, '\xe4\xff': -20, '\xe5g': -10, '\xe5v': -15, '\xe5w': -15, '\xe5y': -20, '\xe5\xfd':
            -20, '\xe5\xff': -20, '\xe7h': -10, '\xe7k': -20, '\xe7l': -20, '\xe7y': -10, '\xe7\xfd': -10, '\xe7\xff':
            -10, '\xe8,': 10, '\xe8.': 20, '\xe8v': -15, '\xe8w': -15, '\xe8x': -15, '\xe8y': -15, '\xe8\xfd': -15,
            '\xe8\xff': -15, '\xe9,': 10, '\xe9.': 20, '\xe9v': -15, '\xe9w': -15, '\xe9x': -15, '\xe9y': -15,
            '\xe9\xfd': -15, '\xe9\xff': -15, '\xea,': 10, '\xea.': 20, '\xeav': -15, '\xeaw': -15, '\xeax': -15,
            '\xeay': -15, '\xea\xfd': -15, '\xea\xff': -15, '\xeb,': 10, '\xeb.': 20, '\xebv': -15, '\xebw': -15,
            '\xebx': -15, '\xeby': -15, '\xeb\xfd': -15, '\xeb\xff': -15, '\xf1u': -10, '\xf1v': -40, '\xf1y': -20,
            '\xf1\xf9': -10, '\xf1\xfa': -10, '\xf1\xfb': -10, '\xf1\xfc': -10, '\xf1\xfd': -20, '\xf1\xff': -20,
            '\xf2v': -20, '\xf2w': -15, '\xf2x': -30, '\xf2y': -20, '\xf2\xfd': -20, '\xf2\xff': -20, '\xf3v': -20,
            '\xf3w': -15, '\xf3x': -30, '\xf3y': -20, '\xf3\xfd': -20, '\xf3\xff': -20, '\xf4v': -20, '\xf4w': -15,
            '\xf4x': -30, '\xf4y': -20, '\xf4\xfd': -20, '\xf4\xff': -20, '\xf5v': -20, '\xf5w': -15, '\xf5x': -30,
            '\xf5y': -20, '\xf5\xfd': -20, '\xf5\xff': -20, '\xf6v': -20, '\xf6w': -15, '\xf6x': -30, '\xf6y': -20,
            '\xf6\xfd': -20, '\xf6\xff': -20, '\xf8v': -20, '\xf8w': -15, '\xf8x': -30, '\xf8y': -20, '\xf8\xfd': -20,
            '\xf8\xff': -20, '\xfd,': -80, '\xfd.': -80, '\xfda': -30, '\xfde': -10, '\xfdo': -25, '\xfd\xe0': -30,
            '\xfd\xe1': -30, '\xfd\xe2': -30, '\xfd\xe3': -30, '\xfd\xe4': -30, '\xfd\xe5': -30, '\xfd\xe8': -10,
            '\xfd\xe9': -10, '\xfd\xea': -10, '\xfd\xeb': -10, '\xfd\xf2': -25, '\xfd\xf3': -25, '\xfd\xf4': -25,
            '\xfd\xf5': -25, '\xfd\xf6': -25, '\xfd\xf8': -25, '\xff,': -80, '\xff.': -80, '\xffa': -30, '\xffe': -10,
            '\xffo': -25, '\xff\xe0': -30, '\xff\xe1': -30, '\xff\xe2': -30, '\xff\xe3': -30, '\xff\xe4': -30,
            '\xff\xe5': -30, '\xff\xe8': -10, '\xff\xe9': -10, '\xff\xea': -10, '\xff\xeb': -10, '\xff\xf2': -25,
            '\xff\xf3': -25, '\xff\xf4': -25, '\xff\xf5': -25, '\xff\xf6': -25, '\xff\xf8': -25
        },
    },
}
