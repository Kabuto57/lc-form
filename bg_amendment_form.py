"""AMENDMENT TO BANKER'S GUARANTEE (Form BGA-01).

Build it:   python build.py bg_amendment_form.py     -> out/BG-Amendment.pdf

Redrawn from the old trade smart form's BG amendment: the same questions, wording and order, and the same rules.
Tick an amendment and its details become mandatory (they stay locked otherwise). Every option a form file can use is
listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import check, date, not_before, long, radio, section, select, text, ticked, when
from lc_form import COUNTRIES, CURRENCIES

DELIVERY = ["Please contact Mr/Mrs (for collection)", "Please send the amendment directly to the beneficiary", "Free text"]

FORM = {
    "title": "Amendment to Banker's Guarantee",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BGA-01 · v1.0 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
            text("cif_no", "Demo Bank C.I.F. No.", max=7, format="cif"),
            text("bg_reference_no", "Amendment to Banker's Guarantee (\"BG\") reference no.", required=True, max=12, format="ref12"),
        ]),
        section("Applicant", fields=[
            text("applicant_name", "Applicant's name", required=True, max=35),
            text("applicant_address_1", "Applicant's address", max=35),
            text("applicant_address_2", "Applicant's address (line 2)", max=35),
            text("applicant_address_3", "Applicant's address (line 3)", max=35),
        ]),
        section("Beneficiary", fields=[
            text("beneficiary_name", "Beneficiary's name", max=35),
            text("beneficiary_address_1", "Beneficiary's address", max=35),
            text("beneficiary_address_2", "Beneficiary's address (line 2)", max=35),
            select("beneficiary_country", "Country", options=COUNTRIES),
        ]),
        section("Amendments", note="Tick each amendment you need; its details then become mandatory.", fields=[
            check("amend_amount", "Amend the amount"),
            select("amount_change", "Increase / decrease the amount by", options=["Increase", "Decrease"], requiredIf=ticked("amend_amount")),
            select("amount_change_currency", "Currency", options=CURRENCIES, requiredIf=ticked("amend_amount")),
            text("amount_change_amount", "Amount", requiredIf=ticked("amend_amount"), max=15, format="amount"),
            select("new_amount_currency", "New BG amount: currency", options=CURRENCIES, requiredIf=ticked("amend_amount")),
            text("new_amount", "New BG amount", requiredIf=ticked("amend_amount"), max=15, format="amount"),
            check("amend_expiry_date", "Amend the expiry date"),
            date("expiry_date", "New expiry date", requiredIf=ticked("amend_expiry_date")),
            check("amend_claim_expiry_date", "Amend the claim expiry date"),
            date("claim_expiry_date", "New claim expiry date", requiredIf=ticked("amend_claim_expiry_date")),
            check("amend_claim_period", "Amend the claim expiry period"),
            text("claim_period", "New claim period", requiredIf=ticked("amend_claim_period"), max=3, format="number"),
            select("claim_period_unit", "Days / months", options=["days", "months"], requiredIf=ticked("amend_claim_period")),
            check("amend_text", "Amend the BG text as provided below"),
            long("amended_text", "Amendment to the BG text", requiredIf=ticked("amend_text"), max=3000),
        ]),
        section("Delivery Instructions", fields=[
            radio("delivery", "Delivery instruction", DELIVERY, required=True),
            text("collector_name", "Contact Mr / Mrs", requiredIf=when("delivery", DELIVERY[0]), max=15),
            select("collector_id_type", "Identification", options=["Passport No.", "IC No.", "Others"], requiredIf=when("delivery", DELIVERY[0])),
            text("collector_id_no", "Identification no.", requiredIf=when("delivery", DELIVERY[0]), max=10),
            text("collector_tel", "Tel no. / mobile no.", requiredIf=when("delivery", DELIVERY[0]), max=15, format="number"),
            text("beneficiary_attn", "Send directly to the beneficiary, attention of", requiredIf=when("delivery", DELIVERY[1]), max=15),
            long("delivery_free_text", "Delivery instruction (free text)", requiredIf=when("delivery", DELIVERY[2]), max=200),
        ]),
        section("Charges", fields=[
            text("fees_account", "We request for our fees, commissions and charges to be debited from our account no.", required=True, max=13, format="account"),
        ]),
        section("Authorised Signature(s)", signoff=True, note="We request you to amend the BG as set out above. We acknowledge that all amendments will be subject to acceptance by the issuing bank and the beneficiary. All other terms and conditions of the BG remain in full force and effect. We agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules, Trade Services Schedule and Banker's Guarantee Issued In Favour of Singapore Government Agency Service Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        not_before("claim_expiry_date", "expiry_date", "Claim expiry date cannot be earlier than expiry date."),
    ],
}

DEFAULTS = {}

PDF_NAME = "BG-Amendment.pdf"
PAGES = None
