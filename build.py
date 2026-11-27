#!/usr/bin/env python3
"""BUILD A FORM AS A FILLABLE PDF.      python build.py lc_form.py      ->  out/LC-Application.pdf

THE FILES THAT BUILD A FORM (the engine files together in one folder, the form files in its forms/ folder)
    forms/lc_form.py  WHAT the form asks: one line per question. The only file you change for the LC form.
                    To make a new form, copy forms/example_form.py (small) or forms/lc_form.py, and change the
                    questions. "python build.py lc_form.py" finds it in forms/.
    build.py        THIS FILE. Run it. Its first section lists every kind of question and every option.
    layout.py       Step 1: where everything goes on the page (and the colours, sizes and answer formats).
                    No page limit: a longer form simply gets more pages.
    pdf_writer.py   Steps 2 and 3: adds the checks and buttons, writes the PDF, then checks the PDF.
    acrobat_js.py   The JavaScript Acrobat runs inside the PDF (red boxes, Check form, QR codes: as many as the answers
                    need, up to 16, the third onwards on extra QR pages that exist only while needed). To stay quick it
                    re-checks only the questions that read the box you just left (an index pdf_writer.py builds from the
                    form file), once per change, and skips writing boxes whose look is unchanged. It is written to be read:
                    plain names, one statement per line, and a comment on every function and every rule.
You only ever edit form files. The other four are the same for every form.
    proof_multiqr.py  Not part of the build: after changing the QR code scripts, run it to prove 1 to 16 codes decode (README).
    forms/lc_pipe_form.py is the LC form again with the old smart form's pipe-delimited text in the QR code (FORM["qrFormat"] = "pipe"
                    and FORM["pipe"], the position table; IN_MENU = False keeps it out of build_all.py). check_pipe.py tests it.

WHAT A BUILD DOES
    1. Reads the form file and checks it for mistakes (a misspelt option, a rule naming a question that doesn't
       exist ...). If it finds one, it stops and says which question and what to fix.
    2. Builds the PDF, then opens it and checks every question's fields, rules, scripts and buttons.
    3. Saves out/<PDF_NAME>, plus out/index.html for viewing it (python -m http.server 8090 -d out).
    It prints PASS when everything is right. Nothing is saved if anything is wrong.

Test the PDF in Adobe Acrobat or Reader: a browser's PDF viewer doesn't run the form's checks.
"""
import importlib.util
import os
import re
import sys


# ====================================================================================================================
# 1. HOW A FORM FILE DESCRIBES ITS QUESTIONS (the words form files use)
# ====================================================================================================================
# A form file (lc_form.py is one) imports these and writes one line per question, for example
#     text("term_days", "Term: days", requiredIf=when("drafts_at", "Term"), format="number"),
# = a text box named term_days, labelled "Term: days", mandatory (and unlocked) only when Drafts at is Term,
# digits only. The layout, numbering, scripts and QR code all follow from these lines.
#
# Question kinds:
#     text(id, label)                     one-line text box
#     long(id, label)                     paragraph box
#     date(id, label)                     date: a calendar box in Acrobat, a drop-down of dates elsewhere
#     radio(id, label, [options])         pick one
#     checks(id, label, options=[...])    tick any
#     check(id, label)                    one tick box
#     select(id, label, options=[...])    drop-down list
# Options for any question:
#     required=True                       always mandatory (red *)
#     requiredIf=ticked("x")              mandatory, and unlocked, only when tick box x is ticked
#     requiredIf=when("x", "A", "B")      mandatory only when x is A or B
#     requiredIf=answered("x")            mandatory once x has any answer (never locked)
#     activeIf=ticked("x")                only applies (unlocked) when x is ticked, but optional
#     max=35                              at most 35 characters
#     format="amount"                     amount / number / phone / account (see FORMATS in layout.py)
#     beside=69.3                         label beside a box this wide, even when the label is long
#     cols=12                             how much of the row it takes, out of 12: cols=12 whole row, cols=6 half,
#                                         cols=4 a third. Leave it out to let the build choose (usually best)
#     words=["amount", "currency"]        filled in by the form: the amount in words ("USD One Hundred only"), read-only
#     height=80                           paragraph boxes (long) only: the whole box this many points tall (default 50)
#     half=True / half=False              kept in the PDF's copy of the form, but has no effect on the layout:
#                                         box widths are worked out automatically from the label and max (use cols)
# Sections:  section("Title", fields=[...]), plus
#     note="..."                          text under the heading
#     bankOnly=True                       shaded, "For Bank Use Only"
#     signoff=True                        signature, date and company stamp lines (always the whole width)
#     width="full"                        always the whole width of the page
#     width="half"                        half the page; two half sections in a row sit side by side
#                                         (leave width out: the build puts two short, similar sections side by side)
#     new_page=True                       starts on a new page
#     min_height=200                      the section's box is at least this many points tall (blank space at the bottom
#                                         for writing on paper); leave it out to fit the questions. If the questions need
#                                         more room they win. A section with no width setting that is 300 points
#                                         tall or more no longer pairs side by side: it goes full width.
#                                         Up to a page's height (768.89 points)
#     buttons=["check-form", "print-form"]  a row of buttons at the bottom right of the section, each one of:
#                                         "check-form" (Check form), "reset-form" (Reset form),
#                                         "generate-qr" (Generate QR Code), "print-form" (Print Form).
#                                         They do the same as the buttons every form already has (top right of every
#                                         page, and on the QR code page), and show on screen only, not on paper.
# Form settings besides the sections (FORM = {...}): "qrFormat": "pipe" with "pipe": [record, ...] puts the old smart form's pipe-delimited
# records in the QR code instead of the JSON (see forms/lc_pipe_form.py). A form file may also say IN_MENU = False (build_all.py refuses to list it).
# Leave width, new_page and cols out and layout.py decides (usually best). Colours and text sizes are the same on
# every form (red = mandatory): they are set in layout.py, section 1.
#
# Mistakes in a form file (a misspelt option, a rule pointing at a question that doesn't exist, two questions with
# the same id ...) are caught by check_form, at the end of this file, before anything is built.

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


# Checks across answers, listed in FORM["checks"] (each is skipped while its answers are blank):
#     not_before("expiry_date", "shipment_date", "Expiry date cannot be earlier than the latest shipment date")
#     after("expiry_date", "effective_date", "...")          strictly later
#     in_range("rate", 0, 100, "Please enter a value from 0 to 100")
#     account_length("debit_acc", "debit_currency", {"SGD": [10], "*": [13]}, "Invalid account no.")   [] = not checked
def not_before(later, earlier, message):
    return {"t": "order", "a": later, "b": earlier, "s": 0, "m": message}


def after(later, earlier, message):
    return {"t": "order", "a": later, "b": earlier, "s": 1, "m": message}


def in_range(field, low, high, message):
    return {"t": "range", "a": field, "lo": low, "hi": high, "m": message}


def account_length(field, currency, lengths, message):
    return {"t": "lengths", "a": field, "b": currency, "by": lengths, "m": message}


# ---- the pipe-format QR text: FORM["qrFormat"] = "pipe" and FORM["pipe"] = [record, ...] (each record a list of position entries;
# the entries are described in acrobat_js.py, PIPE_JS). Every question an entry names must exist, and the answers it maps
# to codes must be options of that question.
def pipe_ids(entry):
    """Every question id an entry of the pipe table names."""
    used = ([entry["id"]] if "id" in entry else []) + entry.get("lines", []) + entry.get("join", [])
    if "if" in entry:
        used.append(entry["if"][0])
    if "tpl" in entry:
        used.append(entry["tpl"]["when"])
        for part in entry["tpl"]["parts"]:
            texts = [part] if isinstance(part, str) else list(part[2].values()) if part[0] == "map" else [part[2], part[3]] if part[0] == "if" else []
            used += [i for t in texts for i in re.findall(r"\{(\w+)\}", t)]
            if not isinstance(part, str):
                used.append(part[1])
    if "qty" in entry:
        q = entry["qty"]
        used += [q["on"], q["o"], q["c"]] + ([q["tail"][0]] + re.findall(r"\{(\w+)\}", q["tail"][1]) if q.get("tail") else [])
    return used


def check_pipe(form, questions, stop):
    if form.get("qrFormat") not in (None, "pipe"):
        stop('FORM["qrFormat"] must be "pipe" (or left out for the usual JSON QR code).')
    if form.get("qrFormat") != "pipe":
        if "pipe" in form:
            stop('FORM["pipe"] is only used with FORM["qrFormat"] = "pipe".')
        return
    if not form.get("pipe") or not all(isinstance(r, list) and r for r in form["pipe"]):
        stop('FORM["pipe"] must be a list of records, each a list of position entries.')
    for record in form["pipe"]:
        for entry in record:
            where = f'FORM["pipe"] position {entry.get("p", "?")}'
            for key in entry:
                if key not in ("p", "c", "id", "lines", "join", "tpl", "qty", "if", "d", "chop", "max", "as", "codes"):
                    stop(f'{where} has an unknown setting "{key}".')
            for qid in pipe_ids(entry):
                if qid not in questions:
                    stop(f'{where} names "{qid}", but no question has that id.')
            if entry.get("codes") and "id" not in entry:
                stop(f'{where}: "codes" needs an "id" (the question whose answers become codes).')
            question = questions[entry["id"]][0] if "id" in entry else None
            options = (["true"] if question["kind"] == "check" else question.get("options") or []) if question else []
            for answer in entry.get("codes", {}):
                if answer not in options:
                    stop(f'{where}: "{answer}" is not one of the answers of "{entry["id"]}" ' +
                         (f'({" / ".join(options)}).' if options else "(a question without options has none to map to codes; remove \"codes\")."))


# ---- check_form: explains mistakes in a form file before anything is built -------------------------------------
KINDS = ("text", "long", "date", "radio", "checks", "check", "select")
QUESTION_OPTIONS = {"id", "label", "kind", "options", "required", "requiredIf", "activeIf", "max", "format", "half", "beside", "cols", "words", "height"}
SECTION_OPTIONS = {"title", "fields", "note", "bankOnly", "signoff", "width", "new_page", "buttons", "min_height"}
BUTTON_NAMES = ("check-form", "reset-form", "generate-qr", "print-form")


def check_form(form, defaults, formats):
    """Stops with a plain-English message at the first mistake in the form file (a typo in an option name, a rule
    that points at a question that doesn't exist, two questions with the same id ...). Returns nothing if all is well."""
    def stop(message):
        raise SystemExit("PROBLEM IN THE FORM FILE: " + message)

    for key in form:
        if key not in ("title", "note", "issuer", "formCode", "sections", "checks", "qrFormat", "pipe"):
            stop(f'FORM has an unknown setting "{key}".')
    for key in ("title", "sections"):
        if key not in form:
            stop(f'FORM has no "{key}".')
    questions, ids = {}, []
    for si, section in enumerate(form["sections"], 1):
        where = f'section {si} ("{section.get("title", "?")}")'
        for key in section:
            if key not in SECTION_OPTIONS:
                stop(f'{where} has an unknown setting "{key}". Allowed: {", ".join(sorted(SECTION_OPTIONS))}.')
        if not section.get("fields"):
            stop(f"{where} has no questions (fields=[...]).")
        if section.get("width") not in (None, "full", "half"):
            stop(f'{where}: width must be "full" or "half" (or leave it out to let the build choose).')
        buttons = section.get("buttons")
        if buttons is not None and (not isinstance(buttons, list) or any(b not in BUTTON_NAMES for b in buttons) or len(set(buttons)) < len(buttons)):
            stop(f'{where}: buttons must be a list of different ones from {", ".join(BUTTON_NAMES)}, like buttons=["check-form"].')
        mh = section.get("min_height")
        if mh is not None and (isinstance(mh, bool) or not isinstance(mh, (int, float)) or not 0 < mh <= PAGE_ROOM):
            stop(f"{where}: min_height must be a number of points above 0 and no taller than a page ({PAGE_ROOM:.2f}), like min_height=200.")
        if section.get("width") == "half" and section.get("signoff"):
            stop(f'{where}: a signoff section needs the whole width (its signature, date and stamp lines). Remove width="half".')
        for qi, q in enumerate(section["fields"], 1):
            name = f'question {si}.{qi} ("{q.get("id", "?")}")'
            for key in q:
                if key not in QUESTION_OPTIONS:
                    stop(f'{name} has an unknown option "{key}" (a typo?). Allowed: {", ".join(sorted(QUESTION_OPTIONS))}.')
            if not str(q.get("id", "")).isidentifier() or q["id"].startswith("__"):
                stop(f'{name}: the id must be letters, digits and _ only, like "applicant_name".')
            if q["id"] in questions:
                stop(f'{name}: the id "{q["id"]}" is already used by another question. Every id must be different.')
            if q["kind"] not in KINDS:
                stop(f'{name}: unknown kind "{q["kind"]}". Allowed: {", ".join(KINDS)}.')
            if q["kind"] in ("radio", "checks", "select") and not q.get("options"):
                stop(f"{name}: a {q['kind']} question needs options=[...].")
            if q.get("format") and q["format"] not in formats:
                stop(f'{name}: unknown format "{q["format"]}". Allowed: {", ".join(formats)}.')
            if q.get("max") is not None and (not isinstance(q["max"], int) or q["max"] < 1):
                stop(f"{name}: max must be a whole number of characters, like max=35.")
            if q.get("height") is not None and (q["kind"] != "long" or not isinstance(q["height"], (int, float)) or not 20 <= q["height"] <= 600):
                stop(f"{name}: height is for paragraph boxes (long) only, in points from 20 to 600, like height=80.")
            if q.get("cols") is not None and q["cols"] not in range(1, 13):
                stop(f"{name}: cols must be a whole number from 1 to 12, like cols=12 (whole row) or cols=6 (half).")
            questions[q["id"]] = (q, name)
            ids.append(q["id"])
    for q, name in questions.values():
        for option in ("requiredIf", "activeIf"):
            for rule in q.get(option) or []:
                other = questions.get(rule["field"])
                if not other:
                    stop(f'{name}: {option} refers to "{rule["field"]}", but no question has that id.')
                choices = other[0].get("options")
                if choices and not rule.get("not"):
                    for value in rule["values"]:
                        if value not in choices:
                            stop(f'{name}: {option} waits for "{rule["field"]}" to be "{value}", but that is not one '
                                 f'of its options ({" / ".join(choices)}).')
    for q, name in questions.values():
        for other in q.get("words") or []:
            if other not in questions:
                stop(f'{name}: words refers to "{other}", but no question has that id.')
    for c in form.get("checks") or []:
        for key in ("a", "b"):
            if c.get(key) and c[key] not in questions:
                stop(f'FORM["checks"]: a check refers to "{c[key]}", but no question has that id.')
    check_pipe(form, questions, stop)
    for key, value in (defaults or {}).items():
        if key not in questions:
            stop(f'DEFAULTS gives an answer for "{key}", but no question has that id.')
        choices = questions[key][0].get("options")
        if choices and isinstance(value, str) and value not in choices:
            stop(f'DEFAULTS: "{value}" is not one of the options of "{key}" ({" / ".join(choices)}).')


# ====================================================================================================================
# 2. RUN: LOAD THE FORM FILE, CHECK IT, BUILD, CHECK THE PDF, SAVE
# ====================================================================================================================
sys.dont_write_bytecode = True   # always read the files fresh (no cached copy of an older version)

try:
    from layout import FORMATS, PAGE_ROOM              # noqa: E402
    from pdf_writer import build, self_check   # noqa: E402
except (SyntaxError, ImportError) as e:
    if getattr(e, "name", None) in ("pikepdf", "lxml", "PIL", "packaging"):
        raise SystemExit(f"The library {e.name} is not installed. Run:  python -m pip install -r requirements.txt")
    raise SystemExit(f"PROBLEM: {getattr(e, 'filename', None) or e.name or 'one of the 5 files'} is missing, incomplete or "
                     f"damaged ({e.__class__.__name__}: {e}). Copy it again from GitHub ('Download raw file') into the "
                     "same folder as build.py, and build again.")


HERE = os.path.dirname(os.path.abspath(__file__))


FORMS = os.path.join(HERE, "forms")


def load_form(path):
    """The form file as a module, with the optional names filled in. "lc_form.py" means forms/lc_form.py."""
    if not os.path.exists(path) and os.path.exists(os.path.join(FORMS, path)):
        path = os.path.join(FORMS, path)
    if not os.path.exists(path):
        raise SystemExit(f"No form file called {path}. Form files sit in the forms folder, e.g.  python build.py lc_form.py")
    if FORMS not in sys.path:
        sys.path.insert(0, FORMS)   # form files import each other ("from lc_form import CURRENCIES")
    loader = importlib.util.spec_from_file_location("form_file", path)
    spec = importlib.util.module_from_spec(loader)
    try:
        loader.loader.exec_module(spec)
    except SyntaxError as e:
        raise SystemExit(f"PROBLEM IN THE FORM FILE: {path}, line {e.lineno}: Python can't read it ({e.msg}). "
                         "Usually a missing comma, quote or bracket on that line or the line before.")
    if not hasattr(spec, "FORM"):
        raise SystemExit(f"{path} has no FORM = {{...}}. Copy example_form.py to see what a form file needs.")
    spec.DEFAULTS = getattr(spec, "DEFAULTS", {})
    spec.PDF_NAME = getattr(spec, "PDF_NAME", re.sub(r"\W+", "-", spec.FORM["title"]).strip("-") + ".pdf")
    spec.IN_MENU = getattr(spec, "IN_MENU", True)   # False: build_all.py's menu must not list this form (e.g. lc_pipe_form.py)
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
    check_form(spec.FORM, spec.DEFAULTS, FORMATS)    # stops with a plain-English message if the form file has a mistake
    pdf_bytes = build(spec.FORM, spec.DEFAULTS)
    result = self_check(pdf_bytes, spec)             # stops with the reason if the PDF isn't right
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, spec.PDF_NAME), "wb") as f:
        f.write(pdf_bytes)
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html(spec.FORM["title"], spec.PDF_NAME))
    print(f"Wrote out/{spec.PDF_NAME}")
    print(result)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "lc_form.py")
