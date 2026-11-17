"""EXAMPLE: A SMALL FORM TO COPY WHEN YOU START A NEW ONE (Annual Leave Request).

Build it:   python build.py example_form.py     -> out/Annual-Leave-Request.pdf

To start a new form: copy this file to a new name ending in _form.py (e.g. trade_loan_form.py), in the same
folder, then change the title, formCode, sections, DEFAULTS and PDF_NAME. Every form file has the same parts in
the same order, so any form can be copied the same way.

WHAT YOU CAN CHANGE (all in this file; the same list is in every form file and in build.py, section 1)
    THE WHOLE FORM      FORM = {...}: "title", "note" (under the title), "issuer" (top of every page), "formCode"
                        (footer and QR code: give every form its own code, e.g. "Form EB-01 · v1.0 · Nov 2026").
                        DEFAULTS: answers filled in when the form opens.  PDF_NAME: the file name in out/.
                        PAGES (optional): the build stops if the form doesn't fit on that many pages (QR page included).
    A SECTION           section("Title", fields=[...], ...) plus any of:
                          note="..."        text under the heading
                          bankOnly=True     shaded "For Bank Use Only" section
                          signoff=True      signature, date and company stamp lines (always the whole width)
                          width="full"      the whole width of the page
                          width="half"      half the page; two half sections in a row sit side by side
                          new_page=True     starts on a new page
    A QUESTION          text / long / date / radio / checks / check / select (id, label, ...) plus any of:
                          required=True                     always mandatory (red *)
                          requiredIf=ticked("x")            mandatory (and unlocked) only when tick box x is ticked
                          requiredIf=when("x", "A", "B")    mandatory only when x is A or B
                          requiredIf=answered("x")          mandatory once x has any answer
                          activeIf=ticked("x")              unlocked only when x is ticked, but optional
                          max=35                            at most 35 characters (also sets the box width)
                          format="amount"                   amount / number / phone / account
                          cols=12                           width out of 12 columns: 12 whole row, 6 half, 4 a third
                          beside=69.3                       label beside a box this wide, even when the label is long
                          options=CURRENCIES                the shared currency list (in build.py)
    LEFT OUT            width, new_page and cols are only for when you want something different: without them
                        layout.py lays the form out by itself. Colours and text sizes are the same on every form
                        (red = mandatory) and are not set here.
    NOT IN THIS FILE    checks that compare two answers (e.g. a date must be after another): acrobat_js.py
                        (across) and read_qr.py (checks_across), kept the same.
"""
# Every form file starts with this same line: it brings in the words used below.
from build import CURRENCIES, answered, check, checks, date, long, radio, section, select, text, ticked, when

FORM = {
    "title": "Annual Leave Request",
    "note": "Please complete in block letters.",
    "issuer": "Demo Bank · HR",
    "formCode": "Form HR-07 · v1.0 · Nov 2026",
    "sections": [
        section("Employee", fields=[
            # text(id, label, ...): a one-line box. The id is the answer's name in the QR code: letters, digits, _
            text("name", "Full name", required=True, max=35),
            text("staff_no", "Staff number", required=True, max=8, format="number"),
        ]),
        section("Leave", fields=[
            date("start", "First day", required=True),
            date("end", "Last day", required=True),
            radio("type", "Type of leave", ["Annual", "Medical", "Other"], required=True),
            # Only mandatory (and only unlocked) when "Type of leave" is "Other":
            text("other_type", "Other: please say", requiredIf=when("type", "Other"), max=30),
            check("handover", "I have handed over my work"),
            # Only mandatory (and only unlocked) when the tick box above is ticked:
            long("handover_notes", "Handover notes", requiredIf=ticked("handover"), max=500),
        ]),
        section("Declaration", signoff=True, fields=[
            text("signed_by", "Name of employee"),
        ]),
    ],
}

# Answers already filled in when the form opens ({} for none).
DEFAULTS = {"type": "Annual"}

# The PDF's file name in out/.
PDF_NAME = "Annual-Leave-Request.pdf"
