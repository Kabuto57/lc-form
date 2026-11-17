"""RE-CHECKING SCANNED ANSWERS: the Bank's side of the QR code.

read_qr.py reads the QR code(s) and passes the JSON here. Everything in a QR code came from outside the Bank, so it
is checked again against the form file, not trusted because the form said "complete": true:
    - every answer belongs to a real question, and has the right kind of value (text, tick, list of options)
    - picked options are real options; lengths are within max; formats (amount, number ...) and dates are right
    - only the characters the form allows are used
    - every question that is mandatory (given the other answers) is answered, and nothing is answered that is
      locked (doesn't apply)
    - the checks across answers that the form makes in Acrobat (expiry after shipment, and so on)
"""
import datetime
import re

from .look import BAD_CHARS, FORMATS
from .rules import active_rules, holds, is_required

DATE = re.compile(r"^(\d\d)/(\d\d)/(\d{4})$")


def to_date(text):
    """A DD/MM/YYYY answer as a date, or None if it isn't a real date."""
    m = DATE.match(text or "")
    try:
        return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    except ValueError:
        return None


def check_answers(form, payload):
    """Returns (problems, warnings): lists of plain-English sentences. No problems = the answers can be accepted."""
    problems, warnings = [], []
    data = payload.get("data")
    if not isinstance(data, dict):
        return ["the QR code has no answers (no \"data\")"], warnings
    questions = {q["id"]: q for s in form["sections"] for q in s["fields"]}
    numbers = {q["id"]: f"{si}.{qi}" for si, s in enumerate(form["sections"], 1) for qi, q in enumerate(s["fields"], 1)}

    def name(qid):
        return f'{numbers[qid]} {questions[qid]["label"]}'

    for qid in data:
        if qid not in questions:
            problems.append(f'unknown answer "{qid}" (no such question in this form)')

    for qid, q in questions.items():
        answer, kind = data.get(qid), q["kind"]
        if answer is None:
            if is_required(q, data):
                problems.append(f"{name(qid)}: mandatory, but not answered")
            continue
        rules = active_rules(q)
        if rules and not any(holds(data, r) for r in rules):
            problems.append(f"{name(qid)}: answered, but the question doesn't apply to these answers (it is locked)")
        if kind == "check":
            if answer is not True:
                problems.append(f"{name(qid)}: should be a tick (true)")
        elif kind == "checks":
            if not isinstance(answer, list) or any(a not in q["options"] for a in answer):
                problems.append(f"{name(qid)}: not a list of its options")
        elif not isinstance(answer, str):
            problems.append(f"{name(qid)}: should be text")
        elif kind in ("radio", "select"):
            if answer not in q["options"]:
                problems.append(f'{name(qid)}: "{answer}" is not one of its options')
        else:
            if q.get("max") and len(answer) > q["max"]:
                problems.append(f"{name(qid)}: {len(answer)} characters, more than its {q['max']}")
            if kind == "date":
                if not to_date(answer):
                    problems.append(f'{name(qid)}: "{answer}" is not a real DD/MM/YYYY date')
            elif q.get("format"):
                if not re.search(FORMATS[q["format"]][1], answer):
                    problems.append(f"{name(qid)}: {FORMATS[q['format']][2]}")
            elif re.search(BAD_CHARS, answer):
                problems.append(f"{name(qid)}: has characters the form doesn't allow")

    problems += checks_across(data, payload.get("saved", ""), questions, name)
    if payload.get("truncated"):
        warnings.append("shortened to fit the QR codes (the full text is only in the PDF): "
                        + ", ".join(name(k) for k in payload["truncated"] if k in questions))
    if payload.get("complete") is not True:
        warnings.append('the form itself said it was not complete ("complete": false)')
    return problems, warnings


def checks_across(data, saved, questions, name):
    """The same checks across answers as the form makes in Acrobat (engine/js/document.js, across()). Each is skipped
    when the form doesn't have those questions. "In the future" is measured from when the QR code was made."""
    out = []
    a, s, e = (to_date(data.get(k)) for k in ("application_date", "latest_shipment_date", "expiry_date"))
    made = to_date(f"{saved[8:10]}/{saved[5:7]}/{saved[0:4]}") if len(saved) >= 10 else None
    if s and e and e < s:
        out.append(f"{name('expiry_date')}: is before the latest shipment date")
    elif a and e and e < a:
        out.append(f"{name('expiry_date')}: is before the application date")
    if a and s and s < a:
        out.append(f"{name('latest_shipment_date')}: is before the application date")
    if a and made and a > made:
        out.append(f"{name('application_date')}: is after the day the QR code was made")
    amount = data.get("amount")
    if isinstance(amount, str) and re.fullmatch(r"[\d,]+(\.\d+)?", amount) and not float(amount.replace(",", "")) > 0:
        out.append(f"{name('amount')}: must be more than zero")
    if data.get("insurance_arrangement") and data.get("price_basis") in ("CIF", "CIP") and "insurance_arrangement" in questions:
        out.append(f"{name('insurance_arrangement')}: is only for FOB/CFR/FCA/CPT, but price basis is {data['price_basis']}")
    return out
