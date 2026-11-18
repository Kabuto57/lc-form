"""AMENDMENT TO ORIGINAL DOCUMENTARY CREDIT (Form LCA-01).

Build it:   python build.py lc_amendment_form.py     -> out/LC-Amendment.pdf

Redrawn from the old trade smart form's LC amendment: the same questions, wording and order, and the same rules
(tick an amendment and its details become mandatory; expiry not before latest shipment; the 12-digit LC number).
Parts the old form kept hidden and never showed (previous amount, cash margin, fax copy) are left out.
Every option a form file can use is listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import check, date, long, not_before, radio, section, select, text, ticked, when
from lc_form import CURRENCIES

FORM = {
    "title": "Amendment to Original Documentary Credit",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form LCA-01 · v1.0 · Nov 2026",
    "sections": [
        section("Documentary Credit", fields=[
            date("application_date", "Date", required=True),
            text("lc_number", "Our documentary credit no. (e.g. 553010012345)", required=True, max=12, format="ref12"),
            text("amendment_no", "Amendment no.", max=2, format="number"),
        ]),
        section("Applicant", fields=[
            text("applicant_name", "Applicant's name", required=True, max=35),
            text("applicant_address_1", "Applicant's address", max=35),
            text("applicant_address_2", "Applicant's address (line 2)", max=35),
            text("applicant_address_3", "Applicant's address (line 3)", max=35),
            text("contact_name", "Contact person", required=True, max=35),
            text("contact_tel", "Tel no.", required=True, max=17, format="phone"),
            text("contact_fax", "Fax no.", required=True, max=15, format="phone"),
        ]),
        section("Beneficiary", fields=[
            text("beneficiary_name", "Beneficiary's name", max=35),
            text("beneficiary_address_1", "Beneficiary's address", max=35),
            text("beneficiary_address_2", "Beneficiary's address (line 2)", max=35),
            text("beneficiary_address_3", "Beneficiary's address (line 3)", max=35),
        ]),
        section("Mode of Advising", fields=[
            radio("mode_of_advising", "Please amend the abovementioned documentary credit by", ["SWIFT", "Registered Airmail", "Courier", "Collection at Counter"]),
        ]),
        section("Amendments", note="Tick each amendment you need; its details then become mandatory.", fields=[
            check("amend_amount", "Amount of the DC"),
            radio("amount_change", "The amount is", ["increased by", "decreased by"], requiredIf=ticked("amend_amount")),
            select("amount_change_currency", "Currency", options=CURRENCIES, requiredIf=ticked("amend_amount")),
            text("amount_change_amount", "Amount", requiredIf=ticked("amend_amount"), max=15, format="amount"),
            check("amend_expiry_date", "The expiry date of the DC is extended to"),
            date("expiry_date", "New expiry date", requiredIf=ticked("amend_expiry_date")),
            check("amend_shipment_date", "The latest shipment date is extended to"),
            date("latest_shipment_date", "New latest shipment date", requiredIf=ticked("amend_shipment_date")),
            check("amend_partial_shipment", "Partial shipment is"),
            radio("partial_shipment", "Partial shipment", ["allowed", "not allowed"], requiredIf=ticked("amend_partial_shipment")),
            check("amend_transhipment", "Transhipment is"),
            radio("transhipment", "Transhipment", ["allowed", "not allowed"], requiredIf=ticked("amend_transhipment")),
            check("amend_presentation_period", "Presentation period is amended to"),
            text("presentation_days", "Presentation period (days)", requiredIf=ticked("amend_presentation_period"), max=2, format="number"),
            long("other_amendments", "Other amendments", max=700),
        ]),
        section("Charges", fields=[
            radio("amendment_charges", "The amendment charge is for the account of", ["Beneficiary", "Applicant"], required=True),
            text("charges_account", "and to be debited to our account no.", requiredIf=when("amendment_charges", "Applicant"), max=17, format="account"),
        ]),
        section("Authorised Signature(s)", signoff=True, note="We request you to amend the DC as set out above. We acknowledge that all amendments will be subject to acceptance by the confirming bank (if any) and the beneficiary. All other terms and conditions of the DC remain in full force and effect. This application shall be subject to the version of the ICC Uniform Customs and Practice for Documentary Credits, as indicated in the DC. We agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules and Trade Services Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them. We further confirm that we agree to each declaration of trust and trust receipt set out in Clauses 10.5 and 11 of the Trade Services Schedule relating to this Trade Service (if any) or any other Trade Service, and whether such Trade Services are provided to us before, on or after the date of this Form.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        not_before("expiry_date", "latest_shipment_date", "Expiry date cannot be earlier than latest shipment date."),
    ],
}

DEFAULTS = {}

PDF_NAME = "LC-Amendment.pdf"
PAGES = None
