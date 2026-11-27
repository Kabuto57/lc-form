# Guide for beginners: change the form, or make a new one

You don't need to know how to program. You edit **one file** (a form file), run **one command**, and open the PDF.

```
lc-form/
  forms/            <- EVERY FORM FILE IS IN HERE
    lc_form.py        <- THE LC FORM. To change the LC form, edit this file only.
    example_form.py   <- a small example. Copy it to start a new form.
    eblc_form.py, obc_form.py, bg_form.py ...   <- the other trade forms (12), redrawn from the old smart form.
                         Build any of them the same way:  python build.py bg_form.py
  forms/lc_pipe_form.py <- the LC form again, but its QR code holds the old smart form's pipe-delimited text (Form LC-01P)
  build.py          <- RUN THIS:  python build.py lc_form.py
  build_all.py      <- or this, for every form in one PDF with a main menu:  python build_all.py
                       (tick the terms box and click a form on the menu to go to it; every form's pages stay in the PDF after the menu, Main menu jumps back to page 1; needs JavaScript on)
  layout.py         \
  pdf_writer.py      > the engine: the same for every form. Never edit these.
  acrobat_js.py     /
  out/              <- the PDF appears here
  (QR reader, benchmark, tools and check scripts: moved out of this repo to ~/Documents/lc-form-extras, not needed to build)
  GUIDE.md            this guide
  README.md           the full reference (rules, QR codes, security, history)
  requirements.txt    the library to install (pikepdf)
```

**Building a PDF needs:** `build.py`, `layout.py`, `pdf_writer.py`, `acrobat_js.py` in one folder, and the form
file in a `forms` folder inside it (`forms/lc_form.py`). The other trade forms use `lc_form.py`'s currency list, so
copy `forms/lc_form.py` too when you build them.

## 0. Getting the files onto a work computer

Copy each file **exactly**. The safest way, for each file on GitHub:

1. Open the file on GitHub and press the **Download raw file** button (the arrow, top right of the file).
2. Save it keeping its name (`build.py`, not `build.py.txt`): engine files into one folder, form files into the
   `forms` folder inside it.

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
| Make a section the whole width / half | Add `width="full"` or `width="half"` to its `section(...)`. Two half sections in a row sit side by side. Without `width` the build decides |
| Make a section taller (blank space at the bottom) | Add `min_height=200` to its `section(...)` (points). The box is at least that tall; if the questions need more room, they win. Leave it out to fit the questions. A section with no `width` that reaches 300 points goes full width instead of sitting beside another |
| Start a section on a new page | Add `new_page=True` to its `section(...)` |
| Make a question take the whole row | Add `cols=12` (the row has 12 columns: `cols=6` = half, `cols=4` = a third). Without `cols` the build picks a width from the label and `max` |
| Make a paragraph box taller or shorter | Add `height=80` to its `long(...)` line (points; the default is 50) |
| Add buttons to a section | Add `buttons=["check-form", "print-form"]` to its `section(...)`. Choose from `"check-form"`, `"reset-form"`, `"generate-qr"`, `"print-form"`: they do what the form's own buttons of those names do, and show on screen only |
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
3. There is no page limit: if your change makes a form longer, it simply gets another page.
4. **Open `out/LC-Application.pdf` in Acrobat** and check your change: red boxes, Check form, Generate QR Code.
5. If you changed questions, update the table in `README.md` ("Every question"), and tell the Bank's system team
   about new or renamed ids: they read the answers from the QR code by id.

## 3. Make a similar form

1. Copy `example_form.py` to a new name that **ends in `_form.py`**, e.g. `trade_loan_form.py`, in the `forms` folder.
   (Copy `lc_form.py` instead if the new form is close to the LC form.)
2. Open it and change the parts marked `CHANGE`: the title, the issuer, the form code (e.g. `Form TL-01`; it must be
   different from every other form's), the sections and questions, `DEFAULTS` and `PDF_NAME`.
3. Build it: `python build.py trade_loan_form.py`. The PDF appears in `out/`.

Every form automatically gets the same features: red mandatory boxes, locking of questions that don't apply,
Check form and Reset form buttons, and the QR code page (one code, or as many as the answers need, up to 16: the extra codes go on extra pages that appear only while needed).

### The pipe-format LC form (`lc_pipe_form.py`)

`python build.py lc_pipe_form.py` makes `out/LC-Application-Pipe.pdf`: the same questions and checks as the LC form (it uses
`lc_form.py`, so change questions there), but Generate QR Code writes the **old smart form's barcode text** (4 records, fields
separated by `|`, in fixed positions) instead of the JSON. It is not in the main-menu PDF. Which question goes in which position
is the table `PIPE` in `forms/lc_pipe_form.py` (one line per position, 62 lines, named `1_01` ... `4_03` as in the old layout):
to move a question or change a code, change its line. Questions the old format never carried (contact details, financing, the
4th address line ...) are not in the QR code; the printed form still shows them. Test it against the old form's own code with
`check_pipe.py` (moved out of this repo to `~/Documents/lc-form-extras/checks/`; needs `node` and the smart-form extract; details in README.md, "The pipe-format form").

## 4. Read a filled-in form's QR code(s)

Moved out of this repo to `~/Documents/lc-form-extras` (not needed to build).

## 5. If something goes wrong

| What you see | What to do |
|---|---|
| `PROBLEM IN THE FORM FILE: ...` | Fix the line it names in your form file. |
| `PROBLEM: pdf_writer.py is missing, incomplete or damaged` (or another engine file) | Copy that file again from GitHub (Download raw file), into the same folder as `build.py`. |
| `PROBLEM IN acrobat_js.py ... characters that break Acrobat` | The file changed while being copied. Copy it again with Download raw file. |
| `The library pikepdf is not installed` | Run the setup step again: `pip install -r requirements.txt`. |
| In Acrobat: no calendars, red boxes never turn black, Check form says the checks did not start | JavaScript is off in Acrobat: yellow bar > Options > Enable JavaScript, or Preferences > JavaScript > Enable Acrobat JavaScript. Then close and reopen the PDF. |
| In the one-PDF menu (`build_all.py`): a message says "This PDF viewer would not go to ..." | The viewer refused to change page. Scroll down to the form instead (the forms follow the menu page in the order listed); send the message text to a developer. |
| Clicking from one box to the next feels slow in Acrobat | The form re-checks only the questions the box you left affects. If it is still slow, send the form name to a developer. |
| A browser shows the form but nothing is checked | Browsers don't run the form's checks. Download it and open it in Acrobat or Reader. |

## 6. When to ask a developer

Ask someone who knows Python if you want to change **how every form looks or works** rather than what one form
asks: colours and sizes (`layout.py`, section 1), how questions are arranged (`layout.py`, section 4), what the
buttons or checks do (`acrobat_js.py`), or what the QR code contains. `README.md` explains each of these. `acrobat_js.py`
is written to be read: every function and every rule has a comment in plain words with an example.
