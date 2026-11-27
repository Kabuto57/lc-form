"""HANDLING / FINANCING OF DOCUMENTS UNDER EXPORT DOCUMENTARY CREDIT (Form EBLC-01).

Build it:   python build.py eblc_form.py     -> out/EBLC-Application.pdf

Redrawn from the old trade smart form's EBLC application: the same questions, wording and order, and the same rules
(mandatory, mandatory-when, locked-until, formats, length limits, the 0-100 haircut). Every option a form file can use
is listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
Not carried over: the old form unlocked the hedging questions only when the financing currency differed from the
credit's currency; here they unlock when financing is requested (the form says when to fill them in).
"""
from build import check, date, in_range, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES

REQUEST = "We request your financing, discounting and/or negotiation of the Documents under the Documentary Credit"
FINANCING = ["We do not need financing. Please pay us upon receipt of funds.", REQUEST]
HEDGING = ["Demo Bank manages foreign exchange rate, currency convertibility and/or transferability risks",
           "Demo Bank enters a Hedging Transaction with us",
           "Without a Hedging Transaction, with a Haircut Percentage of"]
DOCUMENTS = [("drafts", "Drafts"), ("invoice", "Invoice"), ("packing_list", "Packing list"), ("weight_note", "Weight note"),
             ("cert_of_origin", "Certificate of origin"), ("insurance_policy", "Insurance policy"), ("bill_of_lading", "Bill of lading"),
             ("airway_bill", "Airway bill"), ("beneficiary_certificate", "Beneficiary's certificate")]


def document_rows():
    """Documents submitted: originals and copies for each usual document, then 5 rows for other documents."""
    rows = []
    for key, name in DOCUMENTS:
        rows += [text(f"{key}_originals", f"{name}: no. of original(s)", max=3, format="number", cols=6),
                 text(f"{key}_copies", f"{name}: no. of copy(ies)", max=3, format="number", cols=6)]
    for n in range(1, 6):
        rows += [text(f"other_document_{n}", f"Other document {n}", max=35, cols=6),
                 text(f"other_document_{n}_originals", "Originals", max=3, format="number", cols=3),
                 text(f"other_document_{n}_copies", "Copies", max=3, format="number", cols=3)]
    return rows


FORM = {
    "title": "Handling / Financing of Documents under Export Documentary Credit",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form EBLC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
        ]),
        section("Beneficiary", fields=[
            text("beneficiary_name", "Beneficiary name", required=True, max=35),
            text("beneficiary_address_1", "Beneficiary address", required=True, max=35),
            text("beneficiary_address_2", "Beneficiary address (line 2)", max=35),
            text("beneficiary_address_3", "Beneficiary address (line 3)", max=35),
            text("credit_no", "Documentary credit no.", required=True, max=20),
        ]),
        section("Issuing Bank and Credit", fields=[
            text("issuing_bank_name", "Issuing bank name", required=True, max=50),
            text("issuing_bank_name_2", "Issuing bank name (line 2)", max=50),
            select("currency", "Currency", options=CURRENCIES, required=True),
            text("amount", "Amount", required=True, max=15, format="amount"),
            date("credit_issue_date", "Date of issue", required=True),
        ]),
        section("Contact Person", fields=[
            text("contact_name", "Name", required=True, max=35),
            text("contact_tel", "Tel no.", required=True, max=17, format="phone"),
            text("contact_fax", "Fax no.", required=True, max=15, format="phone"),
        ]),
        section("Amendments", fields=[
            check("reject_amendment", "We REJECT amendment no."),
            text("rejected_amendment_no", "Amendment no. rejected", requiredIf=ticked("reject_amendment"), max=10),
        ]),
        section("Shipment and Tenor", fields=[
            text("draft_invoice_no", "Draft / invoice no.", required=True, max=16),
            text("vessel_name", "Vessel name", max=16),
            text("imo_no", "IMO no.", max=10),
            radio("tenor", "Tenor", ["Sight", "Term", "Date"]),
            text("term_days", "Term: days", requiredIf=when("tenor", "Term"), max=3, format="number"),
            text("term_days_after", "Days after", requiredIf=when("tenor", "Term"), max=35),
            date("tenor_date", "Tenor date", requiredIf=when("tenor", "Date")),
            text("port_of_loading", "Port of loading / airport of departure", max=24),
            text("port_of_discharge", "Port of discharge / airport of destination", max=24),
            text("goods_description", "Brief description of goods", max=30),
            date("departure_date", "Departure date", required=True),
            text("transport_document_no", "Transport document number", max=16),
        ]),
        section("Documents Submitted", note="Please indicate the number of originals and copies of each document submitted.", width="full", fields=document_rows()),
        section("Original Documentary Credit", fields=[
            select("original_dc", "Original DC and amendments (if any) are", options=["attached", "with Demo Bank", "with other bank"], required=True),
            text("original_dc_bank", "Name of the other bank", requiredIf=when("original_dc", "with other bank"), max=35),
            radio("checking", "Checking of documents", ["Do not check the Documents and send the unchecked Documents to the Issuing Bank",
                                                         "Check the Documents and send them to the Issuing Bank per Documentary Credit terms"]),
        ]),
        section("Settlement Instructions", width="full", note="Financing is in a currency acceptable to you (the \"Financing Currency\"), at the financing rate (the \"Financing Rate\") and subject to the prevailing General Banking Terms and Conditions (Applicable For Businesses/Non-Individuals), Trade Services Service Schedule and the relevant Jurisdiction Schedules.", fields=[
            radio("financing", "Settlement", FINANCING),
            text("financing_rate", "Financing rate (%)", activeIf=when("financing", REQUEST), max=7, format="amount"),
            select("financing_currency", "Financing currency", options=CURRENCIES, activeIf=when("financing", REQUEST)),
            radio("recourse", "Tick one (if none is ticked, financing is with full recourse)", ["With Full Recourse", "With No Recourse"], activeIf=when("financing", REQUEST)),
            radio("financing_timing", "Tick one (if none is ticked, after acceptance)", ["After the Documents have been accepted by the issuing bank or confirming bank (if any)",
                  "Prior to acceptance of the Documents by the Issuing Bank"], activeIf=when("financing", REQUEST)),
            radio("hedging", "Only where the Financing Currency is different from the Documentary Credit Currency", HEDGING, activeIf=when("financing", REQUEST)),
            text("haircut_percent", "Haircut percentage (%)", requiredIf=when("hedging", HEDGING[2]), max=6, format="amount"),
            radio("hedging_type", "Only where a Hedging Transaction is to be entered into", ["Deliverable forward foreign exchange transaction",
                  "Non-deliverable forward foreign exchange transaction", "Currency option transaction"], activeIf=when("hedging", HEDGING[0], HEDGING[1])),
        ]),
        section("Proceeds", width="full", fields=[
            radio("proceeds", "Please pay the financing / discounting / negotiation proceeds", ["After deducting the financing interest due to you",
                  "Without deducting the financing interest due to you"], required=True),
            check("credit_account", "Credit the funds to our account no."),
            text("credit_account_no", "Account no.", requiredIf=ticked("credit_account"), max=17, format="account"),
            check("remit_funds", "Remit the funds to"),
            text("remit_funds_to", "Remit to", requiredIf=ticked("remit_funds"), max=100),
            check("repay_with_funds", "Use the funds to repay"),
            text("repay_details", "Repay", requiredIf=ticked("repay_with_funds"), max=35),
            check("use_fx_contract", "Use FX contract ref."),
            text("fx_contract_ref", "FX contract ref.", requiredIf=ticked("use_fx_contract"), max=20),
            long("other_instructions", "Other instructions (if any)", max=500),
        ]),
        section("For Bank Use Only", bankOnly=True, fields=[
            text("bank_bill_ref", "Demo Bank use: bill ref.", max=50),
        ]),
        section("Authorised Signature(s)", signoff=True, note="We, as beneficiary, enclose the following documentary credit issued in our favour together with any amendments thereto (details of which are set out below) (the \"Documentary Credit\") and the Documents required under the Documentary Credit for your handling and/or financing. We agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules and Trade Services Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them. We further confirm that we agree to each declaration of trust and trust receipt set out in Clauses 10.5 and 11 of the Trade Services Schedule relating to this Trade Service (if any) or any other Trade Service, and whether such Trade Services are provided to us before, on or after the date of this Form.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        in_range("haircut_percent", 0, 100, "Please enter a value from 0 to 100."),
    ],
}

DEFAULTS = {
    "tenor": "Sight",
    "original_dc": "attached",
    "checking": "Do not check the Documents and send the unchecked Documents to the Issuing Bank",
    "financing": FINANCING[0],
    "proceeds": "After deducting the financing interest due to you",
}

PDF_NAME = "EBLC-Application.pdf"
