# LC application form (Form LC-01)

This project builds one PDF: the **Irrevocable Documentary Credit Application** (Demo Bank, Form LC-01 · v1.0 · Nov 2026).
It's a fillable form with Adobe Acrobat JavaScript checks and a QR code page. It's built in **Python**.

<!-- AUTO:summary (written by build_lc.py from lc.py; don't edit by hand) -->
- 4 pages: 3 pages of questions, plus the QR code page.
- 297 PDF fields: 108 questions, plus date lists, tick-any boxes, buttons and 177 QR rows.
<!-- /AUTO:summary -->

- Needs Python 3.9 or later and **one library, pikepdf**. All its licences are permissive (no GPL/AGPL).
- **7 files.** One command builds the PDF and checks it.

## Run it

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build_lc.py                       # builds out/LC-Application.pdf, checks it, prints PASS
.venv/bin/python -m http.server 8090 -d out        # serves it at http://localhost:8090 (Ctrl+C stops it)
```

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.

`build_lc.py` checks the PDF before saving it. If anything is wrong (a missing field, a broken rule, a damaged
file), it stops with the reason and doesn't save a broken PDF. It then brings this README up to date (see below).

**This README keeps itself up to date.** The parts that come straight from `lc.py` (the page and field counts, the
starting answers, and the table of every question) are rewritten by every build. They sit between invisible
`<!-- AUTO:... -->` markers, so don't edit those parts by hand: change `lc.py` and rebuild. Everything else is written
by hand, and is updated whenever the project changes.

**Use Acrobat or Reader to test the form.** The browser's PDF viewer (Chrome, Edge) shows and fills the form, but it
doesn't run most of the Acrobat JavaScript. So in a browser you won't get the red boxes, locking, Check form or the
QR code. Download the PDF and open it in Acrobat. If a yellow bar appears, enable JavaScript or trust the file.

## Architecture

```
                 ┌──────────────────────────────────────────────────────────────┐
  lc.py          │ THE FORM: 108 questions, their options and rules             │  ← you edit this
                 └──────────────────────────────┬───────────────────────────────┘
                                                ▼
                 ┌──────────────────────────────────────────────────────────────┐
  build_lc.py    │ STEP 1  Lay out the pages                                    │
                 │         sections, questions, boxes, QR page, footers         │
                 │ STEP 2  Add the scripts (from js/), buttons, QR code rows    │
                 │ STEP 3  Write the PDF with pikepdf                           │
                 │ CHECK   Open the result, check it question by question       │
                 │ DOCS    Rewrite this README's question tables and counts     │
                 └──────────────────────────────┬───────────────────────────────┘
                                                ▼
                 ┌──────────────────────────────────────────────────────────────┐
  out/           │ LC-Application.pdf   the finished form (4 pages)             │
                 │ index.html           a page to view it locally               │
                 └──────────────────────────────┬───────────────────────────────┘
                                                ▼  opened in Adobe Acrobat / Reader
                 ┌──────────────────────────────────────────────────────────────┐
  js/            │ document.js  rules engine (red boxes, locking, checks),      │
  (stored inside │              QR code text, QR code encoder                   │
   the PDF)      │ buttons.js   Check form, Reset form, Generate QR Code,       │
                 │              Print Form, warning before save / print         │
                 └──────────────────────────────────────────────────────────────┘
```

## Files

| File | Purpose |
|---|---|
| `lc.py` | **The form.** Every question, one line each: wording, kind, options, mandatory rules, limits, formats. Also the currency list and the starting answers. The only file you need to change for wording or rules. |
| `build_lc.py` | **The builder.** Lays out the pages, adds the scripts and buttons, writes the PDF, checks it, and updates this README. One file in numbered sections, with a contents list at the top (see below). |
| `js/document.js` | **The rules engine**, run by Acrobat inside the PDF: colours boxes red or black, locks questions that don't apply, checks formats and dates. Also makes the QR code's text and draws the code. |
| `js/buttons.js` | **The buttons**, run by Acrobat: Check form, Reset form, Generate QR Code, Print Form, and the warning before saving or printing. One section per button. |
| `helvetica-metrics.json` | Data: Adobe's letter widths for Helvetica, so text is measured exactly as Acrobat draws it. Never changes. |
| `requirements.txt` | The one library (pikepdf) and its three dependencies, at exact versions. |
| `README.md` | This guide. |

**Inside `build_lc.py`:**

| Section | What it does | Change it to... |
|---|---|---|
| 1. Settings | Page size, colours, text sizes, spacing, answer formats | Change the look or the formats |
| 2. Text helpers | Safe characters for the PDF fonts, measuring and wrapping text | (rarely) |
| 3. Rules and dates | "Is this question mandatory now?", "does it apply now?", the date list | (rarely) |
| 4. Step 1: lay out the pages | Where every section, question and box goes | Change how questions are arranged |
| 5. Step 2: scripts, buttons, QR rows | Builds the rules table, attaches the scripts, places the buttons | Add or move a button |
| 6. Step 3: write the PDF | Turns everything into PDF objects with pikepdf | (rarely) |
| 7. Build | Runs the three steps | (rarely) |
| 8. Self-check | Opens the built PDF and checks it | Update the field count if you add or remove questions |
| 9. Documentation | Rewrites this README's question tables, counts and starting answers from `lc.py` | Change how those tables look |
| 10. Run | Builds, checks, saves, updates the README | (rarely) |

**Where to change what:**

| You want to change | Edit |
|---|---|
| A question's wording, options, mandatory rule, max length or format | `lc.py` |
| Add or remove a question | `lc.py`, then the field count (297) in `build_lc.py` section 8 |
| Colours, text sizes, spacing, margins, answer formats | `build_lc.py` section 1 |
| How sections and questions are arranged | `build_lc.py` section 4 |
| How the form checks answers in Acrobat | `js/document.js` |
| What the QR code holds | `js/document.js` (`lcPayload`) |
| What a button says or does | its section in `js/buttons.js` |

## Libraries and licences

| Package | Licence | Used for |
|---|---|---|
| **pikepdf** (bundles the qpdf C++ library, Apache-2.0) | MPL-2.0 | Everything: writes each page's drawing (text, lines, boxes), the fields and how they look, buttons, page links, the scripts and the stored form description |
| lxml (needed by pikepdf) | BSD-3-Clause | Not used by this project directly |
| Pillow (needed by pikepdf) | MIT-CMU | Not used by this project directly |
| packaging (needed by pikepdf) | Apache-2.0 or BSD-2-Clause | Not used by this project directly |
| Python standard library | PSF | Dates, JSON, compression, file handling, and `http.server` for local hosting |

All of these are permissive licences: they allow commercial and internal use, and they don't require you to publish
your own code. MPL-2.0 only asks that changes to *pikepdf's own files* be shared, and this project doesn't change them.
There's no QR library: the QR code is made inside the PDF, by `js/document.js`, when the person presses Generate QR Code.

**Why not PyMuPDF or pdf-lib?** Earlier versions used them. PyMuPDF is AGPL-3.0, a licence banks usually avoid, and its
2.x release installs about a dozen extra AI packages (onnxruntime, numpy, ...). pdf-lib (JavaScript) is MIT but hasn't
had a release since 2021, so security fixes won't come. pikepdf is permissive, actively maintained, and enough on
its own: the page drawing is a few PDF commands (`text`, `line` and `rect` in `build_lc.py` section 4).

## Security

- **What's installed:** 4 packages, about 54 MB, pinned to exact versions in `requirements.txt`. Prebuilt Python
  packages (wheels) don't run code when installed.
- **Native code:** pikepdf includes qpdf (C++). Bugs in PDF libraries usually matter when *opening* untrusted PDFs.
  This builder only *creates* a PDF from `lc.py`, and opens nothing from outside.
- **Where it runs:** build on a trusted machine, and hand out only the finished PDF. People filling in the form
  never get the libraries.
- **What's in the PDF:** JavaScript (the files in `js/`) that runs in each user's Acrobat. This is the same whatever
  builds the PDF, and it's what the bank's IT policy on Acrobat JavaScript applies to. The scripts only read and
  write the form's own fields, show messages and print. They make no network calls and open no files.
- **Upgrading:** to update the libraries, run `.venv/bin/pip install -U pikepdf`, then `.venv/bin/pip freeze >
  requirements.txt`. Then rebuild (it checks itself), and test in Acrobat.

## How the PDF is built

`python build_lc.py` reads the form from `lc.py`, runs three steps, then checks the result:

1. **Lay out the pages (section 4).** Decides where everything goes, and writes each page's text, lines
   and boxes as PDF drawing commands.
   - Header on every page ("DEMO BANK · TRADE SERVICES"); the title and instructions on page 1.
   - Each section: a grey heading band with its number, then its questions on a 12-column grid. Short questions
     share a row. A label sits beside its box when the whole row has room ("Name: [   ]"), otherwise above it.
     Tick boxes have the questions they switch on indented under them. Short sections sit side by side (4 and 5).
   - Each question: its number (e.g. **13.2**), its label, and a red `*` if it's always mandatory.
   - The declaration block (signature, date and company-stamp lines), the QR code page, and the footers on every
     page ("Form LC-01 · v1.0 · Nov 2026", "< Previous page" / "Next page >", "Page n of 4").
   - It also records every fillable box (text box, tick box, drop-down ...) and where it goes. Step 3 makes them.
2. **Add the scripts and buttons (section 5).** Builds the rules table from `lc.py` and fills it into
   `js/document.js`, and says when the rules run (on a click, and on leaving a
   box). Adds the Check form and Reset form buttons on every page, the 177 QR code rows, and the Generate QR Code
   and Print Form buttons.
3. **Write the PDF (section 6, with pikepdf).** Makes every field with its settings and its look (border,
   background, tick, radio dot), the page links, the stored scripts, and a copy of the form's description (JSON)
   for the bank's workbench to read.

The layout runs twice. The second pass gives the room left on the last page of questions to the paragraph boxes on
that page, so the form doesn't end with a blank gap.

The build is **reproducible**: the same `lc.py` on the same day gives a byte-for-byte identical PDF. (The date
drop-downs list the dates from a year back to two years ahead, so they change with the build date.)

## Rules, conditions and validations

### Rules that apply to every question

| Rule | Where it's enforced |
|---|---|
| **Mandatory** questions (red `*`) must be answered | outlined in red with a pink fill while blank or wrong; listed by Check form, Generate QR Code and before save or print |
| **Conditionally mandatory** questions become mandatory when their condition holds (table below) | same as above |
| A conditional question is **locked** until its condition holds: greyed out, read-only, and its answer cleared. This stops a stale answer staying in a question that doesn't apply. | `lcRules` on every change |
| **Max length** (`max`) | the box refuses more characters (PDF `/MaxLen`) |
| **Upper case**: letters are capitalised as you type (SWIFT messages are upper case) | keystroke script on plain text boxes |
| **Allowed characters**: `A-Z a-z 0-9 space . , - / ( ) ' : ? + # & @ %` and line breaks. Anything else is refused as you type, and listed if pasted ("remove ...") | keystroke script, and `lcRules` |
| **Dates** are DD/MM/YYYY and must be real dates | Acrobat's date format plus `lcRules`. With JavaScript off, a drop-down of real dates from a year back to two years ahead (the range depends on the build date). |

### Formats

| Format | Keys allowed while typing | A whole answer must look like | Message |
|---|---|---|---|
| `number` | `0-9` | `^\d+$` | should be a whole number |
| `amount` | `0-9 . ,` | `^\d{1,3}(,?\d{3})*(\.\d{1,2})?$` (e.g. `480,000.00`) | is not an amount |
| `phone` | `0-9 + ( ) - space` | at least one digit, an optional leading `+` | is not a phone number (digits, spaces, + - ( ) only) |
| `account` | `0-9 -` | starts and ends with a digit | is not an account number (digits and - only) |

A wrong whole answer gets an alert when you leave the box, and the box refuses it.

### Checks across answers

| Check | Reported on |
|---|---|
| Date of expiry must not be before the latest shipment date | 11.1 |
| Date of expiry must not be before the application date | 11.1 |
| Latest shipment date must not be before the application date | 10.9 |
| Application date must not be in the future | 1.1 |
| Amount must be more than zero | 8.2 |
| "For FOB/CFR/FCA/CPT" insurance (14.15) must not be filled in when price basis is CIF or CIP (the beneficiary insures) | 14.15 |

### Defaults when the form opens

<!-- AUTO:defaults (written by build_lc.py from lc.py; don't edit by hand) -->
- 2.1 Mode of advising: **Full Swift**
- 11.2 Presentation period (days after shipment): **21**
- 17.1 All bank charges are for account of: **ticked**
- 17.2 Charges for account of: **Beneficiary, except charges at DC Issuing Bank's counter**
- 17.5 Please provide us with post-shipment financing under Docu...: **ticked**
- 17.11 Please debit all DC issuance charges to our account with you: **ticked**
<!-- /AUTO:defaults -->

### Every question

(Written by the build from `lc.py`.)

"Mandatory" says **always**, **when** a condition holds, or **no**. A question with a "when" condition is also locked
until that condition holds, except for 10.4 and 10.7, which are never locked. "Unlocked when" means the question only
applies then, but stays optional.

<!-- AUTO:questions (written by build_lc.py from lc.py; don't edit by hand) -->
**1. Application**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 1.1 | `application_date` | Date | date | **always** |  |  |

**2. Mode of Advising**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 2.1 | `mode_of_advising` | Mode of advising | pick one: Full Swift / Registered Airmail / Airmail with Brief Swift / Courier Service / Courier Service with Brief Swift | **always** |  |  |

**3. Applicant**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 3.1 | `applicant_name` | Applicant name | text | **always** | 35 |  |
| 3.2 | `applicant_address_1` | Applicant address | text | **always** | 35 |  |
| 3.3 | `applicant_address_2` | Applicant address (line 2) | text | no | 35 |  |
| 3.4 | `applicant_address_3` | Applicant address (line 3) | text | no | 35 |  |
| 3.5 | `applicant_address_4` | Applicant address (line 4) | text | no | 35 |  |
| 3.6 | `contact_name` | Contact party for this application & confirmation of FX rate: Name | text | **always** | 35 |  |
| 3.7 | `contact_tel` | Contact party: Tel no | text | **always** | 15 | phone |
| 3.8 | `contact_fax` | Contact party: Fax no | text | no | 15 | phone |

**4. For Bank Use Only** (bank use only)

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 4.1 | `dc_no` | DC no | text | no |  |  |
| 4.2 | `bank_code` | Bank code | text | no |  |  |

**5. Advising Bank (at Issuing Bank's option, if no nomination)**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 5.1 | `advising_bank_name` | Name | text | no | 35 |  |
| 5.2 | `advising_bank_address_1` | Address | text | no | 35 |  |
| 5.3 | `advising_bank_address_2` | Address (line 2) | text | no | 35 |  |
| 5.4 | `advising_bank_address_3` | Address (line 3) | text | no | 35 |  |

**6. For the Benefit of a 3rd Party**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 6.1 | `third_party_name` | Name | text | no | 35 |  |
| 6.2 | `third_party_address_1` | Address | text | no | 35 |  |
| 6.3 | `third_party_address_2` | Address (line 2) | text | no | 35 |  |
| 6.4 | `third_party_address_3` | Address (line 3) | text | no | 35 |  |

**7. Beneficiary**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 7.1 | `beneficiary_name` | Beneficiary's name | text | **always** | 35 |  |
| 7.2 | `beneficiary_address_1` | Beneficiary's address | text | **always** | 35 |  |
| 7.3 | `beneficiary_address_2` | Beneficiary's address (line 2) | text | no | 35 |  |
| 7.4 | `beneficiary_address_3` | Beneficiary's address (line 3) | text | no | 35 |  |
| 7.5 | `beneficiary_address_4` | Beneficiary's address (line 4) | text | no | 35 |  |
| 7.6 | `beneficiary_contact` | Contact person | text | no | 35 |  |
| 7.7 | `beneficiary_tel` | Tel no | text | no | 15 | phone |
| 7.8 | `beneficiary_fax` | Fax no | text | no | 15 | phone |

**8. Credit Amount (Currency & Figures)**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 8.1 | `currency` | Currency | drop-down: ISO currency codes | **always** |  |  |
| 8.2 | `amount` | Amount | text | **always** |  | amount |
| 8.3 | `gst` | For local DCs, amount is (if not checked, it will be inclusive of GST) | pick one: inclusive of GST / No GST | no |  |  |
| 8.4 | `tolerance` | Tolerance on credit amount & goods quantity | tick box | no |  |  |
| 8.5 | `tolerance_plus` | Tolerance + (%) | text | when 8.4 is ticked | 2 | number |
| 8.6 | `tolerance_minus` | Tolerance - (%) | text | when 8.4 is ticked | 2 | number |

**9. Price Basis**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 9.1 | `price_basis` | Price basis | pick one: FOB / CFR / CIF / Local Delivery / FCA / CIP / CPT / Others | **always** |  |  |
| 9.2 | `price_basis_other` | Others (please specify) | text | when 9.1 = "Others" | 35 |  |

**10. Shipment**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 10.1 | `partial_shipment` | Partial shipment | pick one: allowed / not allowed | **always** |  |  |
| 10.2 | `transhipment` | Transhipment | pick one: allowed / not allowed | **always** |  |  |
| 10.3 | `shipment_from` | Shipment from | drop-down: Port of Loading / Airport of Departure / Dispatch from / Place of Taking in charge / Place of Receipt | no |  |  |
| 10.4 | `shipment_from_place` | Shipment from: place | text | when 10.3 is picked | 35 |  |
| 10.5 | `shipment_from_place_2` | Shipment from: place (line 2) | text | no |  |  |
| 10.6 | `shipment_to` | Shipment to | drop-down: Port of Discharge / Airport of Destination / For Transportation to / Place of Final Destination / Place of Delivery | no |  |  |
| 10.7 | `shipment_to_place` | Shipment to: place | text | when 10.6 is picked | 35 |  |
| 10.8 | `shipment_to_place_2` | Shipment to: place (line 2) | text | no |  |  |
| 10.9 | `latest_shipment_date` | Latest shipment date | date | no |  |  |

**11. Expiry and Presentation**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 11.1 | `expiry_date` | Date of expiry (in beneficiary's country) | date | **always** |  |  |
| 11.2 | `presentation_days` | Presentation period (days after shipment) | text | no |  | number |

**12. Back-to-back DC**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 12.1 | `back_to_back` | This is a back-to-back DC to be issued against the master credit (t... | tick box | no |  |  |
| 12.2 | `master_dc_no` | Master credit no | text | when 12.1 is ticked | 20 |  |
| 12.3 | `master_dc_issued_by` | Issued by | text | when 12.1 is ticked | 35 |  |

**13. Drafts**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 13.1 | `drafts` | Drafts for the percentage of invoice value below, at | tick box | no |  |  |
| 13.2 | `drafts_percent` | Percentage of invoice value (%) | text | when 13.1 is ticked | 3 | number |
| 13.3 | `drafts_at` | Drafts at | pick one: Sight / Term / Date | when 13.1 is ticked |  |  |
| 13.4 | `term_days` | Term: days | text | when 13.3 = "Term" |  | number |
| 13.5 | `term_after` | days after | text | when 13.3 = "Term" | 35 |  |
| 13.6 | `draft_date` | Date | date | when 13.3 = "Date" |  |  |
| 13.7 | `term_prepay` | If it is a term LC, please select one | pick one: You may prepay the acceptance of this term LC at the cost of beneficiary / You may not prepay the acceptance of this term LC | when 13.3 = "Term" |  |  |

**14. Documents Required**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 14.1 | `doc_bill_of_lading` | Full set of Clean on Board marine bills of lading | tick box | no |  |  |
| 14.2 | `bl_made_out_to` | Made out to | pick one: order of the Bank / order blank endorsed / other (specify) | when 14.1 is ticked |  |  |
| 14.3 | `bl_made_out_to_other` | Made out to (other) | text | when 14.2 = "other (specify)" | 70 |  |
| 14.4 | `bl_freight` | Marked Freight | pick one: Prepaid / Collect | when 14.1 is ticked |  |  |
| 14.5 | `bl_notify_party` | Notify party (if not specified, notify party is considered to be ap... | text | when 14.1 is ticked | 114 |  |
| 14.6 | `doc_air_waybill` | Original Air Waybill consigned to the Bank | tick box | no |  |  |
| 14.7 | `awb_freight` | Marked Freight | pick one: Prepaid / Collect | when 14.6 is ticked |  |  |
| 14.8 | `awb_notify_party` | Notify party (if not specified, notify party is considered to be ap... | text | when 14.6 is ticked | 114 |  |
| 14.9 | `doc_delivery_order` | Delivery order signed by beneficiary made out to applicant | tick box | no |  |  |
| 14.10 | `do_originals` | Delivery order: originals | text | when 14.9 is ticked | 2 | number |
| 14.11 | `do_copies` | Delivery order: copies | text | when 14.9 is ticked | 2 | number |
| 14.12 | `do_countersigned_by` | Countersigned by how many of our signatories | drop-down: One / Two | when 14.9 is ticked |  |  |
| 14.13 | `do_signature_verified` | Whose signature(s) ... to be verified by the Bank | drop-down: need / need not | when 14.9 is ticked |  |  |
| 14.14 | `doc_insurance` | Marine/Air Insurance Policy or Certificate in duplicate, in Singapo... | tick box | no |  |  |
| 14.15 | `insurance_arrangement` | For FOB/CFR/FCA/CPT | drop-down: Insurance cover note attached / Covered by ultimate buyer / Please arrange insurance on our behalf / Insurance covered by applicant under open Cover No. | no (unlocked when 14.14 is ticked) |  |  |
| 14.16 | `insurance_cover_no` | Open cover no | text | when 14.15 = "Insurance covered by applicant under open Cover No." | 20 |  |
| 14.17 | `insurance_cover_with` | With | text | when 14.15 = "Insurance covered by applicant under open Cover No." | 35 |  |
| 14.18 | `doc_beneficiary_certificate` | Beneficiary's certificate stating 1 set of non-negotiable documents... | tick box | no |  |  |
| 14.19 | `bencert_sent_by` | Sent by | tick any: faxed / mailed / couriered | when 14.18 is ticked |  |  |
| 14.20 | `bencert_days` | Within (days after shipment) | text | when 14.18 is ticked |  | number |
| 14.21 | `doc_commercial_invoice` | Signed commercial invoice | tick box | no |  |  |
| 14.22 | `invoice_originals` | Commercial invoice: originals | text | when 14.21 is ticked | 2 | number |
| 14.23 | `invoice_copies` | Commercial invoice: copies | text | when 14.21 is ticked | 2 | number |
| 14.24 | `doc_packing_list` | Packing list | tick box | no |  |  |
| 14.25 | `packing_list_originals` | Packing list: originals | text | when 14.24 is ticked | 2 | number |
| 14.26 | `packing_list_copies` | Packing list: copies | text | when 14.24 is ticked | 2 | number |
| 14.27 | `doc_weight_note` | Weight note | tick box | no |  |  |
| 14.28 | `weight_note_originals` | Weight note: originals | text | when 14.27 is ticked | 2 | number |
| 14.29 | `weight_note_copies` | Weight note: copies | text | when 14.27 is ticked | 2 | number |
| 14.30 | `doc_certificate_of_origin` | Certificate of origin | tick box | no |  |  |
| 14.31 | `origin_originals` | Certificate of origin: originals | text | when 14.30 is ticked | 2 | number |
| 14.32 | `origin_copies` | Certificate of origin: copies | text | when 14.30 is ticked | 2 | number |
| 14.33 | `origin_country` | Showing country of origin as | text | when 14.30 is ticked | 35 |  |
| 14.34 | `doc_other` | Other documents | tick box | no |  |  |
| 14.35 | `other_documents_1` | Other documents | text | when 14.34 is ticked | 70 |  |
| 14.36 | `other_documents_2` | Other documents (line 2) | text | no (unlocked when 14.34 is ticked) | 70 |  |

**15. Goods Description**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 15.1 | `goods_description` | Goods description (if space is insufficient, attach additional info... | paragraph | **always** | 6500 |  |

**16. Additional Conditions**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 16.1 | `additional_conditions` | Additional conditions (if space is insufficient, attach additional ... | paragraph | no | 6500 |  |

**17. Charges, Confirmation and Settlement**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 17.1 | `bank_charges` | All bank charges are for account of | tick box | **always** |  |  |
| 17.2 | `bank_charges_for` | Charges for account of | pick one: Beneficiary, except charges at DC Issuing Bank's counter / Applicant (including all charges incurred inside and outside of DC Issuing Bank's country) | when 17.1 is ticked |  |  |
| 17.3 | `confirmation` | Confirmation required | tick box | no |  |  |
| 17.4 | `confirmation_charges` | Confirmation charges | pick one: Applicant / Beneficiary | when 17.3 is ticked |  |  |
| 17.5 | `post_shipment_financing` | Please provide us with post-shipment financing under Documentary Cr... | tick box | no |  |  |
| 17.6 | `financing_type` | Financing | pick one: SGD financing / Foreign Currency Financing / Apply Forward Contract | when 17.5 is ticked |  |  |
| 17.7 | `financing_currency` | Foreign currency financing in (type of currency) | drop-down: ISO currency codes | when 17.6 = "Foreign Currency Financing" |  |  |
| 17.8 | `forward_contract_no` | Forward contract no | text | when 17.6 = "Apply Forward Contract" | 20 |  |
| 17.9 | `advance_payment` | We authorise you to debit DC amount in full from our account for ad... | tick box | no |  |  |
| 17.10 | `advance_payment_account` | Account no for advance payment | text | when 17.9 is ticked | 20 | account |
| 17.11 | `debit_issuance_charges` | Please debit all DC issuance charges to our account with you | tick box | no |  |  |
| 17.12 | `issuance_charges_account` | Account no for DC issuance charges | text | **always** | 17 | account |

**18. Declaration and Signature**

| No. | Field | Question | Type | Mandatory | Max | Format |
|---|---|---|---|---|---|---|
| 18.1 | `authorised_person` | Name and title of authorised person(s) | text | no |  |  |
<!-- /AUTO:questions -->

## The JavaScript inside the PDF

Everything is stored in one document-level script, named `lcRules`, built from `js/document.js`. It defines these
functions:

- `lcRules(doc)`: the rules engine. It holds a table `M` of every question that has a rule, a format or
  a lock. On each run it works out, for every question, whether it applies, whether it's mandatory now, and whether
  its answer is blank or wrong. It then sets the box's outline, fill, required flag and lock. It returns the list of
  missing questions, plus `.bad` (wrong answers) and `.first` (the first problem, for the cursor).
- `lcDates(doc)`: in Acrobat, shows each date's calendar box and hides its drop-down list.
- `lcPayload(doc)`: builds the QR code text.
- `lcQrMatrix(text)` and `lcDrawQr(doc, text)`: the QR code (see below).

When `lcRules` runs:

| Event | How |
|---|---|
| Form opens in Acrobat or Reader | end of the document script |
| You leave a text box, list or date | widget `/AA /Bl` |
| You click a tick box, option or date list | widget `/AA /U` |
| Any value changes | hidden field `__checks`, with `/AA /C`; the only entry in `/AcroForm /CO` |
| Check form, Generate QR Code, Print Form | button actions |
| Before save or print | catalog `/AA /WS` and `/WP`: warns if the form is incomplete (but doesn't block) |

The buttons (`js/buttons.js`):

- **Check form** lists what's missing or wrong (at most 15 of each) and puts the cursor on the first problem. If
  nothing is wrong, it says the form is ready.
- **Reset form** asks first, then clears everything back to the starting answers and re-runs the checks.
- **Generate QR Code** is refused while anything is missing or wrong. Otherwise it makes the code and goes to the
  last page.
- **Print Form** is refused until a QR code exists and still matches the current answers. Then it prints.

With JavaScript off, none of this runs. The form still fills, the date lists and page links work, and the mandatory
boxes keep their red outline. Nothing is checked, though.

## How the QR code is made

The code is made **inside the PDF, in Acrobat**, when the person presses Generate QR Code. It isn't made by Python,
and no QR library is used.

1. **The text: `lcPayload` (`js/document.js`).** It gathers every answered question, keyed by field id. Tick boxes
   become `true`, and tick-any questions become lists:
   ```json
   {"form": "LC-01", "version": "1.0", "saved": "2026-11-12T16:30", "complete": true,
    "data": {"applicant_name": "TAN ENGINEERING PTE LTD", "tolerance": true, "bencert_sent_by": ["faxed"], "...": "..."}}
   ```
   - The JSON is padded with spaces to 2,300 characters, so the code is always the same size.
   - If it would be longer, Goods description and then Additional conditions are shortened (ending in "...") and
     listed in `"truncated"`. The full text stays in the PDF's fields.
2. **The code: `lcQrMatrix` (`js/document.js`).** A standard QR encoder, about 70 lines.
   - It makes a version 40 code (177 × 177 squares), with error correction level M, byte mode and mask 0.
   - It places the fixed patterns (finders, timing, alignment, format and version bits).
   - It adds Reed-Solomon error correction: 49 blocks, 28 correction bytes each.
3. **The drawing: `lcDrawQr` (`js/document.js`).** Acrobat scripts can't draw pixels, and Acrobat's own barcode field is
   missing in some installations. So the QR page has **177 read-only text fields, one per row of the code**, each
   with 177 fixed character slots. Each dark square is the letter "n" in the ZapfDingbats font, which prints as a
   solid black square. Each row is set as a string, for example `"nnn n  nn…"`.
4. **Print Form** prints only if the code still matches the current answers.

The bank scans the printed code with any QR reader and gets the JSON.

## Testing in Acrobat

Every build checks the PDF's structure itself: every question's fields, the required flags, limits, starting
answers, the rules table, scripts, buttons and QR rows. The scripts themselves only run inside Acrobat, so after changing a rule
or a script, also test the PDF in Acrobat:
1. On opening, the mandatory boxes are red.
2. Fill a few boxes: each turns black. Empty one again: it turns red.
3. Tick 13.1 Drafts: 13.2 and 13.3 unlock and turn red. Untick it: they lock, grey out and clear.
4. Type letters into 8.2 Amount: they're refused.
5. Press Check form: it lists what's missing.
6. Fill everything, then press Generate QR Code: the code appears on page 4. Scan it with a phone and the JSON shows.

## Changing the form

Edit `lc.py`. Each question is one line. For example:

```python
text("term_days", "Term: days", requiredIf=when("drafts_at", "Term"), format="number"),
```

This line makes a half-width text box named `term_days`, labelled "Term: days". It's mandatory (and unlocked) only
when Drafts at = Term, and it takes digits only. All the options are listed at the top of `lc.py`. The layout,
numbering, scripts, QR code and this README's question table all follow from these lines. Then run
`python build_lc.py` (it checks itself and updates the README). If
you add or remove questions, update the field count (297) in `build_lc.py` section 8.

## Where this came from

1. **Extracted from `pdf-template-studio`.** The builder is that repo's `pdfbuild/build_form.py`, cut down to this one
   form and the JavaScript version only: about 1,040 lines down to 880. The red frames used by the no-JavaScript
   version, the extra modes, and the command-line and one-file-builder options are gone. Before any other change,
   its output matched the full builder's (pages, words, every field and widget, scripts).
2. **Layout changed to match the approved 4-page copy (`test form - Copy.pdf`).** 13.2 now sits beside its box, and the
   Drafts box ends 3 pt higher (`beside` in `lc.py`; `BESIDE_GAP` in `build_lc.py` section 1). Every
   field's page and position matches the copy to within 0.1 pt, and so does every line of text on all 4 pages. These
   defects in the copy were deliberately **not** copied:
   - Its section 14 box on page 2 runs down through the footer.
   - It has no warning before save or print, and no pop-up for a wrong format.
   - Its stored `/FormTemplate` is out of date (no 13.2).
3. **Moved from TypeScript (pdf-lib) to Python (PyMuPDF + pikepdf).** The Python build gives the same PDF as the
   earlier TypeScript build: same pages, text, fields, positions and scripts. The only pixel differences are how the
   text inside boxes is smoothed ("Pick a date", ticks), and Acrobat redraws those boxes itself.
4. **PyMuPDF removed (licence and dependencies): pikepdf only.** The page drawing is now written directly as PDF
   commands. All 4 rendered pages are pixel-identical to the PyMuPDF build.
5. **Restructured for readability.** Plain-English explanations and clearer names throughout, and a header on every
   script. The PDF is byte-for-byte identical to before, apart from those script comments.
6. **Fewer files: 23 down to 7.** The builder is one file again, now in numbered sections with a contents list. The
   8 scripts are now 2 (`document.js`, `buttons.js`). The separate check runs automatically on every build, and the
   local viewing page is written by the build. The PDF is byte-for-byte identical to before.
7. **The README keeps itself up to date.** Every build rewrites the README's question tables, counts and starting
   answers from `lc.py`, so they can't drift from the form. The PDF is unchanged.
