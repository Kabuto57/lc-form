#!/usr/bin/env python3
"""Builds the LC application PDF.

    python build_lc.py        writes out/LC-Application.pdf (and out/index.html for local viewing)

The questions are in lc.py; the builder is the lcbuild/ folder (see lcbuild/__init__.py for how it works).
"""
import os
import shutil

from lc import DEFAULTS, LC
from lcbuild import build

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    out_dir = os.path.join(HERE, "out")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "LC-Application.pdf"), "wb") as f:
        f.write(build(LC, DEFAULTS))
    shutil.copy(os.path.join(HERE, "index.html"), out_dir)   # the page `python -m http.server` shows
    print("Wrote out/LC-Application.pdf")
