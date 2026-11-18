"""Bill of Exchange (Export Documentary Collection) (Form BEOBC-01).

Build it:   python build.py bill_of_exchange_obc_form.py     -> out/Bill-of-Exchange-OBC.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (38 questions, 8 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Bill of Exchange (Export Documentary Collection)",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BEOBC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Details", fields=[
            text("no", "No.", required=True, max=17),
            date("date", "Singapore,"),
            text("exchange", "Exchange", required=True, format="number"),
            text("at", "At", required=True, max=51),
            text("sum1", "the sum of"),
            text("sum2", "the sum of (line 2)"),
            text("sum3", "the sum of (line 3)"),
            text("value1", "value received", required=True),
            text("value2", "value received (line 2)"),
            text("value3", "value received (line 3)"),
            text("to1", "To", required=True, max=35),
            text("to2", "To (line 2)", max=35),
            text("to3", "To (line 3)", max=35),
            text("to4", "To (line 4)", max=35),
            text("signature", "Signature"),
            text("signature_1", "Signature (line 1)"),
            text("for1", "Signature (line 1)", required=True, max=35),
            text("for2", "Signature (line 2)", required=True, max=35),
            select("currency", "For", options=CURRENCIES, required=True),
            text("no_2", "No.", max=17),
            date("date_2", "Singapore,"),
            text("exchange_2", "Singapore, (line 2)", format="number"),
            text("at_2", "At", max=51),
            text("sum1_2", "the sum of"),
            text("sum2_2", "the sum of (line 2)"),
            text("sum3_2", "the sum of (line 2)"),
            text("value1_2", "value received"),
            text("value2_2", "value received (line 2)"),
            text("value3_2", "value received (line 2)"),
            text("to1_2", "To", max=35),
            text("to2_2", "To (line 2)", max=35),
            text("to3_2", "To (line 2)", max=35),
            text("to4_2", "To (line 2)", max=35),
            text("signature1", "To (line 1)"),
            text("for1_2", "To (line 2)", max=35),
            text("for2_2", "To (line 2)", max=35),
            text("signature2", "To (line 2)"),
            select("currency_2", "For", options=CURRENCIES),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "Bill-of-Exchange-OBC.pdf"
PAGES = None
