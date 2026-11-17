# Guide for beginners: change the form, or make a new one

You don't need to know how to program. You will edit **one file** (a form file in `forms/`), run **one
command**, and open the PDF. Everything else (the `engine/` folder) does the work, and you don't need to open it.

```
lc-form/
  forms/                    ← YOU WORK HERE
    lc.py                     the LC application form
    example_leave.py          a small example to copy when you make a new form
  build.py                  ← YOU RUN THIS:  python build.py forms/lc.py
  read_qr.py                  reads the QR code(s) from a scan:  python read_qr.py scan.png
  out/                      ← THE PDF APPEARS HERE
  engine/                     how a form becomes a PDF (no need to open)
  GUIDE.md                    this guide
  README.md                   the full reference (rules, QR code, security, history)
  requirements.txt            the one library to install (pikepdf)
```

## 0. One-time setup

Open a terminal (Windows: Command Prompt) in the `lc-form` folder and run:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt          (Mac: .venv/bin/pip install -r requirements.txt)
```

From then on, "build" means:

```
.venv\Scripts\python build.py forms/lc.py              (Mac: .venv/bin/python build.py forms/lc.py)
```

It prints `PASS: 4 pages, ...` and writes `out/LC-Application.pdf`. Open that in **Adobe Acrobat or Reader** (a
browser doesn't run the form's checks).

## 1. Change the form

Open `forms/lc.py` in any text editor (Notepad, VS Code). Each question is **one line**, like this:

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
| Change the choices of a question | Edit the list: `["Sight", "Term"]` |
| Add a question | Copy a similar line, paste it where it should appear, give it a **new id**, change the label |
| Remove a question | Delete its line. Also delete any `requiredIf=...("its_id")` or `DEFAULTS` entry that names its id. |
| Add a section | Copy a whole `section("...", fields=[ ... ]),` block and change it |
| Change what's filled in when the form opens | Edit `DEFAULTS` at the end of the file |

The kinds of question: `text` (one line), `long` (paragraph), `date`, `radio` (pick one), `checks` (tick any),
`check` (one tick box), `select` (drop-down). Every option is listed at the top of `engine/questions.py`.

### Then

1. **Build** (the command above).
2. If you made a mistake, the build **stops and says what's wrong**, for example:
   ```
   PROBLEM IN THE FORM FILE: question 2.6 ("handover_notes"): requiredIf refers to "hand_over", but no question has that id.
   ```
   Fix that line and build again. Nothing is saved until the build passes.
3. If it says `expected 4 pages`, your change made the LC form longer than its approved 4 pages. Shorten something,
   or (if a longer form is approved) change `PAGES = 4` at the end of `forms/lc.py`.
4. **Open `out/LC-Application.pdf` in Acrobat** and check your change: red boxes, Check form, and Generate QR Code.
5. If you changed questions, update the table in `README.md` ("Every question"), and tell the Bank's system team
   about new or renamed ids: they read the answers from the QR code by id.

## 2. Make a similar form

1. Copy `forms/example_leave.py` to a new name, e.g. `forms/trade_loan.py`. (Or copy `forms/lc.py` if the new form
   is close to the LC form.)
2. Open it and change the parts marked `CHANGE`: the title, the issuer, the form code, the sections and questions,
   `DEFAULTS` and `PDF_NAME`.
3. Build it: `python build.py forms/trade_loan.py`. The PDF appears in `out/`.

Every form automatically gets the same features: red mandatory boxes, locking of questions that don't apply,
Check form and Reset form buttons, and the QR code page (one code, or two when the answers are long).

## 3. Read a filled-in form's QR code(s)

Scan the printed QR code page (300 dpi, as PNG or JPG), then run:

```
.venv\Scripts\python read_qr.py scan.png              (Mac: .venv/bin/python read_qr.py scan.png)
```

If the form printed two codes, both can be in one scan, or give two images: `read_qr.py page1.png page2.png`.
It prints `ACCEPTED`, or `NOT ACCEPTED` with what is wrong, and saves the answers as a `.json` file in `out/`.

## 4. When to ask a developer

Ask someone who knows Python if you want to change **how every form looks or works** rather than what one form
asks: colours and sizes (`engine/look.py`), how questions are arranged (`engine/layout.py`), what the buttons or
checks do (`engine/js/`), or what the QR code contains. `README.md` explains each of these.
