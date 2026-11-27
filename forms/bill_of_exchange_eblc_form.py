"""BILL OF EXCHANGE UNDER AN EXPORT DOCUMENTARY CREDIT (Form BEEBLC-01).

Build it:   python build.py bill_of_exchange_eblc_form.py     -> out/Bill-of-Exchange-EBLC.pdf

The bill of exchange that goes with the EBLC application (eblc_form.py). The old form filled it in from the EBLC
answers; here it is its own form with the same questions and rules as the generic bill (bill_of_exchange_form.py).
"""
from bill_of_exchange_form import bill_sections

FORM = {
    "title": "Bill of Exchange (Export Documentary Credit)",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY. To go with your EBLC application. The first and second of exchange are printed from the same answers.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BEEBLC-01 · v1.0 · Nov 2026",
    "sections": bill_sections(),
}

DEFAULTS = {}

PDF_NAME = "Bill-of-Exchange-EBLC.pdf"
