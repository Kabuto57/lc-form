"""Handling / Financing of Documents Under Export Documentary Credit (Form EBLC-01).

Build it:   python build.py eblc_form.py     -> out/EBLC-Application.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (93 questions, 15 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Handling / Financing of Documents Under Export Documentary Credit",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form EBLC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Left", fields=[
            text("beneficiary_beneficiary_name", "Beneficiary Name", required=True, max=35),
            text("beneficiary_beneficiary_address1", "Beneficiary Address", required=True, max=35),
            text("beneficiary_txtbeneficiary_address2", "Beneficiary Address (line 2)", max=35),
            text("beneficiary_txtbeneficiary_address3", "Beneficiary Address (line 3)", max=35),
            text("beneficiary_credit_no", "Documentary Credit No", required=True, max=20),
        ]),
        section("Right", fields=[
            text("issue_bank_issuing_bank_name", "Issuing Bank Name", required=True, max=50),
            text("issue_bank_issuing_bank_name1", "Issuing Bank Name (line 1)", max=50),
            select("credit_amount_currency", "Currency", options=CURRENCIES, required=True),
            text("credit_amount_amount", "Amount", required=True, format="number"),
            date("right_dated", "Date of Issue", required=True),
        ]),
        section("Contact person", fields=[
            text("contact_person_name", "Name", required=True, max=35),
            text("contact_person_tel_no", "Tel No", required=True, max=17, format="phone"),
            text("contact_person_fax_no", "Fax No", required=True, max=15, format="phone"),
        ]),
        section("Reject", fields=[
            check("reject", "We REJECT Amendment No"),
            text("reject_2", "We REJECT Amendment No (line 2)", requiredIf=ticked("reject"), max=10),
        ]),
        section("Bank use", fields=[
            text("bank_use_draft_inv_no", "Draft / Invoice No", required=True, max=16),
        ]),
        section("Verssel", fields=[
            text("verssel_vessel_name", "Vessel Name", max=16),
            text("verssel_imono", "IMO No"),
        ]),
        section("Tenor", fields=[
            radio("tenor", "Tenor", ["Sight", "Term", "Date"]),
            text("tenor_term", "Tenor", requiredIf=when("tenor", "Term"), max=3, format="number"),
            text("tenor_days_after", "days", requiredIf=when("tenor", "Term")),
            date("tenor_tenor_date", "Tenor", requiredIf=when("tenor", "Date")),
            text("tenor_port_disch", "Port of Discharge / Airport of Destination", max=24),
            text("tenor_port_load", "Port of Loading / Airport of Departure", max=24),
            text("tenor_goods_desc", "Brief Description of Goods", max=30),
            date("tenor_dep_dated", "Departure Date", required=True),
            text("tenor_crno", "Transport Document number", max=16),
        ]),
        section("Row header", fields=[
            long("row_header_drafts", "Documents"),
            long("row_header_invoice", "Documents"),
            long("row_header_packing_list", "Documents"),
            long("row_header_weight_note", "Documents submitted: (Please indicate type and number of originals/copies)"),
            long("row_header_certof_origin", "Documents submitted: (Please indicate type and number of originals/copies)"),
            long("row_header_ins_policy", "Documents submitted: (Please indicate type and number of originals/copies)"),
            long("row_header_bl", "Documents submitted: (Please indicate type and number of originals/copies)"),
            long("row_header_airway_bills", "Documents submitted: (Please indicate type and number of originals/copies)"),
            long("row_header_ben_cert", "Documents submitted: (Please indicate type and number of originals/copies)"),
            long("row_header_input1", "Documents submitted: (Please indicate type and number of originals/copies) (line 1)"),
            long("row_header_input2", "Documents submitted: (Please indicate type and number of originals/copies) (line 2)"),
            long("row_header_input3", "Documents submitted: (Please indicate type and number of originals/copies) (line 3)"),
            long("row_header_input4", "Documents submitted: (Please indicate type and number of originals/copies) (line 4)"),
            long("row_header_input5", "Documents submitted: (Please indicate type and number of originals/copies) (line 5)"),
        ]),
        section("Row original", fields=[
            text("row_original_drafts", "No. of Original(s)", max=3),
            text("row_original_invoice", "No. of Original(s)", max=3),
            text("row_original_packing_list", "No. of Original(s)", max=3),
            text("row_original_weight_note", "No. of Original(s)", max=3),
            text("row_original_certof_origin", "No. of Original(s)", max=3),
            text("row_original_inspolicy", "No. of Original(s)", max=3),
            text("row_original_bl", "No. of Original(s)", max=3),
            text("row_original_airway_bills", "No. of Original(s)", max=3),
            text("row_original_ben_cert", "No. of Original(s)", max=3),
            text("row_original_input1", "No. of Original(s) (line 1)", max=3),
            text("row_original_input2", "No. of Original(s) (line 2)", max=3),
            text("row_original_input3", "No. of Original(s) (line 3)", max=3),
            text("row_original_input4", "No. of Original(s) (line 4)", max=3),
            text("row_original_input5", "No. of Original(s) (line 5)", max=3),
        ]),
        section("Row copies", fields=[
            text("row_copies_drafts", "No. of Copy(ies)", max=3),
            text("row_copies_invoice", "No. of Copy(ies)", max=3),
            text("row_copies_packing_list", "No. of Copy(ies)", max=3),
            text("row_copies_weight_note", "No. of Copy(ies)", max=3),
            text("row_copies_certof_origin", "No. of Copy(ies)", max=3),
            text("row_copies_ins_policy", "No. of Copy(ies)", max=3),
            text("row_copies_bl", "No. of Copy(ies)", max=3),
            text("row_copies_airway_bills", "No. of Copy(ies)", max=3),
            text("row_copies_ben_cert", "No. of Copy(ies)", max=3),
            text("row_copies_input1", "No. of Copy(ies) (line 1)", max=3),
            text("row_copies_input2", "No. of Copy(ies) (line 2)", max=3),
            text("row_copies_input3", "No. of Copy(ies) (line 3)", max=3),
            text("row_copies_input4", "No. of Copy(ies) (line 4)", max=3),
            text("row_copies_input5", "No. of Copy(ies) (line 5)", max=3),
        ]),
        section("Details", fields=[
            select("bank", "Original DC and amendments (if any) are", options=["attached", "with Demo Bank", "with other bank"], required=True),
            text("bank_2", "Original DC and amendments (if any) are (line 2)", requiredIf=when("bank", "with other bank"), max=35),
        ]),
        section("Checking of documents", fields=[
            radio("checking_of_documents", "Checking of Documents", ["Do not check the Documents and send the unchecked Documents to the Issuing Bank", "Check the Documents and send them to the Issuing Bank per Documentary Credit terms"]),
        ]),
        section("Financing", fields=[
            radio("subfrmfinancing_financing", "Settlement Instructions", ["We do not need financing. Please PAY US upon receipt of funds.", "We request your financing, discounting and/or negotiation in respect of the Documents under the Documentary Credit, in such currency acceptable to you (the"]),
            text("financing_rate", "Financing Rate", activeIf=when("subfrmfinancing_financing", "We request your financing, discounting and/or negotiation in respect of the Documents under the Documentary Credit, in such currency acceptable to you (the"), max=7, format="amount"),
            radio("options_request1", "Tick one: (*)", ["With Full Recourse", "With No Recourse (#)"], activeIf=when("subfrmfinancing_financing", "We request your financing, discounting and/or negotiation in respect of the Documents under the Documentary Credit, in such currency acceptable to you (the")),
            radio("options_request2", "Tick one: (**)", ["After the Documents have been accepted by the issuing bank or confirming bank (if any)", "Prior to acceptance of the Documents by the Issuing"], activeIf=when("subfrmfinancing_financing", "We request your financing, discounting and/or negotiation in respect of the Documents under the Documentary Credit, in such currency acceptable to you (the")),
            select("options_currency", "Financing Currency", options=CURRENCIES, activeIf=when("subfrmfinancing_financing", "We request your financing, discounting and/or negotiation in respect of the Documents under the Documentary Credit, in such currency acceptable to you (the")),
            radio("finance_details2_options_request1", "Tick one: (***)", ["Demo Bank manages foreign exchange rate, currency convertibility and/or transferability risks", "Demo Bank enters Hedging Transaction with us", "Without a Hedging Transaction with a Haircut Percentage of"], activeIf=when("subfrmfinancing_financing", "We request your financing, discounting and/or negotiation in respect of the Documents under the Documentary Credit, in such currency acceptable to you (the")),
            text("options_rate", "OR", requiredIf=when("finance_details2_options_request1", "Without a Hedging Transaction with a Haircut Percentage of"), max=3, format="number"),
            radio("finance_details2_options_request2", "Tick one: (****)", ["Deliverable forward foreign exchange transaction", "Non-deliverable forward foreign exchange transaction", "Currency option transaction"], activeIf=when("subfrmfinancing_financing", "We request your financing, discounting and/or negotiation in respect of the Documents under the Documentary Credit, in such currency acceptable to you (the")),
        ]),
        section("Eblc2", fields=[
            radio("other_instructions_proceed_options", "Please pay the financing/discounting/negotiation proceeds in the following manner", ["after deducting the Financing Interest due to you /", "without deducting the"], required=True),
            check("other_instructions_credit_fund", "Credit the funds to our account no"),
            text("eblc2_other_instructions_credit_fund", "Financing interest due to you", requiredIf=ticked("other_instructions_credit_fund"), max=17),
            check("other_instructions_remit_the_funds", "Remit the funds to"),
            text("eblc2_other_instructions_remit_the_funds", "Financing interest due to you", requiredIf=ticked("other_instructions_remit_the_funds"), max=100),
            check("other_instructions_use_the_funds", "Use the funds to repay"),
            text("eblc2_other_instructions_use_the_funds", "Funds", requiredIf=ticked("other_instructions_use_the_funds"), max=35),
            check("other_instructions_use_fx", "Use FX contract Ref"),
            text("eblc2_other_instructions_use_fx", "Fx", requiredIf=ticked("other_instructions_use_fx"), max=20),
            long("other_instructions_others1", "Fx (line 1)"),
            text("others_signature", "Authorised Person(s) & Company Stamp"),
        ]),
        section("Xfa", fields=[
            date("form1_eblcdate", "Date", required=True),
            text("form1_eblc_bank_use", "Use", max=50),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "EBLC-Application.pdf"
PAGES = None
