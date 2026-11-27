"""BILL OF EXCHANGE UNDER AN EXPORT DOCUMENTARY COLLECTION (Form BEOBC-01).

Build it:   python build.py bill_of_exchange_obc_form.py     -> out/Bill-of-Exchange-OBC.pdf

The bill of exchange that goes with the OBC application (obc_form.py). The old form filled it in from the OBC
answers; here it is its own form with the generic bill's questions and rules (bill_of_exchange_form.py), without a
documentary credit (a collection has none). "Value received" starts as "As per invoice", as on the old form.
"""
from bill_of_exchange_form import bill_sections

FORM = {
    "title": "Bill of Exchange (Export Documentary Collection)",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY. To go with your OBC application. The first and second of exchange are printed from the same answers.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BEOBC-01 · v1.0 · Nov 2026",
    "sections": bill_sections(credit=False),
}

DEFAULTS = {"value_received_1": "AS PER INVOICE"}

PDF_NAME = "Bill-of-Exchange-OBC.pdf"
