"""EXAMPLE: A SMALL FORM TO COPY WHEN YOU START A NEW ONE (Annual Leave Request).

Build it:   python build.py forms/example_leave.py     -> out/Annual-Leave-Request.pdf

To start a new form: copy this file to a new name in forms/ (e.g. forms/my_form.py), then change the parts marked
"CHANGE". Every kind of question and every option is listed at the top of engine/questions.py.
"""
# Always keep this line: it brings in the words used below (text, date, radio ...).
from engine.questions import check, date, long, radio, section, text, ticked, when

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
