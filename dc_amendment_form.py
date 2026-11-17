"""DRAFT: APPLICATION TO AMEND A DOCUMENTARY CREDIT (Form LC-02).

Build it:   python build.py dc_amendment_form.py     -> out/DC-Amendment.pdf

A starting point, to be checked with Trade Operations before use. The questions follow the SWIFT amendment
message (MT707): the credit being amended, then only what changes. Each change has a tick box; ticking it
unlocks (and makes mandatory) the new value. Ids that mean the same as on the LC form (applicant_name,
expiry_date ...) are kept the same, so the Bank's system reads them the same way, and the form's date checks
apply (the new expiry date can't be before the new latest shipment date, and so on).

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
    "title": "Application for Amendment to Documentary Credit",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY. Fill in only the terms that change: all other "
            "terms of the credit remain unchanged.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form LC-02 · v0.1 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
        ]),
        section("Documentary Credit to Amend", fields=[
            text("dc_no", "DC no", required=True, max=16),
            date("dc_issue_date", "Date of issue", required=True),
            text("amendment_no", "Amendment no (if known)", max=3, format="number"),
            select("currency", "Currency", options=CURRENCIES, required=True),
            text("current_amount", "Current DC amount", required=True, format="amount"),
        ]),
        section("Applicant", fields=[
            text("applicant_name", "Applicant name", required=True, max=35),
            text("applicant_address_1", "Applicant address", required=True, max=35),
            text("contact_name", "Contact party for this amendment: Name", required=True, max=35),
            text("contact_tel", "Contact party: Tel no", required=True, max=15, format="phone"),
        ]),
        section("Beneficiary", fields=[
            text("beneficiary_name", "Beneficiary's name", required=True, max=35),
            text("beneficiary_address_1", "Beneficiary's address", max=35),
        ]),
        section("Amount", fields=[
            check("amount_change", "Change the credit amount"),
            radio("amount_change_type", "Change", ["Increase", "Decrease"], requiredIf=ticked("amount_change")),
            text("amount_change_by", "By (amount)", requiredIf=ticked("amount_change"), format="amount"),
            text("new_amount", "New DC amount", requiredIf=ticked("amount_change"), format="amount"),
            check("tolerance_change", "Change the tolerance on credit amount & goods quantity"),
            text("tolerance_plus", "New tolerance + (%)", requiredIf=ticked("tolerance_change"), max=2, format="number"),
            text("tolerance_minus", "New tolerance - (%)", requiredIf=ticked("tolerance_change"), max=2, format="number"),
        ]),
        section("Dates", fields=[
            check("expiry_change", "Change the date of expiry"),
            date("expiry_date", "New date of expiry (in beneficiary's country)", requiredIf=ticked("expiry_change")),
            check("shipment_date_change", "Change the latest shipment date"),
            date("latest_shipment_date", "New latest shipment date", requiredIf=ticked("shipment_date_change")),
            check("presentation_change", "Change the presentation period"),
            text("presentation_days", "New presentation period (days after shipment)", requiredIf=ticked("presentation_change"), max=3, format="number"),
        ]),
        section("Shipment", fields=[
            check("shipment_terms_change", "Change the shipment terms (fill in only what changes)"),
            radio("partial_shipment", "Partial shipment", ["allowed", "not allowed"], activeIf=ticked("shipment_terms_change")),
            radio("transhipment", "Transhipment", ["allowed", "not allowed"], activeIf=ticked("shipment_terms_change")),
            text("shipment_from_place", "Port of loading / place of dispatch", max=35, activeIf=ticked("shipment_terms_change")),
            text("shipment_to_place", "Port of discharge / place of delivery", max=35, activeIf=ticked("shipment_terms_change")),
        ]),
        section("Goods, Documents and Conditions", fields=[
            long("goods_amendment", "Changes to the description of goods and/or services", max=6500),
            long("documents_amendment", "Changes to the documents required", max=6500),
            long("conditions_amendment", "Changes to the additional conditions", max=6500),
            long("other_amendments", "Other amendments", max=1000),
        ]),
        section("Charges", fields=[
            radio("amendment_charges_for", "Amendment charges are for account of", ["Applicant", "Beneficiary"], required=True),
            text("charges_account", "Account no for amendment charges", max=17, format="account",
                 requiredIf=when("amendment_charges_for", "Applicant")),
        ]),
        section("For Bank Use Only", bankOnly=True, fields=[
            text("bank_ref", "Bank reference"),
            text("bank_code", "Bank code"),
        ]),
        section("Declaration and Signature", signoff=True, note="We request you to amend the documentary credit above "
                "as stated. All other terms and conditions remain unchanged. We understand that the amendment is "
                "subject to the beneficiary's acceptance (UCP 600 Article 10) and to the Bank's terms and conditions "
                "for documentary credits.", fields=[
            text("authorised_person", "Name and title of authorised person(s)"),
        ]),
    ],
}

# Answers already filled in when the form opens ({} for none).
DEFAULTS = {"amendment_charges_for": "Applicant"}

# The PDF's file name in out/.
PDF_NAME = "DC-Amendment.pdf"
