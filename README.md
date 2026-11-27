# LC application form (Form LC-01)

This project builds one PDF: the **Irrevocable Documentary Credit Application** (Demo Bank, Form LC-01 · v1.0 · Nov 2026).
It's a fillable form with Adobe Acrobat JavaScript checks and a QR code page. It's built in **Python**.

- 4 pages today: 3 pages of questions, plus the QR code page (no page limit: more questions add pages). Long answers add extra QR code pages while they are needed (up to 7 more, two codes each).
- 835 PDF fields: 108 questions, plus date lists, tick-any boxes, buttons and the rows of four QR codes (177 each: two on the QR code page, two on the extra QR code page, which is a hidden template until needed).

## Libraries used

These are everything `build.py` (one form) and `build_all.py` (all forms in one PDF with the main menu) need.
Versions are pinned in `requirements.txt`; install with `python -m pip install -r requirements.txt`.

| Library | Version | Licence | What it does here | Link |
|---|---|---|---|---|
| **pikepdf** (bundles the **qpdf** C++ library, Apache-2.0) | 10.18.1 | MPL-2.0 | **The main library.** Writes the whole PDF: each page's drawing (text, lines, boxes), the fields and how they look, buttons, page links, the Acrobat JavaScript, the stored form description. In `build_all.py` it also joins the forms into one PDF, turns each form's pages into hidden page templates and adds the main menu. | [pypi.org/project/pikepdf](https://pypi.org/project/pikepdf/) · [qpdf.sourceforge.io](https://qpdf.sourceforge.io/) |
| lxml | 6.1.3 | BSD-3-Clause | Installed by pikepdf: pikepdf uses it to read and write the PDF's XML metadata. Not called by this project directly. | [pypi.org/project/lxml](https://pypi.org/project/lxml/) |
| Pillow | 13.0.0 | MIT-CMU | Installed by pikepdf: pikepdf uses it for images inside PDFs. Not called by this project directly. | [pypi.org/project/pillow](https://pypi.org/project/pillow/) |
| packaging | 26.3 | Apache-2.0 or BSD-2-Clause | Installed by pikepdf: pikepdf uses it to check library versions. Not called by this project directly. | [pypi.org/project/packaging](https://pypi.org/project/packaging/) |
| Python standard library | Python 3.9+ | PSF | Dates, JSON (the stored form description), zlib compression of page drawings, loading the form files, file handling. | [docs.python.org](https://docs.python.org/3/library/) |

Inside the finished PDF, no library is needed: the checks, the main menu and the QR code run as Adobe Acrobat
JavaScript (`acrobat_js.py`, `build_all.py`) in the person's Acrobat or Acrobat Reader.

All of these are permissive licences: they allow commercial and internal use, and they don't require you to publish
your own code. MPL-2.0 only asks that changes to *pikepdf's own files* be shared, and this project doesn't change them.
There's no QR library: the QR code is made inside the PDF, by `acrobat_js.py`, when the person presses Generate QR Code.

**Why not PyMuPDF or pdf-lib?** Earlier versions used them. PyMuPDF is AGPL-3.0, a licence banks usually avoid, and its
2.x release installs about a dozen extra AI packages (onnxruntime, numpy, ...). pdf-lib (JavaScript) is MIT but hasn't
had a release since 2021, so security fixes won't come. pikepdf is permissive, actively maintained, and enough on
its own: the page drawing is a few PDF commands (`text`, `line` and `rect` in `layout.py`).

## Quick setup

**New to this? Read [GUIDE.md](GUIDE.md) first.** It shows, step by step, how to change the form and how to make a
similar one, without needing to know Python. The commands below are the short version.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build.py lc_form.py               # builds out/LC-Application.pdf, checks it, prints PASS
.venv/bin/python -m http.server 8090 -d out        # serves it at http://localhost:8090 (Ctrl+C stops it)
```

On Windows, use `.venv\Scripts\python` instead of `.venv/bin/python`.

**Use Acrobat or Reader to test the form.** The browser's PDF viewer (Chrome, Edge) shows and fills the form, but it
doesn't run most of the Acrobat JavaScript. So in a browser you won't get the red boxes, locking, Check form or the
QR code. Download the PDF and open it in Acrobat. If a yellow bar says JavaScript is disabled, choose Options >
Enable JavaScript (or Preferences > JavaScript > Enable Acrobat JavaScript): with JavaScript off, nothing is checked,
dates are plain drop-down lists, and Check form says "The form's checks did not start".

## Detailed explanation

Everything below is the full reference: how the project is organised, how the PDF is built, every rule and question,
the JavaScript inside the PDF, the QR code, testing and history.

### What builds the PDF

- **A form file plus 4 engine files build the PDF:** the form (`forms/lc_form.py`, the only one you edit) and four
  engine files that are the same for every form (`build.py`, `layout.py`, `pdf_writer.py`, `acrobat_js.py`). One
  command builds the PDF and checks it.
- **Folders:** the engine files at the top and every form file in `forms/`. The QR reader, the QR vs AI benchmark and the smart-form tools were moved out of this repo to `~/Documents/lc-form-extras` (not needed to build).

The build checks twice and stops with the reason, saving nothing, if anything is wrong:
- **before building**, it checks the form file for mistakes (a misspelt option, a rule that names a question that
  doesn't exist, two questions with the same id ...) and says which question and what to fix;
- **after building**, it opens the PDF and checks every question's fields, flags, limits, rules, scripts and buttons.

It also stops with a clear message if an engine file is missing, cut short or changed while being copied (for
example an invisible "byte order mark" or curly quotes added by an editor), instead of building a PDF whose checks
silently don't work.

**This README is written by hand.** The page and field counts, the starting answers and the table of every question
below describe `lc_form.py`: when you change the form, update them here too.

### Architecture

```
                 ┌──────────────────────────────────────────────────────────────┐
  forms/         │ THE FORM (what it asks): 108 questions, options and rules    │  ← you edit this
  lc_form.py     │ FORM, DEFAULTS, and the setting PDF_NAME                     │
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
  pdf_writer.py  │ STEP 2  rules table, scripts, buttons, QR code rows (QR page │
                 │         + the hidden extra QR page template "qrx")           │
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

### Files

| File | Purpose | Who opens it |
|---|---|---|
| `forms/lc_form.py` | **The LC form.** Every question, one line each: wording, kind, options, mandatory rules, limits, formats. Also the currency list, the starting answers, and one build setting (`PDF_NAME`). | Anyone changing the form |
| `forms/lc_pipe_form.py` | **The LC form with the old smart form's pipe-delimited QR text** (Form LC-01P): imports `lc_form.py`, adds `FORM["qrFormat"] = "pipe"` and the 62-position table `FORM["pipe"]`; `IN_MENU = False` (not in `build_all.py`). See "The pipe-format form" below. | Anyone changing the pipe format |
| `check_pipe.py`, `check_pipe_mock.js` | The oracle test of the pipe form: its records against the old form's own barcode code (`python check_pipe.py [--decode]`). Not needed to build. | Whoever changes `lc_pipe_form.py` or `PIPE_JS` |
| `forms/example_form.py` | A small, fully commented example form (Annual Leave Request). Copy it to start a new form; name the copy `<something>_form.py`. | Anyone making a new form |
| `forms/eblc_form.py` | **EBLC** (Handling / Financing of Documents under Export Documentary Credit, Form EBLC-01), redrawn from the old smart form with its rules. | Anyone changing that form |
| `forms/`: `lc_amendment_form.py`, `obc_form.py`, `import_financing_form.py`, `export_financing_form.py`, `bg_form.py`, `sblc_form.py`, `bg_amendment_form.py`, `sblc_amendment_form.py`, `bill_of_exchange_form.py`, `bill_of_exchange_eblc_form.py`, `bill_of_exchange_obc_form.py` | **The other trade forms** of the old smart form (LC amendment, export collection, import / export financing, banker's guarantee, standby LC, both amendments, the three bills of exchange), each redrawn in this project's look with the old form's questions, wording and rules. Build each like the LC form: `python build.py bg_form.py`. They use `lc_form.py`'s currency and country lists, so keep them all in `forms/`. | Anyone changing those forms |
| `proof_multiqr.py` | Proof that Generate QR Code makes as many codes as the answers need (`python proof_multiqr.py`): runs the form's own script under Node with a stand-in for Acrobat and decodes every code with zxing-cpp (a test tool, not in `requirements.txt`). See "Testing the QR codes outside Acrobat" below. | After changing `lcPayload`, `lcDrawQr` or the QR pages |
| `build_all.py` | **Builds the whole smart form as one PDF** (`python build_all.py` -> `out/Trade-Application-Forms.pdf`): a main menu page (Import / Export / Loans / Guarantees) with a terms tick box (wording: `TERMS_TEXT` at the top of the file); tick it and click a form and that form's pages are copied in after the menu (every form's pages are hidden page templates, copied with `Template.spawn` by the menu's script; choosing another form asks first and clears the open form's answers); the Main menu button on every page of a form, except the extra QR code pages (and the bookmark) asks, then deletes the open form's pages and clears its answers, so the PDF is just the menu page again (if the viewer refuses to delete pages it only goes to the menu page and the form stays); bookmarks. Needs JavaScript on. Each form keeps its own rules, Check form, Reset form and QR code (its fields are renamed `LC.applicant_name`, `BG.applicant_name` ...). | To build the full PDF |
| `build.py` | **Run this.** Section 1: the question helpers and every option a question can have, and `check_form`, which explains mistakes in a form file. Section 2: loads a form file, checks it, builds, checks the PDF, saves it in `out/`. | To look up an option |
| `layout.py` | Step 1: where every section, question and box goes. Also the settings (section 1: page size, colours, text sizes, spacing, answer formats), text helpers, the rules ("mandatory now?") and Adobe's Helvetica letter widths. | To change the look of every form |
| `pdf_writer.py` | Step 2: builds the rules table, attaches the scripts, places the buttons and QR code rows (the QR code page's two codes and the hidden extra QR code page template). Step 3: writes the PDF with pikepdf. Then the self-check. Refuses scripts with characters that would break Acrobat. | Rarely |
| `acrobat_js.py` | The JavaScript Acrobat runs inside the PDF: `DOCUMENT_JS` (rules engine, QR codes' text, QR encoder, drawing of up to 16 codes over the QR page and the extra QR pages) `PIPE_JS` (the pipe-format records, added to the pipe form's document script only) and `BUTTON_JS` (one entry per button). Plain ASCII only. | To change how answers are checked or what a button does |
| `GUIDE.md` | Step-by-step guide for beginners, including copying the files to a work computer and fixing common problems. | Everyone, first |
| `README.md` | This reference. | When you need the details |
| `requirements.txt` | pikepdf and its three dependencies, at exact versions. | Setup |

**Where to change what:**

| You want to change | Edit |
|---|---|
| A question's wording, options, mandatory rule, max length or format | `forms/lc_form.py` |
| How wide a section is, or start it on a new page | `width="full"` / `width="half"` / `new_page=True` on its `section(...)` in the form file |
| How wide one question is (e.g. a whole row) | add `cols=12` (or `cols=6` for half) to its line in the form file |
| How tall a paragraph box is | add `height=80` (points, default 50) to its `long(...)` line |
| Buttons inside a section (Check form, Reset form, Generate QR Code, Print Form) | `buttons=["check-form", "print-form"]` on its `section(...)`; what they do is `BUTTON_JS` in `acrobat_js.py` |
| Add or remove a question | `forms/lc_form.py` (nothing else: the checks follow the form) |
| Make a new form | copy `forms/example_form.py` to `forms/<name>_form.py` (see [GUIDE.md](GUIDE.md)) |
| Colours, text sizes, spacing, margins, answer formats | `layout.py`, section 1 |
| How sections and questions are arranged | `layout.py`, section 4 |
| How the form checks answers in Acrobat | `DOCUMENT_JS` in `acrobat_js.py`: the LC's rules across answers are numbered Rule 1-9 in `across()` (one sentence each, then its code); the per-question loop is Steps 1-5 |
| Add an LC rule across answers (e.g. a date order) | for any form: a check in the form file's `FORM["checks"]` (`not_before`, `after`, `in_range`, `account_length`); LC-only: a new numbered rule in `across()` |
| What the QR codes hold | `lcPayload` in `acrobat_js.py` |
| How many codes, how they are split, where codes 3 to 16 go | `LC_QR_CAP` / `LC_QR_MAX`, `lcDrawQr`, `lcExtra` in `acrobat_js.py`; the extra QR code page itself: `draw_qr_extra` in `layout.py` and `qr_slot` in `pdf_writer.py` |
| What the pipe form's QR text holds | `FORM["pipe"]` in `forms/lc_pipe_form.py` and `PIPE_JS` in `acrobat_js.py` |
| What a button says or does | its entry in `BUTTON_JS` in `acrobat_js.py` |

### Security

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

### How the PDF is built

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
   box). Adds the Check form and Reset form buttons on every page, the rows of the QR codes (177 each: two on the QR code page, two on the hidden extra QR code page template), and the Generate QR Code
   and Print Form buttons.
3. **Write the PDF (`pdf_writer.py`, with pikepdf).** Makes every field with its settings and its look (border,
   background, tick, radio dot), the page links, the stored scripts, and a copy of the form's description (JSON)
   for the bank's workbench to read.

The layout runs twice. The second pass gives the room left on the last page of questions to the paragraph boxes on
that page, so the form doesn't end with a blank gap.

The build is **reproducible**: the same form file on the same day gives a byte-for-byte identical PDF. (The date
drop-downs list the dates from a year back to two years ahead, so they change with the build date.)

### Rules, conditions and validations

#### Rules that apply to every question

| Rule | Where it's enforced |
|---|---|
| **Mandatory** questions (red `*`) must be answered | outlined in red with a pink fill while blank or wrong; listed by Check form, Generate QR Code and before save or print |
| **Conditionally mandatory** questions become mandatory when their condition holds (table below) | same as above |
| A conditional question is **locked** until its condition holds: greyed out, read-only, and its answer cleared. This stops a stale answer staying in a question that doesn't apply. | `lcRules` on every change |
| **Max length** (`max`) | the box refuses more characters (PDF `/MaxLen`) |
| **Upper case**: letters are capitalised as you type (SWIFT messages are upper case) | keystroke script on plain text boxes |
| **Allowed characters**: `A-Z a-z 0-9 space . , - / ( ) ' : ? + # & @ %` and line breaks. Anything else is refused as you type, and listed if pasted ("remove ...") | keystroke script, and `lcRules` |
| **Dates** are DD/MM/YYYY and must be real dates | Acrobat's date format plus `lcRules`. With JavaScript off, a drop-down of real dates from a year back to two years ahead (the range depends on the build date). |

#### Formats

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

#### Checks across answers

A form file can add its own checks in `FORM["checks"]` (helpers in `build.py`): `not_before` / `after` (one date not
before / strictly after another), `in_range` (a number between two values) and `account_length` (an account number's
length, by currency). They run in Acrobat (`across()` in `acrobat_js.py`). A question with
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

#### Defaults when the form opens

- 2.1 Mode of advising: **Full Swift**
- 11.2 Presentation period (days after shipment): **21**
- 17.1 All bank charges are for account of: **ticked**
- 17.2 Charges for account of: **Beneficiary, except charges at DC Issuing Bank's counter**
- 17.5 Please provide us with post-shipment financing under Docu...: **ticked**
- 17.11 Please debit all DC issuance charges to our account with you: **ticked**

#### Every question

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

### The JavaScript inside the PDF

Everything is stored in one document-level script, named `lcRules`, built from `DOCUMENT_JS` in `acrobat_js.py`. It defines these
functions:

- `lcRules(doc, name)`: the rules engine. It holds a table (`lcModel`) of every question that has a rule, a format or
  a lock. On a full run (no `name`) it works out, for every question, whether it applies, whether it's mandatory now, and whether
  its answer is blank or wrong. It then sets the box's outline, fill, required flag and lock. It returns the list of
  missing questions, plus `.bad` (wrong answers) and `.first` (the first problem, for the cursor).
  **Speed:** with a `name` (the box that just changed: its blur, its click, or the calculation's `event.source`) it re-checks only
  the questions that read that box, using the index `lcDeps` that `dependency_index()` in `pdf_writer.py` builds when the PDF is
  made (a box -> itself, the questions that read it through `requiredIf` / `activeIf` / `words` / the checks across answers
  (`ACROSS_READS` there must match `across()` in `acrobat_js.py`), and what those read in turn). If the form file has a check kind
  the index doesn't know, `lcDeps` is `null` and every run is a full run. It does nothing if the box still holds the value
  the last run saw (so a change that fires both the calculation and the blur is checked once, not twice), skips writing a box
  whose look (required / lock / red or black or grey) is unchanged (every Acrobat property write is slow), and turns
  `doc.calculate` off while it writes. Check form, saving, the QR code and Reset form always do a full run (same messages as before).
- `lcDates(doc)`: in Acrobat, shows each date's calendar box and hides its drop-down list.
- `lcPayload(doc)`: builds the QR codes' text (`lcBytes`, `lcCodes`: its size in bytes, and how many codes that is).
- `lcQrMatrix(text)` and `lcDrawQr(doc, text)`: the QR codes (see below). `lcExtra`, `lcSlot`, `lcPagesFor`,
  `lcLastPage` and `lcQrCheck` find the extra QR pages, work out which page and slot a code goes in, and check before
  printing that the codes on the pages are the ones the answers need.

When `lcRules` runs:

| Event | How |
|---|---|
| Form opens in Acrobat or Reader | end of the document script |
| You leave a text box, list or date | widget `/AA /Bl` |
| You click a tick box, option or date list | widget `/AA /U` |
| Any value changes | hidden field `__checks`, with `/AA /C`; the only entry in `/AcroForm /CO`. It passes `event.source` (the box that changed) to `lcRules`; no source = full run. In the one-PDF build each of the 13 forms has its own `__checks`, which returns at once unless the hidden field `OPEN` names its form |
| Check form, Generate QR Code, Print Form | button actions |
| Before save or print | catalog `/AA /WS` and `/WP`: warns if the form is incomplete (but doesn't block). The warning starts "Before saving:" or "Before printing:", and shows once: an event within 3 seconds of the warning closing is a repeat (`lcWarnedAt`) |

The buttons (`BUTTON_JS` in `acrobat_js.py`):

- **Check form** lists what's missing or wrong (at most 15 of each) and puts the cursor on the first problem. If
  nothing is wrong, it says the form is ready.
- **Reset form** asks first, then clears everything back to the starting answers, removes the QR codes, and
  re-runs the checks.
- **Generate QR Code** is refused while anything is missing or wrong. Otherwise it makes the code (as many codes as
  the answers need, up to 16: codes 3 and up go on extra pages after the QR code page) and goes to the QR code page.
- **Print Form** is refused until a QR code exists, the answers have not changed since, and every code needed is on its
  page (none blank, none left over). Then it prints the form up to the last QR code page in use.

With JavaScript off, none of this runs. The form still fills, the date lists and page links work, and the mandatory
boxes keep their red outline. Nothing is checked, though.

### How the QR code is made

The code is made **inside the PDF, in Acrobat**, when the person presses Generate QR Code. It isn't made by Python,
and no QR library is used.

**As many codes as the answers need (1 to 16).** One QR code holds 2,300 bytes of text. Most applications fit, and get
one code. When the answers are longer, more codes appear: a **second code under the buttons**, and for very long
answers codes 3 to 16 on **extra QR code pages**, two to a page. The Bank scans all of them. 16 is the most the QR
standard's "structured append" allows. The QR page always has room for two codes, one above the other. The Generate QR
Code and Print Form buttons stay right under the first code, where they always were:

```
  APPLICATION QR CODE (FOR BANK USE)
  instructions ...
            QR code 1 of 7 (scan all 7 codes)     <- label: only when there is more than one code
           ┌──────────────────────┐
           │      QR code 1       │                   always used
           └──────────────────────┘
        [ Generate QR Code ]  [ Print Form ]
            QR code 2 of 7
           ┌──────────────────────┐
           │      QR code 2       │                   frame and code appear only when needed
           └──────────────────────┘

  APPLICATION QR CODE (CONTINUED)                     <- extra page 1: only while codes 3 and 4 are needed
            QR code 3 of 7   [frame, code 3]
            QR code 4 of 7   [frame, code 4]
  ... extra pages 2 and 3 for codes 5-6 and 7 (the empty second frame of the last page stays hidden)
```

Each code is 110 mm square: 177 × 177 squares of 0.6 mm, on every page.

**The extra pages exist only while needed.** In the PDF they are one hidden *page template* named `qrx` (not one of the
form's pages: 4 pages as before). Generate QR Code copies it after the QR code page with `Template.spawn` (once for
every two codes beyond the first two) and deletes the copies it no longer needs, so a form whose answers shrink, or
that is reset, goes back to its 4 pages. In the one-PDF build each form has its own template (`LC_qrx`), and the Main
menu button deletes the extra pages with the rest of the form. The fields of a copy are created by the spawn (the viewer
renames them, `bRename: true`), so the form does not carry 16 codes' worth of fields: only the template's 358 (177 rows
× 2 codes, plus labels and frames). If the viewer refuses `deletePages` (not known for the free Reader), a page that
could not be deleted stays but is emptied, says "(this page is not used)", and Print Form leaves it out (it prints
only up to the last QR page in use).

1. **The text: `lcPayload` (`acrobat_js.py`).** It gathers every answered question, keyed by field id. Tick boxes
   become `true`, and tick-any questions become lists:
   ```json
   {"form": "LC-01", "version": "1.0", "saved": "2026-11-12T16:30", "complete": true,
    "data": {"applicant_name": "TAN ENGINEERING PTE LTD", "tolerance": true, "bencert_sent_by": ["faxed"], "...": "..."}}
   ```
   - The JSON is padded with spaces to fill the codes it needs: 2,300 bytes for one code, 4,600 for two, and so on up
     to 36,800 for 16.
   - 16 codes hold 36,800 bytes. Only if the answers are longer still are Goods description and then
     Additional conditions shortened (ending in "...") and listed in `"truncated"`. The full text stays in the
     PDF's fields. (The LC form's worst case, both long paragraphs at their 6,500 characters and other answers filled,
     is about 15,300 characters: 7 codes, nothing shortened.)
2. **Splitting: `lcDrawQr` (`acrobat_js.py`).** The text is cut into consecutive equal slices, one per code (2,300 bytes
   each when padded). Each code is marked with the QR standard's **structured append**
   header (its index, the total, and a check value, the parity, of the whole text), so scanners that support it join
   the codes automatically. With any other scanner, scan code 1, then code 2, and so on, and put the texts together in
   that order: the result is exactly the JSON above. The slices are equal runs of *bytes*, so a multi-byte character can
   straddle two codes: a reader must join the codes' bytes first and only then decode the text. Text too long for 16 codes is refused with a message; a code
   that can't be read is never drawn.
3. **The code: `lcQrMatrix` (`acrobat_js.py`).** A standard QR encoder, written step by step with a comment on each step (fixed patterns, data bits, error correction, placing the bits, mask).
   - It makes a version 40 code (177 × 177 squares), with error correction level M, byte mode and mask 0.
   - It places the fixed patterns (finders, timing, alignment, format and version bits).
   - It adds Reed-Solomon error correction: 49 blocks, 28 correction bytes each.
4. **The drawing: `lcDrawQr` (`acrobat_js.py`).** Acrobat scripts can't draw pixels, and Acrobat's own barcode field is
   missing in some installations. So for each code there are **177 read-only text fields, one per row of the
   code** (`__qr1_0` ... `__qr1_176` and `__qr2_0` ... `__qr2_176` on the QR page; `__qrx_1_0` ... `__qrx_2_176` on each
   extra page, with a prefix the viewer adds), each with 177 fixed character slots. Each
   dark square is the letter "n" in the ZapfDingbats font, which prints as a solid black square. Each row is set as
   a string, for example `"nnn n  nn…"`. The frames (`__qr2_frame`, `__qrx_1_frame`, `__qrx_2_frame`) and the labels
   (`__qr1_label`, `__qr2_label`, `__qrx_1_label`, `__qrx_2_label`) are fields too, so they show only for codes in use.
   Every slot that holds no code is emptied, so no old code stays on any page. `lcExtra` finds the spawned pages by
   their field names ending `__qrx_1_0` and a page number after the QR code page, whatever prefix the viewer gave them.
5. **Print Form** prints only if the codes still match the current answers and every code is on its page (`lcQrCheck`).
   The warning before saving or printing (File > Print) also says so when codes were generated but a page no longer
   holds them.

The bank scans the printed codes with a QR reader and gets the JSON.

### Testing the QR codes outside Acrobat

`python proof_multiqr.py` (needs `node`, and `zxing-cpp` and Pillow in the Python that runs it; zxing-cpp is a test tool and
is not in `requirements.txt`). Build first (`python build_all.py` too, to test the joined PDF). It takes the form's own
document and button scripts out of the built PDF, runs them under Node with a small stand-in for Acrobat's document (fields,
pages, `Template.spawn`, `deletePages`, `print`, `app.alert`), presses Generate QR Code, Print Form, Reset form and the
before-save warning, and decodes every code that was drawn with zxing-cpp. For payloads of about 2,000 / 4,000 / 9,000 and
15,300 characters it checks that 1 / 2 / 4 / 7 codes come out; each code's structured-append index, total and parity are
right (read straight from the code's modules); the codes joined in order equal the payload byte for byte; nothing is
shortened; the printed range ends at the last code's page; shrinking back leaves no stale code, frame or label on any page
(also when `deletePages` is refused); a blanked code or changed answer stops Print Form; when the viewer refuses to add a
page (also with 2 codes already drawn, and with `deletePages` refused too) Generate says so, Print Form prints nothing and
the form alone warns before saving; and beyond 16 codes only the long
paragraphs are shortened and listed in `"truncated"`. The stand-in cannot say how Acrobat or Reader behave: the new pages'
field names (run in three naming styles) and `deletePages` allowed or refused are assumptions, so also run the steps below
in Acrobat.

### The pipe-format form (Form LC-01P): the old smart form's barcode text in the QR code

`forms/lc_pipe_form.py` is the same LC form (it imports `forms/lc_form.py`, so questions, wording, layout and rules cannot
drift) built as its own PDF, `out/LC-Application-Pipe.pdf` (`python build.py lc_pipe_form.py`; footer "Form LC-01P"). It is
**not** in `build_all.py`'s menu (the joined PDF stays 13 forms): the form file says `IN_MENU = False` and `build_all.py` refuses
a menu entry that does. The only difference is what Generate QR Code puts into the QR code: not the JSON of the answers, but the
**4 records of the old smart form's barcode**, so a back end that reads that format keeps working.

Format (from `trade-smartform-extract/docs/LC-system-design.md`, section 5): 4 records, fields separated by `|`, the record
number first, meaning from the position (`1_01` ... `4_03`, 62 positions), empty answers leave an empty slot (`||`), every
position (the last too) followed by `|`; addresses as `[line][line][line]`; long text cut into lines padded with spaces to 65
characters (the old documents say 64; the old code uses 65) joined by `{}`, an Enter also becoming `{}`; choices as codes
(`L5Y`/`L5N`, `L6Y`/`L6N`, `L9Y`/`L9N`, price basis `C B A O D G F O`, `44E`/`44A`, `44F`/`44B`, `GSY`, `Y`/`N`, `S A U`, `LAA`/`LAB`,
`LID`/`LIC`); an empty CIF number / amount / tolerance / term days / presentation days as `0000000` / `0`; dates `YYYY-MM-DD`; the
amount without commas and with 2 decimals (`1250000.00`; assumed from the old layout table, see below); document clauses
as generated sentences (`+ SIGNED COMMERCIAL INVOICES IN 3 ORIGINALS AND 2 COPIES.`).

**How it is wired.** The mapping is data in the form file: `FORM["qrFormat"] = "pipe"` and `FORM["pipe"]`, a list of 4
records, each a list of 62 entries (`{"p": "1_06", "id": "partial_shipment", "codes": {"allowed": "L5Y", "not allowed": "L5N"}}`;
the kinds are listed at the top of `forms/lc_pipe_form.py` and in `acrobat_js.py`). `build.py` (`check_pipe`) refuses an entry that
names a question that does not exist or a code for an answer the question does not offer. The encoder is one separate block in
`acrobat_js.py`, `PIPE_JS` (`lcPipeAnswers`, `lcPipeChop`, `lcPipeValue`, `lcPipeRecords`, `lcPipeText`); `pdf_writer.py` appends it to the
document script of a pipe form only, so every other form's PDF is byte-identical to before. Two button scripts, `generate-qr-pipe`
and `print-form-pipe` in `BUTTON_JS`, call `lcPipeText` where the usual ones call `lcPayload`. **Nothing about the QR codes themselves
changed**: `lcQrMatrix`, `lcDrawQr`, the QR page and the extra QR code pages are the usual ones (see "How the QR codes are made"). The
QR text is the 4 records with a **newline between records**, **not padded** (`lcPayload` pads the JSON; `lcDrawQr` itself does not
change the text, so the records reach the codes exactly). `lcDrawQr` makes one code per 2,300 bytes, at most 16 (codes 3 and up on
extra pages): the table's own cuts (400 / 600 characters) keep the records at one or two codes; without them (a Bank that lifts the
cuts) 6,400-character texts give 5 to 7. The text is cut into equal slices, so a slice boundary can fall inside a record; a reader must
join the codes first. Print Form (`print-form-pipe`) does what the usual one does (every code on its page, none left over, prints to
the last QR page in use) with the current records in place of the JSON. The QR page's explanatory text still says "as JSON": it is the
QR page's, which this form does not change.

**Answers cannot change the layout of the records.** The keystroke filter refuses `| [ ] { }`, but a value set by FDF import,
autofill or a pasted newline skips it, so `lcPipeAnswers` turns each of those characters, and any line break, into a space before
the records are built (in the paragraph boxes, goods description, additional conditions and other documents, only `| [ ] { }` become a
space, and any line break counts as one Enter, written `{}`). Valid answers are unchanged (the oracle still matches byte for byte).
Print Form compares the stored QR text and the current records with all CR/LF removed, because the hidden box is single-line and
Acrobat may keep, change or drop the newlines between records. `check_pipe.py` tries every such character in 27 boxes
and Print Form with each way of storing the newlines.

**What the old format does not carry** (30 of the 108 questions, so they are not in the QR code, as in the old form's barcode; the
printed PDF has them): application date; contact name / tel / fax; DC no, bank code; back-to-back (3); the "Drafts for the percentage"
tick and the percentage; prepay choice; insurance arrangement and open cover no / with; beneficiary contact / tel / fax; the bank
charges tick; post-shipment financing, financing type, currency, forward contract no; advance payment and account; debit
issuance charges and account; authorised person; and the 4th address line of the applicant and the beneficiary (the old form had 3
lines). Positions with no question use the old layout's "if empty" value: 1_02 (CIF number) = `0000000`; 1_18, 1_19, 1_23, 1_24,
1_28, 1_29, 1_30, 1_35 and 2_09 to 2_11 are empty. To put a 4th address line in, add its id to that entry's `lines` list.

**The old form's quirks, reproduced on purpose** (the Bank's back end expects them; change them in the table, not in the engine):
the goods description is cut at 400 characters and the additional conditions at 600 (`"max"`); text lines are padded to 65, and a
line can run to 66 characters before its `{}`; three advising modes share `S`, Local Delivery and Others share `O`; the first filled
place of Dispatch from / Taking in charge / Receipt goes into 1_17 (and of the three destinations into 1_22), which kind it was is
lost except for `44A` / `44B`; Date and Term drafts are both `N`; the drop-down words go into the clauses as typed
(`COUNTERSIGNED BY One`, `need not BE VERIFIED`); the insurance clause is one fixed sentence whatever the arrangement; a
quantity of `00` is not `0` (so `00 ORIGINALS`); a certificate of origin with 0 originals and 0 copies and a country is
`+ CERTIFICATE OF ORIGIN, SHOWING COUNTRY OF ORIGIN AS X.`; "Beneficiary's certificate" with no way of sending ticked gives no
clause; a locked box's stale answer is ignored (tolerance, term days, place, other documents ...). Not reproducible: the old
form's airport text (never encoded) because this form has one "Port of Loading / Airport of Departure" box, so its text is
encoded in 1_16 / 1_21. Not reproduced because the form makes the answer mandatory, so it cannot happen: a blank notify party
(the old code then concatenated a field object, or the applicant's address, or "null"), a blank address line 1 (the old code then
reused the beneficiary's name), a blank quantity next to a `0` ("IN null COPIES"), a `~` in long text (the old code treated it as
Enter; `~` is not an allowed character).

**The test (`check_pipe.py`).** `python check_pipe.py` builds the PDF and runs its own JavaScript in node against a minimal fake of
Acrobat's document (`check_pipe_mock.js`), and runs the **old form's own barcode code** (`tools/run_lc_barcode.mjs` of the
smart-form extract; set `SMARTFORM_EXTRACT` if it is not in `~/Documents/trade-smartform-extract`) on the same answers, translated
to the old form's field paths by a separate table in the test. The 4 records must be byte-identical: for the golden sample of the
extract, then for 300 random valid answer sets (all rules of the form respected; empty optionals, 1 to 3 line addresses, long text
over 65 characters and with Enter, every option of every question, both states of every tick box, answers left in locked boxes),
then it changes one code in the table and checks the comparison fails. `--decode` (needs `zxing-cpp`, install it in a scratch
venv, it is not in `requirements.txt`) also runs the Generate QR Code script in the fake document, draws the QR matrices
it fills in and decodes them with zxing-cpp: the decoded text must equal the 4 joined records, for 1 to 2 codes and (the table with its cuts removed)
5 to 7 codes over the extra pages. The fake document has pages, the hidden `qrx` template, `Template.spawn` and `deletePages`, like
`proof_multiqr.py`'s. It also checks that the build refuses `codes` where there are no answers to map. Exit 0 = all matched.
NOT tested: Acrobat itself (the stand-in has fields, pages and nothing else).

### Reading the QR codes

The QR reader (the Bank's side) and its tests were moved out of this repo to `~/Documents/lc-form-extras` (not needed to build).

### Testing in Acrobat

Every build checks the PDF's structure itself: every question's fields, the required flags, limits, starting
answers, the rules table, scripts, buttons, QR rows and the extra QR code page template. The scripts themselves only run inside Acrobat, so after changing a rule
or a script, also test the PDF in Acrobat:
1. On opening, the mandatory boxes are red.
2. Fill a few boxes: each turns black. Empty one again: it turns red.
3. Tick 13.1 Drafts: 13.2 and 13.3 unlock and turn red. Untick it: they lock, grey out and clear.
4. Type letters into 8.2 Amount: they're refused.
5. Press Check form: it lists what's missing.
6. Fill everything, then press Generate QR Code: the code appears on page 4. Scan it with a phone and the JSON shows.
7. Paste a long text (about 3,000 characters) into Goods description and press Generate QR Code again: two codes
   appear, labelled 1 of 2 and 2 of 2. Scan both; together they give the JSON. Shorten the text and generate again:
   back to one code, and the second frame disappears. Test the codes with the Bank's own scanner too.
8. Paste about 6,000 characters into Goods description and Additional conditions each (the form's own limit is 6,500)
   and press Generate QR Code: the message says how many codes (6); codes 1 and 2 are on the QR code page, and the
   form is now 2 pages longer: "APPLICATION QR CODE (CONTINUED)" pages hold codes 3 onwards, two to a page, each
   labelled "QR code n of N". Scan every code (or hand all of them to the Bank's reader): the JSON is complete.
9. Press Print Form: the printout is the form plus the QR code pages in use, nothing after them. Change one answer: Print
   Form refuses ("Your answers have changed ...").
10. Shorten the answers and press Generate QR Code again: the extra pages go away (or, if the viewer refuses to delete
    pages, are left empty and marked "(this page is not used)"), no old code shows on any page, and Print Form leaves
    them out. Press Reset form: the form is back to its 4 pages.
11. In the one-PDF build (`Trade-Application-Forms.pdf`), open a form from the menu and repeat 8 to 10. Then press Main
    menu: the extra pages go with the form's other pages.
12. In the free Acrobat Reader, repeat 8 and 10 and note what happened: does Generate QR Code add the pages (`spawn` with
    `bRename: true`), do they get deleted (`deletePages`), and how long does drawing 6 or more codes take? None of this
    is tested there.

### Changing the form, and making a new one

See **[GUIDE.md](GUIDE.md)**: it covers both step by step, with a table of common changes.

In short: edit `forms/lc_form.py` (one line per question; a cheat sheet is at the top of the file, and every kind and
option is listed in section 1 of `build.py`), then run `python build.py lc_form.py`. For a new form, copy
`forms/example_form.py` to `forms/<name>_form.py`, change the parts marked `CHANGE`, and run `python build.py <name>_form.py`.

If you changed questions, also update their rows in [Every question](#every-question) above, and tell the Bank's
system team about new or renamed ids (they read the QR code's answers by id).

Note: `half=True` / `half=False` on a question is kept in the PDF's copy of the form but has no effect on the
layout: box widths are worked out from the label and `max`.

### Where this came from

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
    menu page. Answers stay when you switch away and back. (Superseded by item 32: the menu now hides too.)
    Needs Adobe Acrobat with JavaScript on; free Acrobat Reader may refuse to show or hide pages unless the PDF has
    Reader rights; without JavaScript only the menu page is visible. Checked in Acrobat: menu alone at open (1 page,
    38 templates); LC -> 5 pages, BG -> 4 pages with LC hidden; back to LC keeps its answers, QR code page last.
29. **Section buttons and paragraph height (for the studio's canvas).** A section can add a row of buttons at its
    bottom right: `buttons=["check-form", "reset-form", "generate-qr", "print-form"]` (any of these, each once). They
    run the same scripts as the form's own buttons (`BUTTON_JS` in `acrobat_js.py`), show on screen only, and are
    named `__s<section>_<button>` (e.g. `__s14_print_form`). A paragraph box can say how tall it is: `height=80`
    (points; default 50). `check_form` refuses other button names and a height on anything but a paragraph. No form
    file uses them yet, so every form builds byte-identical PDFs. PDF Template Studio's canvas sets both: drag a
    question's edge, or tick a section's buttons.
30. **The warning before save / print shows once.** On the Windows work laptop, Acrobat showed "This form is not
    ready to send" four times in a row when the form was opened. The `/WS` / `/WP` event was firing repeatedly (why
    Acrobat fires it there is not yet known). `before-save` in `acrobat_js.py` now skips an event that comes within
    3 seconds of the warning closing (`lcWarnedAt`, set in the document script), so a burst shows one warning and a
    real save or print later still warns. The message now starts "Before saving:" or "Before printing:" (from
    `event.name`), which says which event fired.
31. **The rules, written as numbered rules.** In `acrobat_js.py`, `across()` now lists the checks across answers as
    Rule 1-9: one plain sentence each (e.g. "Rule 1: the LC must not expire before the latest shipment date"), then
    its code, with named dates (`applied`, `shipment`, `expiry`) instead of one-letter names. The loop that colours
    each question is Steps 1-5 (applies? mandatory and blank? wrong? which boxes? colour). Behaviour unchanged:
    old and new scripts compared on 15,000 random answer sets over 5 forms (LC, import financing, EBLC, OBC, BG;
    every rule fired), 0 differences.
32. **Menu hides when a form is open; terms tick box.** `build_all.py`: the menu page is now a visible named page
    (`MENU`, in the catalog's `Names/Pages`), so the "00 menu" script can hide it like a form: choosing a form shows
    its pages then hides the menu (only the form is visible); the Main menu button on every form page, and the Main menu
    bookmark, now run `showMenu` (show the menu, hide the open form) instead of going to page 1. The menu has a plain
    black-and-white tick box (field `ACCEPT`; wording is the `TERMS_TEXT` constant at the top of `build_all.py`);
    clicking a form or its bookmark while it is not ticked shows an alert and opens nothing. Print Form is back to
    printing from page 1 of the form (the menu is no longer a page beside it). Checked in Acrobat Pro: opens as 1 page
    (13 links, ACCEPT = Off); ticked LC -> 4 pages; Main menu -> 1 page, 13 links, ACCEPT still Yes; BG -> 3 pages;
    back to LC keeps its answers. The alert text itself and clicking with the mouse were not checked.
33. **The menu says why a form did not open.** `build_all.py`: if the PDF viewer refuses to show or hide pages (Adobe
    says the free Acrobat Reader may not allow it), the menu now shows a message with the error and the viewer's name
    and version, instead of doing nothing. Reported 24 Nov: on a work computer the tick-box message worked but a ticked
    form did not open.
34. **Menu works without show/hide (for the free Reader).** Reported 24 Nov: in Acrobat Reader 26 the menu failed with
    "NotAllowedError: Security Settings prevent access to this property or method" (setting `template.hidden` is not
    allowed there). `build_all.py` no longer shows or hides anything: the menu is an ordinary page 0 that stays; a form's
    pages stay hidden templates (`LC_0` ...) and `showForm` copies them in after the menu with `Template.spawn`
    (`bRename: false`, so fields keep names like `LC.applicant_name` and the form's scripts, Check form, Reset form and
    the QR code page, still the last page, work as before). Choosing the open form goes to its first page; choosing
    another asks "Open <form>? The answers in <open form> will be cleared.", then deletes the old copies
    (`deletePages`), clears that form (`resetForm`) and spawns the new one. Which form is open is the hidden field
    `OPEN` (survives save and reopen). Main menu is just `pageNum = 0`: nothing is deleted, answers stay. Print Form
    prints from page 1 (not the menu) again. The "visible named page MENU" of item 32 is gone. If a step is refused,
    the message names it (`spawn`, `deletePages` ...). Checked in Acrobat Pro (this Mac, which cannot prove Reader): LC ->
    1+4 pages, answer kept after Main menu, BG -> 1+3 pages with the question asked and LC answer cleared, BG QR field
    on the last page, saved copy reopens with 5 pages and OPEN = LC. One difference found: copies made by spawn lose
    the widget-level Mouse Up action (`lcRules(this)`) on the 19 radio / list widgets of LC page 1; the rules still run
    through the hidden `__checks` calculation. NOT checked: Reader (it may still refuse `spawn` or `deletePages`).
35. **Main menu clears the form; fixes after the first Reader-era round.** (a) Main menu (button and bookmark) asks
    "Go back to the main menu? The answers in <form> will be cleared."; Yes deletes the form's pages, clears `OPEN`,
    clears the form (`resetForm`, its own `try`) and shows the menu page alone; No stays. If `deletePages` is refused
    (free Reader may), it just goes to page 0 and the form stays, with no message. The menu's intro text says so.
    (b) Spawned copies lost the GoTo "< Previous page" / "Next page >" links: `build_all.py` now makes them JavaScript
    links (`this.pageNum += 1` / `-= 1`), which survive (Acrobat-saved copy: 2 + 2 + 3 Main menu links on BG's 3 pages).
    (c) `showForm`: the ACCEPT read is inside the `try`; `OPEN` is cleared right after `deletePages`, and `resetForm`
    has its own `try`, so a failed reset cannot leave `OPEN` naming a form whose pages are gone. (d) Going to a page
    (`goPage`) never raises an error: a real click refused `d.pageNum = 1` right after `spawn` ("InvalidSetError"),
    so it is retried 100 ms later with `app.setTimeOut`, else the user stays put. (e) The error message blames the free
    Reader only for `spawn` / `deletePages` in Reader; otherwise it says it is a script problem to send to the developer.
    (f) NOT restored: the widget-level click action (`lcRules(this)`) that `spawn` drops from tick boxes, radio buttons
    and lists. `Field.setAction` has no effect on the spawned copies (Acrobat-saved copy: 0 such actions, same as
    before); calling the rules right after `spawn` fails in a real click ("too much recursion": the rules set fields,
    which fires the `__checks` calculation, which calls the rules); a field-level `/V` action was tried and dropped for
    the same re-entry risk. The `__checks` calculation survives spawn and runs the rules after changes; `showForm` only
    asks for one `calculateNow()`. Checked in Acrobat Pro (osascript, not mouse clicks): LC 1+4 pages -> Main menu 1
    page, `OPEN` empty, typed answer cleared -> LC 1+4 -> BG 1+3; saved copy reopens with `OPEN` = BG. NOT checked:
    real clicks after this round, Reader, whether clicking a radio button still updates the form without the widget action.
36. **QR code quality samples 21 to 30 (`benchmark/make_qr_samples.py`).** 10 more typed LC applications, each a
    different bad copy: phone photo, 75 dpi scan, blur, folds and punches, coffee stain and pen, torn corner, cropped
    edge, damaged two-code fax, faded halftone, shrunk and skewed scan (3 have two QR codes). Measured with zxing-cpp
    (as `read_qr.py`) and the workbench's reader: 7 of 10 read with every answer right; the torn corner (lost a corner
    square) and the cropped edge fail, and the fax reads only 1 of its 2 codes. Output in `out/samples-qr-quality/`
    (PDFs, QR close-ups, answer key, README table); a copy is in pdf-template-studio `public/samples/qr-quality/`.
    The form files are unchanged.
37. **No wait when leaving a box (rules once per change, only what the change affects).** Reported 24 Nov: a pause each time a
    person leaves a box and clicks the next. Measured in Acrobat Pro (Mac, `tools/lag_check.py`): standalone LC 163-174 ms per
    simulated commit (the calculation about 85 ms, the blur script another 80 ms: the rules ran twice, each run writing every
    question's colour); the joined PDF has 13 `__checks` calculations, one per form, so every commit ran the rules of forms that
    are not open. Changes (`acrobat_js.py`, `pdf_writer.py`, `build_all.py`; behaviour, messages, required / lock logic and the
    QR text are unchanged): (a) `lcRules(doc, name)` re-checks only the questions in `lcDeps[name]`, an index
    `dependency_index()` builds when the PDF is made (a box, the questions reading it, and what those read); (b) it ignores a
    box whose value is the one it saw last (the calculation fires first, then the blur: one run, not two); (c) it skips writing a
    box whose look is unchanged and sets `doc.calculate = false` while writing, with a second pass only if a box was cleared;
    (d) a full run (opening, Reset form, Check form, saving, QR code, a calculation with no `event.source`) still checks everything
    and rewrites every look; (e) joined PDF: each form's `__checks` returns at once unless `OPEN` is its form. After: standalone LC
    2-9 ms per commit, joined PDF with LC open 2-4 ms. NOT measured: the joined PDF before the change (its document scripts did not
    finish loading in Acrobat within 240 s in this session, JavaScript was switched off for it), Reader, a person's clicks.
    Checked in Acrobat Pro: 18 edits to LC (amount, dates, drafts chain, insurance chain with a cascade clear, price basis)
    gave the same boxes (required, lock, colours, line width, value) after the incremental run as after a full run; in the joined
    PDF, reset + `calculateNow` followed by typing the same answer again still colours the box.
38. **Decluttered to what builds the forms.** The repo now holds only `build.py`, `build_all.py`, the engine files, `forms/`,
    `requirements.txt` and the docs. `read_qr.py` (the Bank's QR reader), `benchmark/` (QR vs AI test), `tools/`
    (`reader_test.py`, `lag_check.py`, `smartform/`) moved to `~/Documents/lc-form-extras` (not needed to build). `zxing-cpp`
    left `requirements.txt` (only the QR reader used it). Pillow stays: pikepdf needs it. Forms and PDFs are unchanged.
39. **Up to 16 QR codes instead of two (`acrobat_js.py`, `layout.py`, `pdf_writer.py`, `build_all.py`, `proof_multiqr.py`).**
    Before, answers over 4,600 characters had their two long paragraphs shortened to fit two codes (the LC form's worst
    case, about 15,300 characters, lost most of both). Now Generate QR Code makes as many codes as the answers need, up to
    16 (the structured-append limit), padded to fill them (2,300 bytes per code). Codes 1 and 2 stay on the QR code page; codes 3
    and up go two to a page on extra QR code pages (same 110 mm, 0.6 mm squares) that are copies of one hidden page template
    (`qrx`; `LC_qrx` in the joined PDF) made with `Template.spawn` and removed when the answers shrink or the form is reset.
    The long paragraphs are shortened (and listed in `"truncated"`) only beyond 16 codes. Print Form prints up to the last QR
    page in use and refuses if a code is missing; the warning before saving or printing says so too. lc_form.py: 477 fields and
    591,354 bytes before; 835 fields (the template's 358 added) and about 550,000 bytes after (the QR row boxes now share one drawing
    each). Tested outside Acrobat (`python proof_multiqr.py`: the form alone and the LC form inside the joined PDF, three
    guesses at how the viewer renames spawned fields, `deletePages` allowed and refused): 2,000 / 4,000 / 9,000 / 15,300
    characters give 1 / 2 / 4 / 7 codes, every code decodes with zxing-cpp 3.1.1 and the joined text equals the payload
    exactly, with the structured-append index, total and parity right; 2 x 30,000 characters give 16 codes with Goods
    description shortened and listed. NOT checked: Acrobat Pro, Reader (does `spawn` with `bRename: true` work and what are
    the new fields called; does `deletePages` work; how long drawing many codes takes), the Bank's scanners on 3 or more
    codes, and the readers (`read_qr.py`, the workbench), which were not changed and still expect at most two codes.
40. **The pipe-format form (Form LC-01P).** `forms/lc_pipe_form.py` (its own PDF, `LC-Application-Pipe.pdf`, not in the menu):
    the same questions as the LC, with the old smart form's 4 pipe-delimited barcode records as the QR text, so the Bank's
    back end that reads that format keeps working. Mapping table in the form file, encoder in `acrobat_js.py` (`PIPE_JS`),
    QR drawing, encoding and pages untouched (the records, a newline between them, go through `lcDrawQr`, which makes as many codes as the text needs). Checked by `check_pipe.py`:
    byte-identical to the old code on the golden sample and 300 random valid answer sets, and the QR codes decode back to the
    records. Every other form's PDF is byte-identical to before (built with `PYTHONHASHSEED=0`: three forms' PDFs differ
    by one byte between two builds without it, as before this change). See "The pipe-format form".
41. **Pipe form: hostile values and Print Form.** Delimiters (`| [ ] { }`) and line breaks in an answer no longer change the
    records' layout (`lcPipeAnswers`), Print Form no longer depends on how Acrobat stores the newlines between records, and
    `build.py` refuses `"codes"` on a question without options (a tick box accepts only the key `true`). `check_pipe.py` has the
    hostile and Print Form checks.
42. **No page limit (`build.py`, `pdf_writer.py`, every form file).** The `PAGES` setting and its check are gone: a new
    question that no longer fits on a form's pages adds a page instead of stopping the build with `expected 4 pages`.
43. **`acrobat_js.py` rewritten to be readable (no behaviour change).** Every script in the file (the rules engine `lcRules` /
    `lcWords` / `lcDates`, the QR text `lcPayload`, the QR encoder `lcQrMatrix`, the page helpers `lcExtra` / `lcSlot` /
    `lcQrCheck` / `lcDrawQr`, the pipe-format functions, and every button and the before-save script) now has descriptive
    names instead of one-letter ones, one statement per line, small named helpers (for example one `parseDate` used by both
    the date check and rules 1-4, in place of two copies of the same pattern), named constants for the magic numbers (hidden
    = 1, the grey and pink colours, "Off"), and a plain-words comment on every function (what it does, what it takes and
    returns, an example). Each of rules 1-9 in `across()` says in everyday words what it stops, with one example.
    The QR encoder's arithmetic is unchanged. The comments no longer repeat the capital-letter placeholders
    (`__MODEL__` and the others), because the build fills those in everywhere in the script, comments included, which had pasted the whole
    rules table into a comment. Proven with a differential test (not committed): the old and the new scripts, run in node against the same
    fake Acrobat document, gave identical results, field writes and QR codes on tens of thousands of random cases.
