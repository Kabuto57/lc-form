# LC application form (Form LC-01)

This project builds one PDF: the **Irrevocable Documentary Credit Application** (Demo Bank, Form LC-01 · v1.0 · Nov 2026).
It's a fillable form with Adobe Acrobat JavaScript checks and a QR code page.

- 5 pages: 4 pages of questions, plus the QR code page.
- 297 PDF fields: 108 questions, plus date lists, tick-any boxes, buttons and 177 QR rows.
- Its only dependency is [pdf-lib](https://pdf-lib.js.org). It needs Node.js 23.6 or later, because it runs `.ts` files directly with no build tools.

## Run it

```
npm install
npm run build   # writes out/LC-Application.pdf
npm test        # runs the PDF's own rules script on a stand-in for Acrobat (prints PASS)
npm run serve   # builds, then serves out/ at http://localhost:8090
```

`npm run serve` uses Python's built-in web server (`python3`, already on macOS). The page shows the PDF and has a
download link. Press Ctrl+C to stop it.

**Use Acrobat or Reader to test the form.** The browser's PDF viewer (Chrome, Edge) shows and fills the form, but it
doesn't run most of the Acrobat JavaScript. So in a browser you won't get the red boxes, locking, Check form or the
QR code. Download the PDF and open it in Acrobat. If a yellow bar appears, enable JavaScript or trust the file.

## Files

| File | What it does |
|---|---|
| `src/lc.ts` | **The form.** Every question, its options, and its rules, one line each. Edit here. |
| `src/lists.ts` | ISO currency codes (and countries) for the drop-downs |
| `src/form/types.ts` | The vocabulary: `Field`, `Rule`, `Section`, `Template`, the answer formats, the allowed characters |
| `src/form/rules.ts` | "Is this question mandatory now?" and "Does it apply now?" |
| `src/form/build.ts` | `buildPdf`: lays out the pages (header, sections, question numbers, boxes, footers, page links) |
| `src/form/look.ts` | Page size, margins, colours, text wrapping |
| `src/form/dates.ts` | Date questions: a drop-down of real dates, plus Acrobat's calendar box when JavaScript runs |
| `src/form/acrobat-script.ts` | The JavaScript inside the PDF: the rules engine, Check form, Reset form, the QR code, typing filters |
| `src/form/red-frames.ts` | Red frames that need no scripts. Used only by the `no-javascript` mode, not by this PDF. |
| `src/form/stored-template.ts` | Stores the form description (JSON) inside the PDF, under the catalog key `/FormTemplate` |
| `build.ts` | Entry point: `buildPdf(LC.template, LC.defaults, "javascript")` written to `out/LC-Application.pdf` |
| `check.ts` | The self-check (`npm test`) |
| `index.html` | The local page served by `npm run serve` |

## How the PDF is built

`buildPdf` (in `src/form/build.ts`) does these steps:

1. Stores the form description (`LC.template`) as JSON inside the PDF.
2. Draws the header on every page: "DEMO BANK · TRADE SERVICES", plus the **Check form** and **Reset form** buttons
   (on screen only, never printed). Then the title and instructions on page 1.
3. Draws each section: a grey heading bar with its number, then its questions on a 12-column grid. Two short
   questions share a row. A label sits beside its box when the whole row fits ("Name: [   ]"), otherwise above it.
   Tick boxes have their follow-up questions indented under them. Sections 4 (bank use) and 5 sit side by side.
4. Draws each question: its number (e.g. **13.2**), its label, a red `*` if always mandatory, and its box. Mandatory
   boxes are outlined in red when the form opens. The field name is the question's `id`, and the tooltip is its label.
5. Adds the page footers ("Form LC-01 · v1.0 · Nov 2026", "< Previous page" / "Next page >" links, "Page n of 5").
6. Adds the declaration block, with signature, date and company-stamp lines, and then the QR code page.
7. Adds the JavaScript (see below).

The layout runs twice. The second pass gives the room left on the last page to the paragraph boxes on that page, so
the form doesn't end with a blank gap.

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

Mode of advising = Full Swift · Presentation period = 21 · 17.1 All bank charges ticked, with 17.2 = Beneficiary ·
17.5 Post-shipment financing ticked · 17.11 Debit issuance charges ticked.

### Every question

"Mandatory" says **always**, **when** a condition holds, or **no**. A question with a "when" condition is also locked
until that condition holds, except for 10.4 and 10.7, which are never locked. "Unlocked when" means the question only
applies then, but stays optional.

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

## The JavaScript inside the PDF

Everything lives in one document-level script, named `lcRules` and stored as a stream. It defines these functions:

- `lcRules(doc)`: the rules engine. It holds a table `M` of every question that has a rule, a format or a lock.
  On each run it works out, for every question, whether it applies, whether it's mandatory now, and whether its
  answer is blank or wrong. It then sets the box's outline, fill, required flag and lock. It returns the list of
  missing questions, plus `.bad` (wrong answers) and `.first` (the first problem, for the cursor).
- `lcDates(doc)`: in Acrobat, shows each date's calendar box and hides its drop-down list.
- `lcPayload(doc)`: builds the QR code text (see below).
- `lcQrMatrix(text)` and `lcDrawQr(doc, text)`: a QR encoder (version 40, error correction M). It draws the code
  into 177 read-only comb text fields `__qr_0` ... `__qr_176`, using the ZapfDingbats black square character. So it
  doesn't need Acrobat's barcode feature.

When `lcRules` runs:

| Event | How |
|---|---|
| Form opens in Acrobat or Reader | end of the document script |
| You leave a text box, list or date | widget `/AA /Bl` |
| You click a tick box, option or date list | widget `/AA /U` |
| Any value changes | hidden field `__checks`, with `/AA /C`; the only entry in `/AcroForm /CO` |
| Check form, Generate QR Code, Print Form | button actions |
| Before save or print | catalog `/AA /WS` and `/WP`: warns if the form is incomplete (but doesn't block) |

The buttons:

- **Check form** lists what's missing or wrong (at most 15 of each) and puts the cursor on the first problem. If
  nothing is wrong, it says the form is ready.
- **Reset form** asks first, then clears everything back to the defaults and re-runs the checks.
- **Generate QR Code** is refused while anything is missing or wrong. Otherwise it fills hidden field `__qr` with
  the JSON payload, draws the code, and goes to the last page.
- **Print Form** is refused until a QR code exists and still matches the current answers. Then it prints.

The QR code holds this JSON, padded with spaces to 2,300 characters so the code is always the same size:

```json
{"form": "LC-01", "version": "1.0", "saved": "2026-11-12T16:30", "complete": true,
 "data": {"applicant_name": "TAN ENGINEERING PTE LTD", "tolerance": true, "bencert_sent_by": ["faxed"], "...": "..."}}
```

`data` holds only answered questions, keyed by field id. Tick boxes become `true`, and tick-any questions become
lists. If the JSON would be too long, Goods description and then Additional conditions are shortened, ending in
"...", and listed in `"truncated"`. The full text stays in the PDF's fields.

With JavaScript off, none of the above runs. The form still fills, the date lists and page links work, and the
mandatory boxes keep their red outline. Nothing is checked, though.

## Changing the form

Edit `src/lc.ts`. Each question is one line. For example:

```ts
text("term_days", "Term: days", { requiredIf: when("drafts_at", "Term"), format: "number" }),
```

This line makes a half-width text box named `term_days`, labelled "Term: days". It's mandatory (and unlocked) only
when Drafts at = Term, and it takes digits only. The other options:
`...req` (always mandatory), `requiredIf: ticked("x")`, `activeIf: ticked("x")` (applies only when x is ticked, but
optional), `max: 35`, `format: "amount" | "number" | "phone" | "account"`, and `half: false` (full width).
The layout, numbering, scripts and QR payload all follow from these lines. Then run `npm run build && npm test`.
`check.ts` expects 5 pages and 297 fields, so update those numbers if you add or remove questions.

## Where this came from

This code was extracted from `pdf-template-studio` at commit `ce54788` (10 Nov 2026, "LC: editable drafts
percentage"). It keeps only the 10 source files (of 112) that build this PDF, and one dependency instead of seven.
The code is unchanged, apart from two things: imports now end in `.ts` so Node runs them directly, and the unused
"uploaded PDF" branch was removed. With the clock frozen to the same time, this project's output is **byte-for-byte
identical** to the original repo's `LC-Application-JavaScript.pdf` at that commit. (Without a frozen clock, the
creation date and the range of the date lists change with the build date.)
