#!/usr/bin/env python3
"""CHECK a section's min_height:  python check_min_height.py   -> prints PASS.
Lays out small forms and reads where the sections end: a section with min_height is at least that tall (blank space at the
bottom), one without it is as tall as its questions, a half-width pair is as tall as the taller one, and a section that no
longer fits moves to the next page. Also checks that build.py refuses a bad min_height."""
import sys

sys.dont_write_bytecode = True
import layout
from layout import Layout, SECTION_GAP, PAGE_ROOM
import build


def sec(**more):
    return {"title": "T", "fields": [{"id": "a", "label": "A", "kind": "text"}], **more}


def laid(*sections):
    form = {"title": "F", "sections": list(sections)}
    lay = Layout(form, {}, {})
    lay.draw_title()
    start = lay.top
    lay.draw_sections()
    return lay, start - lay.top


plain = laid(sec())[1]
assert laid(sec(min_height=200))[1] == 200 + SECTION_GAP, "taller than its questions"
assert laid(sec(min_height=5))[1] == plain, "content wins when min_height is smaller"
half = laid(sec(width="half"), sec(width="half"))[1]
assert laid(sec(width="half", min_height=150), sec(width="half"))[1] == 150 + SECTION_GAP, "a pair is as tall as the taller one"
assert half < 150 + SECTION_GAP
lay, _ = laid(*[sec() for _ in range(3)], sec(min_height=700))
assert len(lay.pages) == 2, "a section that no longer fits moves to the next page"
for bad in (0, -5, "10", True, PAGE_ROOM + 1):
    try:
        build.check_form({"title": "F", "sections": [sec(min_height=bad)]}, {}, layout.FORMATS)
    except SystemExit as e:
        assert "min_height" in str(e)
    else:
        raise AssertionError(f"min_height={bad!r} was accepted")
build.check_form({"title": "F", "sections": [sec(min_height=PAGE_ROOM)]}, {}, layout.FORMATS)
print("PASS")
