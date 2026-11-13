"""The form's rules, evaluated in Python while building (the same rules also run in Acrobat, see js/rules.js).

A question's rules come from lc.py:
  required=True            always mandatory
  requiredIf=[rule, ...]   mandatory when any of these rules holds
  activeIf=[rule, ...]     can only be answered when any of these rules holds (otherwise greyed out and locked)
A rule is {"field": "drafts", "values": ["true"]} = "when Drafts is ticked". With "not": true it means
"when that field is answered with anything else".
"""
import datetime


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
