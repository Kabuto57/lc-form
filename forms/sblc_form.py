"""IRREVOCABLE STANDBY LETTER OF CREDIT APPLICATION (Form SBLC-01).

Build it:   python build.py sblc_form.py     -> out/SBLC-Application.pdf

Redrawn from the old trade smart form's SBLC application: the same questions, wording and order, and the same rules
(mandatory, formats, length limits, the expiry-after-effective-date check). Every option a form file can use is
listed at the top of lc_form.py and in build.py, section 1. Step by step: GUIDE.md.
"""
from build import after, date, long, radio, section, select, text
from lc_form import COUNTRIES, CURRENCIES

FORM = {
    "title": "Irrevocable Standby Letter of Credit Application",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form SBLC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
            text("total_pages", "Total no. of pages (including this page)", required=True, max=3, format="number"),
            text("cif_no", "Demo Bank C.I.F. No.", max=7, format="cif"),
        ]),
        section("Applicant's Information", fields=[
            text("applicant_name", "Applicant's name", required=True, max=35),
            text("applicant_address_1", "Applicant's address", required=True, max=35),
            text("applicant_address_2", "Applicant's address (line 2)", max=35),
            text("applicant_address_3", "Applicant's address (line 3)", max=35),
            text("applicant_contact_name", "Contact person", required=True, max=35),
            text("applicant_tel", "Tel no.", required=True, max=15, format="phone"),
            text("applicant_fax", "Fax no.", required=True, max=15, format="phone"),
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
        section("For the Benefit of a 3rd Party", fields=[
            text("third_party_name", "Name", max=35),
            text("third_party_address_1", "Address", max=35),
            text("third_party_address_2", "Address (line 2)", max=35),
            text("third_party_address_3", "Address (line 3)", max=35),
        ]),
        section("Advising Bank", fields=[
            text("advising_bank_name", "Name", required=True, max=35),
            text("advising_bank_address_1", "Address", required=True, max=35),
            text("advising_bank_address_2", "Address (line 2)", max=35),
            text("advising_bank_address_3", "Address (line 3)", max=35),
            text("advising_bank_swift", "SWIFT address", required=True, max=11, format="swift"),
        ]),
        section("Amount and Validity", fields=[
            select("currency", "Currency", options=CURRENCIES, required=True),
            text("amount", "Amount", required=True, max=15, format="amount"),
            date("effective_date", "Effective date", required=True),
            date("expiry_date", "Expiry date", required=True),
        ]),
        section("Partial Drawings and Charges", fields=[
            radio("partial_drawings", "Partial drawings", ["Allowed", "Not Allowed"], required=True),
            radio("charges_outside_sg", "Charges outside Singapore are for account of", ["Applicant", "Beneficiary"], required=True),
        ]),
        section("SBLC Format", fields=[
            long("sblc_format", "SBLC format: if the format is enclosed with the application form, please sign on every page of the format as per your company mandate", required=True, max=9000),
        ]),
        section("Special Instructions", fields=[
            long("special_instructions", "Special instructions", max=300),
        ]),
        section("Rules", fields=[
            radio("subject_to", "This application, the SBLC to be issued thereunder and any amendments to the SBLC shall be subject to", [
                "The Uniform Customs and Practice for Documentary Credits, ICC Publication No. 600 unless there is instruction to us to apply any other revision of UCP such as UCP 500. We reserve the right not to accept any instructions from you to issue a SBLC which is subject to any revision of UCP other than UCP 600.",
                "International Standby Practice (ISP) 98"], required=True),
        ]),
        section("Fees, Commissions and Charges", fields=[
            text("debit_account_sblc_amount", "We authorise you to debit SBLC amount in full from our account no. (for advance payment)", max=20, format="account"),
            text("fees_account", "We request for our fees, commissions and charges to be debited to our account no.", required=True, max=35, format="account"),
        ]),
        section("Authorised Signature(s)", signoff=True, note="We agree to be bound by your prevailing General Banking Terms and Conditions, applicable Jurisdiction Schedules and Trade Services Schedule (each as may be amended, supplemented, substituted and/or replaced from time to time). We confirm that we have been given such prevailing terms [or accessed them, where published, at bank.example/trade] and have reviewed them.", fields=[
            text("signatory_name", "Name of authorised signatory", max=35),
        ]),
    ],
    "checks": [
        after("expiry_date", "effective_date", "Expiry date cannot be earlier than or equal to effective date."),
    ],
}

DEFAULTS = {}

PDF_NAME = "SBLC-Application.pdf"
PAGES = None
