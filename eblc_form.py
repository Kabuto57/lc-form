"""DRAFT: EXPORT BILLS UNDER LETTER OF CREDIT (Form EB-01).

Build it:   python build.py eblc_form.py     -> out/EBLC-Application.pdf

An exporter (the LC's beneficiary) presents documents under an LC to the Bank for checking and negotiation.
A starting point, to be checked with Trade Operations before use. Ids that mean the same as on the LC form
(currency, amount ...) keep the same names, so the Bank's system reads them the same way.

WHAT YOU CAN CHANGE (all in this file; the same list is in every form file and in build.py, section 1)
    THE WHOLE FORM      FORM = {...}: "title", "note" (under the title), "issuer" (top of every page), "formCode"
                        (footer and QR code: give every form its own code, e.g. "Form EB-01 · v1.0 · Nov 2026").
                        DEFAULTS: answers filled in when the form opens.  PDF_NAME: the file name in out/.
                        PAGES (optional): the build stops if the form doesn't fit on that many pages (QR page included).
    A SECTION           section("Title", fields=[...], ...) plus any of:
                          note="..."        text under the heading
                          bankOnly=True     shaded "For Bank Use Only" section
                          signoff=True      signature, date and company stamp lines (always the whole width)
                          width="full"      the whole width of the page
                          width="half"      half the page; two half sections in a row sit side by side
                          new_page=True     starts on a new page
    A QUESTION          text / long / date / radio / checks / check / select (id, label, ...) plus any of:
                          required=True                     always mandatory (red *)
                          requiredIf=ticked("x")            mandatory (and unlocked) only when tick box x is ticked
                          requiredIf=when("x", "A", "B")    mandatory only when x is A or B
                          requiredIf=answered("x")          mandatory once x has any answer
                          activeIf=ticked("x")              unlocked only when x is ticked, but optional
                          max=35                            at most 35 characters (also sets the box width)
                          format="amount"                   amount / number / phone / account
                          cols=12                           width out of 12 columns: 12 whole row, 6 half, 4 a third
                          beside=69.3                       label beside a box this wide, even when the label is long
                          options=CURRENCIES                the shared currency list (in build.py)
    LEFT OUT            width, new_page and cols are only for when you want something different: without them
                        layout.py lays the form out by itself. Colours and text sizes are the same on every form
                        (red = mandatory) and are not set here.
    NOT IN THIS FILE    checks that compare two answers (e.g. a date must be after another): acrobat_js.py
                        (across) and read_qr.py (checks_across), kept the same.
"""
# Every form file starts with this same line: it brings in the words used below.
from build import CURRENCIES, answered, check, checks, date, long, radio, section, select, text, ticked, when

FORM = {
    "title": "Export Bills under Letter of Credit",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form EB-01 · v0.1 · Nov 2026",
    "sections": [
        section("Exporter", width="full", fields=[
            date("application_date", "Date", required=True),
            text("exporter_name", "Exporter name", required=True, max=35, cols=12),   # cols=12: the whole row (cols=6: half)
            text("exporter_address_1", "Exporter address", required=True, max=35),
            text("exporter_address_2", "Exporter address (line 2)", max=35),
            text("contact_name", "Contact person", required=True, max=35, cols=6),
            text("contact_tel", "Contact tel no", required=True, max=15, format="phone"),
            text("credit_account", "Account to credit the proceeds", required=True, max=20, format="account"),
        ]),

        # 2. The LC
        section("Letter of Credit", width="full", fields=[
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
        section("Documents Presented", width="half", note="Tick each document enclosed and give the number of originals.", fields=[
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
        section("Instructions", width="half", fields=[
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

# Answers already filled in when the form opens ({} for none).
DEFAULTS = {
    "tenor": "Sight",
    "charges_for": "Exporter",
    "discrepancy_instruction": "Send to the issuing bank for approval",
}

# The PDF's file name in out/.
PDF_NAME = "EBLC-Application.pdf"
