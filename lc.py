"""THE FORM: the Irrevocable Documentary Credit (LC) application, Form LC-01.

Each question is one line. For example
    text("term_days", "Term: days", requiredIf=when("drafts_at", "Term"), format="number"),
is a half-width text box named term_days, labelled "Term: days", mandatory (and unlocked) only when
Drafts at = Term, digits only. The layout, numbering, scripts and QR code all follow from these lines.

Question kinds:  text, long (paragraph), date, radio (pick one), checks (tick any), check (one tick box), select (drop-down)
Options:
    required=True                    always mandatory (red *)
    requiredIf=ticked("x")           mandatory, and unlocked, only when tick box x is ticked
    requiredIf=when("x", "A", "B")   mandatory only when x is A or B
    requiredIf=answered("x")         mandatory once x has any answer (never locked)
    activeIf=ticked("x")             only applies (unlocked) when x is ticked, but optional
    max=35                           at most 35 characters
    format="amount"                  amount / number / phone / account (see FORMATS in build_lc.py)
    half=False                       full width (text boxes are half width unless this is given)
    beside=69.3                      label beside a box this wide, even when the label is long (only 13.2)
After a change:  python build_lc.py   (builds the PDF, checks it, and refreshes the tables in README.md)
"""


def ask(kind):
    def make(id, label, **more):
        return {"id": id, "label": label, "kind": kind, **more}
    return make


long, date, checks, select = ask("long"), ask("date"), ask("checks"), ask("select")


def text(id, label, **more):
    return {"id": id, "label": label, "kind": "text", "half": True, **more}


def check(id, label, **more):
    return {"id": id, "label": label, "kind": "check", **more}


def radio(id, label, options, **more):
    return {"id": id, "label": label, "kind": "radio", "options": options, **more}


def section(title, **more):
    return {"title": title, **more}


def when(field, *values):
    return [{"field": field, "values": list(values)}]


def ticked(field):
    return when(field, "true")


def answered(field):
    return [{"field": field, "values": [""], "not": True}]


# ISO 4217 currency codes, common trade currencies first.
CURRENCIES = ["SGD", "USD", "EUR", "GBP", "JPY", "CNY", "HKD", "AUD", "NZD", "CAD", "CHF", "MYR", "IDR", "THB", "INR", "KRW", "TWD", "PHP", "VND", "AED", "SAR", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AWG", "AZN", "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL", "BSD", "BTN", "BWP", "BYN", "BZD", "CDF", "CLP", "COP", "CRC", "CUC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD", "EGP", "ERN", "ETB", "FJD", "FKP", "GEL", "GHS", "GIP", "GMD", "GNF", "GTQ", "GYD", "HNL", "HRK", "HTG", "HUF", "ILS", "IQD", "IRR", "ISK", "JMD", "JOD", "KES", "KGS", "KHR", "KMF", "KPW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD", "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU", "MUR", "MVR", "MWK", "MXN", "MZN", "NAD", "NGN", "NIO", "NOK", "NPR", "OMR", "PAB", "PEN", "PGK", "PKR", "PLN", "PYG", "QAR", "RON", "RSD", "RUB", "RWF", "SBD", "SCR", "SDG", "SEK", "SHP", "SLE", "SOS", "SRD", "SSP", "STN", "SVC", "SYP", "SZL", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TZS", "UAH", "UGX", "UYU", "UZS", "VES", "VUV", "WST", "XAF", "XCD", "XCG", "XDR", "XOF", "XPF", "XSU", "YER", "ZAR", "ZMW", "ZWG"]

SECTIONS = [
    section("Application", fields=[
        date("application_date", "Date", half=True, required=True),
    ]),
    section("Mode of Advising", fields=[
        radio("mode_of_advising", "Mode of advising", ["Full Swift", "Registered Airmail", "Airmail with Brief Swift", "Courier Service", "Courier Service with Brief Swift"], required=True),
    ]),
    section("Applicant", fields=[
        text("applicant_name", "Applicant name", half=False, required=True, max=35),
        text("applicant_address_1", "Applicant address", half=False, required=True, max=35),
        text("applicant_address_2", "Applicant address (line 2)", half=False, max=35),
        text("applicant_address_3", "Applicant address (line 3)", half=False, max=35),
        text("applicant_address_4", "Applicant address (line 4)", half=False, max=35),
        text("contact_name", "Contact party for this application & confirmation of FX rate: Name", half=False, required=True, max=35),
        text("contact_tel", "Contact party: Tel no", required=True, max=15, format="phone"),
        text("contact_fax", "Contact party: Fax no", max=15, format="phone"),
    ]),
    section("For Bank Use Only", bankOnly=True, fields=[
        text("dc_no", "DC no"),
        text("bank_code", "Bank code"),
    ]),
    section("Advising Bank (at Issuing Bank's option, if no nomination)", fields=[
        text("advising_bank_name", "Name", half=False, max=35),
        text("advising_bank_address_1", "Address", half=False, max=35),
        text("advising_bank_address_2", "Address (line 2)", half=False, max=35),
        text("advising_bank_address_3", "Address (line 3)", half=False, max=35),
    ]),
    section("For the Benefit of a 3rd Party", fields=[
        text("third_party_name", "Name", half=False, max=35),
        text("third_party_address_1", "Address", half=False, max=35),
        text("third_party_address_2", "Address (line 2)", half=False, max=35),
        text("third_party_address_3", "Address (line 3)", half=False, max=35),
    ]),
    section("Beneficiary", fields=[
        text("beneficiary_name", "Beneficiary's name", half=False, required=True, max=35),
        text("beneficiary_address_1", "Beneficiary's address", half=False, required=True, max=35),
        text("beneficiary_address_2", "Beneficiary's address (line 2)", half=False, max=35),
        text("beneficiary_address_3", "Beneficiary's address (line 3)", half=False, max=35),
        text("beneficiary_address_4", "Beneficiary's address (line 4)", half=False, max=35),
        text("beneficiary_contact", "Contact person", half=False, max=35),
        text("beneficiary_tel", "Tel no", max=15, format="phone"),
        text("beneficiary_fax", "Fax no", max=15, format="phone"),
    ]),
    section("Credit Amount (Currency & Figures)", fields=[
        select("currency", "Currency", options=CURRENCIES, half=True, required=True),
        text("amount", "Amount", required=True, format="amount"),
        radio("gst", "For local DCs, amount is (if not checked, it will be inclusive of GST)", ["inclusive of GST", "No GST"]),
        check("tolerance", "Tolerance on credit amount & goods quantity"),
        text("tolerance_plus", "Tolerance + (%)", requiredIf=ticked("tolerance"), max=2, format="number"),
        text("tolerance_minus", "Tolerance - (%)", requiredIf=ticked("tolerance"), max=2, format="number"),
    ]),
    section("Price Basis", fields=[
        radio("price_basis", "Price basis", ["FOB", "CFR", "CIF", "Local Delivery", "FCA", "CIP", "CPT", "Others"], required=True),
        text("price_basis_other", "Others (please specify)", half=False, max=35, requiredIf=when("price_basis", "Others")),
    ]),
    section("Shipment", fields=[
        radio("partial_shipment", "Partial shipment", ["allowed", "not allowed"], required=True, half=True),
        radio("transhipment", "Transhipment", ["allowed", "not allowed"], required=True, half=True),
        select("shipment_from", "Shipment from", half=True, options=["Port of Loading / Airport of Departure", "Dispatch from", "Place of Taking in charge", "Place of Receipt"]),
        text("shipment_from_place", "Shipment from: place", max=35, requiredIf=answered("shipment_from")),
        text("shipment_from_place_2", "Shipment from: place (line 2)", half=False),
        select("shipment_to", "Shipment to", half=True, options=["Port of Discharge / Airport of Destination", "For Transportation to", "Place of Final Destination", "Place of Delivery"]),
        text("shipment_to_place", "Shipment to: place", max=35, requiredIf=answered("shipment_to")),
        text("shipment_to_place_2", "Shipment to: place (line 2)", half=False),
        date("latest_shipment_date", "Latest shipment date", half=True),
    ]),
    section("Expiry and Presentation", fields=[
        date("expiry_date", "Date of expiry (in beneficiary's country)", half=True, required=True),
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
        date("draft_date", "Date", half=True, requiredIf=when("drafts_at", "Date")),
        radio("term_prepay", "If it is a term LC, please select one", ["You may prepay the acceptance of this term LC at the cost of beneficiary", "You may not prepay the acceptance of this term LC"], requiredIf=when("drafts_at", "Term")),
    ]),
    section("Documents Required", fields=[
        check("doc_bill_of_lading", "Full set of Clean on Board marine bills of lading"),
        radio("bl_made_out_to", "Made out to", ["order of the Bank", "order blank endorsed", "other (specify)"], requiredIf=ticked("doc_bill_of_lading")),
        text("bl_made_out_to_other", "Made out to (other)", requiredIf=when("bl_made_out_to", "other (specify)"), max=70),
        radio("bl_freight", "Marked Freight", ["Prepaid", "Collect"], half=True, requiredIf=ticked("doc_bill_of_lading")),
        text("bl_notify_party", "Notify party (if not specified, notify party is considered to be applicant)", half=False, max=114, requiredIf=ticked("doc_bill_of_lading")),
        check("doc_air_waybill", "Original Air Waybill consigned to the Bank"),
        radio("awb_freight", "Marked Freight", ["Prepaid", "Collect"], half=True, requiredIf=ticked("doc_air_waybill")),
        text("awb_notify_party", "Notify party (if not specified, notify party is considered to be applicant)", half=False, max=114, requiredIf=ticked("doc_air_waybill")),
        check("doc_delivery_order", "Delivery order signed by beneficiary made out to applicant"),
        text("do_originals", "Delivery order: originals", requiredIf=ticked("doc_delivery_order"), max=2, format="number"),
        text("do_copies", "Delivery order: copies", requiredIf=ticked("doc_delivery_order"), max=2, format="number"),
        select("do_countersigned_by", "Countersigned by how many of our signatories", half=True, options=["One", "Two"], requiredIf=ticked("doc_delivery_order")),
        select("do_signature_verified", "Whose signature(s) ... to be verified by the Bank", half=True, options=["need", "need not"], requiredIf=ticked("doc_delivery_order")),
        check("doc_insurance", "Marine/Air Insurance Policy or Certificate in duplicate, in Singapore in the currency of the credit, covering Institute Cargo Clauses (A), Institute War Clauses, Institute Strikes Clauses / Strikes, Riots and Civil Commotion"),
        select("insurance_arrangement", "For FOB/CFR/FCA/CPT", half=False, options=["Insurance cover note attached", "Covered by ultimate buyer", "Please arrange insurance on our behalf", "Insurance covered by applicant under open Cover No."], activeIf=ticked("doc_insurance")),
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
        text("other_documents_1", "Other documents", half=False, max=70, requiredIf=ticked("doc_other")),
        text("other_documents_2", "Other documents (line 2)", half=False, max=70, activeIf=ticked("doc_other")),
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
        select("financing_currency", "Foreign currency financing in (type of currency)", half=True, options=CURRENCIES, requiredIf=when("financing_type", "Foreign Currency Financing")),
        text("forward_contract_no", "Forward contract no", max=20, requiredIf=when("financing_type", "Apply Forward Contract")),
        check("advance_payment", "We authorise you to debit DC amount in full from our account for advance payment"),
        text("advance_payment_account", "Account no for advance payment", requiredIf=ticked("advance_payment"), max=20, format="account"),
        check("debit_issuance_charges", "Please debit all DC issuance charges to our account with you"),
        text("issuance_charges_account", "Account no for DC issuance charges", required=True, max=17, format="account"),
    ]),
    section("Declaration and Signature", signoff=True, note="We request you to issue an irrevocable documentary credit on the terms above. We confirm that the details given are true and complete, and agree that the credit is subject to the Uniform Customs and Practice for Documentary Credits (UCP 600) and to the Bank's terms and conditions for documentary credits.", fields=[
        text("authorised_person", "Name and title of authorised person(s)", half=False),
    ]),

]

LC = {
    "title": "Irrevocable Documentary Credit Application",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "sections": SECTIONS,
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form LC-01 · v1.0 · Nov 2026",
}

# The answers already filled in when the form opens.
DEFAULTS = {
    "mode_of_advising": "Full Swift",
    "presentation_days": "21",
    "bank_charges": True,
    "bank_charges_for": "Beneficiary, except charges at DC Issuing Bank's counter",
    "post_shipment_financing": True,
    "debit_issuance_charges": True,
}
