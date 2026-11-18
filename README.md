# LC application form (Form LC-01)

This project builds one PDF: the **Irrevocable Documentary Credit Application** (Demo Bank, Form LC-01 · v1.0 · Nov 2026).
It's a fillable form with Adobe Acrobat JavaScript checks and a QR code page. It's built in **Python**.

- 4 pages: 3 pages of questions, plus the QR code page.
- 477 PDF fields: 108 questions, plus date lists, tick-any boxes, buttons and the rows of two QR codes (177 each).

- Needs Python 3.9 or later and **one library to build, pikepdf** (plus zxing-cpp to read QR codes). All its licences are permissive (no GPL/AGPL).
- **New to this? Read [GUIDE.md](GUIDE.md) first.** It shows, step by step, how to change the form and how to make a
  similar one, without needing to know Python.
- **A form file plus 4 engine files build the PDF:** the form (`forms/lc_form.py`, the only one you edit) and four
  engine files that are the same for every form (`build.py`, `layout.py`, `pdf_writer.py`, `acrobat_js.py`). One
  command builds the PDF and checks it.
- **Folders:** the engine files at the top; every form file in `forms/`; `tools/smartform/` holds the tools that
  copied the old smart form (not needed to build); `benchmark/` is the QR code vs AI reading test.

## Run it

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build.py lc_form.py               # builds out/LC-Application.pdf, checks it, prints PASS
.venv/bin/python -m http.server 8090 -d out        # serves it at http://localhost:8090 (Ctrl+C stops it)
```

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.

The build checks twice and stops with the reason, saving nothing, if anything is wrong:
- **before building**, it checks the form file for mistakes (a misspelt option, a rule that names a question that
  doesn't exist, two questions with the same id ...) and says which question and what to fix;
- **after building**, it opens the PDF and checks every question's fields, flags, limits, rules, scripts and buttons.

It also stops with a clear message if an engine file is missing, cut short or changed while being copied (for
example an invisible "byte order mark" or curly quotes added by an editor), instead of building a PDF whose checks
silently don't work.

**This README is written by hand.** The page and field counts, the starting answers and the table of every question
below describe `lc_form.py`: when you change the form, update them here too.

**Use Acrobat or Reader to test the form.** The browser's PDF viewer (Chrome, Edge) shows and fills the form, but it
doesn't run most of the Acrobat JavaScript. So in a browser you won't get the red boxes, locking, Check form or the
QR code. Download the PDF and open it in Acrobat. If a yellow bar says JavaScript is disabled, choose Options >
Enable JavaScript (or Preferences > JavaScript > Enable Acrobat JavaScript): with JavaScript off, nothing is checked,
dates are plain drop-down lists, and Check form says "The form's checks did not start".

## Architecture

```
                 ┌──────────────────────────────────────────────────────────────┐
  forms/         │ THE FORM (what it asks): 108 questions, options and rules    │  ← you edit this
  lc_form.py     │ FORM, DEFAULTS, and the settings PDF_NAME, PAGES             │
                 └──────────────────────────────┬───────────────────────────────┘
                                                ▼  python build.py lc_form.py
                 ┌──────────────────────────────────────────────────────────────┐
  build.py       │ 1. the words form files use (text, radio, date, when ...)    │
                 │    and check_form: mistakes in the form file, in plain words │
                 │ 2. run: load the form file, check it, build, check, save     │
                 └──────────────────────────────┬───────────────────────────────┘
                                                ▼
                 ┌──────────────────────────────────────────────────────────────┐
  layout.py      │ STEP 1  lay out the pages (+ settings, text helpers, rules,  │
                 │         Helvetica letter widths)                             │
  pdf_writer.py  │ STEP 2  rules table, scripts, buttons, QR code rows          │
                 │ STEP 3  write the PDF with pikepdf                           │
                 │ CHECK   open the result, check it question by question       │
  acrobat_js.py  │ the JavaScript stored in the PDF (as Python text)            │
                 └──────────────────────────────┬───────────────────────────────┘
                                                ▼
                 ┌──────────────────────────────────────────────────────────────┐
  out/           │ LC-Application.pdf   the finished form (4 pages)             │
                 │ index.html           a page to view it locally               │
                 └──────────────────────────────┬───────────────────────────────┘
                                                ▼  opened in Adobe Acrobat / Reader, filled in, printed
                 ┌──────────────────────────────────────────────────────────────┐
  inside the PDF │ DOCUMENT_JS  rules engine (red boxes, locking, checks),      │
  (acrobat_js.py)│              QR code text, QR code encoder                   │
                 │ BUTTON_JS    Check form, Reset form, Generate QR Code,       │
                 │              Print Form, warning before save / print         │
                 └──────────────────────────────────────────────────────────────┘
```

**Why so few files, all Python.** A form-maker opens only the form file. The engine is the same for every
form, split into one file per step so each stays readable. The JavaScript is kept inside a Python file
(`acrobat_js.py`), not in separate `.js` files: copying the project by hand then can't leave the scripts behind,
and if a file is cut short Python refuses to run instead of producing a broken form. One folder, `forms/`, for the
form files: `python build.py lc_form.py` looks there, and says so if the file isn't found.

## Files

| File | Purpose | Who opens it |
|---|---|---|
| `forms/lc_form.py` | **The LC form.** Every question, one line each: wording, kind, options, mandatory rules, limits, formats. Also the currency list, the starting answers, and two build settings (`PDF_NAME`, `PAGES`). | Anyone changing the form |
| `forms/example_form.py` | A small, fully commented example form (Annual Leave Request). Copy it to start a new form; name the copy `<something>_form.py`. | Anyone making a new form |
| `forms/eblc_form.py` | **EBLC** (Handling / Financing of Documents under Export Documentary Credit, Form EBLC-01), redrawn from the old smart form with its rules. | Anyone changing that form |
| `forms/`: `lc_amendment_form.py`, `obc_form.py`, `import_financing_form.py`, `export_financing_form.py`, `bg_form.py`, `sblc_form.py`, `bg_amendment_form.py`, `sblc_amendment_form.py`, `bill_of_exchange_form.py`, `bill_of_exchange_eblc_form.py`, `bill_of_exchange_obc_form.py` | **The other trade forms** of the old smart form (LC amendment, export collection, import / export financing, banker's guarantee, standby LC, both amendments, the three bills of exchange), each redrawn in this project's look with the old form's questions, wording and rules. Build each like the LC form: `python build.py bg_form.py`. They use `lc_form.py`'s currency and country lists, so keep them all in `forms/`. | Anyone changing those forms |
| `build_all.py` | **Builds the whole smart form as one PDF** (`python build_all.py` -> `out/Trade-Application-Forms.pdf`): a main menu page (Import / Export / Loans / Guarantees); click a form and only that form is shown (like the old smart form: every form's pages are hidden page templates, shown by the menu's script), each form with a Main menu button on every page, and bookmarks. Needs Acrobat with JavaScript on. Each form keeps its own rules, Check form, Reset form and QR code (its fields are renamed `LC.applicant_name`, `BG.applicant_name` ...). | To build the full PDF |
| `tools/smartform/` | **How the trade forms were made** (not needed to build): tools that read the old vendor smart form in Adobe Acrobat (`harvest.py`, `acrobat/`), found its rules by trying every choice (`acrobat/probe.js`), and wrote first drafts of the form files (`convert.py`, `draft_forms.py`, `drafts/`). `build_smartform.py` is an earlier experiment that copies the old look into one PDF with a menu (`out/Trade-Application-Forms-old-look.pdf`). | Developers |
| `build.py` | **Run this.** Section 1: the question helpers and every option a question can have, and `check_form`, which explains mistakes in a form file. Section 2: loads a form file, checks it, builds, checks the PDF, saves it in `out/`. | To look up an option |
| `layout.py` | Step 1: where every section, question and box goes. Also the settings (section 1: page size, colours, text sizes, spacing, answer formats), text helpers, the rules ("mandatory now?") and Adobe's Helvetica letter widths. | To change the look of every form |
| `pdf_writer.py` | Step 2: builds the rules table, attaches the scripts, places the buttons and QR code rows. Step 3: writes the PDF with pikepdf. Then the self-check. Refuses scripts with characters that would break Acrobat. | Rarely |
| `acrobat_js.py` | The JavaScript Acrobat runs inside the PDF: `DOCUMENT_JS` (rules engine, QR code text, QR encoder) and `BUTTON_JS` (one entry per button). Plain ASCII only. | To change how answers are checked or what a button does |
| `read_qr.py` | **Reads the QR code(s)** from scanned images (or text from a handheld scanner), joins two codes, re-checks every answer against the form file, and saves the result as JSON in `out/`. Not needed to build. | The Bank's side |
| `benchmark/` | **QR code vs AI test** (not needed to build): 10 fake filled-in LC scans (typed with QR, handwritten; clean / medium / poor), read by the QR code and by Gemini 3.7 Flash, scored per form and per field. Report: `benchmark/LC-QR-vs-AI.xlsx`; pictures in `benchmark/screenshots/`; how to re-run in `benchmark/README.md`. | To compare QR with AI |
| `GUIDE.md` | Step-by-step guide for beginners, including copying the files to a work computer and fixing common problems. | Everyone, first |
| `README.md` | This reference. | When you need the details |
| `requirements.txt` | pikepdf and its three dependencies (to build), and zxing-cpp (to read QR codes), at exact versions. | Setup |

**Where to change what:**

| You want to change | Edit |
|---|---|
| A question's wording, options, mandatory rule, max length or format | `forms/lc_form.py` |
| How wide a section is, or start it on a new page | `width="full"` / `width="half"` / `new_page=True` on its `section(...)` in the form file |
| How wide one question is (e.g. a whole row) | add `cols=12` (or `cols=6` for half) to its line in the form file |
| Add or remove a question | `forms/lc_form.py` (nothing else: the checks follow the form) |
| The number of pages the form must fit on | `PAGES` in `forms/lc_form.py` |
| Make a new form | copy `forms/example_form.py` to `forms/<name>_form.py` (see [GUIDE.md](GUIDE.md)) |
| Colours, text sizes, spacing, margins, answer formats | `layout.py`, section 1 |
| How sections and questions are arranged | `layout.py`, section 4 |
| How the form checks answers in Acrobat | `DOCUMENT_JS` in `acrobat_js.py` |
| What the QR code holds | `lcPayload` in `acrobat_js.py` |
| What a button says or does | its entry in `BUTTON_JS` in `acrobat_js.py` |

## Libraries and licences

| Package | Licence | Used for |
|---|---|---|
| **pikepdf** (bundles the qpdf C++ library, Apache-2.0) | MPL-2.0 | Everything: writes each page's drawing (text, lines, boxes), the fields and how they look, buttons, page links, the scripts and the stored form description |
| lxml (needed by pikepdf) | BSD-3-Clause | Not used by this project directly |
| Pillow (needed by pikepdf) | MIT-CMU | Not used by this project directly |
| packaging (needed by pikepdf) | Apache-2.0 or BSD-2-Clause | Not used by this project directly |
| **zxing-cpp** (only for `read_qr.py`) | Apache-2.0 | Reads the printed QR codes from scanned images. Not needed to build the PDF |
| Python standard library | PSF | Dates, JSON, compression, file handling, and `http.server` for local hosting |

All of these are permissive licences: they allow commercial and internal use, and they don't require you to publish
your own code. MPL-2.0 only asks that changes to *pikepdf's own files* be shared, and this project doesn't change them.
There's no QR library: the QR code is made inside the PDF, by `acrobat_js.py`, when the person presses Generate QR Code.

**Why not PyMuPDF or pdf-lib?** Earlier versions used them. PyMuPDF is AGPL-3.0, a licence banks usually avoid, and its
2.x release installs about a dozen extra AI packages (onnxruntime, numpy, ...). pdf-lib (JavaScript) is MIT but hasn't
had a release since 2021, so security fixes won't come. pikepdf is permissive, actively maintained, and enough on
its own: the page drawing is a few PDF commands (`text`, `line` and `rect` in `layout.py`).

## Security

- **What's installed:** 4 packages, about 54 MB, pinned to exact versions in `requirements.txt`. Prebuilt Python
  packages (wheels) don't run code when installed.
- **Native code:** pikepdf includes qpdf (C++). Bugs in PDF libraries usually matter when *opening* untrusted PDFs.
  This builder only *creates* a PDF from a form file, and opens nothing from outside. Note that a form file is
  Python and is run by the builder, so only build form files you trust (treat them like code, not data).
- **Where it runs:** build on a trusted machine, and hand out only the finished PDF. People filling in the form
  never get the libraries.
- **What's in the PDF:** JavaScript (`acrobat_js.py`) that runs in each user's Acrobat. This is the same whatever
  builds the PDF, and it's what the bank's IT policy on Acrobat JavaScript applies to. The scripts only read and
  write the form's own fields, show messages and print. They make no network calls and open no files.
- **Upgrading:** run `.venv/bin/pip list --outdated` to see newer versions, then change the version numbers in
  `requirements.txt` by hand (keep its comments) and run `.venv/bin/pip install -r requirements.txt`. Then rebuild
  (it checks itself), and test in Acrobat.

## How the PDF is built

`python build.py lc_form.py` reads the form from `lc_form.py`, checks it for mistakes, runs three steps, then checks the result:

1. **Lay out the pages (`layout.py`).** Decides where everything goes, and writes each page's text, lines
   and boxes as PDF drawing commands.
   - Header on every page ("DEMO BANK · TRADE SERVICES"); the title and instructions on page 1.
   - Each section: a grey heading band with its number, then its questions on a 12-column grid. Short questions
     share a row (`cols=N` on a question fixes its width: 12 = whole row, 6 = half). A label sits beside its box when the whole row has room ("Name: [   ]"), otherwise above it.
     Tick boxes have the questions they switch on indented under them. Short sections sit side by side (4 and 5).
   - Each question: its number (e.g. **13.2**), its label, and a red `*` if it's always mandatory.
   - The declaration block (signature, date and company-stamp lines), the QR code page, and the footers on every
     page ("Form LC-01 · v1.0 · Nov 2026", "< Previous page" / "Next page >", "Page n of 4").
   - It also records every fillable box (text box, tick box, drop-down ...) and where it goes. Step 3 makes them.
2. **Add the scripts and buttons (`pdf_writer.py`).** Builds the rules table from the form and fills it into
   `DOCUMENT_JS`, and says when the rules run (on a click, and on leaving a
   box). Adds the Check form and Reset form buttons on every page, the rows of two QR codes (177 each), and the Generate QR Code
   and Print Form buttons.
3. **Write the PDF (`pdf_writer.py`, with pikepdf).** Makes every field with its settings and its look (border,
   background, tick, radio dot), the page links, the stored scripts, and a copy of the form's description (JSON)
   for the bank's workbench to read.

The layout runs twice. The second pass gives the room left on the last page of questions to the paragraph boxes on
that page, so the form doesn't end with a blank gap.

The build is **reproducible**: the same form file on the same day gives a byte-for-byte identical PDF. (The date
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
| `cif` | `0-9` | 7 digits | should be your 7-digit C.I.F. number |
| `ref12` | `0-9` | 12 digits | should be a 12-digit reference number |
| `fx8` / `fx2` | `0-9` | 8 digits / 2 digits | FX contract number / sequence |
| `swift` | letters, digits | 8 or 11 letters and digits | is not a SWIFT address |

A wrong whole answer gets an alert when you leave the box, and the box refuses it.

### Checks across answers

A form file can add its own checks in `FORM["checks"]` (helpers in `build.py`): `not_before` / `after` (one date not
before / strictly after another), `in_range` (a number between two values) and `account_length` (an account number's
length, by currency). They run in Acrobat (`across()` in `acrobat_js.py`) and in `read_qr.py`. A question with
`words=["amount", "currency"]` is filled in by the form with the amount in words (the bills of exchange use it).
The LC form's own checks:

| Check | Reported on |
|---|---|
| Date of expiry must not be before the latest shipment date | 11.1 |
| Date of expiry must not be before the application date | 11.1 |
| Latest shipment date must not be before the application date | 10.9 |
| Application date must not be in the future | 1.1 |
| Amount must be more than zero | 8.2 |
| "For FOB/CFR/FCA/CPT" insurance (14.15) must not be filled in when price basis is CIF or CIP (the beneficiary insures) | 14.15 |

### Defaults when the form opens

- 2.1 Mode of advising: **Full Swift**
- 11.2 Presentation period (days after shipment): **21**
- 17.1 All bank charges are for account of: **ticked**
- 17.2 Charges for account of: **Beneficiary, except charges at DC Issuing Bank's counter**
- 17.5 Please provide us with post-shipment financing under Docu...: **ticked**
- 17.11 Please debit all DC issuance charges to our account with you: **ticked**

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
| 8.1 | `currency` | Currency | drop-down: 160 options (SGD, USD, EUR, ...) | **always** |  |  |
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
| 17.7 | `financing_currency` | Foreign currency financing in (type of currency) | drop-down: 160 options (SGD, USD, EUR, ...) | when 17.6 = "Foreign Currency Financing" |  |  |
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

Everything is stored in one document-level script, named `lcRules`, built from `DOCUMENT_JS` in `acrobat_js.py`. It defines these
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

The buttons (`BUTTON_JS` in `acrobat_js.py`):

- **Check form** lists what's missing or wrong (at most 15 of each) and puts the cursor on the first problem. If
  nothing is wrong, it says the form is ready.
- **Reset form** asks first, then clears everything back to the starting answers, removes the QR codes, and
  re-runs the checks.
- **Generate QR Code** is refused while anything is missing or wrong. Otherwise it makes the code (two codes if the
  answers don't fit in one) and goes to the last page.
- **Print Form** is refused until a QR code exists and still matches the current answers. Then it prints.

With JavaScript off, none of this runs. The form still fills, the date lists and page links work, and the mandatory
boxes keep their red outline. Nothing is checked, though.

## How the QR code is made

The code is made **inside the PDF, in Acrobat**, when the person presses Generate QR Code. It isn't made by Python,
and no QR library is used.

**One code, or two when the answers don't fit.** One QR code holds 2,300 characters. Most applications fit, and get
one code. When the answers are longer, a **second code appears under the buttons**, and the Bank scans both. The QR
page always has room for two, one above the other. The Generate QR Code and Print Form buttons stay right under the
first code, where they always were:

```
  APPLICATION QR CODE (FOR BANK USE)
  instructions ...
            QR code 1 of 2 (scan both codes)      <- label: only when there are two codes
           ┌──────────────────────┐
           │      QR code 1       │                   always used
           └──────────────────────┘
        [ Generate QR Code ]  [ Print Form ]
            QR code 2 of 2
           ┌──────────────────────┐
           │      QR code 2       │                   frame and code appear only when needed
           └──────────────────────┘
```

Each code is 110 mm square: 177 × 177 squares of 0.6 mm.

1. **The text: `lcPayload` (`acrobat_js.py`).** It gathers every answered question, keyed by field id. Tick boxes
   become `true`, and tick-any questions become lists:
   ```json
   {"form": "LC-01", "version": "1.0", "saved": "2026-11-12T16:30", "complete": true,
    "data": {"applicant_name": "TAN ENGINEERING PTE LTD", "tolerance": true, "bencert_sent_by": ["faxed"], "...": "..."}}
   ```
   - The JSON is padded with spaces to 2,300 characters (one code), or to 4,600 when it needs two.
   - Two codes hold 4,600 characters. Only if the answers are longer still are Goods description and then
     Additional conditions shortened (ending in "...") and listed in `"truncated"`. The full text stays in the
     PDF's fields.
2. **Splitting: `lcDrawQr` (`acrobat_js.py`).** If the text is too long for one code (2,329 bytes), it is cut in half:
   code 1 holds the first half, code 2 the second. Each code is marked with the QR standard's **structured append**
   header ("code 1 of 2", "code 2 of 2", plus a check value of the whole text), so scanners that support it join
   the two codes automatically. With any other scanner, scan code 1, then code 2, and put the two texts together in
   that order: the result is exactly the JSON above. Text too long for two codes is refused with a message; a code
   that can't be read is never drawn.
3. **The code: `lcQrMatrix` (`acrobat_js.py`).** A standard QR encoder, about 70 lines.
   - It makes a version 40 code (177 × 177 squares), with error correction level M, byte mode and mask 0.
   - It places the fixed patterns (finders, timing, alignment, format and version bits).
   - It adds Reed-Solomon error correction: 49 blocks, 28 correction bytes each.
4. **The drawing: `lcDrawQr` (`acrobat_js.py`).** Acrobat scripts can't draw pixels, and Acrobat's own barcode field is
   missing in some installations. So for each code the QR page has **177 read-only text fields, one per row of the
   code** (`__qr1_0` ... `__qr1_176`, and `__qr2_0` ... `__qr2_176`), each with 177 fixed character slots. Each
   dark square is the letter "n" in the ZapfDingbats font, which prints as a solid black square. Each row is set as
   a string, for example `"nnn n  nn…"`. The second code's frame (`__qr2_frame`) and the labels (`__qr1_label`,
   `__qr2_label`) are fields too, so they show only when there are two codes.
5. **Print Form** prints only if the code (or codes) still match the current answers.

The bank scans the printed code (or both codes) with a QR reader and gets the JSON.

## Reading the QR codes

`read_qr.py` is the Bank's side: it reads the printed code(s) and checks the answers.

```
.venv/bin/python read_qr.py scan.png                 # one image with one or both codes
.venv/bin/python read_qr.py page1.jpg page2.jpg      # codes in separate images, in any order
.venv/bin/python read_qr.py scanned.txt              # text from a handheld scanner, one code per line
```

It prints `ACCEPTED` or `NOT ACCEPTED` with the reasons, and saves `out/LC-01-<date and time>.json`:

```json
{"form": "LC-01", "version": "1.0", "saved": "2026-11-17T09:50", "codes": 2, "accepted": true,
 "problems": [], "warnings": [], "data": {"applicant_name": "TAN ENGINEERING PTE LTD", "...": "..."}}
```

What it does:
1. **Reads every QR code** in the image(s) with zxing-cpp. PNG, JPG, BMP and TIFF (every page of a multi-page TIFF)
   work. A scanner's PDF can't be read directly (reading PDFs as images needs another library): save the scan as an
   image instead. Scan at 300 dpi or more.
2. **Joins two codes.** The order is the one that makes valid JSON (code 1 of 2 always starts the JSON), so the
   images can be given in any order. If only one of two codes is found, it says "Scan both". The same code
   scanned twice counts once.
3. **Finds the form file** (`forms/*_form.py`) whose form code matches the QR code's `"form"` (e.g. `LC-01`), and warns if the
   form version differs.
4. **Re-checks every answer** (`check_answers`, at the end of `read_qr.py`), because a QR code comes from outside the Bank and could have
   been made or edited by anyone: unknown answers, wrong kinds of value, options that don't exist, lengths over
   max, formats and dates, characters the form doesn't allow, mandatory questions left blank, answers to locked
   questions, and the checks across answers (expiry after shipment, and so on). "In the future" is measured from
   when the code was made.
5. **Warns** (without refusing) if paragraphs were shortened to fit (`"truncated"`), or if the form itself said it
   wasn't complete.

Exit status 0 means accepted and 1 means not, so another program (the Bank's workbench) can run it and read the
JSON.

### Which library reads the codes, and why

| Option | Licence | Two codes (structured append) | Notes |
|---|---|---|---|
| **zxing-cpp** (used here) | Apache-2.0 | reads each code; `read_qr.py` joins them | The C++ version of Google's ZXing, the most widely used open-source barcode reader (its Java original is in many Android apps). Reads dense version 40 codes, tilted and blurred scans. Prebuilt for Windows, Mac and Linux, no dependencies. Actively maintained. |
| ZBar / pyzbar | LGPL-2.1 | no | Older, rarely updated, weaker on dense codes. LGPL is more restrictive. |
| OpenCV QR reader | Apache-2.0 | no | A large library (about 100 MB) for one job; less reliable on version 40 codes. |
| Commercial SDKs (Dynamsoft, Scandit, Cognex ...) | paid | yes | What some banks buy for high-volume scanning, with vendor support. Worth it only at scale. |
| Handheld 2D scanners (Honeywell, Zebra ...) | hardware | many models can join structured-append codes (check the model's manual) | Common at bank counters. They "type" the code's text into the computer: save it as a `.txt` file (one code per line) and use `read_qr.py scanned.txt`. |

zxing-cpp's Python package doesn't report which code is "1 of 2", so `read_qr.py` works out the order from the
text instead (only one order makes valid JSON). Tested: one code; both codes on a rendered page; two images in the
wrong order; one of two codes only (refused, "Scan both"); a blank image; a page rescaled to 300 dpi, rotated
1.5°, blurred, speckled and saved as a low-quality JPG (read and accepted); and a QR text with 9 planted mistakes
(all 9 reported, not accepted).

**Security.** The QR text is read only as JSON (never run), limited to the size two codes can hold, and every
value is checked against the form before anything is accepted. zxing-cpp is native code that parses images: give
it scans from the Bank's own scanners, and keep it at the pinned version (update it like pikepdf, see Security).

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
7. Paste a long text (about 2,000 characters) into Goods description and press Generate QR Code again: two codes
   appear, labelled 1 of 2 and 2 of 2. Scan both; together they give the JSON. Shorten the text and generate again:
   back to one code, and the second frame disappears. Test the two codes with the Bank's own scanner too.

## Changing the form, and making a new one

See **[GUIDE.md](GUIDE.md)**: it covers both step by step, with a table of common changes.

In short: edit `forms/lc_form.py` (one line per question; a cheat sheet is at the top of the file, and every kind and
option is listed in section 1 of `build.py`), then run `python build.py lc_form.py`. For a new form, copy
`forms/example_form.py` to `forms/<name>_form.py`, change the parts marked `CHANGE`, and run `python build.py <name>_form.py`.

If you changed questions, also update their rows in [Every question](#every-question) above, and tell the Bank's
system team about new or renamed ids (they read the QR code's answers by id).

Note: `half=True` / `half=False` on a question is kept in the PDF's copy of the form but has no effect on the
layout: box widths are worked out from the label and `max`.

## Where this came from

1. **Extracted from `pdf-template-studio`.** The builder is that repo's `pdfbuild/build_form.py`, cut down to this one
   form and the JavaScript version only: about 1,040 lines down to 880. The red frames used by the no-JavaScript
   version, the extra modes, and the command-line and one-file-builder options are gone. Before any other change,
   its output matched the full builder's (pages, words, every field and widget, scripts).
2. **Layout changed to match the approved 4-page copy (`test form - Copy.pdf`).** 13.2 now sits beside its box, and the
   Drafts box ends 3 pt higher (`beside` in `lc.py`; `BESIDE_GAP` in the builder's settings). Every
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
8. **Libraries and stale notes updated.** pikepdf 10.18.0 to 10.18.1 (the other three were already the latest).
   `requirements.txt` now says what each package is for and its licence. Notes in `lc.py` and `js/document.js` that
   still named files removed in step 6 (`check.py`, `lcbuild/scripts.py`) now point to `build_lc.py`.
9. **Two files: the form and the builder.** `build_lc.py` became `build_form.py`, which builds any form file
   (`python build_form.py lc.py`). The JavaScript (`js/document.js`, `js/buttons.js`) and the font measurements
   (`helvetica-metrics.json`) moved inside it, so `lc.py` and `build_form.py` alone build the PDF. The question
   helpers (`text`, `radio`, ...) moved into the builder, so a form file only describes its form. The self-check no
   longer has the LC form's field count written into it: it checks whatever the form file says, and the page count
   comes from `PAGES` in `lc.py`. The PDF is byte-for-byte identical to before apart from two script comments that
   named old files, all 26 script tests pass, and the QR code still scans.
10. **Two QR codes when the answers don't fit in one.** Before, answers longer than one code (2,300 characters)
    could make an unreadable code: shortening the two long paragraphs wasn't always enough. Now a second code
    appears under the first only when needed (QR structured append, labelled "QR code 1 of 2" / "2 of 2"), and
    text too long even for two codes is refused instead of drawn. The QR page now holds two 111 mm frames with the
    buttons at the bottom; a single code is therefore smaller than before (111 mm instead of 159 mm). 477 fields
    instead of 297. Tested: 34 script tests pass, and both codes scan (also from a rendered page) and join back
    into the exact JSON.
11. **README no longer updated by the build.** `build_form.py` doesn't rewrite this README any more (its
    documentation section and the `README` setting in `lc.py` are gone), so a build only writes `out/`. The question
    tables, counts and starting answers below are now plain text, written by hand: update them when the form
    changes. The PDF is unchanged.
12. **Split for beginners: `forms/`, `build.py`, `engine/`.** A newcomer only opens `forms/` (one file per form, with
    a cheat sheet) and runs `python build.py forms/lc.py`. The builder became the `engine/` folder, one small file
    per step, each with a plain-English header saying what it does and whether you'd need to change it; the
    JavaScript is back in real `.js` files (`engine/js/`). New: a check of the form file before building, which
    explains mistakes in plain words (misspelt options, rules naming unknown ids, duplicate ids, unknown formats,
    defaults that aren't an option, missing commas); `forms/example_leave.py`, a commented example to copy; and
    `GUIDE.md`, a step-by-step guide. The PDF is byte-for-byte identical to before, and all 34 script tests pass.
13. **QR reader.** `read_qr.py` reads one or two QR codes from scanned images (or a handheld scanner's text),
    joins them in the right order, re-checks every answer against the form file (`engine/validate.py`, the same
    rules as the form, plus the checks across answers), and saves the result as JSON. New dependency: zxing-cpp
    3.1.1 (Apache-2.0), only for reading.
14. **QR buttons back under the first code.** Generate QR Code and Print Form sit right under QR code 1 again, as in
    the original layout; the second code (when needed) appears under the buttons. Each code is now 110 mm (squares
    of 0.6 mm). Tested: 34 script tests pass, and both codes scan from a rendered page and join into the exact JSON.
15. **5 files, all Python, in one folder; copying can't silently break the form.** On a work computer, a copy of
    the multi-file version built a PDF whose checks didn't run (Check form said "ready" on an empty form, no
    calendars, red boxes never turned black). The project is now 5 files with no sub-folders: the form file
    (`lc_form.py`) and `build.py`, `layout.py`, `pdf_writer.py`, `acrobat_js.py`. The JavaScript lives inside
    `acrobat_js.py` as Python text, so it can't be left behind, and a file cut short makes Python stop. The build
    stops, naming the file to copy again, if an engine file is missing or damaged, or if the scripts contain any
    character that would break Acrobat (an invisible byte order mark, curly quotes ...). The engine files are plain
    ASCII. If the form's main script still doesn't run in Acrobat (for example with JavaScript turned off), Check
    form and Generate QR Code now say "The form's checks did not start" instead of "ready". Button helpers use
    function expressions (older Acrobat versions reject a function declared inside a block). Forms are named
    `<name>_form.py`: `lc_form.py`, `example_form.py`. The PDF is unchanged apart from those button scripts; all 34
    script tests pass, and a copy with a byte order mark and Windows line endings on every file builds the
    identical PDF.
16. **Tidy-up.** Removed `build_lc_application.py`, an old single-file builder uploaded early on. Nothing used it,
    and it needed PyMuPDF (AGPL), which this project no longer uses. The PDF is unchanged.
17. **EBLC demo form.** Added `eblc_form.py` (Export Bills under Letter of Credit, Form EB-01, draft v0.1): 5
    sections, 3 pages, using every kind of mandatory rule. Questions to be checked with Trade Operations before use.
18. **`cols=` sets a question's width.** A question can say how much of its row it takes, out of 12 columns:
    `cols=12` the whole row, `cols=6` half, `cols=4` a third. Without it the build still chooses (as before), so
    the LC, example and leave forms build byte-identical PDFs. A section with a whole-row question no longer sits
    side by side with another. `eblc_form.py` uses it: Exporter name takes the whole row, Contact person half.
19. **Layout and look from the form file.** Sections take `width="full"` or `width="half"` (two half sections in a
    row sit side by side; without `width` the build decides, as before) and `new_page=True`. A form file can set
    `STYLE = {...}` for its own colours and text sizes (ACCENT, TINT, BANK_SHADE, LABEL, TEXT). Wrong values stop the
    build with a plain message; a signoff section can't be half. Every form file now starts with a "WHAT YOU CAN
    CUSTOMISE" list. `eblc_form.py` uses full and half sections and now fits on one page plus the QR page. The LC
    and example forms build byte-identical PDFs.
20. **No per-form colours.** `STYLE` (added in 19) is removed: a simple form doesn't need it, and every form keeps
    the same look (red = mandatory). Colours and text sizes stay in `layout.py`, section 1. `width`, `new_page` and
    `cols` stay, as optional overrides only: without them `layout.py` decides.
22. **Back to the previous way; only the LC form file restyled.** Item 21 is undone (`half=` is accepted again, the
    currency list stays in `lc_form.py`, no file-name or form-code checks, `dc_amendment_form.py` is a local draft
    again). `lc_form.py` alone now matches `eblc_form.py`: the "WHAT YOU CAN CUSTOMISE" list at the top, the
    sections written inside `FORM`, and no `half=` (it did nothing). The LC PDF's pages and fields are in exactly
    the same places; the other forms build byte-identical PDFs.
23. **QR code vs AI test (`benchmark/`).** 10 fake LC applications (4 typed with their QR code, 6 handwritten;
    clean, medium and poor scans) read back by the QR code and by Gemini 3.7 Flash. QR: every answer right on all 4
    typed forms, about 0.04 s a form. Gemini: 599 of 602 answers right (99.5%), 8 of 10 forms fully right, about
    39 s a form (22 to 76 s); its 3 errors were pick-one circles on poor scans, with no warning. Results, per-field
    accuracy and pictures in `benchmark/LC-QR-vs-AI.xlsx`. The form files are unchanged.
24. **The other 12 trade forms.** The old vendor smart form's other application forms are now form files in this
    project's look (`lc_amendment_form.py`, `eblc_form.py` (replaces the EB-01 demo), `obc_form.py`,
    `import_financing_form.py`, `export_financing_form.py`, `bg_form.py`, `sblc_form.py`, `bg_amendment_form.py`,
    `sblc_amendment_form.py` and the three bills of exchange). Their questions, wording, mandatory and conditional
    rules come from the old form: read in Adobe Acrobat and found by trying every choice (`smartform/`), then reviewed
    against the old scripts. The engine gained what they need: formats `cif`, `ref12`, `fx8`, `fx2`, `swift`; per-form
    checks (`FORM["checks"]`: date order, ranges, account length by currency); the amount in words (`words=`); long
    radio options wrap. The LC, example and other existing forms build as before. Not carried over: hidden parts the
    old form never showed; "add a row" tables are 3 fixed rows; the old BG branch list that changed with the entity
    lists every branch; the bills of exchange are their own forms instead of being filled from EBLC / OBC answers;
    the menu is in the one-PDF build (item 25).
25. **One PDF with a main menu, like the old smart form.** `build_all.py` builds all 13 forms and joins them: a
    menu page, every form with a Main menu button, and bookmarks (39 pages). Each form's fields are renamed under
    its code (`BG.applicant_name`) and its scripts rewritten to match (`lcRules_BG` ...), so Check form, Reset form,
    Generate QR Code and Print Form work on that form only, and its QR code holds only its answers, with the same
    question ids as the form built on its own. Checked: every script in the PDF is rewritten; all 13 forms' scripts
    run together (in Node, against the PDF's fields) and stay separate; the amount in words and the date checks work.
26. **No terms and conditions pages.** The old smart form has LC, EBLC and OBC terms pages, but every one of its
    scripts keeps them hidden (none ever shows them), so users never saw them. They are left out of the one-PDF build
    (`terms.json` and `smartform/make_terms.py` removed; 46 pages down to 39).
27. **Tidied into folders.** Form files moved to `forms/` (`python build.py lc_form.py` still works: build.py looks
    in `forms/`, and form files there can still import each other, e.g. `from lc_form import CURRENCIES`). The tools
    that copied the old smart form moved to `tools/smartform/` (its old-look builder now writes
    `Trade-Application-Forms-old-look.pdf`, so it no longer overwrites `build_all.py`'s PDF). `dist/` is no longer
    kept in git: build the full PDF with `python build_all.py`. The old draft `dc_amendment_form.py` (replaced by
    `lc_amendment_form.py`) deleted. Every PDF is byte-identical to before the move.
28. **Only the chosen form is shown, like the old smart form.** In `build_all.py`'s PDF every form's pages are now
    hidden page templates (`LC_0`, `LC_1` ...; `/Type /Template`, names sorted). Clicking a form on the menu, or its
    bookmark, runs `showForm` (document script "00 menu"): it hides the open form and shows the chosen one after the
    menu page. Answers stay when you switch away and back. Print Form prints pages 2 to the end (leaves out the menu).
    Needs Adobe Acrobat with JavaScript on; free Acrobat Reader may refuse to show or hide pages unless the PDF has
    Reader rights; without JavaScript only the menu page is visible. Checked in Acrobat: menu alone at open (1 page,
    38 templates); LC -> 5 pages, BG -> 4 pages with LC hidden; back to LC keeps its answers, QR code page last.
