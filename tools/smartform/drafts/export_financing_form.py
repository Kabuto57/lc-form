"""Export Financing - Pre-shipment Financing on Open Account Basis / Sales Invoice Financing (Form EXP-01).

Build it:   python build.py export_financing_form.py     -> out/Export-Financing.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (93 questions, 17 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Export Financing - Pre-shipment Financing on Open Account Basis / Sales Invoice Financing",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form EXP-01 · v1.0 · Nov 2026",
    "sections": [
        section("Exportbcode", fields=[
            date("exportbcode_exportdate", "Date"),
        ]),
        section("Applicant", fields=[
            text("applicant_name", "Name", required=True, max=35),
            text("applicant_address1", "Address", required=True, max=35),
            text("applicant_address2", "Address (line 2)", max=35),
            text("applicant_address3", "Address (line 3)", max=35),
            text("applicant_contract_name", "Name", required=True, max=35),
            text("applicant_tel", "Contact number", required=True, max=15, format="phone"),
            text("applicant_fax", "Fax No.", max=15, format="phone"),
            radio("applicant_shipment", "Applicant's details", ["Pre-Shipment Financing against export Documentary Credit No.", "Pre-Shipment Financing against purchase order / export contract or pro-forma invoice from buyer / purchaser under Open Account basis", "Sales Invoice Financing"], required=True),
            text("shipment_credit_no", "Please tick box for financing required", requiredIf=when("applicant_shipment", "Pre-Shipment Financing against export Documentary Credit No."), max=16),
        ]),
        section("Third party", fields=[
            text("3_party_beneficiary_name", "Name", max=35),
            text("3_party_beneficiary_address1", "Address", max=35),
            text("3_party_beneficiary_address2", "Address (line 2)", max=35),
            text("3_party_beneficiary_address3", "Address (line 3)", max=35),
            text("buyer_bname", "Name", required=True, max=35),
            text("sup_details_name", "Name", max=35),
            text("sup_details_city", "City/Country", max=35),
            text("sup_details_address1", "Address", max=35),
            text("sup_details_address2", "Address (line 2)", max=35),
            text("sup_details_address3", "Address (line 3)", max=35),
            select("bill_amount_currency", "Currency", options=CURRENCIES, required=True),
            text("bill_amount_amount", "Amount", required=True, format="number"),
        ]),
        section("Financing", fields=[
            select("financing_finance_currency", "Financing Currency", options=CURRENCIES, required=True),
            text("financing_txtdays", "Financing Period (days)", required=True, max=3, format="number"),
            text("financing_contract_no_2", "Forward Contract No", max=35),
            text("financing_amount", "Financing Amount", required=True, format="number"),
            text("financing_currency", "Financing details"),
            text("financing_currency2", "Financing details (line 2)"),
        ]),
        section("Contract", fields=[
            text("fx_fxcontract_seq", "-", max=2, format="number"),
            text("fx_contract_no", "FX Contract Number.", max=8, format="number"),
            text("fx_currency", "FX Contract Number."),
            text("fx_amount", "FX Contract Number.", max=12, format="number"),
        ]),
        section("Purchase", fields=[
            radio("purchase_descrip", "Please select nature of underlying trade and provide description of goods/services", ["Sales of Services", "Sales of Goods"], required=True),
            text("purchase_services", "Please select nature of underlying trade and provide description of goods/services", requiredIf=when("purchase_descrip", "Sales of Services"), max=30),
            text("purchase_goods", "Please select nature of underlying trade and provide description of goods/services", requiredIf=[{"field": "purchase_descrip", "values": ["S"], "not": True}], max=30),
        ]),
        section("Description", fields=[
            text("description_description1", "Brief Description & Quantity of Goods", max=35),
            text("description_description2", "Brief Description & Quantity of Goods (line 2)", max=35),
            text("description_description3", "Brief Description & Quantity of Goods (line 3)", max=35),
            text("description_description4", "Brief Description & Quantity of Goods (line 4)", max=35),
            text("description_description5", "Brief Description & Quantity of Goods (line 5)", max=35),
        ]),
        section("Brief description", fields=[
            text("brief_description_description_description1", "Brief Description & Quantity of Goods", max=35),
            text("brief_description_description_description2", "Brief Description & Quantity of Goods (line 2)", max=35),
            text("brief_description_description_description3", "Brief Description & Quantity of Goods (line 3)", max=35),
            text("brief_description_description_description4", "Brief Description & Quantity of Goods (line 4)", max=35),
            text("brief_description_description_description5", "Brief Description & Quantity of Goods (line 5)", max=35),
            select("brief_description_financing_finance_currency", "Financing Currency", options=CURRENCIES),
            text("financing_days", "Financing Period (days)", max=3, format="number"),
            text("financing_contract_no", "Forward Contract No.", max=35),
        ]),
        section("Doc attached", fields=[
            long("row_documents_invoice", "Documents Attached"),
            long("row_documents_landing", "Documents Attached"),
            long("row_documents_air_bill", "Documents Attached"),
            long("row_documents_delivery", "Documents Attached"),
            long("row_documents_lcoriginal", "Documents Attached"),
            long("row_documents_lcamdt", "Documents Attached"),
            long("row_documents_input1", "Documents Attached (line 1)", max=20),
            long("row_documents_input2", "Documents Attached (line 2)", max=20),
            text("row_copies_input1", "Documents Attached (line 1)", max=3),
            text("row_copies_input2", "Documents Attached (line 2)", max=3),
            text("row_copies_input3", "Documents Attached (line 3)", max=3),
            text("row_copies_input4", "Documents Attached (line 4)", max=3),
            text("row_copies_input5", "Documents Attached (line 5)", max=3),
            text("row_copies_input6", "Documents Attached (line 6)", max=3),
            text("row_copies_input7", "Documents Attached (line 7)", max=3),
            text("row_copies_input8", "Documents Attached (line 8)", max=3),
        ]),
        section("Doc att", fields=[
            radio("doc_att_doc", "Documents Attached", ["Summary Listing of Invoices", "Invoice(s) and/or Evidence of Shipment/Delivery"], required=True),
        ]),
        section("Disbursement", fields=[
            radio("disbursement", "DISBURSEMENT INSTRUCTION:-", ["To credit our account number", "Others (specify)"], required=True),
            text("disbursement_credit_acc_no", "DISBURSEMENT INSTRUCTION:-", requiredIf=when("disbursement", "To credit our account number"), max=13, format="number"),
            text("disbursement_others1", "DISBURSEMENT INSTRUCTION:- (line 1)", requiredIf=when("disbursement", "Others (specify)"), max=100),
            text("disbursement_others2", "DISBURSEMENT INSTRUCTION:- (line 2)", activeIf=when("disbursement", "Others (specify)"), max=100),
            text("disbursement_others3", "DISBURSEMENT INSTRUCTION:- (line 3)", activeIf=when("disbursement", "Others (specify)"), max=100),
            select("disbursement_ccurrency", "DISBURSEMENT INSTRUCTION:-", options=CURRENCIES, requiredIf=when("disbursement", "To credit our account number")),
        ]),
        section("Debit comm", fields=[
            text("debit_comm_debit_acc", "Charges", max=13, format="number"),
            select("debit_comm_debit_currency", "Charges", options=CURRENCIES),
            text("details_fxcontract_no", "CF", max=8, format="number"),
            text("details_fxcontract_seq", "-", max=2, format="number"),
            select("details_currency1", "- (line 1)", options=CURRENCIES),
            text("details_account", "Currency", max=13, format="number"),
            select("details_currency2", "Currency (line 2)", options=CURRENCIES),
            text("details_debit_acc_no", "A/C No", max=13, format="number"),
            select("details_currency3", "A/C No (line 3)", options=CURRENCIES),
            text("details_interest_acc_no", "A/C No", max=13, format="number"),
            radio("debit_comm_debit", "With respect to any charges, please debit our account number", ["All charges", "Foreign currency charges"]),
            select("debit_comm_re_currency", "With respect to any repayment for this financing, please debit our account number", options=CURRENCIES, required=True),
            text("debit_comm_re_account", "With respect to any repayment for this financing, please debit our account number", required=True, max=13, format="number"),
            select("debit_comm_a_currency", "With respect to any charges, please debit our account number", options=CURRENCIES, requiredIf=when("debit_comm_debit", "All charges")),
            text("debit_comm_a_account", "With respect to any charges, please debit our account number", requiredIf=when("debit_comm_debit", "All charges"), max=13, format="number"),
            select("debit_comm_f_currency", "With respect to any charges, please debit our account number", options=CURRENCIES, requiredIf=when("debit_comm_debit", "Foreign currency charges")),
            text("debit_comm_f_account", "With respect to any charges, please debit our account number", requiredIf=when("debit_comm_debit", "Foreign currency charges"), max=13, format="number"),
            text("debit_comm_l_account", "Local Currency charges SGD", requiredIf=when("debit_comm_debit", "Foreign currency charges"), max=13, format="number"),
            long("others_others1", "Local Currency charges SGD (line 1)", max=575),
        ]),
        section("Bank charges", fields=[
            text("bank_charges_acc_no", "Please debit all charges to our account no.", max=17),
        ]),
        section("Settlement", fields=[
            text("settlement_acc_no", "On maturity of the financing, you are authorised to debit our account no.", max=17),
        ]),
        section("Signature", fields=[
            text("signature", "Without prejudice to the Application for Export Pre-Shipment & Open Account Post-Shipment Financing Terms and Conditions, if we do not indicate any specific account number, you are authorised to debit our account with you which is denominated in the same currency as the financing currency indicated in this Application."),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "Export-Financing.pdf"
PAGES = None
