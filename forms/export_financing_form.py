"""EXPORT FINANCING - PRE-SHIPMENT FINANCING ON OPEN ACCOUNT BASIS / SALES INVOICE FINANCING (Form EXP-01).

Build it:   python build.py export_financing_form.py     -> out/Export-Financing.pdf

Redrawn from the old trade smart form's Export Financing application: the same questions, wording and order, and the
same rules (mandatory, mandatory-when, locked-until, formats, LC / FX contract / account number checks). Parts the old
form kept hidden and never showed are left out; its buyer and FX contract rows ("add a row") are 3 fixed rows here.
Every option a form file can use is listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import account_length, date, long, radio, section, select, text, when
from lc_form import CURRENCIES

TYPES = ["Pre-Shipment Financing against export Documentary Credit No.",
         "Pre-Shipment Financing against purchase order / export contract or pro-forma invoice from buyer / purchaser under Open Account basis",
         "Sales Invoice Financing"]
CREDIT, OTHERS = "To credit our account number with you", "Others (specify)"
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
    "title": "Application for Export Financing - Pre-shipment Financing on Open Account Basis / Sales Invoice Financing",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY. To: Demo Bank Ltd, Trade Services, Singapore.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form EXP-01 · v1.0 · Nov 2026",
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
            text("contact_fax", "Fax no.", max=15, format="phone"),
        ]),
        section("Financing Required", width="full", fields=[
            radio("financing_type", "Please tick box for financing required", TYPES, required=True),
            text("credit_no", "Export documentary credit no. (e.g. 553010012345)", requiredIf=when("financing_type", TYPES[0]), max=12, format="ref12"),
        ]),
        section("For the Benefit of a 3rd Party", fields=[
            text("third_party_name", "Name", max=35),
            text("third_party_address_1", "Address", max=35),
            text("third_party_address_2", "Address (line 2)", max=35),
            text("third_party_address_3", "Address (line 3)", max=35),
        ]),
        section("Buyer's Details", fields=[
            text("buyer_name_1", "Buyer's name", required=True, max=35),
            text("buyer_name_2", "Buyer's name (2)", max=35),
            text("buyer_name_3", "Buyer's name (3)", max=35),
        ]),
        section("Invoice Value and Financing", fields=[
            select("currency", "Invoice value: currency", options=CURRENCIES, required=True),
            text("amount", "Invoice value: amount", required=True, max=15, format="amount"),
            select("financing_currency", "Financing currency", options=CURRENCIES, required=True),
            text("financing_days", "Financing period (days)", required=True, max=3, format="number"),
            select("financing_amount_currency", "Financing amount: currency", options=CURRENCIES),
            text("financing_amount", "Financing amount", required=True, max=15, format="amount"),
        ]),
        section("FX Contracts", width="full", note="FX contract number: 8 digits; sequence: 2 digits (e.g. 01).", fields=fx_rows()),
        section("Underlying Trade", width="full", fields=[
            radio("trade_nature", "Please select nature of underlying trade and provide description of goods / services", ["Sales of Services", "Sales of Goods"], required=True),
            text("services_description", "Description of services", requiredIf=when("trade_nature", "Sales of Services"), max=30),
            text("goods_description", "Description of goods", requiredIf=when("trade_nature", "Sales of Goods"), max=30),
            radio("documents_attached", "Documents attached", ["Summary Listing of Invoices", "Invoice(s) and/or Evidence of Shipment / Delivery"], required=True),
        ]),
        section("Disbursement Instruction", width="full", fields=[
            radio("disbursement", "Disbursement", [CREDIT, OTHERS], required=True),
            select("credit_account_currency", "Account currency", options=CURRENCIES, requiredIf=when("disbursement", CREDIT)),
            text("credit_account_no", "Account number", requiredIf=when("disbursement", CREDIT), max=13, format="account"),
            text("other_disbursement_1", "Others (specify)", requiredIf=when("disbursement", OTHERS), max=100),
            text("other_disbursement_2", "Others (line 2)", activeIf=when("disbursement", OTHERS), max=100),
            text("other_disbursement_3", "Others (line 3)", activeIf=when("disbursement", OTHERS), max=100),
        ]),
        section("Settlement Instructions", width="full", fields=[
            radio("charges_debit", "Charges: with respect to any charges, please debit our account number", [ALL, FOREIGN]),
            select("all_charges_currency", "All charges: currency", options=CURRENCIES, requiredIf=when("charges_debit", ALL)),
            text("all_charges_account", "All charges: account no.", requiredIf=when("charges_debit", ALL), max=13, format="account"),
            select("foreign_charges_currency", "Foreign currency charges: currency", options=CURRENCIES, requiredIf=when("charges_debit", FOREIGN)),
            text("foreign_charges_account", "Foreign currency charges: account no.", requiredIf=when("charges_debit", FOREIGN), max=13, format="account"),
            text("local_charges_account", "Local currency charges SGD: account no.", requiredIf=when("charges_debit", FOREIGN), max=13, format="account"),
            select("repayment_currency", "With respect to any repayment for this financing, please debit our account: currency", options=CURRENCIES, required=True),
            text("repayment_account", "Repayment: account no.", required=True, max=13, format="account"),
            long("other_instructions", "Other instructions (if any)", max=300),
        ]),
        section("Authorised Signature(s)", signoff=True, note="We confirm that all necessary documents evidencing the transaction as required by you are enclosed herewith. We agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules and Trade Services Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them. We further confirm that we agree to each declaration of trust and trust receipt set out in Clauses 10.5 and 11 of the Trade Services Schedule relating to this Trade Service (if any) or any other Trade Service, and whether such Trade Services are provided to us before, on or after the date of this Form.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        account_length("credit_account_no", "credit_account_currency", {"SGD": [], "*": [10, 13]}, "Invalid account no."),
        account_length("all_charges_account", "all_charges_currency", {"SGD": [], "*": [10, 13]}, "Invalid account no."),
        account_length("foreign_charges_account", "foreign_charges_currency", {"SGD": [], "*": [10, 13]}, "Invalid account no."),
        account_length("local_charges_account", None, {"*": [10, 11, 12, 13]}, "Invalid account no."),
        account_length("repayment_account", "repayment_currency", {"SGD": [], "*": [10, 13]}, "Invalid account no."),
    ],
}

DEFAULTS = {"trade_nature": "Sales of Goods"}

PDF_NAME = "Export-Financing.pdf"
PAGES = None
