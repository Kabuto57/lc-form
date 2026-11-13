"""STEP 1 OF 3: LAY OUT THE PAGES.

Walks through the form (lc.py) section by section and decides where everything goes. It produces:
  - each page's drawing (text, lines, boxes) as PDF drawing commands, in Page.ops
  - a description of every fillable field (text box, tick box, drop-down, button ...) and where its boxes
    ("widgets") sit, in Layout.fields. Step 3 (writer.py) turns these into real PDF fields.

How the page is organised:
  - Each section is a box with a grey heading band. Its questions sit on a grid of 12 columns; each question
    takes as many columns as it needs, and questions fill a row left to right.
  - A tick box starts a new row, and the questions it switches on are indented under it.
  - Two short sections that follow each other can sit side by side (e.g. 4 and 5).
  - Labels sit beside their boxes ("Name: [    ]") when the whole row has room, otherwise above them.

The cursor `self.top` is the y position (from the bottom of the page) where the next thing is drawn; it moves
down the page as content is added.
"""
import datetime
import json

from .rules import active_rules, date_label, date_options, has_options, is_required
from .style import (ACCENT, BAD_CHARS, BAND, BANK_SHADE, BESIDE_GAP, BOTTOM, BOX, COLUMN_GAP, COLUMNS, FORMATS, GREY, INDENT,
                    INK, LABEL, MARGIN, PAD, PAGE_HEIGHT, PAGE_WIDTH, RED, RULE, SECTION_GAP, SIGN_OFF, TEXT, TINT, WHITE)
from .text import fmt, pdf_string, rgb, safe, width, wrap

W, H, M = PAGE_WIDTH, PAGE_HEIGHT, MARGIN   # short names for the page size and margin, used throughout


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
    # A field is described here as a plain dict; writer.py makes the PDF objects from it.
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
            # JavaScript shows it (lcDates in js/rules.js). AFDate_* are Acrobat's own date functions.
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
        """A last page with a frame for the QR code of the answers (js/qr.js draws the code into it in Acrobat)."""
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
