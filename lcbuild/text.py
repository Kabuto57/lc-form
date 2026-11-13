"""Text helpers: making text safe for the PDF's built-in fonts, measuring it, and wrapping it into lines.

The form uses only the fonts every PDF reader has built in (Helvetica, Helvetica-Bold and ZapfDingbats), so no
font files are embedded. Those fonts cover Western European characters (the "WinAnsi" set).
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Characters outside WinAnsi that have a plain equivalent.
PLAIN = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "…": "..."}


def read_file(name):
    """A file from the project folder (js/*.js or helvetica-metrics.json)."""
    encoding = "latin-1" if name.endswith(".js") else "utf-8"
    with open(os.path.join(ROOT, name), encoding=encoding) as f:
        return f.read()


def safe(s):
    """Text the built-in fonts can draw: curly quotes and dashes become plain ones; anything else unknown becomes '?'."""
    return re.sub(r"[^\n\x20-\x7e\xa0-\xff€]", lambda m: PLAIN.get(m.group(0), "?"), s or "")


# Adobe's own Helvetica measurements (each character's width and kerning, per 1000 units of font size), so text is
# measured exactly as Acrobat will draw it. Used to place labels, wrap text and size boxes.
METRICS = json.loads(read_file("helvetica-metrics.json"))


def width(text, size, bold=False):
    """How wide `text` is, in points, at font size `size`."""
    m = METRICS["bold" if bold else "helv"]
    units = sum(m["widths"].get(c, 0) for c in text) + sum(m["kern"].get(text[i:i + 2], 0) for i in range(len(text) - 1))
    return units * size / 1000


def wrap(text, size, max_width):
    """Splits text into lines no wider than max_width (breaking between words)."""
    lines = []
    for paragraph in safe(text).split("\n"):
        line = ""
        for word in re.split(r"\s+", paragraph):
            longer = f"{line} {word}" if line else word
            if line and width(longer, size) > max_width:
                lines.append(line)
                line = word
            else:
                line = longer
        lines.append(line)
    return lines


def fmt(n):
    """A number written into a PDF drawing command: at most 4 decimals, no trailing zeros (12.5, not 12.5000)."""
    return ("%.4f" % n).rstrip("0").rstrip(".")


def num(n):
    """A number stored in a PDF object: whole numbers as integers, others rounded to 4 decimals."""
    return int(n) if n == int(n) else round(n, 4)


def rgb(colour):
    """A colour (r, g, b) as PDF drawing-command text, e.g. '0.8 0 0'."""
    return " ".join(map(fmt, colour))


def pdf_string(s):
    """Text inside a PDF drawing command, with ( ) and backslash escaped."""
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def js_json(value):
    """JSON exactly as JavaScript's JSON.stringify writes it (no spaces, non-ASCII kept)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
