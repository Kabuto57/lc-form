"""Export Documentary Collection / Financing of Bills under Export Documentary Collection (Form OBC-01).

Build it:   python build.py obc_form.py     -> out/OBC-Application.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (88 questions, 15 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Export Documentary Collection / Financing of Bills under Export Documentary Collection",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form OBC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Drawer", fields=[
            text("name_and_address_name", "Name", required=True, max=35),
            text("name_and_address_address1", "Address", required=True, max=35),
            text("name_and_address_address2", "Address (line 2)", max=35),
            text("name_and_address_address3", "Address (line 3)", max=35),
            text("drawer_contact_person", "Contact Person", required=True, max=35),
            text("drawer_tel", "Tel", required=True, max=17, format="phone"),
        ]),
        section("Currency amount", fields=[
            select("currency_amount_currency", "Currency", options=CURRENCIES, required=True),
            text("currency_amount_amount", "Amount", required=True, format="number"),
        ]),
        section("Drawee bank", fields=[
            text("drawee_bank_name", "Name", required=True, max=35),
            text("drawee_bank_address1", "Address", required=True, max=35),
            text("drawee_bank_address2", "Address (line 2)", max=35),
            text("drawee_bank_address3", "Address (line 3)", max=35),
        ]),
        section("Drawee", fields=[
            text("drawee", "Drawee / Buyer", required=True, max=35),
        ]),
        section("Deliver document against", fields=[
            check("deliver_document_against_payment", "Payment", requiredIf=[{"field": "deliver_document_against_acceptance", "values": ["on"], "not": True}]),
            check("deliver_document_against_acceptance", "Acceptance", requiredIf=[{"field": "deliver_document_against_payment", "values": ["on"], "not": True}]),
        ]),
        section("Invoice", fields=[
            text("invoice", "Invoice / Reference No", required=True, max=16),
        ]),
        section("Tenor", fields=[
            radio("tenor", "Tenor", ["Sight", "Term"], required=True),
            text("tenor_term", "Deliver Documents Against", requiredIf=when("tenor", "Term"), max=3),
            text("tenor_days_after", "days", requiredIf=when("tenor", "Term"), max=35),
        ]),
        section("Port", fields=[
            text("port_vessel_no", "Vessel/ Flight No", max=16),
            text("port_crno", "Transport Document number", max=16),
            text("port_goods_desc", "Brief Description of Goods", max=30),
            date("port_dep_dated", "Departure Date", required=True),
            text("port_port_disch", "Port of Discharge / Airport of Destination", max=24),
            text("port_port_load", "Port of Loading / Airport of Departure", max=24),
        ]),
        section("Row documents", fields=[
            long("row_documents_drafts", "Documents"),
            long("row_documents_invoice", "Documents"),
            long("row_documents_packing_list", "Documents"),
            long("row_documents_certof_origin", "Documents"),
            long("row_documents_insurance_policy", "Documents"),
            long("row_documents_bloriginals", "Documents"),
            long("row_documents_blnn", "Documents"),
            long("row_documents_weight_note", "Documents"),
            long("row_documents_airway_bills", "Documents"),
            long("row_documents_ben_cert", "Documents"),
            long("row_documents_input1", "Documents (line 1)"),
            long("row_documents_input2", "Documents (line 2)"),
            long("row_documents_input3", "Documents (line 3)"),
            long("row_documents_in_input4", "Documents (line 4)"),
        ]),
        section("Row original", fields=[
            text("row_original_drafts", "No. of Original(s)", max=3),
            text("row_original_invoice", "No. of Original(s)", max=3),
            text("row_original_packing_list", "No. of Original(s)", max=3),
            text("row_original_certof_origin", "No. of Original(s)", max=3),
            text("row_original_insurance_policy", "No. of Original(s)", max=3),
            text("row_original_bloriginals", "No. of Original(s)", max=3),
            text("row_original_blnn", "No. of Original(s)", max=3),
            text("row_original_weight_note", "No. of Original(s)", max=3),
            text("row_original_airway_bills", "No. of Original(s)", max=3),
            text("row_original_ben_cert", "No. of Original(s)", max=3),
            text("row_original_input2", "No. of Original(s) (line 2)", max=3),
            text("row_original_input3", "No. of Original(s) (line 3)", max=3),
            text("row_original_input4", "No. of Original(s) (line 4)", max=3),
            text("row_original_input5", "No. of Original(s) (line 5)", max=3),
        ]),
        section("Row copies", fields=[
            text("row_copies_drafts", "No. of Copy(ies)", max=3),
            text("row_copies_invoice", "No. of Copy(ies)", max=3),
            text("row_copies_packing_list", "No. of Copy(ies)", max=3),
            text("row_copies_certof_origin", "No. of Copy(ies)", max=3),
            text("row_copies_insurance_policy", "No. of Copy(ies)", max=3),
            text("row_copies_bloriginals", "No. of Copy(ies)", max=3),
            text("row_copies_blnn", "No. of Copy(ies)", max=3),
            text("row_copies_weight_note", "No. of Copy(ies)", max=3),
            text("row_copies_airway_bills", "No. of Copy(ies)", max=3),
            text("row_copies_ben_cert", "No. of Copy(ies)", max=3),
            text("row_copies_input1", "No. of Copy(ies) (line 1)", max=3),
            text("row_copies_input2", "No. of Copy(ies) (line 2)", max=3),
            text("row_copies_input3", "No. of Copy(ies) (line 3)", max=3),
            text("row_copies_input4", "No. of Copy(ies) (line 4)", max=3),
        ]),
        section("Charges drawee", fields=[
            check("charges_drawee_collection", "Collect your charges from Drawee."),
        ]),
        section("Interest drawee", fields=[
            check("interest_drawee", "Collect interest from Drawee at"),
            text("interest_drawee_at", "% p.a. from", requiredIf=ticked("interest_drawee"), max=2, format="number"),
            text("interest_drawee_from", "( interest start date) to", requiredIf=ticked("interest_drawee"), max=35),
            text("interest_drawee_to", "To", activeIf=ticked("interest_drawee"), max=35),
        ]),
        section("Waive", fields=[
            check("waive", "Do not waive interest and / or collection charges if refused"),
        ]),
        section("Advise", fields=[
            check("advise", "Advise non-acceptance / non-payment by telex / SWIFT."),
        ]),
        section("Protest", fields=[
            check("protest", "Protest non-acceptance / non-payment."),
        ]),
        section("Documents", fields=[
            check("documents", "Documents to be sent to drawee's banker by courier service in one(1)"),
        ]),
        section("Finance", fields=[
            check("finance", "Please finance us for"),
            text("finance_for", "% of the collection amount", requiredIf=ticked("finance"), max=3, format="number"),
        ]),
        section("Forward documents", fields=[
            check("forward_documents", "Please forward documents to drawee's bank regardless of whether"),
        ]),
        section("Hold documents", fields=[
            check("hold_documents", "Please hold documents until financing of the collection has been"),
        ]),
        section("Credit financing", fields=[
            check("credit_financing", "Please credit financing / payment proceeds to our account"),
            text("credit_financing_no", "with you", requiredIf=ticked("credit_financing"), max=17),
        ]),
        section("Fxcontract", fields=[
            check("fxcontract_fx", "Please use FX Contract Ref."),
            text("fxcontract_ref", "Ref", requiredIf=ticked("fxcontract_fx"), max=20),
        ]),
        section("Other special instructions", fields=[
            check("other_special_instructions", "Other Special Instructions"),
            long("other_special_instructions_2", "Other Special Instructions (line 2)", requiredIf=ticked("other_special_instructions")),
        ]),
        section("Signature", fields=[
            text("signature_text_field1", "Authorised Person(s) & Company Stamp"),
        ]),
        section("Xfa", fields=[
            date("form1_obcdate", "Date", required=True),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "OBC-Application.pdf"
PAGES = None
