"""THE QUESTION HELPERS: the words a form file uses to describe its questions.

Form files (forms/*.py) import these:  from engine.questions import text, radio, date, ...
You only need to read the comment block below to write or change a form.
"""
# A form file (forms/lc.py is one) imports these and writes one line per question, for example
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
#     format="amount"                     amount / number / phone / account (see FORMATS in engine/look.py)
#     beside=69.3                         label beside a box this wide, even when the label is long
#     half=True / half=False              kept in the PDF's copy of the form, but has no effect on the layout:
#                                         box widths are worked out automatically from the label and max
# Sections:  section("Title", fields=[...]), plus note="..." (text under the heading), bankOnly=True (shaded,
# "For Bank Use Only"), signoff=True (signature, date and company stamp lines).
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


# ---- check_form: explains mistakes in a form file before anything is built -------------------------------------
KINDS = ("text", "long", "date", "radio", "checks", "check", "select")
QUESTION_OPTIONS = {"id", "label", "kind", "options", "required", "requiredIf", "activeIf", "max", "format", "half", "beside"}
SECTION_OPTIONS = {"title", "fields", "note", "bankOnly", "signoff"}


def check_form(form, defaults, formats):
    """Stops with a plain-English message at the first mistake in the form file (a typo in an option name, a rule
    that points at a question that doesn't exist, two questions with the same id ...). Returns nothing if all is well."""
    def stop(message):
        raise SystemExit("PROBLEM IN THE FORM FILE: " + message)

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
    for key, value in (defaults or {}).items():
        if key not in questions:
            stop(f'DEFAULTS gives an answer for "{key}", but no question has that id.')
        choices = questions[key][0].get("options")
        if choices and isinstance(value, str) and value not in choices:
            stop(f'DEFAULTS: "{value}" is not one of the options of "{key}" ({" / ".join(choices)}).')
