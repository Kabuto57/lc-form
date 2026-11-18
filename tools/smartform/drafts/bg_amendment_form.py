"""Banker's Guarantee Amendment (Form BGA-01).

Build it:   python build.py bg_amendment_form.py     -> out/BG-Amendment.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (35 questions, 9 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Banker's Guarantee Amendment",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BGA-01 · v1.0 · Nov 2026",
    "sections": [
        section("Bgabcode", fields=[
            date("bgabcode_sblcadate", "Date"),
        ]),
        section("Bank and ref no", fields=[
            text("bank_no_bank_cifno", "Demo Bank CIF No.", max=7, format="number"),
            text("bank_and_ref_no_ref_no", "Amendment to Banker's Guarantee : (\u201cBG\u201d) Reference No.", required=True, max=12, format="number"),
        ]),
        section("Applicant and beneficiary", fields=[
            text("applicant_info_applicant_name", "Applicant's Name", required=True, max=35),
            text("applicant_info_applicant_address1", "Applicant's Name (line 1)", max=35),
            text("applicant_info_applicant_address2", "Applicant's Name (line 2)", max=35),
            text("applicant_info_applicant_address3", "Applicant's Name (line 3)", max=35),
            text("beneficiary_info_beneficiary_name", "Beneficiary's Name", max=35),
            text("beneficiary_info_beneficiary_address1", "Beneficiary's Name (line 1)", max=35),
            text("beneficiary_info_beneficiary_address2", "Beneficiary's Name (line 2)", max=35),
            select("beneficiary_info_beneficiary_country", "Country", options=CURRENCIES),
        ]),
        section("Amount", fields=[
            check("amount_amend_amount", "the amount by", required=True),
            select("amount_amend_amount_2", "the amount by (line 2)", options=["Increase", "Decrease"], requiredIf=ticked("amount_amend_amount")),
            select("amount_currency", "Currency", options=CURRENCIES, requiredIf=ticked("amount_amend_amount")),
            text("amount", "Amount", requiredIf=ticked("amount_amend_amount"), max=15, format="amount"),
            text("amount_amount2", "Amount (line 2)", requiredIf=ticked("amount_amend_amount"), max=15, format="amount"),
            select("amount_currency2", "Amount (line 2)", options=CURRENCIES, requiredIf=ticked("amount_amend_amount")),
        ]),
        section("Expiry date", fields=[
            check("expiry_date_amend_expiry_date", "Amend the expiry date to", required=True),
            date("expiry_date", "Currency", requiredIf=ticked("expiry_date_amend_expiry_date")),
        ]),
        section("Claim expiry date", fields=[
            check("claim_expiry_date_amend_claim_expiry_date", "Amend the claim expiry date to", required=True),
            date("claim_expiry_date", "Currency", requiredIf=ticked("claim_expiry_date_amend_claim_expiry_date")),
        ]),
        section("Claim period", fields=[
            check("claim_period_amend_claim_period", "Amend the claim expiry period to", required=True),
            text("claim_period", "Currency", requiredIf=ticked("claim_period_amend_claim_period"), max=3, format="number"),
            select("claim_period_day_month", "DD/MM/YYYY", options=["days", "months"], requiredIf=ticked("claim_period_amend_claim_period")),
        ]),
        section("Amend text", fields=[
            check("text_amend_text", "Amend the BG text as provided below", required=True),
            long("amend_text_amend", "Amend", requiredIf=ticked("text_amend_text"), max=3000),
        ]),
        section("Delivery instructions", fields=[
            radio("delivery_instructions_delivery", "Delivery Instruction", ["Please contact Mr/Mrs.", "Please send the amendment directly to the beneficiary, attn.", "Free Text"], required=True),
            text("delivery_instructions_contact_name", "Delivery Instruction", requiredIf=when("delivery_instructions_delivery", "Please contact Mr/Mrs."), max=15),
            select("delivery_instructions_passport_ic", "Delivery Instruction", options=["Passport No.", "IC No.", "Others"], requiredIf=when("delivery_instructions_delivery", "Please contact Mr/Mrs.")),
            text("delivery_instructions_passport_icno", "Delivery Instruction", requiredIf=when("delivery_instructions_delivery", "Please contact Mr/Mrs."), max=10),
            text("delivery_instructions_tel_no", "tel no./mobile no.", requiredIf=when("delivery_instructions_delivery", "Please contact Mr/Mrs."), max=15, format="number"),
            text("delivery_instructions_attn", "for collection.", requiredIf=when("delivery_instructions_delivery", "Please send the amendment directly to the beneficiary, attn."), max=15),
            long("delivery_instructions_free_text", "tel no./mobile no.", requiredIf=when("delivery_instructions_delivery", "Free Text"), max=200),
        ]),
        section("We", fields=[
            text("we_acc_no", "We request for our fees, commissions and charges to be debited from our Account No.", required=True, max=13),
        ]),
        section("Signature", fields=[
            text("signature", "We request for our fees, commissions and charges to be debited from our Account No."),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "BG-Amendment.pdf"
PAGES = None
