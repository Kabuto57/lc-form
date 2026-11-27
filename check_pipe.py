#!/usr/bin/env python3
"""THE ORACLE TEST OF THE PIPE-FORMAT FORM (forms/lc_pipe_form.py).     python check_pipe.py [--cases 300] [--decode]

Proves that the 4 records the PDF's own JavaScript writes are byte-for-byte the records the OLD smart form's own barcode
code writes for the same answers:
  (a) build the PDF, take its document script, run lcPipeRecords in node against a minimal fake of Acrobat's document
      (check_pipe_mock.js: fields that hold values, nothing else);
  (b) translate the same answers to the old form's field paths (to_old below, written separately from the form's table),
      and run the old code with tools/run_lc_barcode.mjs of the smart-form extract;
  (c) compare. Done for the golden sample of the extract, then for random valid answer sets (every question's rules
      respected: mandatory, locked, formats) with empty optionals, 1-3 line addresses, long text with Enter, every option
      of every question, and stale answers left in locked boxes.
Then it proves the test can fail: the same comparison on a form whose table has one code changed must disagree.

--decode (needs `pip install zxing-cpp`, not part of requirements.txt): also runs the Generate QR Code button's script in the
fake document, draws the QR matrices it fills in, decodes them with zxing-cpp and compares the text with the records.

Needs node, and the smart-form extract (the old form's scripts and the golden sample): SMARTFORM_EXTRACT=<folder>
(default ~/Documents/trade-smartform-extract). Exit 0 = everything matched; anything else = a failure or a missing tool
(a missing extract is a failure, never a skip).
"""
import argparse
import contextlib
import copy
import datetime
import io
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import zlib

import pikepdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "forms"))
from build import check_form, load_form  # noqa: E402
from layout import FORMATS, active_rules  # noqa: E402
from pdf_writer import build  # noqa: E402

EXTRACT = os.path.expanduser(os.environ.get("SMARTFORM_EXTRACT", "~/Documents/trade-smartform-extract"))
OLD_RUNNER = os.path.join(EXTRACT, "tools", "run_lc_barcode.mjs")
RECORD_OF_FIELD = {"txtBarcode1": 0, "txtBarcode2": 1, "txtBarcode1_1": 2, "txtBarcode2_1": 3}


def fail(message):
    print("FAIL:", message)
    sys.exit(1)


# ====================================================================================================================
# THE PDF'S OWN SCRIPTS, RUN IN NODE
# ====================================================================================================================
def build_pdf(form):
    return build(form, load_form("lc_pipe_form.py").DEFAULTS)


def pdf_parts(pdf_bytes):
    """(document script, Generate QR Code script, {field name: mock type}, Print Form script) of a built PDF."""
    pdf = pikepdf.open(__import__("io").BytesIO(pdf_bytes))
    doc_js = zlib.decompress(pdf.Root.Names.JavaScript.Names[1].JS.read_raw_bytes()).decode("latin-1")
    types, button, printer = {}, None, None
    pages = {p.objgen: i for i, p in enumerate(pdf.pages)}
    for f in pdf.Root.AcroForm.Fields:
        name, ft, ff = str(f.T), str(f.get("/FT", "")), int(f.get("/Ff", 0))
        widget = f.Kids[0] if "/Kids" in f else f
        types[name] = [{"/Tx": "text", "/Ch": "combobox"}.get(ft) or ("button" if ff & 65536 else "radiobutton" if ff & 32768 else "checkbox"),
                       pages.get(widget.P.objgen, -1) if "/P" in widget else -1]
        if name in ("__generate_qr", "__print_form"):
            js = f.Kids[0].A.JS if "/Kids" in f else f.A.JS
            js = js.read_bytes().decode("latin-1") if isinstance(js, pikepdf.Stream) else str(js)
            if name == "__generate_qr":
                button = js
            else:
                printer = js
    return doc_js, button, types, printer


def run_node(mode, parts, cases):
    doc_js, button, types, printer = parts
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
        json.dump({"mode": mode, "script": doc_js, "button": button, "printer": printer, "types": types, "cases": cases}, t)
    try:
        r = subprocess.run(["node", os.path.join(HERE, "check_pipe_mock.js")], stdin=open(t.name), capture_output=True, text=True)
    finally:
        os.unlink(t.name)
    if r.returncode:
        fail("node could not run the PDF's script:\n" + r.stderr[-1500:])
    return json.loads(r.stdout)


def field_values(form, a):
    """The answers (id -> text, True, or a list for tick-any) as the PDF's fields would hold them: field name -> value."""
    values = {}
    for section in form["sections"]:
        for q in section["fields"]:
            x, kind = a.get(q["id"]), q["kind"]
            if kind == "checks":
                for i, option in enumerate(q["options"]):
                    if option in (x or []):
                        values[f"{q['id']}__{i}"] = "Yes"
            elif kind == "check":
                if x:
                    values[q["id"]] = "Yes"
            elif x:
                values[q["id"]] = x
    return values


# ====================================================================================================================
# THE OLD FORM'S SIDE: the same answers as the old form's fields, and its own code
# ====================================================================================================================
OLD_PLACES = {   # shipment type -> (old subform, text box prefix)
    "Port of Loading / Airport of Departure": ("subfrmShipmentFrom.subfrmLoadDeparture.subfrmPortOfLoad", "txtLoading"),
    "Dispatch from": ("subfrmShipmentFrom.subfrmLoadDeparture.subfrmDispatchfrom", "txtDispatchfrom"),
    "Place of Taking in charge": ("subfrmShipmentFrom.subfrmLoadDeparture.subfrmPlaceOfTakingInCharge", "txtPlaceOfTakingInCharge"),
    "Place of Receipt": ("subfrmShipmentFrom.subfrmLoadDeparture.subfrmPlaceOfReceipt", "txtPlaceOfReceipt"),
    "Port of Discharge / Airport of Destination": ("subfrmShipmentTo.subfrmDischargeDestination.subfrmDischarge", "txtDischarge"),
    "For Transportation to": ("subfrmShipmentTo.subfrmDischargeDestination.subfrmForTransportationTo", "txtForTransportationTo"),
    "Place of Final Destination": ("subfrmShipmentTo.subfrmDischargeDestination.subfrmPlaceOfFinalDestination", "txtPlaceOfFinalDestination"),
    "Place of Delivery": ("subfrmShipmentTo.subfrmDischargeDestination.subfrmPlaceOfDelivery", "txtPlaceOfDelivery"),
}
TWO_BOXES = ("Place of Taking in charge", "Place of Receipt", "Place of Final Destination", "Place of Delivery")   # choices that show Port + Place
OLD_PRICE = {"FOB": "FOB", "CFR": "CFR", "CIF": "CIF", "Local Delivery": "LocalDelivery", "FCA": "FCA", "CIP": "CIP", "CPT": "CPT", "Others": "Others"}
OLD_MODE = {"Full Swift": "FullTelexSwift", "Registered Airmail": "RegisteredAirmail", "Airmail with Brief Swift": "AirmailWithBriefTelexSwift",
            "Courier Service": "CourierService", "Courier Service with Brief Swift": "CourierServiceWithBriefTelexSwift"}
OLD_CONSIGNEE = {"order of the Bank": "1", "order blank endorsed": "2", "other (specify)": "3"}
OLD_CHARGES = {"Beneficiary, except charges at DC Issuing Bank's counter": "LAB",
               "Applicant (including all charges incurred inside and outside of DC Issuing Bank's country)": "LAA"}
L, F = "LC.subfrmLC.", "LC.subfrmLCFoot."
# boxes the old form blanks when they are locked (its cleanUpLC): lc question -> old box, locked when its rule doesn't hold
OLD_LOCKED = {"tolerance_plus": L + "subfrmCreditAmount.txtPlusValue", "tolerance_minus": L + "subfrmCreditAmount.txtMinusValue",
              "price_basis_other": L + "subfrmPriceBasis.txtOthers", "term_days": L + "subfrmDrafts.sufrmDraft.txtTerm",
              "term_after": L + "subfrmDrafts.sufrmDraft.txtDaysAfter", "draft_date": L + "subfrmDrafts.sufrmDraft.txtDate",
              "other_documents_1": F + "subfrmOtherDoc.txtOtherDoc", "other_documents_2": F + "subfrmOtherDoc.txtOtherDoc1",
              "bl_made_out_to_other": L + "subfrmDrafts.txtFullSet", "bl_notify_party": L + "subfrmDrafts.txtNotifyParty",
              "awb_notify_party": L + "subfrmOriginalAirWaybill.txtNotifyParty", "bencert_days": L + "subfrmBeneficiaryCertificate.txtDaysAfterShipment",
              "do_originals": L + "subfrmTransportDocumentsByDO.txtOriginals", "do_copies": L + "subfrmTransportDocumentsByDO.txtCopies",
              "do_countersigned_by": L + "subfrmTransportDocumentsByDO.drpCountersignedBy", "do_signature_verified": L + "subfrmTransportDocumentsByDO.drpWhoseSignature",
              "invoice_originals": F + "subfrmInvoice.txtSignedOriginals", "invoice_copies": F + "subfrmInvoice.txtSignedCopies",
              "packing_list_originals": F + "subfrmInvoice.txtPackingListOriginals", "packing_list_copies": F + "subfrmInvoice.txtPackingListCopies",
              "weight_note_originals": F + "subfrmInvoice.txtWeightNoteOriginals", "weight_note_copies": F + "subfrmInvoice.txtWeightNoteCopies",
              "origin_originals": F + "subfrmInvoice.txtCertificateOfOriginInOriginals", "origin_copies": F + "subfrmInvoice.txtCertificateOfOriginCopies",
              "origin_country": F + "subfrmInvoice.txtCertificateOfOriginCountry"}


def iso(d):
    return f"{d[6:]}-{d[3:5]}-{d[:2]}" if d else None


def to_old(a, locked):
    """The answers (lc-form ids) as the old form's fields: {path under form1: value}; blank = left out. locked = the ids of
    the questions that do not apply (their old boxes are read-only, as in the old form)."""
    v, g = {}, a.get

    def put(path, value):
        if value not in (None, "", False):
            v[path] = value

    def tick(path, x):
        v[path] = "1" if x else "0"

    for who, prefix in (("applicant", L + "subfrmApplicant"), ("beneficiary", L + "subfrmBeneficiary")):
        put(prefix + ".txtName", g(who + "_name"))
        for n in (1, 2, 3):
            put(f"{prefix}.txtAddress{n}", g(f"{who}_address_{n}"))
    for who, prefix in (("third_party", L + "subfrm3PartyBeneficiary"), ("advising_bank", L + "subfrmForBankUse.subfrmAdvisingBank")):
        put(prefix + ".txtName", g(who + "_name"))
        for n in (1, 2, 3):
            put(f"{prefix}.txtAddress{n}", g(f"{who}_address_{n}"))
    for key, group in (("partial_shipment", "radPartialShipment"), ("transhipment", "radTranshipment")):
        put(f"{L}subfrmPartialshipment.{group}.{'allowed' if g(key) == 'allowed' else 'notAllowed'}", {"allowed": "Y", "not allowed": "N"}.get(g(key)))
    put(L + "subfrmCreditAmount.drpCurrency", g("currency"))
    amount = (g("amount") or "").replace(",", "")
    if amount:
        amount += ".00" if "." not in amount else "0" if len(amount.split(".")[1]) == 1 else ""
    put(L + "subfrmCreditAmount.txtAmount", amount)
    if g("gst") == "inclusive of GST":
        v[L + "subfrmCreditAmount.radGST.InclusiveofGST"] = "GSY"
    put(L + "subfrmCreditAmount.txtPlusValue", g("tolerance_plus"))
    put(L + "subfrmCreditAmount.txtMinusValue", g("tolerance_minus"))
    if g("price_basis"):
        v[f"{L}subfrmPriceBasis.RadioButtonList.{OLD_PRICE[g('price_basis')]}"] = g("price_basis")
    put(L + "subfrmPriceBasis.txtOthers", g("price_basis_other"))
    for key, drop, port in (("shipment_from", "subfrmShipmentFrom.drpPortOfLoading", "Port of Loading / Airport of Departure"),
                            ("shipment_to", "subfrmShipmentTo.drpPortOfDischarge", "Port of Discharge / Airport of Destination")):
        if g(key):
            v[L + drop] = g(key)
            # the two-box choices show the port box as well as their own (the old form's drpPortOfLoading change event)
            for choice in dict.fromkeys([port, g(key)] if g(key) in TWO_BOXES else [g(key)]):
                box, name = OLD_PLACES[choice]
                suffix = "_port" if choice == port else "_place"
                put(f"{L}{box}.{name}1", g(key + suffix))
                put(f"{L}{box}.{name}2", g(key + suffix + "_2"))
    put(L + "subfrmShipmentDate.txtDate", iso(g("latest_shipment_date")))
    put(L + "subfrmDateOfExpiry.txtDate", iso(g("expiry_date")))
    put(L + "subfrmPresentation.txtPeriod", g("presentation_days"))
    put(L + "subfrmDrafts.sufrmDraft.radDrafts", g("drafts_at"))
    if g("drafts_at") == "Term":
        v[L + "subfrmDrafts.sufrmDraft.radDrafts.chkTerm"] = "Term"
    put(L + "subfrmDrafts.sufrmDraft.txtTerm", g("term_days"))
    put(L + "subfrmDrafts.sufrmDraft.txtDaysAfter", g("term_after"))
    put(L + "subfrmDrafts.sufrmDraft.txtDate", iso(g("draft_date")))
    if g("mode_of_advising"):
        v[f"{L}subfrmModeOfAdvising.RadioButtonList.{OLD_MODE[g('mode_of_advising')]}"] = g("mode_of_advising")
    tick(L + "subfrmDrafts.chkFullSet", g("doc_bill_of_lading"))
    put(L + "subfrmDrafts.radConsignee", OLD_CONSIGNEE.get(g("bl_made_out_to")))
    put(L + "subfrmDrafts.txtFullSet", g("bl_made_out_to_other"))
    put(L + "subfrmDrafts.radFreight", g("bl_freight"))
    put(L + "subfrmDrafts.txtNotifyParty", g("bl_notify_party"))
    tick(L + "subfrmOriginalAirWaybill.chkOriginalAirWaybill", g("doc_air_waybill"))
    put(L + "subfrmOriginalAirWaybill.radioButtonList", g("awb_freight"))
    put(L + "subfrmOriginalAirWaybill.txtNotifyParty", g("awb_notify_party"))
    tick(L + "subfrmTransportDocumentsByDO.chkDeliveryOrderIn", g("doc_delivery_order"))
    put(L + "subfrmTransportDocumentsByDO.txtOriginals", g("do_originals"))
    put(L + "subfrmTransportDocumentsByDO.txtCopies", g("do_copies"))
    put(L + "subfrmTransportDocumentsByDO.drpCountersignedBy", g("do_countersigned_by"))
    put(L + "subfrmTransportDocumentsByDO.drpWhoseSignature", g("do_signature_verified"))
    tick(L + "subfrmInsurance.chkInsurance", g("doc_insurance"))
    tick(L + "subfrmBeneficiaryCertificate.chkBeneficiaryCertificate", g("doc_beneficiary_certificate"))
    for option, box in (("faxed", "chkFaxed"), ("mailed", "chkMailed"), ("couriered", "chkCouriered")):
        tick(f"{L}subfrmBeneficiaryCertificate.{box}", option in (g("bencert_sent_by") or []))
    put(L + "subfrmBeneficiaryCertificate.txtDaysAfterShipment", g("bencert_days"))
    for doc, chk, o, c in (("invoice", "chkSignedCommercialInvoice", "txtSignedOriginals", "txtSignedCopies"),
                           ("packing_list", "chkPackingList", "txtPackingListOriginals", "txtPackingListCopies"),
                           ("weight_note", "chkWeightNote", "txtWeightNoteOriginals", "txtWeightNoteCopies"),
                           ("origin", "chkCertificateOfOrigin", "txtCertificateOfOriginInOriginals", "txtCertificateOfOriginCopies")):
        tick(f"{F}subfrmInvoice.{chk}", g("doc_" + ("commercial_invoice" if doc == "invoice" else "certificate_of_origin" if doc == "origin" else doc)))
        put(f"{F}subfrmInvoice.{o}", g(doc + "_originals"))
        put(f"{F}subfrmInvoice.{c}", g(doc + "_copies"))
    put(F + "subfrmInvoice.txtCertificateOfOriginCountry", g("origin_country"))
    put(F + "subfrmOtherDoc.txtOtherDoc", g("other_documents_1"))
    put(F + "subfrmOtherDoc.txtOtherDoc1", g("other_documents_2"))
    put(F + "subfrmGoodsDescription.txtGoodsDescription", g("goods_description"))
    put(F + "subfrmAdditionalCond.txtAdditionalCond", g("additional_conditions"))
    base = F + "subfrmDetails.subfrmOne."
    tick(base + "subfrmConfirmation.chkConfirmation", g("confirmation"))
    put(base + "subfrmConfirmation.radioButtonList", {"Applicant": "LID", "Beneficiary": "LIC"}.get(g("confirmation_charges")))
    put(base + "subfrmBankCharges.radChargeAccount", OLD_CHARGES.get(g("bank_charges_for")))
    for qid, path in OLD_LOCKED.items():
        if qid in locked:
            v[path + "#access"] = "readOnly"
    return v


def old_records(a, locked):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as t:
        json.dump(to_old(a, locked), t)
    try:
        r = subprocess.run(["node", OLD_RUNNER, EXTRACT, t.name], capture_output=True, text=True)
    finally:
        os.unlink(t.name)
    if r.returncode:
        fail("the old form's code stopped:\n" + r.stderr[-800:] + "\nanswers: " + json.dumps(a)[:600])
    out = [None] * 4
    for rec in json.loads(r.stdout)["records"]:
        out[RECORD_OF_FIELD[rec["field"].rsplit(".", 1)[1]]] = rec["value"]
    return out


# ====================================================================================================================
# RANDOM VALID ANSWERS: every rule of the form file respected (mandatory, locked, formats, dates in order)
# ====================================================================================================================
WORDS = ["ACME", "TRADING", "PTE", "LTD", "10", "ANSON", "ROAD", "#12-01", "INTERNATIONAL", "PLAZA", "SINGAPORE", "079903", "ST.", "NO.", "AT&T",
         "50%", "(A)", "CRATES,", "MODEL", "XP-200", "stainless", "steel", "316", "50HZ", "415V", "MOTOR:", "PACKED", "IN", "SEAWORTHY", "WOODEN",
         "O'NEIL", "A/B", "UNIT", "PRICE", "USD", "2,500.00", "FOB", "IMPELLER?", "x+y", "name@host", "CHINA", "BILL", "OF", "LADING", "DATE"]
QTY = ["0", "1", "2", "3", "10", "00", "01", "25"]


def holds(rules, a):
    """The form's own 'does any of these rules hold?' (acrobat_js.py, any())."""
    for r in rules:
        x = a.get(r["field"], "")
        x = ("true" if x else "false") if isinstance(x, bool) else x
        hit = any(i in r["values"] for i in x) if isinstance(x, list) else x in r["values"]
        if (not hit and bool(x)) if r.get("not") else hit:
            return True
    return False


def words(rng, low, high, cap=None):
    s = " ".join(rng.choice(WORDS) for _ in range(rng.randint(low, high)))
    return s[:cap].rstrip() if cap else s


def long_text(rng):
    kind = rng.choice(["short", "mid", "long", "enter", "enter", "noSpace", "edge", "bigword"])
    if kind == "short":
        return words(rng, 1, 6)
    if kind == "mid":
        return words(rng, 8, 14)
    if kind == "long":
        return words(rng, 40, 160)
    if kind == "enter":
        paras = [words(rng, 1, 40) for _ in range(rng.randint(2, 6))]
        s = rng.choice(["\r", "\r", "\r\r"]).join(paras)
        return rng.choice(["", "\r", " "]) + s + rng.choice(["", "\r", "\r\r", " "])
    if kind == "noSpace":
        s = "X" * rng.choice([64, 65, 66, 130, 131, 200, 500]) + (rng.choice(["", "\r" + words(rng, 1, 20)]))
        return s
    if kind == "edge":
        n = rng.choice([63, 64, 65, 66, 67, 129, 130, 131])
        return (words(rng, 30, 40) + " " + "Y" * 80)[:n].rstrip() if rng.random() < .5 else ("A" * (n - 1) + " B" * 3)[:n]
    return words(rng, 3, 5) + " " + "Z" * rng.choice([70, 140]) + " " + words(rng, 3, 30)


def value_for(rng, q, today, maxi=False):
    kind, fmt, cap = q["kind"], q.get("format"), q.get("max")
    if kind == "long":
        return long_text_of(rng, 3000) if maxi else long_text(rng)
    if maxi and kind == "text" and not fmt:
        return ("ABCD EFGH " * 20)[:cap or 35].rstrip()
    if kind == "text":
        if fmt == "number":
            return rng.choice(QTY) if (cap or 9) <= 2 else str(rng.randint(0, 10 ** min(cap or 3, 3) - 1))
        if fmt == "amount":
            return rng.choice(["1250000.00", "1,250,000.00", "1250.5", "1250", "1,234", "0.01", "999999999.99", "75000.50"])
        if fmt == "phone":
            return rng.choice(["+65 6123 4567", "61234567", "(65) 6123-4567"])
        if fmt == "account":
            return rng.choice(["123-456-789", "1234567890"])
        s = words(rng, 1, 4, cap or 35)
        return (s + " ") if rng.random() < .03 else s
    if kind == "select" or kind == "radio":
        return rng.choice(q["options"])
    if kind == "checks":
        return [o for o in q["options"] if rng.random() < .5] or [rng.choice(q["options"])]
    if kind == "check":
        return True
    raise AssertionError(kind)


def random_answers(rng, form, maxi=False):
    """(answers, locked ids). Optional boxes sometimes blank; a locked box is blank, or (sometimes) holds a stale answer."""
    today = datetime.date(2026, 11, 26)
    questions = [q for s in form["sections"] for q in s["fields"]]
    a, locked = {}, set()
    app = today - datetime.timedelta(days=rng.randint(1, 300))
    ship = app + datetime.timedelta(days=rng.randint(0, 200))
    expiry = ship + datetime.timedelta(days=rng.randint(0, 100))
    dates = {"application_date": app, "latest_shipment_date": ship, "expiry_date": expiry}
    for q in questions:
        rules, act = q.get("requiredIf") or [], active_rules(q)
        applies = not act or holds(act, a)
        required = q.get("required") or (applies and holds(rules, a))
        if not applies:
            locked.add(q["id"])
            if rng.random() < .3:
                a[q["id"]] = date_text(today - datetime.timedelta(days=rng.randint(1, 99))) if q["kind"] == "date" else value_for(rng, q, today)
            continue
        if not required and not maxi and rng.random() < .35:
            continue
        if q["kind"] == "date":
            d = dates.get(q["id"]) or today - datetime.timedelta(days=rng.randint(0, 400))
            a[q["id"]] = date_text(d)
        else:
            a[q["id"]] = value_for(rng, q, today, maxi)
            if q["kind"] == "check" and not required and not maxi and rng.random() < .4:
                del a[q["id"]]
        if q["id"] == "insurance_arrangement" and a.get("price_basis") in ("CIF", "CIP"):
            del a[q["id"]]
    return {k: v for k, v in a.items() if v not in ("", [], False)}, locked


def long_text_of(rng, n):
    s = ""
    while len(s) < n:
        s += rng.choice(WORDS) + rng.choice([" ", " ", " ", "\r"])
    return s[:n]


def date_text(d):
    return d.strftime("%d/%m/%Y")


# ====================================================================================================================
# THE GOLDEN SAMPLE (synthetic, from the extract: docs/lc/sample-lc-input.json and sample-lc-output.txt)
# ====================================================================================================================
GOLDEN = {
    "applicant_name": "ACME TRADING PTE LTD", "applicant_address_1": "10 ANSON ROAD #12-01", "applicant_address_2": "INTERNATIONAL PLAZA",
    "applicant_address_3": "SINGAPORE 079903", "beneficiary_name": "GLOBAL EXPORTS LLC", "beneficiary_address_1": "88 HARBOUR STREET",
    "beneficiary_address_2": "SHENZHEN 518000", "beneficiary_address_3": "CHINA", "partial_shipment": "allowed", "transhipment": "not allowed",
    "currency": "USD", "amount": "1,250,000.00", "tolerance": True, "tolerance_plus": "5", "tolerance_minus": "5", "price_basis": "FOB",
    "shipment_from": "Port of Loading / Airport of Departure", "shipment_from_port": "ANY CHINESE PORT",
    "shipment_to": "Port of Discharge / Airport of Destination", "shipment_to_port": "SINGAPORE",
    "latest_shipment_date": "28/02/2027", "expiry_date": "31/03/2027", "presentation_days": "21", "drafts": True, "drafts_at": "Term",
    "term_days": "90", "term_after": "BILL OF LADING DATE", "mode_of_advising": "Full Swift", "doc_bill_of_lading": True,
    "bl_made_out_to": "order of the Bank", "bl_notify_party": "APPLICANT", "bl_freight": "Collect", "confirmation": True,
    "confirmation_charges": "Beneficiary", "bank_charges": True, "bank_charges_for": "Beneficiary, except charges at DC Issuing Bank's counter",
    "doc_beneficiary_certificate": True, "bencert_days": "5", "doc_commercial_invoice": True, "invoice_originals": "3", "invoice_copies": "2",
    "doc_packing_list": True, "packing_list_originals": "3", "packing_list_copies": "2", "doc_certificate_of_origin": True,
    "origin_originals": "1", "origin_copies": "1", "origin_country": "CHINA", "doc_other": True,
    "other_documents_1": "INSPECTION CERTIFICATE ISSUED BY AN INDEPENDENT SURVEYOR",
    "goods_description": "500 UNITS INDUSTRIAL CENTRIFUGAL PUMPS MODEL XP-200, STAINLESS STEEL 316 IMPELLER, 50HZ 415V MOTOR, PACKED IN SEAWORTHY "
                         "WOODEN CRATES, EACH CRATE MARKED WITH PO NUMBER AND GROSS WEIGHT. INCLUDING SPARE PARTS KIT (SEALS, BEARINGS, GASKETS) FOR "
                         "TWO YEARS OPERATION AND ONE SET OF OPERATING MANUALS IN ENGLISH. UNIT PRICE USD 2,500.00 FOB SINGAPORE AS PER PROFORMA "
                         "INVOICE NO. PI-2026-0415 DATED 15 OCTOBER 2026. ALL GOODS TO BE NEW AND UNUSED. THIS SENTENCE IS PAST CHARACTER 400 AND "
                         "SHOULD BE CUT.",
    "additional_conditions": "ALL DOCUMENTS MUST INDICATE THE CREDIT NUMBER.\rTHIRD PARTY DOCUMENTS ACCEPTABLE EXCEPT DRAFTS AND INVOICE.",
}


def golden_records():
    text = open(os.path.join(EXTRACT, "docs", "lc", "sample-lc-output.txt"), encoding="utf-8").read()
    records = re.findall(r"^LC\.subfrmBarcodeRecord\.\S+\s+\(\d+ chars\)\n(.*)$", text, re.M)
    if len(records) != 4:
        fail("could not read the 4 golden records from sample-lc-output.txt")
    return records


# ====================================================================================================================
def compare(label, ours, theirs):
    """Prints and returns the number of records that differ."""
    bad = 0
    for i, (x, y) in enumerate(zip(ours, theirs), 1):
        if x != y:
            bad += 1
            at = next((k for k in range(min(len(x), len(y))) if x[k] != y[k]), min(len(x), len(y)))
            print(f"  {label}: record {i} differs at character {at}\n    ours: {x[max(0, at - 30):at + 40]!r}\n    old : {y[max(0, at - 30):at + 40]!r}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=300)
    ap.add_argument("--seed", type=int, default=20261126)
    ap.add_argument("--decode", action="store_true")
    args = ap.parse_args()
    if not os.path.exists(OLD_RUNNER):
        fail(f"the old form's runner is missing ({OLD_RUNNER}). Set SMARTFORM_EXTRACT to the smart-form extract folder.")
    spec = load_form("lc_pipe_form.py")
    check_form(spec.FORM, spec.DEFAULTS, FORMATS)
    positions = [e["p"] for r in spec.FORM["pipe"] for e in r]
    expected = [f"{r}_{n:02d}" for r, n in [(1, n) for n in range(1, 37)] + [(2, n) for n in range(1, 15)] + [(3, n) for n in range(1, 10)] + [(4, n) for n in range(1, 4)]]
    assert positions == expected, "the position table must hold 1_01 ... 4_03, in order, 62 positions"
    parts = pdf_parts(build_pdf(spec.FORM))

    # 1. the golden sample
    golden = golden_records()
    # the sample has a CIF number (from the old form's main page, which this form has no question for): it is 0000000 here
    assert golden[0].startswith("1|1234567|"), "the golden sample's CIF number changed"
    golden[0] = "1|0000000|" + golden[0][len("1|1234567|"):]
    ours = run_node("records", parts, [field_values(spec.FORM, GOLDEN)])[0]
    theirs = old_records(GOLDEN, set())
    bad = compare("golden vs the extract's sample output", ours, golden) + compare("golden vs the old code", theirs, golden)
    bad += compare("golden", ours, theirs)
    if bad:
        fail("the golden sample does not match")
    print(f"golden sample: our 4 records = the old code's = the extract's sample output ({sum(map(len, ours))} characters)")

    # 2. random valid answer sets
    rng = random.Random(args.seed)
    cases = [random_answers(rng, spec.FORM) for _ in range(args.cases)]
    cases += [random_answers(rng, spec.FORM, maxi=True) for _ in range(3)]   # every optional box answered, texts at full length
    covered = coverage(spec.FORM, cases)
    # (a stale answer in a locked shipment box is cleared by the form's rules before the records are made: shipment_check proves it)
    mine = run_node("records", parts, [field_values(spec.FORM, {k: v for k, v in a.items() if not (k in locked and k.startswith(("shipment_from_", "shipment_to_")))}) for a, locked in cases])
    bad = 0
    for n, ((a, locked), ours) in enumerate(zip(cases, mine)):
        theirs = old_records(a, locked)
        if ours != theirs:
            bad += 1
            print(f"case {n} (seed {args.seed}): answers {json.dumps(a)[:900]}")
            compare(f"case {n}", ours, theirs)
    if bad:
        fail(f"{bad} of {len(cases)} random answer sets differ from the old form's records")
    print(f"{len(cases)} random valid answer sets: our records = the old code's, byte for byte ({covered})")

    # 3. the test can fail: the same comparison on a form whose table has one code changed must disagree
    broken = copy.deepcopy(spec.FORM)
    broken["pipe"][0][5]["codes"]["allowed"] = "L5X"
    bparts = pdf_parts(build_pdf(broken))
    wrong = run_node("records", bparts, [field_values(broken, GOLDEN)])[0]
    if wrong == old_records(GOLDEN, set()) or wrong[0] == golden[0]:
        fail("the guard does not bite: a changed code (L5Y -> L5X) was not noticed")
    print("guard bites: with 1_06 allowed = L5X the records no longer match the old code's")

    shipment_check(spec, parts)
    build_guard_check(spec)
    hostile_check(spec, parts, cases[0][0])
    print_check(spec, parts, {k: v for k, v in cases[0][0].items() if k not in cases[0][1]})   # (Generate QR Code clears locked boxes first)
    if args.decode:
        # (the golden sample is not a complete application: Generate QR Code would refuse it. Generate QR Code first clears the
        # answers left in locked boxes, so those are left out here.)
        clean = [{k: v for k, v in a.items() if k not in locked} for a, locked in cases]
        sizes = sorted(range(len(cases)), key=lambda i: -sum(map(len, mine[i])))
        maxi = {k: v for k, v in random_answers(rng, spec.FORM, maxi=True)[0].items()}   # every optional box answered, texts at full length
        decode_check(spec, parts, clean[:12] + [clean[i] for i in sizes[:3]] + [maxi])
        # Records longer than the table's own cuts allow (400 / 600 characters: a Bank that lifts them) need several codes: codes 3
        # and up go on the extra QR code pages. The same table with "max" removed; 6,400-character goods and conditions.
        free = copy.deepcopy(spec.FORM)
        for r in free["pipe"]:
            for e in r:
                e.pop("max", None)
        fparts = pdf_parts(build_pdf(free))
        big = {k: v for k, v in maxi.items() if k not in ("goods_description", "additional_conditions")}
        bigs = [dict(big, goods_description=long_text_of(rng, 6400), additional_conditions=long_text_of(rng, n)) for n in (300, 2500, 6400)]
        decode_check(spec, fparts, bigs, free, minimum_codes=3)
        print_check(spec, fparts, bigs[2], free)
    print("PASS")


SHIPMENT = {   # choice -> the boxes it shows (port, place), per side
    "shipment_from": {"Port of Loading / Airport of Departure": (1, 0), "Dispatch from": (0, 1), "Place of Taking in charge": (1, 1), "Place of Receipt": (1, 1)},
    "shipment_to": {"Port of Discharge / Airport of Destination": (1, 0), "For Transportation to": (0, 1), "Place of Final Destination": (1, 1), "Place of Delivery": (1, 1)},
}


def shipment_problems(form, parts):
    """What differs from the old form's behaviour, for each of the 4 + 4 choices with stale answers left in every shipment box:
    the form's rules (lcRules, run under Node) must unlock and require exactly the boxes the choice shows, grey, lock and clear
    the others, and the records must equal the old barcode code's for the same answers."""
    names = [f"{side}_{kind}{n}" for side in SHIPMENT for kind in ("port", "place") for n in ("", "_2")]
    cases, labels = [], []
    for side, choices in SHIPMENT.items():
        other = "shipment_to" if side == "shipment_from" else "shipment_from"
        for choice, shows in choices.items():
            a = {k: v for k, v in GOLDEN.items() if not k.startswith(("shipment_from_", "shipment_to_"))}
            a[side], a[other] = choice, list(SHIPMENT[other])[0]
            for kind in ("port", "place"):   # stale answers everywhere: the rules must clear what does not apply
                a[f"{side}_{kind}"], a[f"{side}_{kind}_2"] = f"{kind.upper()} {choice[:6]}", f"{kind.upper()} TWO"
            a[f"{other}_port"] = "OTHER SIDE PORT"
            blank = {k: v for k, v in a.items() if not k.startswith(("shipment_from_", "shipment_to_"))}
            cases += [{"values": field_values(form, a), "watch": names}, {"values": field_values(form, blank), "watch": names}]
            labels += [(side, choice, shows, a, False), (side, choice, shows, blank, True)]
    bad = []
    for (side, choice, shows, a, empty), res in zip(labels, run_node("rules", parts, cases)):
        for kind, show in zip(("port", "place"), shows):
            one, two = res["fields"][f"{side}_{kind}"], res["fields"][f"{side}_{kind}_2"]
            if one["readonly"] == bool(show) or two["readonly"] == bool(show):
                bad.append(f"{choice}: {kind} box is {'locked' if show else 'unlocked'} (want {'unlocked' if show else 'locked'})")
            if empty and (one["required"] != bool(show) or two["required"]):   # (mandatory shows only while the box is blank)
                bad.append(f"{choice}: {kind} box required = {one['required']} / {two['required']} (want {bool(show)} / False)")
            if not empty and not show and (one["value"] or two["value"]):
                bad.append(f"{choice}: {kind} box was not cleared")
        want = old_records(a, set()) if not empty else res["records"]
        if res["records"] != want:
            bad.append(f"{choice}: records differ from the old code's ({compare(choice, res['records'], want)} of 4)")
    return bad


def shipment_check(spec, parts):
    bad = shipment_problems(spec.FORM, parts)
    if bad:
        fail("Shipment from / to do not behave like the old form's:\n  " + "\n  ".join(bad[:12]))
    plain = copy.deepcopy(spec.FORM)   # the same boxes without their rules: the check must notice
    for q in (q for s in plain["sections"] for q in s["fields"]):
        if q["id"].startswith(("shipment_from_p", "shipment_to_p")):
            q.pop("requiredIf", None)
            q.pop("activeIf", None)
    with contextlib.redirect_stdout(io.StringIO()):   # (compare prints each difference)
        found = shipment_problems(plain, pdf_parts(build_pdf(plain)))
    if not found:
        fail("the shipment check does not bite: boxes without rules still passed")
    print("shipment from / to: 4 + 4 choices unlock, require, grey and clear the right boxes, and their records = the old code's (boxes without rules fail)")


DELIMITERS = ["AC|ME", "A[B", "A]B", "A{B", "A}B", "A{}B", "A\nB", "A\rB", "A\r\nB", "|", "[]", "A|B|C|D", "\n|[{\r}]"]


def hostile_check(spec, parts, base):
    """Values that reach the fields without the keystroke filter (FDF import, autofill, a pasted newline) must not change the
    layout of the records: each record keeps its number of positions, and no record holds a raw newline."""
    form = spec.FORM
    counts = [len(r) for r in form["pipe"]]
    on = {"doc_bill_of_lading": True, "bl_made_out_to": "other (specify)", "bl_freight": "Collect", "doc_air_waybill": True, "awb_freight": "Prepaid",
          "doc_other": True, "doc_certificate_of_origin": True, "origin_originals": "1", "origin_copies": "1", "price_basis": "Others",
          "shipment_from": "Place of Taking in charge", "shipment_to": "Place of Delivery", "drafts_at": "Term", "doc_delivery_order": True,
          "do_originals": "1", "do_copies": "1", "do_countersigned_by": "One", "do_signature_verified": "need"}
    targets = ["applicant_name", "beneficiary_name", "third_party_name", "advising_bank_name", "applicant_address_1", "beneficiary_address_2",
               "beneficiary_address_3", "third_party_address_1", "advising_bank_address_2", "shipment_from_port", "shipment_from_port_2", "shipment_from_place",
               "shipment_from_place_2", "shipment_to_port", "shipment_to_port_2", "shipment_to_place", "shipment_to_place_2", "price_basis_other", "term_after", "bl_made_out_to_other", "bl_notify_party",
               "awb_notify_party", "origin_country", "other_documents_1", "other_documents_2", "goods_description", "additional_conditions",
               "currency", "term_days", "tolerance_plus", "presentation_days"]
    cases, labels = [], []
    for t in targets:
        for d in DELIMITERS:
            cases.append(dict(base, **on, **{t: d}))
            labels.append((t, d))
    out = run_node("records", parts, [field_values(form, a) for a in cases])
    bad = []
    for (t, d), recs in zip(labels, out):
        for n, (r, want) in enumerate(zip(recs, counts), 1):
            if r.count("|") != want or "\n" in r or "\r" in r:
                bad.append(f"{t} = {d!r}: record {n} has {r.count('|')} positions (want {want})" + (", a raw newline" if "\n" in r or "\r" in r else ""))
        if len(recs) != 4:
            bad.append(f"{t} = {d!r}: {len(recs)} records")
    if bad:
        print(f"  {len(bad)} of {len(cases)} hostile answers break the records, e.g.:")
        for b in bad[:8]:
            print("   ", b)
        fail("delimiters or newlines in an answer change the layout of the records")
    print(f"hostile answers: {len(cases)} (each of {len(DELIMITERS)} delimiter / newline values in {len(targets)} boxes) keep every record at {counts} positions with no raw newline")


def print_check(spec, parts, base, form=None):
    """After Generate QR Code, Print Form must print whatever way the viewer stored the newlines of the single-line hidden field,
    and refuse a changed answer, a missing code and an empty field."""
    form = form or spec.FORM
    vals = field_values(form, base)
    text = "\n".join(run_node("records", parts, [vals])[0])
    ways = {"kept": text, "removed": text.replace("\n", ""), "CR": text.replace("\n", "\r"), "CRLF": text.replace("\n", "\r\n"),
            "Acrobat's single space": text.replace("\n", " ")}
    cases = [{"values": vals, "gen": True, "stored": s, "after": {}} for s in ways.values()]
    cases.append({"values": vals, "gen": True, "stored": None, "after": {"applicant_name": base["applicant_name"] + "X"}})
    cases.append({"values": vals, "gen": False, "stored": "", "after": {}})
    cases.append({"values": vals, "gen": False, "stored": text, "after": {}})   # a stored text but no code drawn
    # one extra space inside an answer (after the first "|") must still refuse, even with Acrobat's spaces between records
    cases.append({"values": vals, "gen": True, "stored": text.replace("\n", " ").replace("|", "| ", 1), "after": {}})
    res = run_node("print", parts, cases)
    for way, r in zip(ways, res):
        if not r["printed"]:
            fail(f"Print Form refused the stored QR text ({way}): {r['alerts']}")
    if any(r["printed"] for r in res[len(ways):]):
        fail("Print Form printed although the answers changed, no code was drawn or the field is empty: the check does not bite")
    print("Print Form: prints after Generate QR Code with the stored text's newlines kept, removed, CR, CRLF or one space (Acrobat's single-line field); refuses a changed answer, "
          "a missing code, an empty code and one extra space in an answer")


def build_guard_check(spec):
    """The build must stop on a table that maps answers to codes where there are no answers to map: codes on a free-text question,
    codes on a tick box under a key other than "true", codes without an id; and must accept the real table."""
    def entry(form, p):
        return next(e for r in form["pipe"] for e in r if e["p"] == p)
    bad = {"codes on a free-text question": ("1_03", {"codes": {"ACME": "X"}}),
           "codes on a tick box with the key 'yes'": ("2_12", {"codes": {"yes": "L9Y"}}),
           "codes without an id": ("1_05", {"codes": {"x": "y"}})}
    for label, (p, change) in bad.items():
        form = copy.deepcopy(spec.FORM)
        entry(form, p).update(change)
        try:
            check_form(form, spec.DEFAULTS, FORMATS)
        except SystemExit:
            continue
        fail(f"the build accepted a table with {label} (position {p})")
    check_form(copy.deepcopy(spec.FORM), spec.DEFAULTS, FORMATS)
    print(f"build guard: refuses {len(bad)} tables with codes where there are no answers to map; accepts the real table")


def coverage(form, cases):
    """Fails unless the cases between them used every option, both states of every tick box, blank optionals, 1-3 line
    addresses, long text with Enter, and locked boxes holding stale answers. Returns a one-line summary."""
    seen = {}
    for a, _ in cases:
        for k, x in a.items():
            for item in x if isinstance(x, list) else [x]:
                seen.setdefault(k, set()).add(item)
    for s in form["sections"]:
        for q in s["fields"]:
            if q.get("options") and len(q["options"]) <= 10:   # (not the 150 currencies)
                missing = [o for o in q["options"] if o not in seen.get(q["id"], ())]
                if missing:
                    fail(f"the random cases never used {missing} of {q['id']}: use more cases")
    ticks = [q["id"] for s in form["sections"] for q in s["fields"] if q["kind"] == "check" and not q.get("required")]
    for t in ticks:
        if not any(t in a for a, _ in cases) or not any(t not in a for a, _ in cases):
            fail(f"tick box {t} was not both ticked and unticked in the random cases")
    addr = {sum(1 for n in (1, 2, 3) if a.get(f"beneficiary_address_{n}") for _ in [0]) for a, _ in cases}
    if not {1, 2, 3} <= addr:
        fail("the random cases lack 1-, 2- and 3-line addresses")
    entered = sum(1 for a, _ in cases if "\r" in a.get("goods_description", "") and len(a["goods_description"]) > 65)
    longer = sum(1 for a, _ in cases if len(a.get("additional_conditions", "")) > 130)
    stale = sum(1 for a, locked in cases if any(k in a for k in locked))
    empty_opt = sum(1 for a, _ in cases if "goods_description" not in a or "additional_conditions" not in a)
    if min(entered, longer, stale, empty_opt) < 5:
        fail(f"too few special cases: enter {entered}, long {longer}, stale-locked {stale}, empty optional {empty_opt}")
    return f"{entered} with Enter in long text, {longer} over 130 characters, {stale} with a stale answer in a locked box, {empty_opt} with an empty optional paragraph"


def decode_check(spec, parts, answer_sets, form=None, minimum_codes=1):
    """Runs the Generate QR Code script of the PDF, renders the QR matrices it draws and decodes them with zxing-cpp."""
    try:
        import zxingcpp
        from PIL import Image
    except ImportError:
        fail("--decode needs zxing-cpp (python -m pip install zxing-cpp, in a scratch venv; it is not in requirements.txt)")
    form = form or spec.FORM
    results = run_node("generate", parts, [field_values(form, a) for a in answer_sets])
    records = run_node("records", parts, [field_values(form, a) for a in answer_sets])
    sizes = []
    for n, (res, recs) in enumerate(zip(results, records)):
        expected = "\n".join(recs)
        if res["qr"] != expected:
            fail(f"decode case {n}: the Generate QR Code script put {res['qr'][:80]!r}... in the QR text, not the records (alerts: {res['alerts']})")
        if not res["codes"]:
            fail(f"decode case {n}: no QR code was drawn (alerts: {res['alerts']})")
        text = ""
        for rows in res["codes"]:
            scale, quiet = 5, 4
            size = (177 + 2 * quiet) * scale
            img = Image.new("L", (size, size), 255)
            px = img.load()
            for y, row in enumerate(rows):
                for x, ch in enumerate(row[:177]):
                    if ch == "n":
                        for dy in range(scale):
                            for dx in range(scale):
                                px[(x + quiet) * scale + dx, (y + quiet) * scale + dy] = 0
            found = zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.QRCode)
            if len(found) != 1:
                fail(f"decode case {n}: zxing-cpp read {len(found)} codes from one drawn code")
            text += found[0].text
        if text != expected:
            fail(f"decode case {n}: decoded text differs from the records\n  decoded: {text[:120]!r}\n  records: {expected[:120]!r}")
        sizes.append(len(res["codes"]))
        if len(res["codes"]) != -(-len(expected.encode("latin-1", "replace")) // 2300):
            fail(f"decode case {n}: {len(res['codes'])} codes for {len(expected)} characters (one per 2,300 bytes expected)")
    if max(sizes) < minimum_codes:
        fail(f"decode: no case needed {minimum_codes} codes (most: {max(sizes)})")
    print(f"decode: {len(answer_sets)} answer sets -> Generate QR Code -> codes per set {sorted(set(sizes))} (largest {max(sizes)}), decoded text = the joined records")


if __name__ == "__main__":
    main()
