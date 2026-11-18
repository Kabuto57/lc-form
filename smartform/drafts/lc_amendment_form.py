"""Amendment to Original Documentary Credit (Form LCA-01).

Build it:   python build.py lc_amendment_form.py     -> out/LC-Amendment.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (40 questions, 8 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Amendment to Original Documentary Credit",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form LCA-01 · v1.0 · Nov 2026",
    "sections": [
        section("Bank address", fields=[
            date("bank_address_date", "Date"),
        ]),
        section("Number", fields=[
            text("number_no", "Number", required=True),
            text("number_amend_no", "Amendment no.", max=2, format="number"),
        ]),
        section("Applicant", fields=[
            text("applicant_name", "Applicant's Name", required=True, max=35),
            text("applicant_address1", "Applicant's Address", max=35),
            text("applicant_address2", "Applicant's Address (line 2)", max=35),
            text("applicant_address3", "Applicant's Address (line 3)", max=35),
            text("applicant_contract_name", "Contact Person", required=True, max=35),
            text("applicant_tel", "Tel No", required=True, max=17, format="phone"),
            text("applicant_fax", "Fax No", required=True, max=15, format="phone"),
        ]),
        section("Beneficiary", fields=[
            text("beneficiary_name", "Beneficiary's Name", max=35),
            text("beneficiary_address1", "Beneficiary's Address", max=35),
            text("beneficiary_address2", "Beneficiary's Address (line 2)", max=35),
            text("beneficiary_address3", "Beneficiary's Address (line 3)", max=35),
        ]),
        section("Mode of advising", fields=[
            radio("mode_of_advising", "Please amend the abovementioned documentary credit by", ["SWIFT", "Registered Airmail", "Courier", "Collection at Counter"]),
        ]),
        section("Credit amount", fields=[
            text("credit_amount_amount1", "Amount", format="number"),
            select("credit_amount_currency2", "Amount (line 2)", options=CURRENCIES, requiredIf=ticked("credit_amount_amount")),
            text("credit_amount_amount2", "Amount (line 2)", requiredIf=ticked("credit_amount_amount"), format="number"),
            check("credit_amount_amount", "Amount of the DC"),
            radio("credit_amount_amount_2", "Please amend the abovementioned documentary credit by", ["increased by", "decreased by"], requiredIf=ticked("credit_amount_amount")),
            select("credit_amount_currency1", "Currency", options=CURRENCIES),
        ]),
        section("Date of expiry", fields=[
            date("date_of_expiry_date", "Currency", requiredIf=ticked("date_of_expiry_expiry_date")),
            check("date_of_expiry_expiry_date", "The expiry date of the DC is extended to"),
        ]),
        section("Shipment date", fields=[
            date("shipment_date_date", "Currency", requiredIf=ticked("shipment_date")),
            check("shipment_date", "The latest shipment date is extended to"),
        ]),
        section("Partialshipment", fields=[
            radio("partialshipment_partial_shipment_2", "Partialshipment_partial_shipment_2", ["allowed", "not allowed"], requiredIf=ticked("partialshipment_partial_shipment")),
            radio("partialshipment_transhipment_2", "Partialshipment_transhipment_2", ["allowed", "not allowed"], requiredIf=ticked("partialshipment_transhipment")),
            check("partialshipment_partial_shipment", "Partial Shipment is"),
            check("partialshipment_transhipment", "Transhipment is"),
            check("partialshipment_period", "Presentation period is amended to"),
            text("partialshipment_amend_no", "No", requiredIf=ticked("partialshipment_period"), max=2, format="number"),
        ]),
        section("Foot", fields=[
            long("other_attachement_goods_description", "Other amendments", max=700),
            radio("account_amendment_charges", "The amendment charge is for the account of", ["Beneficiary", "Applicant"], required=True),
            text("account_acc_no", "and to be debited to our account no.", requiredIf=[{"field": "account_amendment_charges", "values": ["Beneficiary"], "not": True}], max=17),
            text("account_fax_no", "Please fax DC copy to fax number", max=15, format="phone"),
            text("debit_margin_acc_no", "with you , if applicable.", max=17),
            text("debit_margin_amount", "Please also debit additional cash margin of", format="number"),
            select("debit_margin_currency", "Please also debit additional cash margin of", options=CURRENCIES),
            text("foot_signature", "Authorised Person(s) & Company's Stamp"),
        ]),
        section("Xfa", fields=[
            date("form1_lcadate", "Date", required=True),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "LC-Amendment.pdf"
PAGES = None
