# Guide for beginners: change the form, or make a new one

You don't need to know how to program. You edit **one file** (a form file), run **one command**, and open the PDF.

```
lc-form/
  lc_form.py        <- THE LC FORM. To change the LC form, edit this file only.
  example_form.py   <- a small example. Copy it to start a new form.
  eblc_form.py      <- a 5-section demo (Export Bills under LC): every kind of mandatory rule.
  build.py          <- RUN THIS:  python build.py lc_form.py
  layout.py         \
  pdf_writer.py      > the engine: the same for every form. Never edit these.
  acrobat_js.py     /
  out/              <- the PDF appears here
  read_qr.py          reads the printed QR code(s) back (the Bank's side)
  GUIDE.md            this guide
  README.md           the full reference (rules, QR codes, security, history)
  requirements.txt    the library to install (pikepdf)
```

**Building a PDF needs exactly 5 files in one folder:** the form file + `build.py`, `layout.py`, `pdf_writer.py`,
`acrobat_js.py`. No sub-folders.

## 0. Getting the files onto a work computer

Copy each file **exactly**. The safest way, for each file on GitHub:

1. Open the file on GitHub and press the **Download raw file** button (the arrow, top right of the file).
2. Save it into one folder, keeping its name (`build.py`, not `build.py.txt`).

If you can only copy and paste: on GitHub press **Raw**, select everything (Ctrl+A), copy, and paste into a new file
in a plain-text editor (Notepad or VS Code, not Word). Save as **UTF-8**.

You can't break the form silently: if a file is missing, cut short or changed while copying, the build stops and
names the file to copy again.

## 1. One-time setup

Open a terminal (Windows: Command Prompt) in that folder and run:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt          (Mac: .venv/bin/pip install -r requirements.txt)
```

From then on, "build" means:

```
.venv\Scripts\python build.py lc_form.py               (Mac: .venv/bin/python build.py lc_form.py)
```

It prints `PASS: 4 pages, ...` and writes `out/LC-Application.pdf`. Open that in **Adobe Acrobat or Reader** (a
browser doesn't run the form's checks). If a yellow bar says JavaScript is disabled, choose **Options > Enable
JavaScript** (or ask IT): without it, nothing on the form is checked.

**Quick test after every build:** with the form empty, press **Check form**. It must list the mandatory questions.
If it says "The form's checks did not start", JavaScript is off in Acrobat (see above).

## 2. Change the form

Open `lc_form.py` in a text editor. Each question is **one line**, like this:

```python
text("applicant_name", "Applicant name", required=True, max=35),
```

| Part | Meaning |
|---|---|
| `text` | the kind of question: a one-line box |
| `"applicant_name"` | the **id**: the answer's name in the PDF and the QR code. Letters, digits and `_` only. Every id different. |
| `"Applicant name"` | the **label** people see |
| `required=True` | mandatory (red until filled in) |
| `max=35` | at most 35 characters |

### Common changes

| I want to... | Do this |
|---|---|
| Change the wording of a question | Edit the label (the second text in quotes). Don't change the id. |
| Make a question mandatory | Add `required=True` |
| Make it mandatory only when a box is ticked | Add `requiredIf=ticked("drafts")` (the id of the tick box) |
| Make it mandatory only for some answers | Add `requiredIf=when("drafts_at", "Term")` (the id, then the answer(s)) |
| Allow digits only / an amount | Add `format="number"` or `format="amount"` (also `phone`, `account`) |
| Limit the length | Add or change `max=35` |
| Make a question take the whole row | Add `cols=12` (the row has 12 columns: `cols=6` = half, `cols=4` = a third). Without `cols` the build picks a width from the label and `max` |
| Change the choices of a question | Edit the list: `["Sight", "Term"]` |
| Add a question | Copy a similar line, paste it where it should appear, give it a **new id**, change the label |
| Remove a question | Delete its line. Also delete any `requiredIf=...("its_id")` or `DEFAULTS` entry that names its id. |
| Add a section | Copy a whole `section("...", fields=[ ... ]),` block and change it |
| Change what's filled in when the form opens | Edit `DEFAULTS` near the end of the file |

The kinds of question: `text` (one line), `long` (paragraph), `date`, `radio` (pick one), `checks` (tick any),
`check` (one tick box), `select` (drop-down). Every option is listed in section 1 of `build.py`.

### Then

1. **Build** (the command above).
2. If you made a mistake, the build **stops and says what's wrong**, for example:
   ```
   PROBLEM IN THE FORM FILE: question 2.6 ("handover_notes"): requiredIf refers to "hand_over", but no question has that id.
   ```
   Fix that line and build again. Nothing is saved until the build passes.
3. If it says `expected 4 pages`, your change made the LC form longer than its approved 4 pages. Shorten something,
   or (if a longer form is approved) change `PAGES = 4` at the end of `lc_form.py`.
4. **Open `out/LC-Application.pdf` in Acrobat** and check your change: red boxes, Check form, Generate QR Code.
5. If you changed questions, update the table in `README.md` ("Every question"), and tell the Bank's system team
   about new or renamed ids: they read the answers from the QR code by id.

## 3. Make a similar form

1. Copy `example_form.py` to a new name that **ends in `_form.py`**, e.g. `trade_loan_form.py`, in the same folder.
   (Copy `lc_form.py` instead if the new form is close to the LC form.)
2. Open it and change the parts marked `CHANGE`: the title, the issuer, the form code (e.g. `Form TL-01`; it must be
   different from every other form's), the sections and questions, `DEFAULTS` and `PDF_NAME`.
3. Build it: `python build.py trade_loan_form.py`. The PDF appears in `out/`.

Every form automatically gets the same features: red mandatory boxes, locking of questions that don't apply,
Check form and Reset form buttons, and the QR code page (one code, or two when the answers are long).

## 4. Read a filled-in form's QR code(s)

Scan the printed QR code page (300 dpi, as PNG or JPG), then run:

```
.venv\Scripts\python read_qr.py scan.png               (Mac: .venv/bin/python read_qr.py scan.png)
```

If the form printed two codes, both can be in one scan, or give two images: `read_qr.py page1.png page2.png`.
It prints `ACCEPTED`, or `NOT ACCEPTED` with what is wrong, and saves the answers as a `.json` file in `out/`.
It needs `zxing-cpp` (in `requirements.txt`). Phone apps that look up products ("no product found") can't read
these codes; use `read_qr.py` or a QR reader that shows the text.

## 5. If something goes wrong

| What you see | What to do |
|---|---|
| `PROBLEM IN THE FORM FILE: ...` | Fix the line it names in your form file. |
| `PROBLEM: pdf_writer.py is missing, incomplete or damaged` (or another engine file) | Copy that file again from GitHub (Download raw file), into the same folder as `build.py`. |
| `PROBLEM IN acrobat_js.py ... characters that break Acrobat` | The file changed while being copied. Copy it again with Download raw file. |
| `The library pikepdf is not installed` | Run the setup step again: `pip install -r requirements.txt`. |
| In Acrobat: no calendars, red boxes never turn black, Check form says the checks did not start | JavaScript is off in Acrobat: yellow bar > Options > Enable JavaScript, or Preferences > JavaScript > Enable Acrobat JavaScript. Then close and reopen the PDF. |
| A browser shows the form but nothing is checked | Browsers don't run the form's checks. Download it and open it in Acrobat or Reader. |

## 6. When to ask a developer

Ask someone who knows Python if you want to change **how every form looks or works** rather than what one form
asks: colours and sizes (`layout.py`, section 1), how questions are arranged (`layout.py`, section 4), what the
buttons or checks do (`acrobat_js.py`), or what the QR code contains. `README.md` explains each of these.
