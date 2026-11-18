"""Reads the vendor's smart form in Adobe Acrobat and saves what the converter needs (data/raw/, not committed).

    python tools/smartform/harvest.py ~/Downloads/Trade-Smartform.pdf [SECTION ...]

Needs Adobe Acrobat on a Mac (it is driven with AppleScript's "do script"). The vendor PDF is opened hidden, so
nothing appears on screen. For each section it saves:
    data/raw/<SECTION>.layout.json   where everything is drawn (acrobat/harvest.js)
    data/raw/<SECTION>.probe.json    the old rules, found by trying every choice (acrobat/probe.js)
Parts that start hidden and push the rest down when shown get their room: they are measured shown.
Every text is anonymised on the way in (the bank's name becomes Demo Bank).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "data", "raw")
SECTIONS = ["MainPage", "LC", "LCTermsAndConditions", "LC_Amendment", "EBLC", "EBLCTermsAndConditions",
            "EBLCTermsAndConditions1", "OBC", "OBCTermsAndConditions", "DBRP", "BEOBC", "BEEBLC", "BEGeneric",
            "SBLC", "SBLCA", "BG", "BGA", "EXPORT"]
TERMS = {"LCTermsAndConditions", "EBLCTermsAndConditions", "EBLCTermsAndConditions1", "OBCTermsAndConditions"}

# The bank's identity, most specific first: (pattern, replacement, flags) triples in anon.local.json beside this file.
# Kept out of the repository (it would name the bank); the visible name becomes "Demo Bank".
ANON = json.load(open(os.path.join(HERE, "anon.local.json"))) if os.path.exists(os.path.join(HERE, "anon.local.json")) else []


def anonymise(text):
    for pattern, repl, flags in ANON:
        text = re.sub(pattern, repl, text, flags=flags)
    return text


def run(script, **params):
    """Runs acrobat/<script> in Acrobat with the given parameters; returns its JSON result (not yet anonymised)."""
    pre = "".join(f"var __{k} = {json.dumps(v)};\n" for k, v in params.items())
    path = os.path.join(HERE, "acrobat", ".job.js")
    with open(path, "w") as f:
        f.write(pre + open(os.path.join(HERE, "acrobat", script)).read())
    out = subprocess.run([os.path.join(HERE, "acrobat", "run_in_acrobat.sh"), path], capture_output=True, text=True).stdout.strip()
    if not out.startswith("{"):
        raise SystemExit(f"{script} {params.get('ONLY')}: {out[:300]}")
    return json.loads(out)


def save(data, name):
    with open(os.path.join(RAW, name), "w") as f:
        f.write(anonymise(json.dumps(data)))


def main(pdf, sections):
    os.makedirs(RAW, exist_ok=True)
    acro = "/Macintosh HD" + os.path.abspath(os.path.expanduser(pdf))   # Acrobat's own path form
    for s in sections:
        layout = run("harvest.js", PATH=acro, ONLY=s)
        grow = [h["som"] for h in layout["hidden"] if h["shifted"]]
        if grow:   # measure again with those parts shown, so they have room in the new form
            layout = run("harvest.js", PATH=acro, ONLY=s, PREREVEAL=grow)
        save(layout, f"{s}.layout.json")
        line = f"{s}: {layout['pages']} page(s), {len(layout['base'])} items, {len(layout['hidden'])} hidden parts, shown to make room: {len(grow)}"
        if s not in TERMS and s != "MainPage":
            probe = run("probe.js", PATH=acro, ONLY=s)
            save(probe, f"{s}.probe.json")
            line += f", {len(probe['probes'])} rule probes"
        print(line)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or SECTIONS)
