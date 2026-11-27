"""THE LC APPLICATION FORM WITH THE OLD SMART FORM'S PIPE-DELIMITED QR TEXT (Form LC-01P).

Build it:   python build.py lc_pipe_form.py     -> out/LC-Application-Pipe.pdf

The same questions, wording, layout and rules as the LC form (forms/lc_form.py: this file imports them, so the two
cannot drift apart). The one difference is what Generate QR Code puts into the QR code: not the JSON of every answer, but
the 4 records of the old smart form's barcode, each field in a fixed position separated by "|":

    1|1234567|ACME TRADING PTE LTD|GLOBAL EXPORTS LLC|[88 HARBOUR STREET][SHENZHEN 518000][CHINA]|L5Y|L6N|USD|...
    2|[10 ANSON ROAD #12-01][INTERNATIONAL PLAZA]|||||+ FULL SET OF CLEAN ON BOARD MARINE BILLS OF LADING ...
    3||||+ SIGNED COMMERCIAL INVOICES IN 3 ORIGINALS AND 2 COPIES.|...
    4|500 UNITS INDUSTRIAL CENTRIFUGAL PUMPS ...|ALL DOCUMENTS MUST INDICATE THE CREDIT NUMBER.{}THIRD PARTY ...|

so a back end that reads that format keeps working. The 4 records go into the ordinary QR code one after the other, a
newline between records (the usual QR code path: one code, or two when the text is longer than one code holds).

THE POSITION TABLE (PIPE below, the "pipe" setting of FORM) is data: one entry per position, 62 in all, named as in the
old layout (1_01 ... 4_03). The engine (acrobat_js.py, PIPE_JS) reads it; to move a field, change a code, or put the CIF
number in, edit the table. Entries (all are checked at build time: every question must exist, every code must be an
answer of its question):
    {"p": "1_01", "c": "1"}                    a fixed text
    {"p": "1_03", "id": "applicant_name"}      the answer as typed
        "codes": {answer: code}                answers become codes (an answer not listed gives nothing)
        "as": "amount" | "date"                1250000.00 (no commas, 2 decimals) / 2027-02-28 (from DD/MM/YYYY)
        "max": 400                             cut after this many characters
    {"p": "1_05", "lines": [q, ...]}           each non-blank answer in [ ]
    {"p": "1_16", "join": [q, ...]}            the non-blank answers, one space between
    {"p": "2_07", "tpl": {...}}                a sentence made from the ticks and answers (see PIPE_JS)
    {"p": "3_05", "qty": {...}}                "+ SIGNED COMMERCIAL INVOICES IN 3 ORIGINALS AND 2 COPIES."
  and on any entry: "if": [q, [answers]]  (blank unless the answer is one of these), "d": text used when the result is
  blank (e.g. "0"), "chop": True  (long text in lines padded to 65 characters, joined by {}; Enter becomes {}).

WHAT THE OLD FORMAT CANNOT CARRY (30 of the 108 questions are not in the QR code, exactly as in the old form's barcode; the
printed PDF still has them): application date, contact name / tel / fax, DC no, bank code, back-to-back (3), "Drafts for the
percentage" tick and percentage, prepay choice, insurance arrangement and open cover (2), beneficiary contact / tel / fax,
bank charges tick, post-shipment financing (4), advance payment (2), debit issuance charges (2), authorised person, and the
4th address line of the applicant and beneficiary (the old form had 3). Positions with no question here use the old
layout's "if empty" value: 1_02 (CIF number) is 0000000; the eight reserved / unused ones (1_18 1_19 1_23 1_24 1_28 1_29
1_30 1_35) and 2_09 to 2_11 (HK only) are empty.

THE OLD FORM'S QUIRKS ARE KEPT ON PURPOSE (a back end built for it expects them): the goods description is cut at 400
characters and the additional conditions at 600 ("max" below: raise them if the Bank's back end allows); three advising
modes share the code S, Local Delivery and Others share O; 1_18, 1_19, 1_23, 1_24 are always empty, the port box goes into
1_16 / 1_21 and the place box into 1_17 / 1_22 (the two-box choices fill both); long text is padded to 65 characters (the old documents say 64). See GUIDE.md and README.md.
"""
import copy

from lc_form import COUNTRIES, CURRENCIES, DEFAULTS, FORM as LC_FORM  # noqa: F401  (COUNTRIES, CURRENCIES: the LC form's lists)

FROM_PORT = ["Port of Loading / Airport of Departure"]
TO_PORT = ["Port of Discharge / Airport of Destination"]
TICKED = ["true"]


def address(p, prefix, lines=3):
    return {"p": p, "lines": [f"{prefix}_{n}" for n in range(1, lines + 1)]}


def clause(p, **entry):
    return {"p": p, "chop": True, **entry}


PIPE = [
    # ---- Record 1 -----------------------------------------------------------------------------------------------
    [
        {"p": "1_01", "c": "1"},
        {"p": "1_02", "c": "0000000"},                     # CIF number: no question here
        {"p": "1_03", "id": "applicant_name"},
        {"p": "1_04", "id": "beneficiary_name"},
        address("1_05", "beneficiary_address"),
        {"p": "1_06", "id": "partial_shipment", "codes": {"allowed": "L5Y", "not allowed": "L5N"}},
        {"p": "1_07", "id": "transhipment", "codes": {"allowed": "L6Y", "not allowed": "L6N"}},
        {"p": "1_08", "id": "currency"},
        {"p": "1_09", "id": "amount", "as": "amount", "d": "0"},
        {"p": "1_10", "id": "gst", "codes": {"inclusive of GST": "GSY"}},
        {"p": "1_11", "id": "tolerance_plus", "if": ["tolerance", TICKED], "d": "0"},
        {"p": "1_12", "id": "tolerance_minus", "if": ["tolerance", TICKED], "d": "0"},
        {"p": "1_13", "id": "price_basis", "codes": {"FOB": "C", "CFR": "B", "CIF": "A", "Local Delivery": "O", "FCA": "D", "CIP": "G", "CPT": "F", "Others": "O"}},
        {"p": "1_14", "id": "price_basis_other", "if": ["price_basis", ["Others"]]},
        {"p": "1_15", "id": "shipment_from", "codes": {FROM_PORT[0]: "44E", "Dispatch from": "44A", "Place of Taking in charge": "44A", "Place of Receipt": "44A"}},
        {"p": "1_16", "join": ["shipment_from_port", "shipment_from_port_2"]},
        {"p": "1_17", "join": ["shipment_from_place", "shipment_from_place_2"]},
        {"p": "1_18", "c": ""},
        {"p": "1_19", "c": ""},
        {"p": "1_20", "id": "shipment_to", "codes": {TO_PORT[0]: "44F", "For Transportation to": "44B", "Place of Final Destination": "44B", "Place of Delivery": "44B"}},
        {"p": "1_21", "join": ["shipment_to_port", "shipment_to_port_2"]},
        {"p": "1_22", "join": ["shipment_to_place", "shipment_to_place_2"]},
        {"p": "1_23", "c": ""},
        {"p": "1_24", "c": ""},
        {"p": "1_25", "id": "latest_shipment_date", "as": "date"},
        {"p": "1_26", "id": "expiry_date", "as": "date"},
        {"p": "1_27", "id": "presentation_days", "d": "0"},
        {"p": "1_28", "c": ""},
        {"p": "1_29", "c": ""},
        {"p": "1_30", "c": ""},
        {"p": "1_31", "id": "drafts_at", "codes": {"Sight": "Y", "Term": "N", "Date": "N"}},
        {"p": "1_32", "id": "term_days", "if": ["drafts_at", ["Term"]], "d": "0"},
        {"p": "1_33", "id": "term_after", "if": ["drafts_at", ["Term"]]},
        {"p": "1_34", "id": "mode_of_advising", "codes": {"Full Swift": "S", "Registered Airmail": "A", "Airmail with Brief Swift": "S", "Courier Service": "U", "Courier Service with Brief Swift": "S"}},
        {"p": "1_35", "c": ""},
        {"p": "1_36", "id": "draft_date", "as": "date", "if": ["drafts_at", ["Date"]]},
    ],
    # ---- Record 2 -----------------------------------------------------------------------------------------------
    [
        {"p": "2_01", "c": "2"},
        address("2_02", "applicant_address"),
        {"p": "2_03", "id": "third_party_name"},
        address("2_04", "third_party_address"),
        {"p": "2_05", "id": "advising_bank_name"},
        address("2_06", "advising_bank_address"),
        clause("2_07", tpl={"when": "doc_bill_of_lading", "parts": [
            "+ FULL SET OF CLEAN ON BOARD MARINE BILLS OF LADING MADE OUT TO ORDER",
            ["map", "bl_made_out_to", {"order of the Bank": " OF THE BANK LIMITED, NOTIFYING ",
                                       "order blank endorsed": ", BLANK ENDORSED, NOTIFYING ",
                                       "other (specify)": " OF {bl_made_out_to_other}, NOTIFYING "}],
            "{bl_notify_party} MARKED 'FREIGHT ",
            ["map", "bl_freight", {"Prepaid": "PREPAID'.", "Collect": "COLLECT'."}]]}),
        clause("2_08", tpl={"when": "doc_air_waybill", "parts": [
            "+ ORIGINAL CLEAN AIR WAYBILL CONSIGNED TO THE BANK LIMITED, MARKED 'FREIGHT ",
            ["map", "awb_freight", {"Prepaid": "PREPAID' NOTIFYING ", "Collect": "COLLECT' NOTIFYING "}],
            "{awb_notify_party}."]}),
        {"p": "2_09", "c": ""},
        {"p": "2_10", "c": ""},
        {"p": "2_11", "c": ""},
        {"p": "2_12", "id": "confirmation", "codes": {"true": "L9Y"}, "d": "L9N"},
        {"p": "2_13", "id": "bank_charges_for", "codes": {"Beneficiary, except charges at DC Issuing Bank's counter": "LAB",
                                                          "Applicant (including all charges incurred inside and outside of DC Issuing Bank's country)": "LAA"}},
        {"p": "2_14", "id": "confirmation_charges", "codes": {"Applicant": "LID", "Beneficiary": "LIC"}},
    ],
    # ---- Record 3 -----------------------------------------------------------------------------------------------
    [
        {"p": "3_01", "c": "3"},
        clause("3_02", tpl={"when": "doc_delivery_order", "parts": [
            "+ DELIVERY ORDER IN {do_originals} ORIGINALS {do_copies} COPIES SIGNED BY BENEFICIARY MADE OUT TO APPLICANT AND "
            "COUNTERSIGNED BY {do_countersigned_by} OF OUR SIGNATORIES, WHOSE SIGNATURE(S) {do_signature_verified} BE VERIFIED BY THE BANK LIMITED."]}),
        clause("3_03", tpl={"when": "doc_insurance", "parts": [
            "+ INSURANCE POLICY/CERTIFICATE IN DUPLICATE SHOWING BENEFICIARY AS ASSURED, BLANK ENDORSED FOR 110 PERCENT OF INVOICE VALUE "
            "WITH CLAIMS PAYABLE IN SINGAPORE IN THE CURRENCY OF THE CREDIT COVERING INSTITUTE CARGO CLAUSE (A), INSTITUTE WAR CLAUSES, "
            "INSTITUTE STRIKES CLAUSES/SRCC."]}),
        clause("3_04", tpl={"when": "doc_beneficiary_certificate", "parts": [
            "+ BENEFICIARY'S CERTIFICATE CERTIFYING THAT ONE SET OF NON-NEGOTIABLE DOCUMENTS HAS BEEN ",
            ["list", "bencert_sent_by", ", ", [["faxed", "FAXED"], ["mailed", "MAILED"], ["couriered", "COURIERED"]]],
            " TO THE APPLICANT ",
            ["if", "bencert_days", "WITHIN {bencert_days} DAY(S) AFTER SHIPMENT.", "AFTER SHIPMENT."]]}),
        {"p": "3_05", "qty": {"on": "doc_commercial_invoice", "o": "invoice_originals", "c": "invoice_copies", "head": "+ SIGNED COMMERCIAL INVOICES"}},
        {"p": "3_06", "qty": {"on": "doc_packing_list", "o": "packing_list_originals", "c": "packing_list_copies", "head": "+ PACKING LIST"}},
        {"p": "3_07", "qty": {"on": "doc_weight_note", "o": "weight_note_originals", "c": "weight_note_copies", "head": "+ WEIGHT NOTE"}},
        clause("3_08", qty={"on": "doc_certificate_of_origin", "o": "origin_originals", "c": "origin_copies", "head": "+ CERTIFICATE OF ORIGIN",
                            "tail": ["origin_country", ", SHOWING COUNTRY OF ORIGIN AS {origin_country}"]}),
        clause("3_09", join=["other_documents_1", "other_documents_2"], **{"if": ["doc_other", TICKED]}),
    ],
    # ---- Record 4 -----------------------------------------------------------------------------------------------
    [
        {"p": "4_01", "c": "4"},
        clause("4_02", id="goods_description", max=400),
        clause("4_03", id="additional_conditions", max=600),
    ],
]

FORM = copy.deepcopy(LC_FORM)
FORM["formCode"] = "Form LC-01P · v1.0 · Nov 2026"
FORM["qrFormat"] = "pipe"
FORM["pipe"] = PIPE

PDF_NAME = "LC-Application-Pipe.pdf"   # written to out/
IN_MENU = False                         # not in build_all.py's menu (the one PDF stays 13 forms)
