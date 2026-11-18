"""IMPORT FINANCING (Form DBRP-01).

Build it:   python build.py import_financing_form.py     -> out/Import-Financing.pdf

Redrawn from the old trade smart form's Import Financing application: the same questions, wording and order, and the
same rules (mandatory, mandatory-when, locked-until, formats, SWIFT / FX contract / account number checks). Parts the
old form kept hidden and never showed are left out; its FX contract rows ("add a row") are 3 fixed rows here.
Every option a form file can use is listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import account_length, answered, date, long, radio, section, select, text, when
from lc_form import COUNTRIES, CURRENCIES

TYPES = ["Post-shipment Financing on open account basis / Purchase Invoice Financing",
         "Pre-shipment Financing against purchase order / import contract or pro-forma invoice from seller / supplier",
         "Freight Loan Financing"]
REMIT, CREDIT = "To remit proceeds directly to Beneficiary", "To credit our account number with you (by arrangement only)"
TT, CO = "Telegraphic Transfer", "Cashier's Order / Demand Draft"
ALL, FOREIGN = "All charges", "Foreign currency charges"


def fx_rows(n=3):
    rows = []
    for i in range(1, n + 1):
        rows += [text(f"fx_contract_no_{i}", f"FX contract no. {i}: CF", max=8, format="fx8", cols=4),
                 text(f"fx_contract_seq_{i}", "Sequence", max=2, format="fx2", cols=2),
                 select(f"fx_currency_{i}", "Currency", options=CURRENCIES, cols=3),
                 text(f"fx_amount_{i}", "Amount to be used", max=15, format="amount", cols=3)]
    return rows


FORM = {
    "title": "Import Financing",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form DBRP-01 · v1.0 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
        ]),
        section("Applicant's Details", fields=[
            text("applicant_name", "Name", required=True, max=35),
            text("applicant_address_1", "Address", required=True, max=35),
            text("applicant_address_2", "Address (line 2)", max=35),
            text("applicant_address_3", "Address (line 3)", max=35),
            text("contact_name", "Contact party for this application & confirmation of FX rate: name", required=True, max=35),
            text("contact_tel", "Contact number", required=True, max=17, format="phone"),
            text("contact_fax", "Fax number", max=15, format="phone"),
        ]),
        section("Financing Type", width="full", fields=[
            radio("financing_type", "Please select financing type", TYPES, required=True),
        ]),
        section("For the Benefit of a 3rd Party", fields=[
            text("third_party_name", "Name", max=35),
            text("third_party_address_1", "Address", max=35),
            text("third_party_address_2", "Address (line 2)", max=35),
            text("third_party_address_3", "Address (line 3)", max=35),
        ]),
        section("Supplier's Details", fields=[
            text("supplier_name", "Name", required=True, max=35),
            text("supplier_address_1", "Address", required=True, max=35),
            text("supplier_address_2", "Address (line 2)", max=35),
            text("supplier_address_3", "Address (line 3)", max=35),
            text("supplier_city_country", "City / country", max=35),
        ]),
        section("Invoice Value and Financing", fields=[
            select("currency", "Invoice value: currency", options=CURRENCIES, required=True),
            text("amount", "Invoice value: amount", required=True, max=15, format="amount"),
            select("financing_currency", "Financing currency", options=CURRENCIES, required=True),
            text("financing_days", "Financing period (days)", required=True, max=3, format="number"),
            select("financing_amount_currency", "Financing amount: currency", options=CURRENCIES),
            text("financing_amount", "Financing amount", required=True, max=15, format="amount"),
            date("financing_value_date", "Financing value date"),
        ]),
        section("FX Contracts", width="full", note="FX contract number: 8 digits; sequence: 2 digits (e.g. 01).", fields=fx_rows()),
        section("Underlying Trade", width="full", fields=[
            radio("trade_nature", "Please select nature of underlying trade and provide description of goods / services", ["Purchase of Services", "Purchase of Goods"], required=True),
            text("services_description", "Description of services", requiredIf=when("trade_nature", "Purchase of Services"), max=30),
            text("goods_description", "Description of goods", requiredIf=when("trade_nature", "Purchase of Goods"), max=30),
            radio("documents_attached", "Documents attached", ["Summary Listing of Invoices", "Invoice(s) and/or Evidence of Shipment / Delivery"], required=True),
        ]),
        section("Disbursement Instruction", width="full", fields=[
            radio("disbursement", "Disbursement", [REMIT, CREDIT], requiredIf=answered("financing_type")),
            radio("remit_method", "Remit by", [TT, CO], requiredIf=when("disbursement", REMIT)),
            radio("supplier_is_beneficiary", "Supplier is same as beneficiary", ["Yes", "No"], requiredIf=when("disbursement", REMIT)),
            text("beneficiary_name", "Name of beneficiary", requiredIf=when("disbursement", REMIT), max=70),
            text("beneficiary_name_2", "Name of beneficiary (line 2)", activeIf=when("disbursement", REMIT), max=70),
            text("beneficiary_address_1", "Address", requiredIf=when("disbursement", REMIT), max=70),
            text("beneficiary_address_2", "Address (line 2)", activeIf=when("disbursement", REMIT), max=70),
            select("beneficiary_country", "Country", options=COUNTRIES, requiredIf=when("disbursement", REMIT)),
            text("beneficiary_postal_code", "Postal code", activeIf=when("disbursement", REMIT), max=16),
            text("beneficiary_town", "Town", requiredIf=when("disbursement", REMIT), max=35),
            text("beneficiary_account_no", "Account number", requiredIf=when("remit_method", TT), max=34),
            text("beneficiary_reference", "Reference number", requiredIf=when("disbursement", REMIT), max=16),
            text("beneficiary_bank_name", "Beneficiary's bank: name", requiredIf=when("remit_method", TT), max=35),
            text("beneficiary_bank_address_1", "Beneficiary's bank: address", activeIf=when("disbursement", REMIT), max=35),
            text("beneficiary_bank_address_2", "Beneficiary's bank: address (line 2)", activeIf=when("disbursement", REMIT), max=35),
            text("beneficiary_bank_city", "Beneficiary's bank: city / country", activeIf=when("disbursement", REMIT), max=35),
            text("beneficiary_bank_swift", "Beneficiary's bank: SWIFT code", activeIf=when("disbursement", REMIT), max=11, format="swift"),
            text("correspondent_bank_name", "Name of correspondent bank", activeIf=when("disbursement", REMIT), max=35),
            text("correspondent_bank_address", "Correspondent bank: address", activeIf=when("disbursement", REMIT), max=35),
            text("correspondent_bank_swift", "Correspondent bank SWIFT code", activeIf=when("disbursement", REMIT), max=11, format="swift"),
            radio("remittance_charges", "Charges", ["SHA (we pay Demo Bank charges, supplier pays their bank's charges)", "OUR (we pay all charges)",
                  "BEN (supplier pays all charges)"], activeIf=when("disbursement", REMIT)),
            text("credit_account_no", "To credit our account number", requiredIf=when("disbursement", CREDIT), max=13, format="account"),
            text("other_instructions_1", "Others (specify)", max=100),
            text("other_instructions_2", "Others (line 2)", max=100),
        ]),
        section("Settlement Instruction", width="full", fields=[
            radio("charges_debit", "With respect to any charges, please debit our account number", [ALL, FOREIGN]),
            select("all_charges_currency", "All charges: currency", options=CURRENCIES, requiredIf=when("charges_debit", ALL)),
            text("all_charges_account", "All charges: account no.", requiredIf=when("charges_debit", ALL), max=13, format="account"),
            select("foreign_charges_currency", "Foreign currency charges: currency", options=CURRENCIES, requiredIf=when("charges_debit", FOREIGN)),
            text("foreign_charges_account", "Foreign currency charges: account no.", requiredIf=when("charges_debit", FOREIGN), max=13, format="account"),
            text("local_charges_account", "Local currency charges SGD: account no.", requiredIf=when("charges_debit", FOREIGN), max=13, format="account"),
            select("repayment_currency", "With respect to any repayment for this financing, please debit our account: currency", options=CURRENCIES, required=True),
            text("repayment_account", "Repayment: account no.", required=True, max=13, format="account"),
        ]),
        section("Authorised Signature(s)", signoff=True, note="In consideration of Demo Bank Ltd granting to us the financing as indicated above, we agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules and Trade Services Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them. We confirm that all necessary documents evidencing the transaction as required by you are enclosed herewith. We further confirm that we agree to each declaration of trust and trust receipt set out in Clauses 10.5 and 11 of the Trade Services Schedule relating to this Trade Service (if any) or any other Trade Service, and whether such Trade Services are provided to us before, on or after the date of this Form.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        account_length("credit_account_no", None, {"*": [10, 13]}, "Invalid account no."),
        account_length("all_charges_account", "all_charges_currency", {"SGD": [], "*": [10, 13]}, "Invalid account no."),
        account_length("foreign_charges_account", "foreign_charges_currency", {"SGD": [], "*": [10, 13]}, "Invalid account no."),
        account_length("local_charges_account", None, {"*": [10, 11, 12, 13]}, "Invalid account no."),
        account_length("repayment_account", "repayment_currency", {"SGD": [], "*": [10, 13]}, "Invalid account no."),
    ],
}

DEFAULTS = {"trade_nature": "Purchase of Goods"}

PDF_NAME = "Import-Financing.pdf"
PAGES = None
