#!/usr/bin/env python3
"""BUILD A FORM:   python build.py forms/lc.py     (with no name, it builds forms/lc.py)

Reads the form file, checks it for mistakes, builds the PDF, checks the PDF, and saves it in out/
(with out/index.html, a page for viewing it:  python -m http.server 8090 -d out  ->  http://localhost:8090).

A form file defines:
    FORM       the form: title, note, issuer, formCode, sections               (required)
    DEFAULTS   answers already filled in when the form opens                   (optional)
    PDF_NAME   the file name to write in out/                                  (optional; default: from the title)
    PAGES      the number of pages the form must fit on; the build stops if not (optional)
"""
import importlib.util
import os
import re
import sys

sys.dont_write_bytecode = True   # always read the form file fresh (no cached copy of an older version)

from engine import build                        # noqa: E402
from engine.check import self_check             # noqa: E402
from engine.look import FORMATS                 # noqa: E402
from engine.questions import check_form         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def load_form(path):
    """The form file as a module, with the optional names filled in."""
    if not os.path.exists(path):
        raise SystemExit(f"No form file called {path}. The forms are in the forms/ folder, e.g.  python build.py forms/lc.py")
    loader = importlib.util.spec_from_file_location("form_file", path)
    spec = importlib.util.module_from_spec(loader)
    try:
        loader.loader.exec_module(spec)
    except SyntaxError as e:
        raise SystemExit(f"PROBLEM IN THE FORM FILE: {path}, line {e.lineno}: Python can't read it ({e.msg}). "
                         "Usually a missing comma, quote or bracket on that line or the line before.")
    if not hasattr(spec, "FORM"):
        raise SystemExit(f"{path} has no FORM = {{...}}. Copy forms/example_leave.py to see what a form file needs.")
    spec.DEFAULTS = getattr(spec, "DEFAULTS", {})
    spec.PDF_NAME = getattr(spec, "PDF_NAME", re.sub(r"\W+", "-", spec.FORM["title"]).strip("-") + ".pdf")
    spec.PAGES = getattr(spec, "PAGES", None)
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
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "forms", "lc.py"))
