"""EXPORT DOCUMENTARY COLLECTION / FINANCING OF BILLS UNDER EXPORT DOCUMENTARY COLLECTION (Form OBC-01).

Build it:   python build.py obc_form.py     -> out/OBC-Application.pdf

Redrawn from the old trade smart form's OBC application: the same questions, wording and order, and the same rules
(mandatory, mandatory-when, locked-until, formats, length limits, financing 1-100%). Every option a form file can use
is listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import check, date, in_range, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES

DOCUMENTS = [("drafts", "Drafts (not applicable for sight bills)"), ("invoice", "Invoice"), ("packing_list", "Packing list"),
             ("cert_of_origin", "Certificate of origin"), ("insurance_policy", "Insurance policy"), ("bl_originals", "B/L (originals)"),
             ("bl_non_negotiable", "B/L (non-negotiable)"), ("weight_note", "Weight note"), ("airway_bill", "Airway bill"),
             ("beneficiary_certificate", "Beneficiary's certificate")]


def document_rows():
    """Documents enclosed: originals and copies for each usual document, then 4 rows for other documents."""
    rows = []
    for key, name in DOCUMENTS:
        rows += [text(f"{key}_originals", f"{name}: no. of original(s)", max=3, format="number", cols=6),
                 text(f"{key}_copies", f"{name}: no. of copy(ies)", max=3, format="number", cols=6)]
    for n in range(1, 5):
        rows += [text(f"other_document_{n}", f"Other document {n}", max=35, cols=6),
                 text(f"other_document_{n}_originals", "Originals", max=3, format="number", cols=3),
                 text(f"other_document_{n}_copies", "Copies", max=3, format="number", cols=3)]
    return rows


FORM = {
    "title": "Application for Export Documentary Collection / Financing of Bills under Export Documentary Collection",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form OBC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
        ]),
        section("Drawer / Seller", fields=[
            text("drawer_name", "Drawer / seller name", required=True, max=35),
            text("drawer_address_1", "Drawer / seller address", required=True, max=35),
            text("drawer_address_2", "Drawer / seller address (line 2)", max=35),
            text("drawer_address_3", "Drawer / seller address (line 3)", max=35),
            text("contact_name", "Contact person", required=True, max=35),
            text("contact_tel", "Tel", required=True, max=17, format="phone"),
        ]),
        section("Currency and Amount", fields=[
            select("currency", "Currency", options=CURRENCIES, required=True),
            text("amount", "Amount", required=True, max=15, format="amount"),
        ]),
        section("Drawee's Banker", fields=[
            text("drawee_bank_name", "Name", required=True, max=35),
            text("drawee_bank_address_1", "Address", required=True, max=35),
            text("drawee_bank_address_2", "Address (line 2)", max=35),
            text("drawee_bank_address_3", "Address (line 3)", max=35),
        ]),
        section("Collection", fields=[
            text("drawee", "Drawee / buyer", required=True, max=35),
            radio("deliver_against", "Deliver documents against (if unchecked: against payment if tenor is sight, against acceptance if tenor is term)", ["Payment", "Acceptance"]),
            text("invoice_no", "Invoice / reference no.", required=True, max=16),
            radio("tenor", "Tenor", ["Sight", "Term"], required=True),
            text("term_days", "Term: days", requiredIf=when("tenor", "Term"), max=3, format="number"),
            text("term_days_after", "Days after", requiredIf=when("tenor", "Term"), max=35),
        ]),
        section("Shipment", fields=[
            text("vessel_flight_no", "Vessel / flight no.", max=16),
            text("transport_document_no", "Transport document number", max=16),
            text("goods_description", "Brief description of goods", max=30),
            date("departure_date", "Departure date", required=True),
            text("port_of_loading", "Port of loading / airport of departure", max=24),
            text("port_of_discharge", "Port of discharge / airport of destination", max=24),
        ]),
        section("Documents Enclosed", width="full", fields=document_rows()),
        section("Instructions", width="full", fields=[
            check("collect_charges", "Collect your charges from drawee"),
            check("collect_interest", "Collect interest from drawee"),
            text("interest_rate", "Interest (% p.a.)", requiredIf=ticked("collect_interest"), max=2, format="number"),
            text("interest_from", "From (interest start date)", requiredIf=ticked("collect_interest"), max=35),
            text("interest_to", "To (if blank, up to payment by drawee)", activeIf=ticked("collect_interest"), max=35),
            check("do_not_waive", "Do not waive interest and / or collection charges if refused"),
            check("advise_by_swift", "Advise non-acceptance / non-payment by telex / SWIFT"),
            check("protest", "Protest non-acceptance / non-payment"),
            check("send_by_courier", "Documents to be sent to drawee's banker by courier service in one (1) lot unless otherwise instructed"),
            check("finance", "Please finance us for"),
            text("finance_percent", "% of the collection amount", requiredIf=ticked("finance"), max=3, format="number"),
            check("forward_regardless", "Please forward documents to drawee's bank regardless of whether approval has been obtained for financing the collection"),
            check("hold_until_approved", "Please hold documents until financing of the collection has been approved"),
            check("credit_proceeds", "Please credit financing / payment proceeds to our account with you"),
            text("credit_account_no", "Account no.", requiredIf=ticked("credit_proceeds"), max=17, format="account"),
            check("use_fx_contract", "Please use FX contract ref."),
            text("fx_contract_ref", "FX contract ref.", requiredIf=ticked("use_fx_contract"), max=20),
            check("other_instructions", "Other special instructions"),
            long("other_instructions_text", "Other special instructions", requiredIf=ticked("other_instructions"), max=500),
        ]),
        section("Authorised Signature(s)", signoff=True, note="We enclose herewith the following bill and documents for collection / advance according to the instructions set out below. We agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules and Trade Services Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them. We further confirm that we agree to each declaration of trust and trust receipt set out in Clauses 10.5 and 11 of the Trade Services Schedule relating to this Trade Service (if any) or any other Trade Service, and whether such Trade Services are provided to us before, on or after the date of this Form.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        in_range("finance_percent", 1, 100, "Please provide a valid number between 1 and 100."),
    ],
}

DEFAULTS = {"tenor": "Sight", "goods_description": "AS PER INVOICE"}

PDF_NAME = "OBC-Application.pdf"
PAGES = None
