"""Puts the three steps together and produces the PDF bytes."""
import io

from .layout import Layout
from .scripts import add_scripts
from .writer import Writer


def build(form, answers):
    """The finished PDF as bytes.

    The layout runs twice: the second time, the room left at the end of the last page of questions is shared out
    to the paragraph boxes on that page (Goods description, Additional conditions), so the form doesn't end with a
    blank gap. The second layout is kept only if it doesn't add a page.
    """
    def lay_out(extra_height):
        layout = Layout(form, answers, extra_height)
        layout.draw()
        return layout

    layout = lay_out({})
    last_paragraphs = [qid for qid, page in layout.paragraph_page.items() if page == layout.last_question_page]
    if last_paragraphs and layout.spare >= 20:
        each = min(90, int((layout.spare - 10) // len(last_paragraphs)))   # at most 90 points more per box
        taller = lay_out({qid: each for qid in last_paragraphs})
        if len(taller.pages) == len(layout.pages):
            layout = taller

    doc_script = add_scripts(layout)                 # step 2
    pdf = Writer(layout, doc_script).write()         # step 3
    out = io.BytesIO()
    pdf.save(out, deterministic_id=True)             # same input, same file (reproducible builds)
    return out.getvalue()
