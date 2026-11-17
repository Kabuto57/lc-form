"""THE ENGINE: turns a form file (forms/*.py) into a fillable PDF. You don't need to open these files to change a form.

    forms/lc.py ──► build.py ──► engine.build() ──► out/LC-Application.pdf
                                   │
                                   ├─ questions.py  the helpers form files use: text, radio, date ... and check_form,
                                   │                which explains mistakes in a form file in plain words
                                   ├─ layout.py     STEP 1  where every section, question and box goes
                                   ├─ scripts.py    STEP 2  the rules table, buttons and QR code rows
                                   │   └─ js/       the JavaScript Acrobat runs inside the PDF
                                   │        document.js   rules engine (red boxes, locking, checks), QR text and encoder
                                   │        buttons.js    Check form, Reset form, Generate QR Code, Print Form, before save
                                   ├─ writer.py     STEP 3  pikepdf writes the real PDF
                                   └─ check.py      opens the result and checks it before it is saved
    Shared by the steps:
        look.py    page size, colours, text sizes, spacing, answer formats   (change the look of every form here)
        text.py    safe characters, measuring and wrapping text
        rules.py   "mandatory now?", "applies now?", the date list
        fonts.py   Helvetica letter widths (data)
"""
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

    layout = lay_out({})                             # step 1
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
