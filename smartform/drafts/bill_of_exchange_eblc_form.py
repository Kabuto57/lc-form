"""Bill of Exchange (Export Documentary Credit) (Form BEEBLC-01).

Build it:   python build.py bill_of_exchange_eblc_form.py     -> out/Bill-of-Exchange-EBLC.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (42 questions, 10 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Bill of Exchange (Export Documentary Credit)",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BEEBLC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Details", fields=[
            text("no", "No.", required=True, max=17),
            date("date", "Singapore,", required=True),
            text("exchange", "Exchange", required=True, format="number"),
            text("at", "At", required=True),
            text("sum1", "the sum of"),
            text("sum2", "the sum of (line 2)"),
            text("sum3", "the sum of (line 3)"),
            text("to1", "To", required=True, max=35),
            text("to2", "To (line 2)", max=35),
            text("to3", "To (line 3)", max=35),
            text("signature1", "To (line 1)"),
            text("documentary", "Documentary Credit No.", required=True, max=20),
            text("signature2", "Documentary Credit No. (line 2)"),
            text("to4", "Documentary Credit No. (line 4)", max=35),
            text("for1", "Documentary Credit No. (line 1)", required=True, max=50),
            text("value2", "Documentary Credit No. (line 2)"),
            text("value3", "Documentary Credit No. (line 3)"),
            date("dated", "dated"),
            text("for2", "dated (line 2)", required=True, max=50),
            select("currency", "For", options=CURRENCIES, required=True),
            text("value1", "value received \"Drawn under", required=True),
            text("no_2", "No."),
            date("date_2", "No. (line 2)"),
            text("exchange_2", "No. (line 2)", format="number"),
            text("at_2", "At"),
            text("sum1_2", "the sum of"),
            text("sum2_2", "the sum of (line 2)"),
            text("sum3_2", "the sum of (line 2)"),
            text("to1_2", "To", max=35),
            text("to2_2", "To (line 2)", max=35),
            text("to3_2", "To (line 2)", max=35),
            text("signature1_2", "To (line 2)"),
            text("signature2_2", "To (line 2)"),
            text("value1_2", "value received \"Drawn under"),
            text("value2_2", "value received \"Drawn under (line 2)"),
            text("value3_2", "value received \"Drawn under (line 2)"),
            date("dated_2", "dated"),
            text("documentary_2", "Documentary Credit No."),
            text("to4_2", "Documentary Credit No. (line 2)", max=35),
            text("for1_2", "Documentary Credit No. (line 2)", max=50),
            text("for2_2", "Documentary Credit No. (line 2)", max=50),
            select("currency_2", "For", options=CURRENCIES),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "Bill-of-Exchange-EBLC.pdf"
PAGES = None
