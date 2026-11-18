"""Irrevocable Standby Letter of Credit Application (Form SBLC-01).

Build it:   python build.py sblc_form.py     -> out/SBLC-Application.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (39 questions, 24 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Irrevocable Standby Letter of Credit Application",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form SBLC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Sblcbcode", fields=[
            date("sblcbcode_sblcdate", "Date"),
        ]),
        section("Total page no", fields=[
            text("total_page_no_page_no", "Total No. of pages", required=True, max=3, format="number"),
        ]),
        section("Applicant info", fields=[
            text("applicant_info_bank_cifno", "Demo Bank CIF No.", max=7, format="number"),
            text("applicant_info_applicant_name", "Applicant's Name", required=True, max=35),
            text("applicant_info_applicant_address1", "Applicant's Name (line 1)", required=True, max=35),
            text("applicant_info_applicant_address2", "Applicant's Name (line 2)", max=35),
            text("applicant_info_applicant_address3", "Applicant's Name (line 3)", max=35),
            text("applicant_info_contact_name", "Contact Person", required=True, max=35),
            text("applicant_info_tel_no", "Tel No.", required=True, max=15, format="phone"),
            text("applicant_info_fax_no", "Fax No.", required=True, max=15, format="phone"),
        ]),
        section("Beneficiary info", fields=[
            text("beneficiary_info_registration_no", "Registration No.", max=35),
            text("beneficiary_info_beneficiary_name", "Beneficiary's Name", required=True, max=35),
            text("beneficiary_info_beneficiary_address1", "Beneficiary's Name (line 1)", required=True, max=35),
            text("beneficiary_info_beneficiary_address2", "Beneficiary's Name (line 2)", max=35),
            select("beneficiary_info_beneficiary_country", "Country", options=CURRENCIES, required=True),
            text("beneficiary_info_contact_name", "Contact Person", required=True, max=35),
            text("beneficiary_info_tel_no", "Tel No.", required=True, max=15, format="phone"),
            text("beneficiary_info_fax_no", "Fax No.", required=True, max=15, format="phone"),
        ]),
        section("Third party and advising bank", fields=[
            text("third_party_third_party_address1", "Fax No. (line 1)", max=35),
            text("third_party_third_party_address2", "Fax No. (line 2)", max=35),
            text("third_party_third_party_address3", "Fax No. (line 3)", max=35),
            text("third_party_third_party_name", "Name", max=35),
            text("advising_bank_advising_bank_name", "Name", required=True, max=35),
            text("advising_bank_advising_bank_address1", "Name (line 1)", required=True, max=35),
            text("advising_bank_advising_bank_address2", "Name (line 2)", max=35),
            text("advising_bank_advising_bank_address3", "Name (line 3)", max=35),
            text("advising_bank_swiftaddress", "SWIFT Address", required=True, max=11),
        ]),
        section("Amount and period", fields=[
            select("curreny_amount_currency", "Currency", options=CURRENCIES, required=True),
            text("curreny_amount_amount", "Amount", required=True, max=15, format="amount"),
            date("valid_period_effective_date", "Effective Date", required=True),
            date("valid_period_expiry_date", "Expiry Date", required=True),
        ]),
        section("Partial and charges", fields=[
            radio("partial_drawings_partial", "Partial Drawings", ["Allowed", "Not Allowed"], required=True),
            radio("partial_and_charges_charges", "Partial Drawings", ["Applicant", "Beneficiary"], required=True),
        ]),
        section("Sblc format", fields=[
            long("sblc_format_sblcformat", "SBLC format: if the format is enclosed with the application form, please sign on every page of the format as per your company mandate", required=True, max=9000),
        ]),
        section("Special instructions", fields=[
            long("special_instructions", "Special Instructions", max=300),
        ]),
        section("This application", fields=[
            radio("this_application_application", "This Application, the SBLC to be issued thereunder and any amendments to the SBLC shall be subject to :-", ["The Uniform Customs and Practice for Documentary Credits, ICC Publication No. 600 unless there is instruction to us to apply any other revision of UCP such as UCP 500. We reserve the right not to accept any instructions from you to issue a SBLC which is subject to any revision of UCP other than UCP 600.", "International Standby Practice (ISP) 98"], required=True),
        ]),
        section("All fees", fields=[
            text("sblcac_no_acc_no", "We authorise you to debit SBLC amount in full from our account no.", max=20),
            text("header_acc_no", "We request for our fees, commissions and charges are to be debited to our Account No.", required=True, max=35),
        ]),
        section("Signature", fields=[
            text("signature", "Signature"),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "SBLC-Application.pdf"
PAGES = None
