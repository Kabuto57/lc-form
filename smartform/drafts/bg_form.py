"""Banker's Guarantee Application (Form BG-01).

Build it:   python build.py bg_form.py     -> out/BG-Application.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (52 questions, 21 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Banker's Guarantee Application",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BG-01 · v1.0 · Nov 2026",
    "sections": [
        section("Bgbcode", fields=[
            date("bgbcode_bgdate", "Date"),
        ]),
        section("Applicant and beneficiary", fields=[
            text("applicant_info_bank_cifno", "Demo Bank CIF No.", max=7, format="number"),
            text("applicant_info_applicant_name", "Applicant's Name", required=True, max=35),
            text("applicant_info_applicant_address1", "Applicant's Name (line 1)", required=True, max=35),
            text("applicant_info_applicant_address2", "Applicant's Name (line 2)", max=35),
            text("applicant_info_applicant_address3", "Applicant's Name (line 3)", max=35),
            text("applicant_info_contact_name", "Contact Person", required=True, max=35),
            text("applicant_info_tel_no", "Tel No.", required=True, max=15, format="phone"),
            text("applicant_info_fax_no", "Email", required=True, max=35, format="phone"),
            text("beneficiary_info_registration_no", "Registration No.", max=35),
            text("beneficiary_info_beneficiary_name", "Beneficiary's Name", required=True, max=35),
            text("beneficiary_info_beneficiary_address1", "Beneficiary's Name (line 1)", required=True, max=35),
            text("beneficiary_info_beneficiary_address2", "Beneficiary's Name (line 2)", max=35),
            select("beneficiary_info_beneficiary_country", "Country", options=CURRENCIES, required=True),
            text("beneficiary_info_contact_name", "Contact Person", required=True, max=35),
            text("beneficiary_info_tel_no", "Tel No.", required=True, max=15, format="phone"),
            text("beneficiary_info_fax_no", "Fax No.", required=True, max=15, format="phone"),
        ]),
        section("Currency and amount", fields=[
            select("curreny_amount_currency", "Currency", options=CURRENCIES, required=True),
            text("curreny_amount_amount", "Amount", required=True, max=15, format="amount"),
        ]),
        section("Third party and effective date", fields=[
            text("third_party_third_party_name", "Name", max=35),
            text("third_party_third_party_address1", "Name (line 1)", max=35),
            text("third_party_third_party_address2", "Name (line 2)", max=35),
            text("third_party_third_party_address3", "Name (line 3)", max=35),
            radio("third_party_and_effective_date_effective_date", "Effective Date", ["Specific Date", "As per format enclosed", "Date of Issue"], required=True),
            date("effective_date_specific_date", "Effective Date", requiredIf=when("third_party_and_effective_date_effective_date", "Specific Date")),
        ]),
        section("Expiry date and claim expiry date", fields=[
            radio("expire_date_expiry_date", "Expiry Date", ["Specific Date", "As per format enclosed", "Open ended (not allowed if beneficiary is located in Singapore, as per ABS Bye-Laws)"], required=True),
            date("expire_date_specific_date", "Expiry Date", requiredIf=when("expire_date_expiry_date", "Specific Date")),
            radio("expiry_date_and_claim_expiry_date_claim_expiry_date", "DD/MM/YYYY", ["Specific Date", "As per format enclosed", "Claim period: after expiry date"], required=True),
            date("claim_expiry_date_specific_date", "DD/MM/YYYY", requiredIf=when("expiry_date_and_claim_expiry_date_claim_expiry_date", "Specific Date")),
            text("claim_expiry_date_claim_period", "DD/MM/YYYY", requiredIf=when("expiry_date_and_claim_expiry_date_claim_expiry_date", "Claim period: after expiry date"), max=3, format="number"),
            select("claim_expiry_date_day_month", "Claim Expiry Date", options=["days", "months"], requiredIf=when("expiry_date_and_claim_expiry_date_claim_expiry_date", "Claim period: after expiry date")),
        ]),
        section("Requirements of issuing bank", fields=[
            radio("requirements_of_issuing_bank_requirements", "Please choose one of the following options", ["Issuing Bank shall be Demo Bank Ltd, Singapore", "Issuing Bank shall be branch or subsidiary of Demo Bank Ltd", "Issuing Bank shall be a Correspondent Agent Bank located in country of Beneficiary", "Issuing Bank nominated by the Beneficiary (Name & SWIFT Code)"], required=True),
            select("requirements_entity", "Entity", options=[], requiredIf=when("requirements_of_issuing_bank_requirements", "Issuing Bank shall be branch or subsidiary of Demo Bank Ltd")),
            select("requirements_branch_country", "Branch", options=[], requiredIf=when("requirements_of_issuing_bank_requirements", "Issuing Bank shall be branch or subsidiary of Demo Bank Ltd")),
            text("requirements_issue_bank_name", "Issuing Bank Name", requiredIf=when("requirements_of_issuing_bank_requirements", "Issuing Bank nominated by the Beneficiary (Name & SWIFT Code)"), max=35),
            text("requirements_swift_address", "Issuing Bank SWIFT Address", requiredIf=when("requirements_of_issuing_bank_requirements", "Issuing Bank nominated by the Beneficiary (Name & SWIFT Code)"), max=11),
            text("requirements_others_entity", "Entity", max=35),
            text("requirements_others_branch", "Branch", max=35),
        ]),
        section("Delivery instructions", fields=[
            radio("section_a_sg", "Where this BG is issued by Demo Bank Ltd, Singapore directly", ["Please contact us for self-collection", "Please courier directly to Beneficiary Address for attention of Contract Person as indicated above (courier charges apply)", "Please courier to us (courier charges apply)", "Please issue this BG and send it by authenticated SWIFT to Advising Bank for delivery to Beneficiary and furnish us with a copy"], required=True, activeIf=when("requirements_of_issuing_bank_requirements", "Issuing Bank shall be Demo Bank Ltd, Singapore")),
            text("section_a_advise_bank_name", "Advising Bank Name", requiredIf=when("section_a_sg", "Please issue this BG and send it by authenticated SWIFT to Advising Bank for delivery to Beneficiary and furnish us with a copy"), activeIf=when("section_a_sg", "Please issue this BG and send it by authenticated SWIFT to Advising Bank for delivery to Beneficiary and furnish us with a copy") + when("requirements_of_issuing_bank_requirements", "Issuing Bank shall be Demo Bank Ltd, Singapore"), max=35),
            text("section_a_swift_address", "Advising Bank SWIFT Address", requiredIf=when("section_a_sg", "Please issue this BG and send it by authenticated SWIFT to Advising Bank for delivery to Beneficiary and furnish us with a copy"), activeIf=when("section_a_sg", "Please issue this BG and send it by authenticated SWIFT to Advising Bank for delivery to Beneficiary and furnish us with a copy") + when("requirements_of_issuing_bank_requirements", "Issuing Bank shall be Demo Bank Ltd, Singapore"), max=11),
            radio("section_b_non_sg", "Where this BG is issued by Demo Bank Branch / Subsidiary / Correspondent Agent Bank outside of Singapore", ["Please release original guarantee to / to order of our agent / beneficiary Mr/Mrs", "Please courier directly to Beneficiary Address for attention of Contact Person as indicated above in the section \"Beneficiary's Information\"", "Please courier back to Applicant at Address for attention of Contact Person as indicated above. We are aware of the additional transit time of 3-5 working days."], required=True),
            text("section_b_mrs", "Where this BG is issued by Demo Bank Branch / Subsidiary / Correspondent Agent Bank outside of Singapore", requiredIf=when("section_b_non_sg", "Please release original guarantee to / to order of our agent / beneficiary Mr/Mrs"), max=35),
            select("section_b_passport", "Where this BG is issued by Demo Bank Branch / Subsidiary / Correspondent Agent Bank outside of Singapore", options=["Passport No.", "IC No.", "Others"], requiredIf=when("section_b_non_sg", "Please release original guarantee to / to order of our agent / beneficiary Mr/Mrs")),
            text("section_b_passport_no", "Where this BG is issued by Demo Bank Branch / Subsidiary / Correspondent Agent Bank outside of Singapore", requiredIf=when("section_b_non_sg", "Please release original guarantee to / to order of our agent / beneficiary Mr/Mrs"), max=20),
            text("section_b_at", "at place / city for collection", requiredIf=when("section_b_non_sg", "Please release original guarantee to / to order of our agent / beneficiary Mr/Mrs"), max=35),
            text("section_b_mobile_no", "Mobile No.", requiredIf=when("section_b_non_sg", "Please release original guarantee to / to order of our agent / beneficiary Mr/Mrs"), max=15),
        ]),
        section("Guarantees format", fields=[
            long("guarantees_format", "Guarantee Format: if the format is enclosed with the application form, please sign on every page of the format as per your company mandate", required=True, max=9000),
        ]),
        section("Special instructions", fields=[
            long("special_instructions", "Any Other Details or Special Instructions", max=300),
        ]),
        section("All fees", fields=[
            text("bgac_no_acc_no", "We authorise you to debit BG amount in full from our account no.", max=20),
            text("header_acc_no", "We request for our fees, commissions and charges are to be debited to our Account No.", required=True, max=35),
        ]),
        section("Signature", fields=[
            text("signature", "Signature"),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "BG-Application.pdf"
PAGES = None
