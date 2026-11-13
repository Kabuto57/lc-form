"""STEP 2 OF 3: ADD THE SCRIPTS, BUTTONS AND QR CODE ROWS.

Everything interactive in the PDF is Acrobat JavaScript, kept as plain files in js/. This step:
  1. builds the "rules table" (which questions are mandatory, when, and their formats) from lc.py, and fills it
     into js/rules.js; adds js/payload.js (the QR code's text) and js/qr.js (the QR encoder). Together they are
     the one document-level script stored in the PDF, named "lcRules".
  2. says when the rules run: when a tick box or option is clicked, and when the person leaves a box
  3. adds the hidden helper fields, the 177 QR code rows, and the buttons (Check form, Reset form on every page;
     Generate QR Code and Print Form on the QR page)
It only adds field descriptions to the layout; writer.py makes the PDF objects.
"""
import json
import re

from .rules import active_rules
from .style import ACCENT, FORMATS, INK, MARGIN, PAGE_HEIGHT, PAGE_WIDTH, WHITE
from .text import fmt, js_json, read_file, safe

RUN_RULES = "lcRules(this);"   # the call every event uses


def script(name, **values):
    """A file from js/, with its __PLACEHOLDERS__ filled in."""
    text = read_file("js/" + name)
    for key, value in values.items():
        text = text.replace(f"__{key}__", value)
    return text


def rules_table(layout):
    """What js/rules.js needs to know about each question, in form order (so Check form lists problems top to
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
    """The one document-level script: js/rules.js + js/payload.js + js/qr.js, filled in for this form."""
    form, questions = layout.form, layout.questions
    rules = script("rules.js", MODEL=js_json(table), DATES=js_json([q["id"] for q in questions if q["kind"] == "date"]))
    tick_any = ", ".join(f"{json.dumps(q['id'])}: {js_json(q.get('options') or [])}" for q in questions if q["kind"] == "checks")
    code = re.search(r"[A-Z]+-\d+", form.get("formCode") or "")     # "LC-01"
    version = re.search(r"v([\d.]+)", form.get("formCode") or "")   # "1.0"
    payload = script("payload.js", GROUPS=tick_any, LONG=js_json([q["id"] for q in questions if q["kind"] == "long"]),
                     FORM=json.dumps(code.group(0) if code else safe(form["title"]), ensure_ascii=False),
                     VERSION=json.dumps(version.group(1) if version else "1"))
    return f"{rules}\n{payload}\n{script('qr.js')}"


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

    # The QR code: a hidden field "__qr" holds the answers as JSON; js/qr.js draws the code into 177 read-only
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
    buttons = [("__check_form", "Check form", script("check-form.js"), 64), ("__reset_form", "Reset form", script("reset-form.js"), 64)]
    for i, (name, caption, code, button_w) in enumerate(buttons):
        x = PAGE_WIDTH - MARGIN - sum(b[3] + 4 for b in buttons[i:]) + 4   # right-aligned, 4 points apart
        button = layout.add_field(name, "button", size=8)
        for page in layout.pages:
            layout.page = page
            layout.add_widget(button, x, PAGE_HEIGHT - 25, button_w, 13, caption=caption, border=ACCENT, bg=ACCENT,
                              border_width=0, action=code, flags=0)

    # "Generate QR Code" and "Print Form", under the QR code.
    layout.page = layout.pages[qr["page"]]
    for i, (name, caption, js_file) in enumerate((("__generate_qr", "Generate QR Code", "generate-qr.js"),
                                                  ("__print_form", "Print Form", "print-form.js"))):
        button = layout.add_field(name, "button", size=10)
        bx, by = qr["button"]
        layout.add_widget(button, bx + i * 162, by, 150, 22, caption=caption, border=ACCENT, bg=ACCENT, border_width=0,
                          action=script(js_file), flags=0)
    return doc_script
