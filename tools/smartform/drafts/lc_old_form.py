"""Irrevocable Documentary Credit Application (Form LC-01).

Build it:   python build.py lc_old_form.py     -> out/LC-old.pdf

Redrawn from the old vendor smart form: every question in its order and wording, with the old form's mandatory and
conditional rules (125 questions, 17 always mandatory). Step by step: GUIDE.md.
"""
from build import answered, check, checks, date, long, radio, section, select, text, ticked, when
from lc_form import CURRENCIES   # the same currency list as the LC form

FORM = {
    "title": "Irrevocable Documentary Credit Application",
    "note": "Please complete in block letters. Dates are DD/MM/YYYY.",
    "issuer": "Demo Bank · Trade Services",
    "formCode": "Form LC-01 · v1.0 · Nov 2026",
    "sections": [
        section("Mode of advising", fields=[
            radio("mode_of_advising", "Mode of Advising", ["Full Swift", "Registered Airmail", "Airmail with Brief Swift", "Courier Service", "Courier Service with Brief Swift"]),
        ]),
        section("Applicant", fields=[
            text("applicant_name", "Applicant Name", required=True, max=35),
            text("applicant_address1", "Applicant Address", required=True, max=35),
            text("applicant_address2", "Applicant Address (line 2)", max=35),
            text("applicant_address3", "Applicant Address (line 3)", max=35),
            text("applicant_contract_name", "Name", required=True, max=35),
            text("applicant_tel", "Tel No", required=True, max=15, format="phone"),
            text("applicant_fax", "Fax No", max=15, format="phone"),
        ]),
        section("For bank use", fields=[
            text("for_bank_use_dcno", "DC No"),
            text("for_bank_use_bank_code", "Bank Code"),
            text("advising_bank_name", "Name", max=35),
            text("advising_bank_address1", "Address", max=35),
            text("advising_bank_address2", "Address (line 2)", max=35),
            text("advising_bank_address3", "Address (line 3)", max=35),
        ]),
        section("3party beneficiary", fields=[
            text("3_party_beneficiary_name", "Name", max=35),
            text("3_party_beneficiary_address1", "Address", max=35),
            text("3_party_beneficiary_address2", "Address (line 2)", max=35),
            text("3_party_beneficiary_address3", "Address (line 3)", max=35),
        ]),
        section("Beneficiary", fields=[
            text("beneficiary_name", "Beneficiary's Name", required=True, max=35),
            text("beneficiary_address1", "Beneficiary's Address", required=True, max=35),
            text("beneficiary_address2", "Beneficiary's Address (line 2)", max=35),
            text("beneficiary_address3", "Beneficiary's Address (line 3)", max=35),
            text("beneficiary_contract_name", "Contact Person", max=35),
            text("beneficiary_tel", "Tel No", max=15, format="phone"),
            text("beneficiary_fax", "Fax No", max=15, format="phone"),
        ]),
        section("Credit amount", fields=[
            select("credit_amount_currency", "Currency", options=CURRENCIES, required=True),
            text("credit_amount_amount", "Amount", required=True, format="number"),
            radio("credit_amount_gst", "For Local DCs, amount is", ["inclusive of GST", "No GST"]),
            check("credit_amount_tolerance", "Tolerance on credit amount & goods quantity"),
            text("credit_amount_plus_value", "+/-", requiredIf=ticked("credit_amount_tolerance"), max=2),
            text("credit_amount_minus_value", "/", requiredIf=ticked("credit_amount_tolerance"), max=2),
        ]),
        section("Price basis", fields=[
            radio("price_basis", "Price Basis", ["FOB", "CFR", "Local Delivery", "FCA", "CIP", "CPT", "Others"], required=True),
            text("price_basis_others", "Price Basis", requiredIf=when("price_basis", "Others"), max=35),
        ]),
        section("Partialshipment", fields=[
            radio("partialshipment_partial_shipment", "Partial shipment", ["allowed", "not allowed"], required=True),
            radio("partialshipment_transhipment", "Transhipment", ["allowed", "not allowed"], required=True),
        ]),
        section("Shipment from", fields=[
            select("shipment_from_port_of_loading", "Loading", options=["<Select value for Shipment From>", "Port of Loading / Airport of Departure", "Dispatch from", "Place of Taking in charge", "Place of Receipt"]),
            text("place_of_receipt_place_of_receipt1", "Loading (line 1)", activeIf=when("shipment_from_port_of_loading", "Place of Receipt"), max=35),
            text("place_of_receipt_place_of_receipt2", "Loading (line 2)", activeIf=when("shipment_from_port_of_loading", "Place of Receipt")),
            text("place_of_taking_in_charge_place_of_taking_in_charge1", "Loading (line 1)", activeIf=when("shipment_from_port_of_loading", "Place of Taking in charge"), max=35),
            text("place_of_taking_in_charge_place_of_taking_in_charge2", "Loading (line 2)", activeIf=when("shipment_from_port_of_loading", "Place of Taking in charge")),
            text("dispatchfrom_dispatchfrom1", "Loading (line 1)", activeIf=when("shipment_from_port_of_loading", "Dispatch from"), max=35),
            text("dispatchfrom_dispatchfrom2", "Loading (line 2)", activeIf=when("shipment_from_port_of_loading", "Dispatch from")),
            text("port_of_load_loading1", "Loading (line 1)", activeIf=when("shipment_from_port_of_loading", "Port of Loading / Airport of Departure", "Place of Taking in charge"), max=35),
            text("port_of_load_loading2", "Loading (line 2)", activeIf=when("shipment_from_port_of_loading", "Port of Loading / Airport of Departure", "Place of Taking in charge")),
            text("airport_of_departure_departure1", "Loading (line 1)", max=35),
            text("airport_of_departure_departure2", "Loading (line 2)"),
        ]),
        section("Shipment to", fields=[
            select("shipment_to_port_of_discharge", "Discharge", options=["<Select value for Shipment To>", "Port of Discharge / Airport of Destination", "For Transportation to", "Place of Final Destination", "Place of Delivery"]),
            text("for_transportation_to_for_transportation_to1", "Discharge (line 1)", activeIf=when("shipment_to_port_of_discharge", "For Transportation to"), max=35),
            text("for_transportation_to_for_transportation_to2", "Discharge (line 2)", activeIf=when("shipment_to_port_of_discharge", "For Transportation to")),
            text("destination_destination1", "Discharge (line 1)", max=35),
            text("destination_destination2", "Discharge (line 2)"),
            text("place_of_final_destination_place_of_final_destination1", "Discharge (line 1)", activeIf=when("shipment_to_port_of_discharge", "Place of Final Destination"), max=35),
            text("place_of_final_destination_place_of_final_destination2", "Discharge (line 2)", activeIf=when("shipment_to_port_of_discharge", "Place of Final Destination")),
            text("place_of_delivery_place_of_delivery1", "Discharge (line 1)", activeIf=when("shipment_to_port_of_discharge", "Place of Delivery"), max=35),
            text("place_of_delivery_place_of_delivery2", "Discharge (line 2)", activeIf=when("shipment_to_port_of_discharge", "Place of Delivery")),
            text("discharge_discharge1", "Discharge (line 1)", activeIf=when("shipment_to_port_of_discharge", "Port of Discharge / Airport of Destination", "Place of Final Destination"), max=35),
            text("discharge_discharge2", "Discharge (line 2)", activeIf=when("shipment_to_port_of_discharge", "Port of Discharge / Airport of Destination", "Place of Final Destination")),
        ]),
        section("Shipment date", fields=[
            date("shipment_date_date", "Latest shipment date"),
        ]),
        section("Date of expiry", fields=[
            date("date_of_expiry_date", "(in beneficiary's country)", required=True),
        ]),
        section("Presentation", fields=[
            text("presentation_period", "(in beneficiary's country)", max=2, format="number"),
        ]),
        section("Drafts", fields=[
            text("bto_b_cr_no", "This is a back-to-back DC to be issued against the master credit no.", activeIf=ticked("bto_b_btb"), max=20),
            text("bto_b_issu_by", "issue by", activeIf=ticked("bto_b_btb"), max=35),
            check("bto_b_btb", "This is a back-to-back DC to be issued against the master credit no."),
            check("drafts_draft", "Drafts for 100% invoice value at"),
            radio("draft_drafts", "This is a back-to-back DC to be issued against the master credit no.", ["Sight or", "Term", "Date"], activeIf=ticked("drafts_draft")),
            text("draft_term", "This is a back-to-back DC to be issued against the master credit no.", requiredIf=when("draft_drafts", "Term"), max=3, format="number"),
            text("draft_days_after", "days after", requiredIf=when("draft_drafts", "Term"), max=35),
            radio("drafts_draft_term", "Documents Required", ["You may prepay the acceptance of this term LC at the cost of beneficiary", "You may not prepay the acceptance of this term LC"]),
            date("draft_date", "Date", requiredIf=when("draft_drafts", "Date")),
            check("drafts_full_set", "Full set of Clean on Board marine bills of lading made out to"),
            text("drafts_full_set_2", "Full set of Clean on Board marine bills of lading made out to (line 2)", requiredIf=when("drafts_consignee", "3"), max=70),
            radio("drafts_consignee", "Documents Required", ["order of Demo Bank Ltd or", "order blank endorsed, marked Freight", "3"], requiredIf=ticked("drafts_full_set")),
            radio("drafts_freight", "Documents Required", ["Prepaid or", "Collect"], requiredIf=ticked("drafts_full_set")),
            text("drafts_notify_party", "Notify party", requiredIf=ticked("drafts_full_set"), max=114),
        ]),
        section("Original air waybill", fields=[
            check("original_air_waybill", "Original Air Waybill consigned to Demo Bank Ltd marked Freight"),
            radio("original_air_waybill_2", "(if not specify, notify party is considered to be applicant)", ["Prepaid or", "Collect"], requiredIf=ticked("original_air_waybill")),
            text("original_air_waybill_notify_party", "Notify party", requiredIf=ticked("original_air_waybill"), max=114),
        ]),
        section("Transport documents by do", fields=[
            check("transport_documents_by_do_delivery_order_in", "Delivery order in"),
            text("transport_documents_by_do_originals", "originals", requiredIf=ticked("transport_documents_by_do_delivery_order_in"), max=2, format="number"),
            text("transport_documents_by_do_copies", "copies", requiredIf=ticked("transport_documents_by_do_delivery_order_in"), max=2, format="number"),
            select("transport_documents_by_do_countersigned_by", "By", options=["One", "Two"], requiredIf=ticked("transport_documents_by_do_delivery_order_in")),
            select("transport_documents_by_do_whose_signature", "of our signatories, whose signature(s)", options=["need", "need not"], requiredIf=ticked("transport_documents_by_do_delivery_order_in")),
        ]),
        section("Insurance", fields=[
            check("insurance", "Marine/Air Insurance Policy or Certificate in duplicate showing beneficiary as assured, blank endorsed for 110% of invoice value with claims payable"),
            select("insurance_for_fobcfr", "For FOB/CFR/FCA/CPT", options=["Insurance cover note attached", "Covered by ultimate buyer", "Please arrange insurance on our behalf", "Insurance covered by applicant under open Cover No."], activeIf=when("price_basis", "FOB", "CFR", "FCA", "CPT")),
            text("insurance_cover_no", "in Singapore in the currency of the credit covering, Institute Cargo Clauses (A), Institute War Clauses, Institute Strikes Clauses/Strikes, Riots and Civil Commotion.", requiredIf=when("price_basis", "CFR", "FCA", "CPT"), activeIf=when("price_basis", "CFR", "FCA", "CPT") + when("price_basis", "CFR", "FCA", "CPT"), max=20),
            text("cover_no_with", "with", requiredIf=when("price_basis", "CFR", "FCA", "CPT"), activeIf=when("price_basis", "CFR", "FCA", "CPT") + when("price_basis", "CFR", "FCA", "CPT"), max=35),
        ]),
        section("Beneficiary certificate", fields=[
            check("beneficiary_certificate", "Beneficiary's certificate stating 1 set of non-negotiable documents have been"),
            check("beneficiary_certificate_faxed", "faxed,", requiredIf=ticked("beneficiary_certificate"), format="phone"),
            check("beneficiary_certificate_mailed", "mailed,", requiredIf=ticked("beneficiary_certificate")),
            check("beneficiary_certificate_couriered", "couriered to", requiredIf=ticked("beneficiary_certificate")),
            text("beneficiary_certificate_days_after_shipment", "days after shipment.", activeIf=ticked("beneficiary_certificate"), max=2, format="number"),
        ]),
        section("Lcfoot", fields=[
            check("invoice_signed_commercial_invoice", "Signed commercial invoice in"),
            text("invoice_signed_originals", "originals and", activeIf=ticked("invoice_signed_commercial_invoice"), max=2, format="number"),
            text("invoice_signed_copies", "copies", activeIf=ticked("invoice_signed_commercial_invoice"), max=2, format="number"),
            check("invoice_packing_list", "Packing list in"),
            text("invoice_packing_list_originals", "originals and", activeIf=ticked("invoice_packing_list"), max=2, format="number"),
            text("invoice_packing_list_copies", "copies", activeIf=ticked("invoice_packing_list"), max=2, format="number"),
            check("invoice_weight_note", "Weight Note in"),
            text("invoice_weight_note_originals", "originals and", activeIf=ticked("invoice_weight_note"), max=2, format="number"),
            text("invoice_weight_note_copies", "copies", activeIf=ticked("invoice_weight_note"), max=2, format="number"),
            check("invoice_certificate_of_origin", "Certificate of Origin in"),
            text("invoice_certificate_of_origin_in_originals", "originals and", activeIf=ticked("invoice_certificate_of_origin"), max=2, format="number"),
            text("invoice_certificate_of_origin_copies", "copies,", activeIf=ticked("invoice_certificate_of_origin"), max=2, format="number"),
            text("invoice_certificate_of_origin_country", "showing country of origin as", activeIf=ticked("invoice_certificate_of_origin"), max=35),
            check("other_doc_beneficiary_certificate", "Other documents"),
            text("other_doc", "Doc", requiredIf=ticked("other_doc_beneficiary_certificate"), max=70),
            text("other_doc_other_doc1", "Doc (line 1)", activeIf=ticked("other_doc_beneficiary_certificate"), max=70),
            long("goods_description", "Goods Description: If space is insufficient, please submit additional information as an attachment (with Company's stamp and signed by authorised signors)", required=True, max=6500),
            long("additional_cond", "Additional Conditions: If space is insufficient, please submit additional information as an attachment (with Company's stamp and signed by authorised signors)", max=6500),
            check("one_bank_charges", "All Bank Charges are for account of"),
            radio("bank_charges_charge_account", "Bank_charges_charge_account", ["Beneficiary, except charges at DC Issuing Bank's counter", "Applicant (including all charges incurred inside and outside of"], required=True),
            check("one_reimbursement_instructions", "Pay upon receipt of documents at Demo Bank Ltd's counters in Singapore"),
            check("one_confirmation", "Confirmation required"),
            radio("details_one_confirmation", "Confirmation charges", ["Applicant", "Beneficiary"], requiredIf=ticked("one_confirmation")),
            check("settlement_instructions_trust_receipts", "Please provide us with post-shipment financing under Documentary Credit"),
            radio("one_settlement_instructions_trust_receipts", "(\"TR/BRP\") financing", ["SGD financing, or", "Foreign Currency Financing in", "Apply Forward Contract No"], required=True),
            text("settlement_instructions_forgeign", "(\"TR/BRP\") financing", requiredIf=when("one_settlement_instructions_trust_receipts", "Foreign Currency Financing in"), max=20),
            text("settlement_instructions_apply_forward", "(type of currency), or", requiredIf=when("one_settlement_instructions_trust_receipts", "Apply Forward Contract No"), max=20),
            check("settlement_instructions_btb", "We authorise you to debit DC amount in full from our account no."),
            check("one_pay", "T/T reimbursement allowed"),
            check("issuance_charges_debit", "Please debit all DC issuance charges to our account"),
            text("issuance_charges_withyou", "with you.", required=True, max=17),
            text("two_signature", "Authorised Person(s) & Company Stamp"),
        ]),
        section("Xfa", fields=[
            date("form1_lcdate", "Date", required=True),
        ]),
        section("Lcfoot", fields=[
            text("settlement_instructions_apply_forward_1", "Date (line 1)", max=20),
        ]),
    ],
}

DEFAULTS = {}

PDF_NAME = "LC-old.pdf"
PAGES = None
