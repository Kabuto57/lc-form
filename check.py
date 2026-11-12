"""Checks the built PDF:  python check.py   (after python build_lc.py)

Opens out/LC-Application.pdf with pikepdf and checks that every question in lc.py became the right fields, with
their rules, limits and starting answers, and that the scripts, buttons and QR code rows are there.
(The scripts themselves run only inside Acrobat; test them there: see README, "Testing in Acrobat".)
"""
import json
import re
import zlib

import pikepdf

from lc import DEFAULTS, LC

pdf = pikepdf.open("out/LC-Application.pdf")
fields = {str(f.T): f for f in pdf.Root.AcroForm.Fields}
questions = [f for s in LC["sections"] for f in s["fields"]]
assert len(pdf.pages) == 4, len(pdf.pages)
assert len(fields) == 297, len(fields)

# 1. Every question has its fields: dates a list + a calendar box, "tick any" one box per option.
for q in questions:
    names = [f"{q['id']}__{i}" for i in range(len(q["options"]))] if q["kind"] == "checks" else \
        [q["id"], f"{q['id']}__list"] if q["kind"] == "date" else [q["id"]]
    for n in names:
        assert n in fields, f"missing field {n}"
    f = fields[names[0]]
    assert int(f.get("/Ff", 0)) & 2 == (2 if q.get("required") and q["kind"] != "date" else 0), f"required flag on {q['id']}"
    if q.get("max") and q["kind"] in ("text", "long"):
        assert int(f.MaxLen) == q["max"], f"max length of {q['id']}"

# 2. Starting answers, kept as the values "Reset form" goes back to.
for k, v in DEFAULTS.items():
    f = fields[k]
    assert "/DV" in f, f"no reset value for {k}"
    if isinstance(v, str) and f.FT == "/Tx":
        assert str(f.V) == v, f"{k} starts as {f.V}"

# 3. The rules script: one document script holding the rules table, the QR code encoder and the payload.
js = zlib.decompress(pdf.Root.Names.JavaScript.Names[1].JS.read_raw_bytes()).decode("latin-1")
for name in ("function lcRules(", "function lcDates(", "function lcPayload(", "function lcQrMatrix(", "function lcDrawQr("):
    assert name in js, f"script lacks {name}"
M = json.loads(re.search(r"var M = (\{.*?\});\n", js).group(1))
assert M["applicant_name"].get("always") == 1
assert M["drafts_percent"]["requiredIf"] == [["drafts", ["true"], 0]]
assert M["term_days"]["requiredIf"] == [["drafts_at", ["Term"], 0]]
assert M["amount"]["check"][0] == r"^\d{1,3}(,?\d{3})*(\.\d{1,2})?$"
for q in questions:   # every mandatory or conditional question is in the table
    if q.get("required") or q.get("requiredIf") or q.get("activeIf"):
        assert q["id"] in M, f"{q['id']} not in the rules table"

# 4. Buttons, the hidden re-check field, and the QR code rows.
for b in ("__check_form", "__reset_form", "__generate_qr", "__print_form", "__checks", "__qr"):
    assert b in fields, f"missing {b}"
assert len(fields["__check_form"].Kids) == 4, "Check form on every page"
assert all(f"__qr_{y}" in fields for y in range(177))
assert "/WS" in pdf.Root.AA and "/WP" in pdf.Root.AA, "warnings before save / print"
print("PASS: 4 pages, 297 fields, rules table, scripts, buttons and QR rows OK")
