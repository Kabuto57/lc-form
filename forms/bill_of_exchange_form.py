"""BILL OF EXCHANGE (GENERIC - FREE FORMAT) (Form BE-01).

Build it:   python build.py bill_of_exchange_form.py     -> out/Bill-of-Exchange.pdf

Redrawn from the old trade smart form's bill of exchange. The old form printed the FIRST and the SECOND of exchange,
the second copied from the first; here the answers are given once and both copies print from them (the QR code
carries them once). "The sum of" is the amount in words, filled in by the form as on the old one.
bill_of_exchange_eblc_form.py and bill_of_exchange_obc_form.py use bill_sections() from this file.
Every option a form file can use is listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import date, section, select, text
from lc_form import CURRENCIES


def bill_sections(credit=True):
    """The questions of a bill of exchange. credit=False: a collection bill (OBC), with no documentary credit."""
    return [
        section("Bill of Exchange", fields=[
            text("bill_no", "No.", required=True, max=17),
            date("bill_date", "Singapore, (date)", required=True),
            select("currency", "For (currency)", options=CURRENCIES, required=True),
            text("exchange_amount", "Exchange (amount)", required=True, max=15, format="amount"),
            text("tenor", "At (e.g. SIGHT, or 30 DAYS AFTER SIGHT)", required=True, max=51),
            text("sum_in_words", "Of this FIRST OF EXCHANGE (second of the same tenor and date being unpaid) pay to the order of Demo Bank Ltd the sum of",
                 words=["exchange_amount", "currency"], cols=12),
        ]),
        section("Drawn Under", fields=[
            text("value_received_1", "Value received \"drawn under\"", required=True, max=35),
            text("value_received_2", "Value received (line 2)", max=35),
            text("value_received_3", "Value received (line 3)", max=35),
        ] + ([
            text("credit_no", "Documentary credit no.", required=True, max=20),
            date("credit_dated", "Dated", required=True),
        ] if credit else [])),
        section("Drawee (To)", fields=[
            text("drawee_1", "To", required=True, max=35),
            text("drawee_2", "To (line 2)", max=35),
            text("drawee_3", "To (line 3)", max=35),
            text("drawee_4", "To (line 4)", max=35),
        ]),
        section("Drawer", fields=[
            text("drawer_1", "For and on behalf of (drawer)", required=True, max=35),
            text("drawer_2", "For and on behalf of (line 2)", required=True, max=35),
        ]),
        section("Authorised Signature(s)", signoff=True, note="INDORSEMENT: PAY TO THE ORDER OF DEMO BANK LTD.", fields=[
            text("signatory_name", "Name of authorised signatory (drawer)", max=35),
        ]),
    ]


FORM = {
    "title": "Bill of Exchange (Generic - Free Format)",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY. The first and second of exchange are printed from the same answers.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BE-01 · v1.0 · Nov 2026",
    "sections": bill_sections(),
}

DEFAULTS = {}

PDF_NAME = "Bill-of-Exchange.pdf"
