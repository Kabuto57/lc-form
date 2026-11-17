"""DRAFT: EXPORT BILLS UNDER LETTER OF CREDIT (Form EB-01).

Build it:   python build.py eblc_form.py     -> out/EBLC-Application.pdf

An exporter (the LC's beneficiary) presents documents under an LC to the Bank for checking and negotiation.
A starting point, to be checked with Trade Operations before use. 5 sections:
    1. Exporter                  who is presenting, and the account to credit
    2. Letter of Credit          the LC the documents are presented under
    3. Documents Presented       which documents are enclosed, and how many
    4. Instructions              discrepancies, proceeds, financing
    5. Declaration and Signature
Ids that mean the same as on the LC form (currency, amount ...) keep the same names, so the Bank's system reads
them the same way. Every kind of question and option: build.py, section 1. Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Export Bills under Letter of Credit",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form EB-01 · v0.1 · Nov 2026",   # "EB-01" goes into the QR code; read_qr.py uses it to find this file
    "sections": [

        # 1. Who is presenting
        section("Exporter", fields=[
            date("application_date", "Date", required=True),
            text("exporter_name", "Exporter name", required=True, max=35),
            text("exporter_address_1", "Exporter address", required=True, max=35),
            text("exporter_address_2", "Exporter address (line 2)", max=35),
            text("contact_name", "Contact person", required=True, max=35),
            text("contact_tel", "Contact tel no", required=True, max=15, format="phone"),
            text("credit_account", "Account to credit the proceeds", required=True, max=20, format="account"),
        ]),

        # 2. The LC
        section("Letter of Credit", fields=[
            text("lc_number", "LC number", required=True, max=16),
            text("issuing_bank", "Issuing bank", required=True, max=35),
            date("lc_expiry_date", "LC expiry date", required=True),
            select("currency", "Currency", options=CURRENCIES, required=True),
            text("amount", "Bill amount", required=True, format="amount"),
            radio("tenor", "Tenor", ["Sight", "Usance"], required=True),
            # Only mandatory (and only unlocked) when the tenor is Usance:
            text("usance_days", "Usance: days", requiredIf=when("tenor", "Usance"), max=3, format="number"),
            select("usance_from", "Usance: days after", options=["Bill of lading date", "Invoice date", "Sight"],
                   requiredIf=when("tenor", "Usance")),
        ]),

        # 3. What is enclosed
        section("Documents Presented", note="Tick each document enclosed and give the number of originals.", fields=[
            check("doc_invoice", "Commercial invoice"),
            text("doc_invoice_count", "Commercial invoice: originals", requiredIf=ticked("doc_invoice"), max=2, format="number"),
            check("doc_transport", "Bill of lading / air waybill"),
            text("doc_transport_count", "Transport document: originals", requiredIf=ticked("doc_transport"), max=2, format="number"),
            date("shipment_date", "Shipment date (on the transport document)", requiredIf=ticked("doc_transport")),
            check("doc_insurance", "Insurance policy / certificate"),
            text("doc_insurance_count", "Insurance: originals", requiredIf=ticked("doc_insurance"), max=2, format="number"),
            check("doc_packing", "Packing list"),
            check("doc_origin", "Certificate of origin"),
            check("doc_other", "Other documents"),
            long("doc_other_details", "Other documents: please list", requiredIf=ticked("doc_other"), max=300),
        ]),

        # 4. What the Bank should do
        section("Instructions", fields=[
            radio("discrepancy_instruction", "If the documents are discrepant",
                  ["Send to the issuing bank for approval", "Hold and contact us", "Return the documents to us"],
                  required=True),
            check("request_financing", "We request financing (negotiation / discounting) of this bill"),
            text("financing_percent", "Financing: % of the bill amount", requiredIf=ticked("request_financing"),
                 max=3, format="number"),
            text("fx_contract", "Forward FX contract no", max=16),
            # Mandatory once an FX contract number is given:
            text("fx_rate", "Forward FX contract rate", requiredIf=answered("fx_contract"), max=12, format="amount"),
            radio("charges_for", "Bank charges outside the issuing bank are for", ["Exporter", "Importer"], required=True),
            long("special_instructions", "Special instructions", max=300),
        ]),

        # 5. Signature
        section("Declaration and Signature", signoff=True,
                note="We present the documents listed above under the letter of credit stated, and request you to "
                     "deal with them on the instructions above, subject to the Uniform Customs and Practice for "
                     "Documentary Credits (UCP 600) and to the Bank's terms and conditions.", fields=[
            text("authorised_person", "Name and title of authorised person(s)", max=35),
        ]),
    ],
}

# Answers already filled in when the form opens.
DEFAULTS = {
    "tenor": "Sight",
    "charges_for": "Exporter",
    "discrepancy_instruction": "Send to the issuing bank for approval",
}

PDF_NAME = "EBLC-Application.pdf"   # written to out/
