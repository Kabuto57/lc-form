"""lcbuild: builds the LC application form (lc.py) into a fillable PDF.

The build has three steps, one file each:
  layout.py    STEP 1  lay out the pages: where every section, question and box goes
  scripts.py   STEP 2  add the Acrobat JavaScript (from js/), the buttons and the QR code rows
  writer.py    STEP 3  write the PDF objects with pikepdf
build.py ties them together. Supporting files:
  style.py     page size, colours, sizes, answer formats
  text.py      making text safe for the PDF fonts, measuring and wrapping it
  rules.py     "is this question mandatory now?", "does it apply now?", the date list
"""
from .build import build

__all__ = ["build"]
