"""Scores QR and AI results against the true answers, and writes the report.

    ../.venv/bin/python score.py [MODEL ...]      -> results/report.md, results/scores.json

Per question:  correct (same answer) / wrong (a different answer) / missed (answered, but not read) /
               invented (blank on the form, but the reader gave an answer).
Fair on formatting only: case, spaces, "6/11/2026" = "06/11/2026", "612,072.50" = "612072.50", phone spacing.
Anything else (a wrong letter or digit, a wrong option) counts as wrong: the Bank would have to fix it.
"""
import datetime
import glob
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "forms"))
sys.dont_write_bytecode = True
import lc_form   # noqa: E402

QUESTIONS = {q["id"]: q for s in lc_form.FORM["sections"] for q in s["fields"]}
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def norm(q, v):
    """An answer in a form where only formatting differences disappear."""
    if v is None or v == "" or v is False or v == []:
        return None
    kind = q["kind"]
    if kind == "check":
        return True if v is True or str(v).strip().lower() in ("true", "yes", "x", "ticked") else None
    if kind == "checks":
        items = v if isinstance(v, list) else [v]
        return tuple(sorted(str(i).strip().upper() for i in items)) or None
    s = re.sub(r"\s+", " ", str(v)).strip().upper()
    if kind == "date":
        m = re.match(r"^(\d{1,2})[/\-. ](\d{1,2}|[A-Z]{3})[/\-. ](\d{4})$", s)
        if m:
            month = MONTHS.index(m.group(2)) + 1 if m.group(2).isalpha() and m.group(2) in MONTHS else int(m.group(2)) if m.group(2).isdigit() else 0
            try:
                return datetime.date(int(m.group(3)), month, int(m.group(1))).isoformat()
            except ValueError:
                return s
        return s
    if q.get("format") == "amount":
        return s.replace(",", "")
    if q.get("format") == "phone":
        return re.sub(r"[\s\-()]", "", s)
    return s


def score(truth, answers):
    out = {"correct": 0, "wrong": 0, "missed": 0, "invented": 0, "answered": 0, "problems": []}
    for qid, q in QUESTIONS.items():
        t, a = norm(q, truth.get(qid)), norm(q, answers.get(qid))
        if t is not None:
            out["answered"] += 1
        if t is None and a is None:
            continue
        if t == a:
            out["correct"] += 1
        elif t is None:
            out["invented"] += 1; out["problems"].append(("invented", qid, None, answers.get(qid)))
        elif a is None:
            out["missed"] += 1; out["problems"].append(("missed", qid, truth.get(qid), None))
        else:
            out["wrong"] += 1; out["problems"].append(("wrong", qid, truth.get(qid), answers.get(qid)))
    out["errors"] = out["wrong"] + out["missed"] + out["invented"]
    out["accuracy"] = round(100 * out["correct"] / out["answered"], 1) if out["answered"] else 0
    # every one of the form's questions (blank ones too) read right
    out["all_questions"] = round(100 * (len(QUESTIONS) - out["errors"]) / len(QUESTIONS), 1)
    return out


def stats(values):
    v = sorted(x for x in values if x is not None)
    if not v:
        return "-", "-", "-", "-"
    return min(v), statistics.median(v), max(v), sum(v) / len(v)


def fmt(x, unit=""):
    return "-" if x == "-" else f"{x:.1f}{unit}" if isinstance(x, float) else f"{x}{unit}"


def main():
    models = sys.argv[1:] or sorted(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "results", "*")) if os.path.isdir(p))
    samples = sorted(glob.glob(os.path.join(HERE, "samples", "*")))
    truth = {os.path.basename(f): json.load(open(os.path.join(f, "truth.json"))) for f in samples}
    readers = {}
    qr_path = os.path.join(HERE, "results", "qr.json")
    readers["QR code"] = json.load(open(qr_path)) if os.path.exists(qr_path) else {}
    for m in models:
        readers[m] = {os.path.basename(p)[:-5]: json.load(open(p)) for p in glob.glob(os.path.join(HERE, "results", m, "*.json"))}

    scores = {}
    for reader, results in readers.items():
        for name in truth:
            r = results.get(name)
            if r and r.get("answers"):
                sc = score(truth[name], r["answers"])
                sc["seconds"] = r.get("seconds")
                scores.setdefault(reader, {})[name] = sc

    L = ["# LC form: QR code vs AI reading (Gemini)", "",
         f"{len(truth)} fake LC applications: 4 typed (filled on a computer, printed with the QR code) and 6 handwritten "
         "(printed blank, filled by hand: no QR code). Scan quality clean / medium / poor. Accuracy = answers read exactly "
         "right / answers on the form; formatting differences (case, spaces, 6/11/2026 vs 06/11/2026, 1,000.00 vs 1000.00) "
         "don't count as errors. Wrong = a different answer; missed = an answer not read; invented = an answer read from a "
         "blank question.", "", "## Summary", "",
         "| Reader | Forms read | Forms 100% correct | Accuracy min | median | max | average (all answers) | Seconds min | median | max | average |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for reader, ss in scores.items():
        acc = stats([x["accuracy"] for x in ss.values()])
        sec = stats([x["seconds"] for x in ss.values()])
        overall = 100 * sum(x["correct"] for x in ss.values()) / sum(x["answered"] for x in ss.values())
        perfect = sum(1 for x in ss.values() if x["errors"] == 0)
        L.append(f"| {reader} | {len(ss)} | {perfect} of {len(ss)} | {fmt(acc[0], '%')} | {fmt(acc[1], '%')} | {fmt(acc[2], '%')} | "
                 f"{overall:.1f}% | {fmt(sec[0])} | {fmt(sec[1])} | {fmt(sec[2])} | {fmt(sec[3])} |")
    L += ["", "QR codes exist only on forms filled on a computer, so the QR row covers the 4 typed forms.", ""]

    L += ["## Each form", "", "| Form | Filled | Scan | Answers | " + " | ".join(f"{r}: correct / errors / 100%? / s" for r in scores) + " |",
          "|---|---|---|---|" + "---|" * len(scores)]
    for name in truth:
        _, filled, quality = name.split("-")
        row = f"| {name[:2]} | {'typed' if filled == 'typed' else 'handwritten'} | {quality} | {len(truth[name])} |"
        for reader in scores:
            x = scores[reader].get(name)
            row += (f" {x['correct']}/{x['answered']} ({x['accuracy']}%) / {x['errors']} / {'YES' if x['errors'] == 0 else 'no'} / {x['seconds']} |"
                    if x else (" no QR code |" if reader == "QR code" else " not run |"))
        L.append(row)
    L.append("")

    for reader, ss in scores.items():
        L += [f"## {reader}: by type of form and scan", "", "| Group | Forms | 100% correct | Accuracy | Errors | Average seconds |", "|---|---|---|---|---|---|"]
        groups = {}
        for name, x in ss.items():
            groups.setdefault(re.sub(r"^\d+-", "", name), []).append(x)
        for g, xs in sorted(groups.items()):
            a = sum(x["answered"] for x in xs); c = sum(x["correct"] for x in xs)
            L.append(f"| {g} | {len(xs)} | {sum(1 for x in xs if x['errors'] == 0)} | {100 * c / a:.1f}% | "
                     f"{sum(x['errors'] for x in xs)} | {sum(x['seconds'] for x in xs) / len(xs):.1f} |")
        L.append("")

        # by kind of question, and by data field
        kinds, fields = {}, {}
        for name, x in ss.items():
            bad = {qid: kind for kind, qid, _, _ in x["problems"]}
            for qid, q in QUESTIONS.items():
                t = norm(q, truth[name].get(qid))
                f = fields.setdefault(qid, {"answered": 0, "correct": 0, "invented": 0})
                k = kinds.setdefault(q.get("format") or q["kind"], {"answered": 0, "correct": 0})
                if t is not None:
                    f["answered"] += 1; k["answered"] += 1
                    if qid not in bad:
                        f["correct"] += 1; k["correct"] += 1
                elif bad.get(qid) == "invented":
                    f["invented"] += 1
        L += [f"## {reader}: by kind of answer", "", "| Kind | Answers | Correct | Accuracy |", "|---|---|---|---|"]
        for k, v in sorted(kinds.items(), key=lambda kv: kv[1]["correct"] / max(1, kv[1]["answered"])):
            if v["answered"]:
                L.append(f"| {k} | {v['answered']} | {v['correct']} | {100 * v['correct'] / v['answered']:.1f}% |")
        field_acc = [100 * v["correct"] / v["answered"] for v in fields.values() if v["answered"]]
        mn, md, mx, av = stats(field_acc)
        L += ["", f"## {reader}: by data field", "",
              f"{len(field_acc)} fields were answered on at least one form. Field accuracy: min {mn:.1f}%, median {md:.1f}%, "
              f"max {mx:.1f}%, average {av:.1f}%. {sum(1 for a in field_acc if a == 100)} of {len(field_acc)} fields were "
              "read right on every form. Worst fields first:", "",
              "| # | Field (id) | Question | Forms answered | Correct | Accuracy | Invented on blank forms |", "|---|---|---|---|---|---|---|"]
        numbers = {q["id"]: f"{s}.{i}" for s, sec in enumerate(lc_form.FORM["sections"], 1) for i, q in enumerate(sec["fields"], 1)}
        for qid, v in sorted(fields.items(), key=lambda kv: (kv[1]["correct"] / max(1, kv[1]["answered"]) if kv[1]["answered"] else 2, -kv[1]["invented"], numbers[kv[0]])):
            if v["answered"] or v["invented"]:
                acc = f"{100 * v['correct'] / v['answered']:.0f}%" if v["answered"] else "-"
                L.append(f"| {numbers[qid]} | `{qid}` | {QUESTIONS[qid]['label'][:60]} | {v['answered']} | {v['correct']} | {acc} | {v['invented'] or ''} |")
        L += ["", f"## {reader}: every error", ""]
        errs = [(name, *p) for name, x in ss.items() for p in x["problems"]]
        L += [f"- {name} `{qid}` {kind}: true {json.dumps(t, ensure_ascii=False)} -> read {json.dumps(a, ensure_ascii=False)}"
              for name, kind, qid, t, a in errs] or ["None."]
        L.append("")

    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "scores.json"), "w") as f:
        json.dump(scores, f, indent=1, ensure_ascii=False, default=str)
    with open(os.path.join(HERE, "results", "report.md"), "w") as f:
        f.write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    # self-check of the formatting rules
    q_date, q_amt = QUESTIONS["application_date"], QUESTIONS["amount"]
    assert norm(q_date, "6/11/2026") == norm(q_date, "06/11/2026") == norm(q_date, "6 NOV 2026")
    assert norm(q_amt, "612,072.50") == norm(q_amt, "612072.50") and norm(q_amt, "612,072.50") != norm(q_amt, "612,072.80")
    main()
