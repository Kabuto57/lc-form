"""THE LC APPLICATION FORM (Irrevocable Documentary Credit Application, Form LC-01).

Build it:   python build.py lc_form.py     -> out/LC-Application.pdf

The questions keep the order and full wording of the Bank's form. The id (first word in quotes) is the answer's
name in the PDF and in the QR code: don't change it lightly, the Bank's system reads it.

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
    "title": "Irrevocable Documentary Credit Application",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form LC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Application", fields=[
            date("application_date", "Date", required=True),
        ]),
        section("Mode of Advising", fields=[
            radio("mode_of_advising", "Mode of advising", ["Full Swift", "Registered Airmail", "Airmail with Brief Swift", "Courier Service", "Courier Service with Brief Swift"], required=True),
        ]),
        section("Applicant", fields=[
            text("applicant_name", "Applicant name", required=True, max=35),
            text("applicant_address_1", "Applicant address", required=True, max=35),
            text("applicant_address_2", "Applicant address (line 2)", max=35),
            text("applicant_address_3", "Applicant address (line 3)", max=35),
            text("applicant_address_4", "Applicant address (line 4)", max=35),
            text("contact_name", "Contact party for this application & confirmation of FX rate: Name", required=True, max=35),
            text("contact_tel", "Contact party: Tel no", required=True, max=15, format="phone"),
            text("contact_fax", "Contact party: Fax no", max=15, format="phone"),
        ]),
        section("For Bank Use Only", bankOnly=True, fields=[
            text("dc_no", "DC no"),
            text("bank_code", "Bank code"),
        ]),
        section("Advising Bank (at Issuing Bank's option, if no nomination)", fields=[
            text("advising_bank_name", "Name", max=35),
            text("advising_bank_address_1", "Address", max=35),
            text("advising_bank_address_2", "Address (line 2)", max=35),
            text("advising_bank_address_3", "Address (line 3)", max=35),
        ]),
        section("For the Benefit of a 3rd Party", fields=[
            text("third_party_name", "Name", max=35),
            text("third_party_address_1", "Address", max=35),
            text("third_party_address_2", "Address (line 2)", max=35),
            text("third_party_address_3", "Address (line 3)", max=35),
        ]),
        section("Beneficiary", fields=[
            text("beneficiary_name", "Beneficiary's name", required=True, max=35),
            text("beneficiary_address_1", "Beneficiary's address", required=True, max=35),
            text("beneficiary_address_2", "Beneficiary's address (line 2)", max=35),
            text("beneficiary_address_3", "Beneficiary's address (line 3)", max=35),
            text("beneficiary_address_4", "Beneficiary's address (line 4)", max=35),
            text("beneficiary_contact", "Contact person", max=35),
            text("beneficiary_tel", "Tel no", max=15, format="phone"),
            text("beneficiary_fax", "Fax no", max=15, format="phone"),
        ]),
        section("Credit Amount (Currency & Figures)", fields=[
            select("currency", "Currency", options=CURRENCIES, required=True),
            text("amount", "Amount", required=True, format="amount"),
            radio("gst", "For local DCs, amount is (if not checked, it will be inclusive of GST)", ["inclusive of GST", "No GST"]),
            check("tolerance", "Tolerance on credit amount & goods quantity"),
            text("tolerance_plus", "Tolerance + (%)", requiredIf=ticked("tolerance"), max=2, format="number"),
            text("tolerance_minus", "Tolerance - (%)", requiredIf=ticked("tolerance"), max=2, format="number"),
        ]),
        section("Price Basis", fields=[
            radio("price_basis", "Price basis", ["FOB", "CFR", "CIF", "Local Delivery", "FCA", "CIP", "CPT", "Others"], required=True),
            text("price_basis_other", "Others (please specify)", max=35, requiredIf=when("price_basis", "Others")),
        ]),
        section("Shipment", fields=[
            radio("partial_shipment", "Partial shipment", ["allowed", "not allowed"], required=True),
            radio("transhipment", "Transhipment", ["allowed", "not allowed"], required=True),
            select("shipment_from", "Shipment from", options=["Port of Loading / Airport of Departure", "Dispatch from", "Place of Taking in charge", "Place of Receipt"]),
            text("shipment_from_place", "Shipment from: place", max=35, requiredIf=answered("shipment_from")),
            text("shipment_from_place_2", "Shipment from: place (line 2)"),
            select("shipment_to", "Shipment to", options=["Port of Discharge / Airport of Destination", "For Transportation to", "Place of Final Destination", "Place of Delivery"]),
            text("shipment_to_place", "Shipment to: place", max=35, requiredIf=answered("shipment_to")),
            text("shipment_to_place_2", "Shipment to: place (line 2)"),
            date("latest_shipment_date", "Latest shipment date"),
        ]),
        section("Expiry and Presentation", fields=[
            date("expiry_date", "Date of expiry (in beneficiary's country)", required=True),
            text("presentation_days", "Presentation period (days after shipment)", format="number"),
        ]),
        section("Back-to-back DC", fields=[
            check("back_to_back", "This is a back-to-back DC to be issued against the master credit (the \"Master DC\")"),
            text("master_dc_no", "Master credit no", requiredIf=ticked("back_to_back"), max=20),
            text("master_dc_issued_by", "Issued by", requiredIf=ticked("back_to_back"), max=35),
        ]),
        section("Drafts", fields=[
            check("drafts", "Drafts for the percentage of invoice value below, at"),
            text("drafts_percent", "Percentage of invoice value (%)", requiredIf=ticked("drafts"), format="number", max=3, beside=69.3),
            radio("drafts_at", "Drafts at", ["Sight", "Term", "Date"], requiredIf=ticked("drafts")),
            text("term_days", "Term: days", requiredIf=when("drafts_at", "Term"), format="number"),
            text("term_after", "days after", requiredIf=when("drafts_at", "Term"), max=35),
            date("draft_date", "Date", requiredIf=when("drafts_at", "Date")),
            radio("term_prepay", "If it is a term LC, please select one", ["You may prepay the acceptance of this term LC at the cost of beneficiary", "You may not prepay the acceptance of this term LC"], requiredIf=when("drafts_at", "Term")),
        ]),
        section("Documents Required", fields=[
            check("doc_bill_of_lading", "Full set of Clean on Board marine bills of lading"),
            radio("bl_made_out_to", "Made out to", ["order of the Bank", "order blank endorsed", "other (specify)"], requiredIf=ticked("doc_bill_of_lading")),
            text("bl_made_out_to_other", "Made out to (other)", requiredIf=when("bl_made_out_to", "other (specify)"), max=70),
            radio("bl_freight", "Marked Freight", ["Prepaid", "Collect"], requiredIf=ticked("doc_bill_of_lading")),
            text("bl_notify_party", "Notify party (if not specified, notify party is considered to be applicant)", max=114, requiredIf=ticked("doc_bill_of_lading")),
            check("doc_air_waybill", "Original Air Waybill consigned to the Bank"),
            radio("awb_freight", "Marked Freight", ["Prepaid", "Collect"], requiredIf=ticked("doc_air_waybill")),
            text("awb_notify_party", "Notify party (if not specified, notify party is considered to be applicant)", max=114, requiredIf=ticked("doc_air_waybill")),
            check("doc_delivery_order", "Delivery order signed by beneficiary made out to applicant"),
            text("do_originals", "Delivery order: originals", requiredIf=ticked("doc_delivery_order"), max=2, format="number"),
            text("do_copies", "Delivery order: copies", requiredIf=ticked("doc_delivery_order"), max=2, format="number"),
            select("do_countersigned_by", "Countersigned by how many of our signatories", options=["One", "Two"], requiredIf=ticked("doc_delivery_order")),
            select("do_signature_verified", "Whose signature(s) ... to be verified by the Bank", options=["need", "need not"], requiredIf=ticked("doc_delivery_order")),
            check("doc_insurance", "Marine/Air Insurance Policy or Certificate in duplicate, in Singapore in the currency of the credit, covering Institute Cargo Clauses (A), Institute War Clauses, Institute Strikes Clauses / Strikes, Riots and Civil Commotion"),
            select("insurance_arrangement", "For FOB/CFR/FCA/CPT", options=["Insurance cover note attached", "Covered by ultimate buyer", "Please arrange insurance on our behalf", "Insurance covered by applicant under open Cover No."], activeIf=ticked("doc_insurance")),
            text("insurance_cover_no", "Open cover no", max=20, requiredIf=when("insurance_arrangement", "Insurance covered by applicant under open Cover No.")),
            text("insurance_cover_with", "With", max=35, requiredIf=when("insurance_arrangement", "Insurance covered by applicant under open Cover No.")),
            check("doc_beneficiary_certificate", "Beneficiary's certificate stating 1 set of non-negotiable documents has been sent to applicant"),
            checks("bencert_sent_by", "Sent by", options=["faxed", "mailed", "couriered"], requiredIf=ticked("doc_beneficiary_certificate")),
            text("bencert_days", "Within (days after shipment)", requiredIf=ticked("doc_beneficiary_certificate"), format="number"),
            check("doc_commercial_invoice", "Signed commercial invoice"),
            text("invoice_originals", "Commercial invoice: originals", requiredIf=ticked("doc_commercial_invoice"), max=2, format="number"),
            text("invoice_copies", "Commercial invoice: copies", requiredIf=ticked("doc_commercial_invoice"), max=2, format="number"),
            check("doc_packing_list", "Packing list"),
            text("packing_list_originals", "Packing list: originals", requiredIf=ticked("doc_packing_list"), max=2, format="number"),
            text("packing_list_copies", "Packing list: copies", requiredIf=ticked("doc_packing_list"), max=2, format="number"),
            check("doc_weight_note", "Weight note"),
            text("weight_note_originals", "Weight note: originals", requiredIf=ticked("doc_weight_note"), max=2, format="number"),
            text("weight_note_copies", "Weight note: copies", requiredIf=ticked("doc_weight_note"), max=2, format="number"),
            check("doc_certificate_of_origin", "Certificate of origin"),
            text("origin_originals", "Certificate of origin: originals", requiredIf=ticked("doc_certificate_of_origin"), max=2, format="number"),
            text("origin_copies", "Certificate of origin: copies", requiredIf=ticked("doc_certificate_of_origin"), max=2, format="number"),
            text("origin_country", "Showing country of origin as", requiredIf=ticked("doc_certificate_of_origin"), max=35),
            check("doc_other", "Other documents"),
            text("other_documents_1", "Other documents", max=70, requiredIf=ticked("doc_other")),
            text("other_documents_2", "Other documents (line 2)", max=70, activeIf=ticked("doc_other")),
        ]),
        section("Goods Description", fields=[
            long("goods_description", "Goods description (if space is insufficient, attach additional information with Company's stamp, signed by authorised signors)", max=6500, required=True),
        ]),
        section("Additional Conditions", fields=[
            long("additional_conditions", "Additional conditions (if space is insufficient, attach additional information with Company's stamp, signed by authorised signors)", max=6500),
        ]),
        section("Charges, Confirmation and Settlement", fields=[
            check("bank_charges", "All bank charges are for account of", required=True),
            radio("bank_charges_for", "Charges for account of", ["Beneficiary, except charges at DC Issuing Bank's counter", "Applicant (including all charges incurred inside and outside of DC Issuing Bank's country)"], requiredIf=ticked("bank_charges")),
            check("confirmation", "Confirmation required"),
            radio("confirmation_charges", "Confirmation charges", ["Applicant", "Beneficiary"], requiredIf=ticked("confirmation")),
            check("post_shipment_financing", "Please provide us with post-shipment financing under Documentary Credit (\"TR/BRP\") financing for 100% value of all documentary presentations made in compliance with this DC, but where there are discrepancies, we hereby agree to waive all such discrepancies"),
            radio("financing_type", "Financing", ["SGD financing", "Foreign Currency Financing", "Apply Forward Contract"], requiredIf=ticked("post_shipment_financing")),
            select("financing_currency", "Foreign currency financing in (type of currency)", options=CURRENCIES, requiredIf=when("financing_type", "Foreign Currency Financing")),
            text("forward_contract_no", "Forward contract no", max=20, requiredIf=when("financing_type", "Apply Forward Contract")),
            check("advance_payment", "We authorise you to debit DC amount in full from our account for advance payment"),
            text("advance_payment_account", "Account no for advance payment", requiredIf=ticked("advance_payment"), max=20, format="account"),
            check("debit_issuance_charges", "Please debit all DC issuance charges to our account with you"),
            text("issuance_charges_account", "Account no for DC issuance charges", required=True, max=17, format="account"),
        ]),
        section("Declaration and Signature", signoff=True, note="We request you to issue an irrevocable documentary credit on the terms above. We confirm that the details given are true and complete, and agree that the credit is subject to the Uniform Customs and Practice for Documentary Credits (UCP 600) and to the Bank's terms and conditions for documentary credits.", fields=[
            text("authorised_person", "Name and title of authorised person(s)"),
        ]),
    ],
}

# Answers already filled in when the form opens ({} for none).
DEFAULTS = {
    "mode_of_advising": "Full Swift",
    "presentation_days": "21",
    "bank_charges": True,
    "bank_charges_for": "Beneficiary, except charges at DC Issuing Bank's counter",
    "post_shipment_financing": True,
    "debit_issuance_charges": True,
}

# The PDF's file name in out/.
PDF_NAME = "LC-Application.pdf"

# The build stops if the form doesn't fit on this many pages (the QR code page included).
PAGES = 4
