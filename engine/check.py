"""THE SELF-CHECK: opens every PDF the build makes and checks it, before it is saved.

If something is wrong, the build stops here with the reason.
"""
import io
import json
import re
import zlib

import pikepdf

from .text import safe
from .writer import REQUIRED

# Opens the finished PDF and checks that every question in the form file became the right fields, with their rules, limits
# and starting answers, and that the scripts, buttons and QR code rows are there. Stops with an error if not.
# (The scripts themselves run only inside Acrobat; test them there, see README "Testing in Acrobat".)

def self_check(pdf_bytes, spec):
    """spec: the form file (FORM, DEFAULTS, PAGES). Returns a one-line summary; stops with the reason if anything is wrong."""
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    fields = {str(f.T): f for f in pdf.Root.AcroForm.Fields}
    questions = [q for s in spec.FORM["sections"] for q in s["fields"]]
    problems = pdf.check_pdf_syntax()
    assert not problems, f"PDF structure problems: {problems}"
    if spec.PAGES:
        assert len(pdf.pages) == spec.PAGES, f"expected {spec.PAGES} pages (PAGES in the form file), got {len(pdf.pages)}"

    # Every question has its fields: dates a list + a calendar box, "tick any" one box per option.
    for q in questions:
        if q["kind"] == "checks":
            names = [f"{q['id']}__{i}" for i in range(len(q["options"]))]
        elif q["kind"] == "date":
            names = [q["id"], f"{q['id']}__list"]
        else:
            names = [q["id"]]
        for name in names:
            assert name in fields, f"missing field {name}"
        f = fields[names[0]]
        expected = REQUIRED if q.get("required") and q["kind"] != "date" else 0
        assert int(f.get("/Ff", 0)) & REQUIRED == expected, f"required flag wrong on {q['id']}"
        if q.get("max") and q["kind"] in ("text", "long"):
            assert int(f.MaxLen) == q["max"], f"max length wrong on {q['id']}"

    # Starting answers, kept as the values "Reset form" goes back to.
    for key, value in spec.DEFAULTS.items():
        f = fields[key]
        assert "/DV" in f, f"no reset value for {key}"
        if isinstance(value, str) and f.FT == "/Tx":
            assert str(f.V) == value, f"{key} starts as {f.V}"

    # The document script holds the rules table, the QR code's text and the QR encoder.
    doc_script = zlib.decompress(pdf.Root.Names.JavaScript.Names[1].JS.read_raw_bytes()).decode("latin-1")
    for name in ("function lcRules(", "function lcDates(", "function lcPayload(", "function lcQrMatrix(", "function lcDrawQr("):
        assert name in doc_script, f"script lacks {name}"
    table = json.loads(re.search(r"var M = (\{.*?\});\n", doc_script).group(1))
    for q in questions:   # every rule in the form file reached the rules table unchanged
        if q.get("required") or q.get("requiredIf") or q.get("activeIf"):
            assert q["id"] in table, f"{q['id']} not in the rules table"
        assert table.get(q["id"], {}).get("always") == (1 if q.get("required") else None), f"'always' wrong on {q['id']}"
        rules = [[r["field"], [safe(v) for v in r["values"]], 1 if r.get("not") else 0] for r in q.get("requiredIf") or []]
        assert table.get(q["id"], {}).get("requiredIf") == (rules or None), f"requiredIf wrong on {q['id']}"

    # Buttons, the hidden re-check field, and the QR code rows.
    for name in ("__check_form", "__reset_form", "__generate_qr", "__print_form", "__checks", "__qr"):
        assert name in fields, f"missing {name}"
    assert len(fields["__check_form"].Kids) == len(pdf.pages), "Check form should be on every page"
    assert all(f"__qr{k}_{y}" in fields for k in (1, 2) for y in range(177)), "missing QR code rows"
    assert int(fields["__qr2_frame"].Kids[0].F) == 2, "the second QR frame should start hidden"
    assert "/WS" in pdf.Root.AA and "/WP" in pdf.Root.AA, "missing the warning before save / print"
    return f"PASS: {len(pdf.pages)} pages, {len(fields)} fields, rules table, scripts, buttons and QR rows OK"
