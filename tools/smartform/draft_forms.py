"""DRAFT FORM FILES: data/forms.json (the old forms' questions and probed rules) -> drafts/<name>_form.py.

    python tools/smartform/draft_forms.py

Writes one form file per old form, in lc-form's format (the same as lc_form.py), as a starting point: every question
in the old form's order, its wording, kind, options, length limit, format, and its mandatory / conditional rules as
found by probing the old form. Each draft is then reviewed by hand (labels, sections, rules the probe can't see)
and copied to the repo's forms folder as <name>_form.py.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

from xfa import Template, child, tag

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
TEMPLATE = os.path.expanduser("~/Documents/trade-smartform-extract/xfa/template.xml")
OUT = os.path.join(HERE, "drafts")
FILES = {"LC_Amendment": "lc_amendment", "EBLC": "eblc", "OBC": "obc", "DBRP": "import_financing", "EXPORT": "export_financing",
         "BG": "bg", "SBLC": "sblc", "BGA": "bg_amendment", "SBLCA": "sblc_amendment", "BEGeneric": "bill_of_exchange",
         "BEEBLC": "bill_of_exchange_eblc", "BEOBC": "bill_of_exchange_obc", "LC": "lc_old"}
PDF = {"LC_Amendment": "LC-Amendment", "EBLC": "EBLC-Application", "OBC": "OBC-Application", "DBRP": "Import-Financing",
       "EXPORT": "Export-Financing", "BG": "BG-Application", "SBLC": "SBLC-Application", "BGA": "BG-Amendment",
       "SBLCA": "SBLC-Amendment", "BEGeneric": "Bill-of-Exchange", "BEEBLC": "Bill-of-Exchange-EBLC", "BEOBC": "Bill-of-Exchange-OBC", "LC": "LC-old"}


def clean(s):
    s = re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("–", "-")).strip()
    s = re.sub(r"\s*\*\s*:?\s*$", "", s)
    return re.sub(r"\s*:\s*$", "", s).strip()


def humanize(name):
    name = re.sub(r"^(subfrm|sufrm|sub|txt|drp|chk|rad|lbl)", "", name)
    name = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return name.strip().capitalize() or "Details"


def main():
    T = Template(TEMPLATE)
    data = json.load(open(os.path.join(HERE, "data", "forms.json")))
    os.makedirs(OUT, exist_ok=True)
    # document order of every template path inside each section
    for sec in data["forms"]:
        name = sec["name"]
        layout = json.load(open(os.path.join(RAW, f"{name}.layout.json")))
        items = layout["base"] + [it for h in layout["hidden"] for it in h["items"]]
        draws = [it for it in items if it["cls"] == "draw" and (it.get("text") or "").strip() and not it["master"]]
        order = {}
        for som in T.by_som:
            if f".{name}[0]." in som:
                p = ".".join(re.sub(r"\[0\]$", "", x) for x in som.split(f".{name}[0].", 1)[1].split(".") if not x.startswith("#"))
                order.setdefault(p, len(order))
        fields = sorted(sec["fields"], key=lambda f: order.get(f["xfa"], 10 ** 6))
        if not fields:
            continue

        def parent(som):
            return som.rsplit(".", 1)[0]

        def nearby_label(f):
            """The text drawn nearest above or left of a question, inside the same box (a radio group's question)."""
            rect = f["options"][0]["rect"] if f["kind"] == "radio" else f["rect"]
            page = f["options"][0]["page"] if f["kind"] == "radio" else f["page"]
            best, score = None, 1e9
            for d in draws:
                if d["page"] != page:
                    continue
                dx, dy = d["x"] + 12 * 72 / 25.4, d["y"] + 28.325 * 72 / 25.4
                if dy > rect[1] + 4 or dx > rect[0] + 20:
                    continue
                s = (rect[1] - dy) * 2 + max(0, rect[0] - dx - d["w"]) * 0.2
                if s < score and rect[1] - dy < 40:
                    best, score = d, s
            return clean(best["text"]) if best else ""

        # sections: the box (subform) each question sits in, ignoring the containers most questions share
        groups = [f["xfa"].split(".")[:-1] for f in fields]
        common = Counter(p for g in groups for p in set(g))
        def group_of(f):
            parts = [p for p in f["xfa"].split(".")[:-1] if common[p] < 0.4 * len(fields)]
            return parts[0] if parts else "Details"
        sections, last = [], None
        for f in fields:
            g = group_of(f)
            if g != last:
                sections.append([g, []])
                last = g
            sections[-1][1].append(f)

        by_id = {f["id"]: f for f in fields}
        lines = []
        prev_label = ""
        for g, fs in sections:
            title = humanize(g)
            lines.append(f'        section("{title}", fields=[')
            for f in fs:
                label = clean(f.get("label"))
                if f["kind"] == "radio" or not label:
                    near = nearby_label(f)
                    if f["kind"] == "radio":
                        label = near or label or humanize(f["id"])
                    elif not label:
                        m = re.search(r"(\d)$", f["id"])
                        label = f"{prev_label} (line {m.group(1)})" if m and prev_label else near or humanize(f["id"].split("_")[-1])
                prev_label = re.sub(r" \(line \d\)$", "", label)
                lines.append("            " + question(f, label, by_id) + ",")
            lines.append("        ]),")
        always = sum(1 for f in fields if (f.get("rules") or {}).get("always"))
        text = HEADER.format(title=sec["title"], file=FILES[name], code=sec["code"], pdf=PDF[name], n=len(fields), always=always,
                             sections="\n".join(lines))
        path = os.path.join(OUT, f"{FILES[name]}_form.py")
        open(path, "w").write(text)
        print(f"{path}: {len(fields)} questions, {len(sections)} sections")


def rule_text(rules, by_id):
    """Probe rules [[trigger id, [values]]] as form-file rules."""
    out = []
    for t, vals in rules:
        tf = by_id.get(t)
        if not tf:
            continue
        if "*" in vals:
            out.append(f'answered("{t}")')
        elif tf["kind"] == "check":
            out.append(f'ticked("{t}")')
        else:
            if tf["kind"] == "radio":
                labels = {o["on"]: clean(o["label"]) or o["on"] for o in tf["options"]}
                vals = [labels.get(v, v) for v in vals]
            if tf["kind"] == "select":
                disp = {s: d for d, s in tf.get("options") or []}
                vals = [disp.get(v, v) for v in vals]
            out.append("when(%s)" % ", ".join(json.dumps(x) for x in [t] + vals))
    return " + ".join(out)


def question(f, label, by_id):
    kind, r = f["kind"], f.get("rules") or {}
    args = [json.dumps(f["id"]), json.dumps(label)]
    if kind == "radio":
        opts = [clean(o["label"]) or o["on"] for o in f["options"]]
        args.append(json.dumps(opts))
        make = "radio"
    elif kind == "select":
        opts = [d for d, s in f.get("options") or [] if d.strip()]
        make = "select"
        args.append("options=" + ("CURRENCIES" if len(opts) > 40 and all(len(o) <= 3 or o[:3].isupper() for o in opts[:5]) else json.dumps(opts)))
    else:
        make = {"text": "text", "long": "long", "date": "date", "number": "text", "check": "check"}[kind]
    if r.get("always") and not r.get("nreq"):
        args.append("required=True")
    req = rule_text(r.get("req", []), by_id)
    if r.get("always") and r.get("nreq"):
        # mandatory unless the trigger has one of these values
        parts = []
        for t, vals in r["nreq"]:
            tf = by_id.get(t)
            if tf and tf["kind"] == "select":
                disp = {s: d for d, s in tf.get("options") or []}
                vals = [disp.get(v, v) for v in vals]
            parts.append('[{"field": %s, "values": %s, "not": True}]' % (json.dumps(t), json.dumps(vals)))
        req = " + ".join([req] + parts if req else parts)
    if req:
        args.append("requiredIf=" + req)
    act = rule_text((r.get("open") or []) + (r.get("show") or []), by_id)
    if act and act != req:
        args.append("activeIf=" + act)
    mx = f.get("max") or (f.get("ks") or {}).get("limit")
    if mx and kind in ("text", "long", "number"):
        args.append(f"max={mx}")
    spec = (f.get("ks") or {}).get("spec", "")
    if kind == "number":
        args.append('format="amount"' if f.get("decimals") else 'format="number"')
    elif "D" in spec:
        args.append('format="number"')
    elif "N" in spec:
        args.append('format="amount"')
    elif re.search(r"tel|fax|phone", f["id"]):
        args.append('format="phone"')
    return f"{make}({', '.join(args)})"


HEADER = '''"""{title} (Form {code}).

Build it:   python build.py {file}_form.py     -> out/{pdf}.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules ({n} questions, {always} always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {{
    "title": "{title}",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form {code} · v1.0 · Nov 2026",
    "sections": [
{sections}
    ],
}}

DEFAULTS = {{}}

PDF_NAME = "{pdf}.pdf"
PAGES = None
'''

if __name__ == "__main__":
    main()
