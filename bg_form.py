"""BANKER'S GUARANTEE APPLICATION (Form BG-01).

Build it:   python build.py bg_form.py     -> out/BG-Application.pdf

Redrawn from the old trade smart form's BG application: the same questions, wording and order, and the same rules
(mandatory, mandatory-when, locked-until, formats, length limits, date checks). Every option a form file can use is
listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import after, answered, check, date, long, radio, section, select, text, ticked, when
from lc_form import COUNTRIES, CURRENCIES

ISSUER_OPTIONS = ["Issuing Bank shall be Demo Bank Ltd, Singapore",
                  "Issuing Bank shall be branch or subsidiary of Demo Bank Ltd",
                  "Issuing Bank shall be a Correspondent Agent Bank located in country of Beneficiary",
                  "Issuing Bank nominated by the Beneficiary (Name & SWIFT Code)"]
ENTITIES = ["DEMO BANK LTD", "DEMO BANK (CHINA) LTD", "DEMO BANK (HONG KONG) LTD", "DEMO BANK LTD, INDIA",
            "PT DEMO BANK INDONESIA", "DEMO BANK (TAIWAN) LTD", "OTHERS"]
# The old form changed the branch list with the entity; here every branch is listed with its entity.
BRANCHES = ["DUBAI BRANCH (DEMO BANK LTD)", "HONG KONG BRANCH (DEMO BANK LTD)", "HO CHI MINH BRANCH (DEMO BANK LTD)",
            "LABUAN BRANCH (DEMO BANK LTD)", "LONDON BRANCH (DEMO BANK LTD)", "SEOUL BRANCH (DEMO BANK LTD)",
            "SYDNEY BRANCH (DEMO BANK LTD)", "TAIPEI BRANCH (DEMO BANK LTD)",
            "SHANGHAI BRANCH (CHINA)", "BEIJING BRANCH (CHINA)", "CHONGQING BRANCH (CHINA)", "DONGGUAN BRANCH (CHINA)",
            "SHANGHAI FREE TRADE ZONE SUB-BRANCH (CHINA)", "GUANGZHOU BRANCH (CHINA)", "HANGZHOU BRANCH (CHINA)",
            "NANNING BRANCH (CHINA)", "QINGDAO BRANCH (CHINA)", "SHENZHEN BRANCH (CHINA)", "SUZHOU BRANCH (CHINA)",
            "TIANJIN BRANCH (CHINA)", "XI'AN BRANCH (CHINA)",
            "HONGKONG BRANCH (HONG KONG)", "MACAU BRANCH (HONG KONG)",
            "MUMBAI BRANCH (INDIA)", "BANGALORE BRANCH (INDIA)", "CHENNAI BRANCH (INDIA)", "CUDDALORE BRANCH (INDIA)",
            "KOLHAPUR BRANCH (INDIA)", "KOLKATA BRANCH (INDIA)", "MORADABAD BRANCH (INDIA)", "NASHIK BRANCH (INDIA)",
            "NEW DELHI BRANCH (INDIA)", "PUNE BRANCH (INDIA)", "SALEM BRANCH (INDIA)", "SURAT BRANCH (INDIA)",
            "JAKARTA BRANCH (INDONESIA)", "MEDAN BRANCH (INDONESIA)", "SURABAYA BRANCH (INDONESIA)",
            "TAIWAN BRANCH (TAIWAN)", "OTHERS"]
SECTION_A = ["Please contact us for self-collection",
             "Please courier directly to Beneficiary Address for attention of Contact Person as indicated above (courier charges apply)",
             "Please courier to us (courier charges apply)",
             "Please issue this BG and send it by authenticated SWIFT to Advising Bank for delivery to Beneficiary and furnish us with a copy"]
SECTION_B = ["Please release original guarantee to / to order of our agent / beneficiary",
             "Please courier directly to Beneficiary Address for attention of Contact Person as indicated above in the section \"Beneficiary's Information\"",
             "Please courier back to Applicant at Address for attention of Contact Person as indicated above. We are aware of the additional transit time of 3-5 working days."]

FORM = {
    "title": "Banker's Guarantee Application",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form BG-01 · v1.0 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
            text("cif_no", "Demo Bank C.I.F. No.", max=7, format="cif"),
        ]),
        section("Applicant's Information", fields=[
            text("applicant_name", "Applicant's name", required=True, max=35),
            text("applicant_address_1", "Applicant's address", required=True, max=35),
            text("applicant_address_2", "Applicant's address (line 2)", max=35),
            text("applicant_address_3", "Applicant's address (line 3)", max=35),
            text("applicant_contact_name", "Contact person", required=True, max=35),
            text("applicant_tel", "Tel no.", required=True, max=15, format="phone"),
            text("applicant_email", "Email", required=True, max=35),
        ]),
        section("Beneficiary's Information", fields=[
            text("beneficiary_registration_no", "Registration no.", max=35),
            text("beneficiary_name", "Beneficiary's name", required=True, max=35),
            text("beneficiary_address_1", "Beneficiary's address", required=True, max=35),
            text("beneficiary_address_2", "Beneficiary's address (line 2)", max=35),
            select("beneficiary_country", "Country", options=COUNTRIES, required=True),
            text("beneficiary_contact_name", "Contact person", required=True, max=35),
            text("beneficiary_tel", "Tel no.", required=True, max=15, format="phone"),
            text("beneficiary_fax", "Fax no.", required=True, max=15, format="phone"),
        ]),
        section("Currency and Amount", fields=[
            select("currency", "Currency", options=CURRENCIES, required=True),
            text("amount", "Amount", required=True, max=15, format="amount"),
        ]),
        section("For the Benefit of a 3rd Party", fields=[
            text("third_party_name", "Name", max=35),
            text("third_party_address_1", "Address", max=35),
            text("third_party_address_2", "Address (line 2)", max=35),
            text("third_party_address_3", "Address (line 3)", max=35),
        ]),
        section("Effective Date", fields=[
            radio("effective_date_type", "Effective date", ["Specific Date", "As per format enclosed", "Date of Issue"], required=True),
            date("effective_date", "Effective date: specific date", requiredIf=when("effective_date_type", "Specific Date")),
        ]),
        section("Expiry Date and Claim Expiry Date", fields=[
            radio("expiry_date_type", "Expiry date", ["Specific Date", "As per format enclosed",
                  "Open ended (not allowed if beneficiary is located in Singapore, as per ABS Bye-Laws)"], required=True),
            date("expiry_date", "Expiry date: specific date", requiredIf=when("expiry_date_type", "Specific Date")),
            radio("claim_expiry_type", "Claim expiry date", ["Specific Date", "As per format enclosed", "Claim period after expiry date"], required=True),
            date("claim_expiry_date", "Claim expiry date: specific date", requiredIf=when("claim_expiry_type", "Specific Date")),
            text("claim_period", "Claim period after expiry date", requiredIf=when("claim_expiry_type", "Claim period after expiry date"), max=3, format="number"),
            select("claim_period_unit", "Claim period: days / months", options=["days", "months"], requiredIf=when("claim_expiry_type", "Claim period after expiry date")),
        ]),
        section("Requirements of Issuing Bank", fields=[
            radio("issuing_bank", "Please choose one of the following options", ISSUER_OPTIONS, required=True),
            select("issuing_entity", "Entity", options=ENTITIES, requiredIf=when("issuing_bank", ISSUER_OPTIONS[1])),
            select("issuing_branch", "Branch", options=BRANCHES, requiredIf=[{"field": "issuing_entity", "values": ["OTHERS"], "not": True}]),
            text("issuing_entity_other", "Entity (others)", requiredIf=when("issuing_entity", "OTHERS"), max=35),
            text("issuing_branch_other", "Branch (others)", requiredIf=when("issuing_branch", "OTHERS"), max=35),
            text("nominated_bank_name", "Issuing bank name", requiredIf=when("issuing_bank", ISSUER_OPTIONS[3]), max=35),
            text("nominated_bank_swift", "Issuing bank SWIFT address", requiredIf=when("issuing_bank", ISSUER_OPTIONS[3]), max=11, format="swift"),
        ]),
        section("Delivery Instructions", fields=[
            radio("delivery_sg", "A. Where this BG is issued by Demo Bank Ltd, Singapore directly", SECTION_A,
                  requiredIf=when("issuing_bank", ISSUER_OPTIONS[0])),
            text("advising_bank_name", "Advising bank name", requiredIf=when("delivery_sg", SECTION_A[3]), max=35),
            text("advising_bank_swift", "Advising bank SWIFT address", requiredIf=when("delivery_sg", SECTION_A[3]), max=11, format="swift"),
            radio("delivery_abroad", "B. Where this BG is issued by a Demo Bank branch / subsidiary / correspondent agent bank outside Singapore",
                  SECTION_B, requiredIf=when("issuing_bank", *ISSUER_OPTIONS[1:])),
            text("collector_name", "Agent / beneficiary: Mr / Mrs", requiredIf=when("delivery_abroad", SECTION_B[0]), max=35),
            select("collector_id_type", "Identification", options=["Passport No.", "IC No.", "Others"], requiredIf=when("delivery_abroad", SECTION_B[0])),
            text("collector_id_no", "Identification no.", requiredIf=when("delivery_abroad", SECTION_B[0]), max=20),
            text("collector_city", "At place / city for collection", requiredIf=when("delivery_abroad", SECTION_B[0]), max=35),
            text("collector_mobile", "Mobile no.", requiredIf=when("delivery_abroad", SECTION_B[0]), max=15, format="phone"),
        ]),
        section("Guarantee Format", fields=[
            long("guarantee_format", "Guarantee format: if the format is enclosed with the application form, please sign on every page of the format as per your company mandate", required=True, max=9000),
        ]),
        section("Any Other Details or Special Instructions", fields=[
            long("special_instructions", "Any other details or special instructions", max=300),
        ]),
        section("Fees, Commissions and Charges", fields=[
            text("debit_account_bg_amount", "We authorise you to debit BG amount in full from our account no.", max=20, format="account"),
            text("fees_account", "We request for our fees, commissions and charges to be debited to our account no.", required=True, max=35, format="account"),
        ]),
        section("Authorised Signature(s)", signoff=True, note="We agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules, Trade Services Schedule and Banker's Guarantee Issued In Favour of Singapore Government Agency Service Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        after("expiry_date", "effective_date", "Expiry date cannot be earlier than or equal to effective date."),
        after("claim_expiry_date", "expiry_date", "Claim expiry date cannot be earlier than expiry date."),
    ],
}

DEFAULTS = {}

PDF_NAME = "BG-Application.pdf"
PAGES = None
