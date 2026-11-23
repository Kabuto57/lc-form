"""EXAMPLE: A SMALL FORM TO COPY WHEN YOU START A NEW ONE (Annual Leave Request).

Build it:   python build.py example_form.py     -> out/Annual-Leave-Request.pdf

To start a new form: copy this file to a new name ending in _form.py (e.g. trade_loan_form.py), then change the parts marked
"CHANGE". Every kind of question and every option is listed in section 1 of build.py. eblc_form.py shows the
layout options in use (full / half sections, cols=).

WHAT YOU CAN CUSTOMISE (all in this file; every option is also listed in build.py, section 1)
    THE WHOLE FORM      FORM = {...}: "title", "note" (under the title), "issuer" (top of every page), "formCode" (footer
                        and QR code). PDF_NAME (the file name). DEFAULTS (answers filled in when the form opens).
    A SECTION           section("Title", fields=[...], ...) plus any of:
                          width="full"      the whole width of the page
                          width="half"      half the page; two half sections in a row sit side by side
                          (no width)        the build decides: two short, similar sections sit side by side
                          new_page=True     starts on a new page
                          note="..."        text under the heading
                          bankOnly=True     shaded "For Bank Use Only" section
                          signoff=True      signature, date and company stamp lines (always the whole width)
                          buttons=["check-form", "print-form"]   a row of buttons at its bottom right: any of
                                            "check-form", "reset-form", "generate-qr", "print-form" (screen only)
    A QUESTION          text / long / date / radio / checks / check / select (id, label, ...) plus any of:
                          required=True                     always mandatory (red *)
                          requiredIf=ticked("x")            mandatory (and unlocked) only when tick box x is ticked
                          requiredIf=when("x", "A", "B")    mandatory only when x is A or B
                          requiredIf=answered("x")          mandatory once x has any answer
                          activeIf=ticked("x")              unlocked only when x is ticked, but optional
                          max=35                            at most 35 characters (also sets the box width)
                          format="amount"                   amount / number / phone / account
                          cols=12                           width out of 12 columns: 12 whole row, 6 half, 4 a third
                          height=80                         paragraph boxes (long) only: the box's height in points (50)
                                                            (no cols: the build picks from the label and max)
    LEFT OUT            width, new_page and cols are only for when you want something different: without them
                        layout.py lays the form out by itself. Colours and text sizes are the same on every form
                        (red = mandatory) and are not set here.
    NOT IN THIS FILE    checks that compare two answers (e.g. a date must be after another): acrobat_js.py
                        (across) and read_qr.py (checks_across), kept the same.
"""
# Always keep this line: it brings in the words used below (text, date, radio ...).
from build import check, date, long, radio, section, text, ticked, when

FORM = {
    "title": "Annual Leave Request",                 # CHANGE: shown at the top of page 1
    "note": "Please complete in block letters.",     # CHANGE: the instruction under the title
    "issuer": "Demo Bank · HR",                      # CHANGE: shown at the top of every page
    "formCode": "Form HR-07 · v1.0 · Nov 2026",      # CHANGE: shown at the bottom of every page; "HR-07" and "1.0"
                                                     #         also go into the QR code
    "sections": [                                    # CHANGE: the sections, in order; each has its questions
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

# CHANGE: answers already filled in when the form opens (or delete these lines).
DEFAULTS = {"type": "Annual"}

# CHANGE: the PDF's file name in out/ (or delete: it is then named after the title).
PDF_NAME = "Annual-Leave-Request.pdf"
