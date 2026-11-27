"""THE JAVASCRIPT THAT RUNS INSIDE THE PDF, IN ACROBAT. pdf_writer.py copies it into every PDF it builds.

Kept inside a Python file (not as .js files) so that copying the project can never leave the scripts behind or
change them: if this file is cut short, Python itself refuses to run. Acrobat's JavaScript is old-style: var and
function only, no let, const or =>. Use plain ASCII characters only (the build checks this).
The __NAMES__ in capitals are filled in for each form by document_script() in pdf_writer.py.
"""

# The document script, stored in the PDF as "lcRules" (the placeholders __MODEL__, __DEPS__, __CHECKS__ and __DATES__ in it are filled in per form
# by pdf_writer.py): the rules engine (red boxes, locking, checks), the QR
# codes' text (lcPayload), the QR encoder (lcQrMatrix), and the drawing of up to 16 codes over the QR page and the extra QR
# pages (lcDrawQr, lcExtra, lcQrCheck).
DOCUMENT_JS = r"""
// =====================================================================================================================
// THE RULES ENGINE (runs inside Acrobat). Built into the PDF as the document script "lcRules".
//
// lcRules(doc) checks every question and colours its box:
//   blank or wrong mandatory answer -> red outline, pink fill, marked Required
//   answered and right              -> black outline, white fill
//   doesn't apply yet               -> greyed out, locked, and its answer cleared
// It returns the list of missing questions, plus .bad (wrong answers) and .first (where to put the cursor).
//
// lcWords(amount, currency) writes an amount in words ("USD One Thousand ... only").
// lcDates(doc) shows each date's calendar box and hides its drop-down list (Acrobat only).
//
// The form's own data is pasted into this script when the PDF is built (see document_script in pdf_writer.py):
//   lcModel  the rules table: one entry per question (its label, kind, "applies only if" rules, "mandatory if" rules ...)
//   lcDeps   an index: box name -> the questions to re-check when that box changes (null = always check everything)
//   lcState  what the last run saw, so the next run can skip work that cannot have changed:
//              v  = each box's last-seen value (a box whose value did not change is not checked again)
//              st = each box's last-written look (a box whose look did not change is not written again)
//
// Acrobat's JavaScript is old-style (ES3/ES5): write "var" and "function" only, and none of the newer (ES6) syntax or
// methods. Plain ASCII characters only (the build checks this).
// Every read or write of an Acrobat field is slow, so the code below avoids repeating them.
// =====================================================================================================================
var lcModel = __MODEL__;
var lcDeps = __DEPS__;
var lcState = {v: {}, st: {}};

// ---------------------------------------------------------------------------------------------------------------------
// lcRules(d, src)
//   d    the PDF document (Acrobat's "this").
//   src  optional. The name of the box that just changed (its blur, its click, or what the calculation says triggered
//        it). Then only the questions that read that box are re-checked, and nothing at all if its value is what the
//        last run saw. No src (opening, Reset form, Check form, saving ...): every question, and every look is
//        written again.
// Returns the array of missing questions' labels, with two extra properties:
//   .bad    the wrong answers, as "<question>: <what is wrong>"
//   .first  the name of the box of the first problem (Check form puts the cursor there)
// ---------------------------------------------------------------------------------------------------------------------
function lcRules(d, src) {
  // ---- Fixed values used below, given names -------------------------------------------------------------------------
  var DISPLAY_HIDDEN = 1;                               // a field's .display is 1 when it is hidden (Acrobat's display.hidden)
  var OFF = "Off";                                      // the value of a tick box or option that is not ticked
  var GREY_LINE = ["G", 0.6];                           // outline of a box that does not apply (mid grey)
  var GREY_FILL = ["G", 0.86];                          // fill of a box that does not apply (light grey)
  var PINK_FILL = ["RGB", 1, 0.88, 0.88];              // fill of a box that is blank or wrong (the outline is red)
  var MONTH_NAMES = "JanFebMarAprMayJunJulAugSepOctNovDec";   // 3 letters each, so month number = position / 3 + 1
  // The characters an answer may contain (letters, digits, space and . , - / ( ) ' : ? + # & @ % and line breaks). This
  // is written as a string, so the backslashes are doubled: it reads [^A-Za-z0-9 .,\-/()':?+#&@%\r\n] ("anything else").
  var OTHER_CHARACTERS = "[^A-Za-z0-9 .,\\-/()':?+#&@%\\r\\n]";

  var model = lcModel;        // the rules table (see the top of this script)
  var state = lcState;        // what the last run saw
  var onlyThese = null;       // null = check every question; otherwise {question id: 1} = check just those
  var cleared = false;        // did this pass clear a box? (then a second pass is needed: another question may read it)
  var i;

  // ---- Which questions to check? ----------------------------------------------------------------------------------
  if (src) {
    // The box's name, without the "Field." style prefix Acrobat can put in front of it.
    var changedName = String(src).replace(/^[A-Z]+\./, "");
    // A tick-any option or a date's drop-down list is named "<question>__<number>" or "<question>__list".
    var partOfGroup = /^(.+)__(\d+|list)$/.exec(changedName);
    // The question that box belongs to ("" if it belongs to none).
    var changedQuestion = "";
    if (model[changedName]) changedQuestion = changedName;
    else if (partOfGroup && model[partOfGroup[1]]) changedQuestion = partOfGroup[1];

    if (lcDeps) {
      var toRecheck = changedQuestion && lcDeps[changedQuestion];   // the list of question ids that read this box
      var changedField = d.getField(changedName);
      var newValue = changedField ? String(changedField.value) : "";
      // Nothing reads this box, or its value is the one the last run saw: there is nothing to do.
      if (!toRecheck || state.v[changedName] === newValue) {
        var nothing = [];
        nothing.bad = [];
        nothing.first = "";
        return nothing;
      }
      state.v[changedName] = newValue;
      onlyThese = {};
      for (i = 0; i < toRecheck.length; i++) onlyThese[toRecheck[i]] = 1;
    }
  }
  // A full run starts from scratch: forget what the last run saw, so every box is checked and written again.
  if (!onlyThese) {
    state.v = {};
    state.st = {};
  }

  // ===================================================================================================================
  // HELPERS. They read the document d and the rules table, and are used by the checks further down.
  // ===================================================================================================================

  // Is value one of the items in list? (Loose == on purpose: a rule may list the number 1 for the text "1".)
  function has(list, value) {
    for (var k = 0; k < list.length; k++) {
      if (list[k] == value) return true;
    }
    return false;
  }

  // A real DD/MM/YYYY date as a Date, or null (blank text, wrong shape, or a day that does not exist such as 31/02/2026).
  // new Date() rolls 31/02 over to 03/03, so a date is real only if the day and month come back unchanged.
  function parseDate(text) {
    var parts = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(text);
    if (!parts) return null;
    var dayOfMonth = +parts[1];
    var monthIndex = parts[2] - 1;   // Date counts months from 0
    var date = new Date(+parts[3], monthIndex, dayOfMonth);
    if (date.getDate() == dayOfMonth && date.getMonth() == monthIndex) return date;
    return null;
  }

  // Is this box on the page? (A date has two boxes: the calendar box, and a drop-down list for when JavaScript is off;
  // lcDates hides one of them.)
  function shown(id) {
    var field = d.getField(id);
    return !!field && field.display != DISPLAY_HIDDEN;
  }

  // Is this answer blank? An answer is text, or a list of ticked options (for tick-any questions).
  function empty(answer) {
    if (typeof answer == "object") return !answer.length;
    return answer === "";
  }

  // --- Reading an answer -----------------------------------------------------------------------------------------

  // A tick-any question: the list of the options that are ticked, e.g. ["Air", "Sea"].
  function tickedOptions(id, question) {
    var ticked = [];
    for (var k = 0; k < question.options.length; k++) {
      var option = d.getField(id + "__" + k);   // one tick box per option
      if (option && option.value != OFF) ticked.push(question.options[k]);
    }
    return ticked;
  }

  // The drop-down list's text "05 Mar 2026" as "05/03/2026" ("" while it still says "Pick a date").
  function dateFromList(text) {
    var parts = /^(\d\d) (\w{3}) (\d{4})$/.exec(text);
    if (!parts) return "";
    var monthNumber = ("0" + (MONTH_NAMES.indexOf(parts[2]) / 3 + 1)).slice(-2);   // "Mar" -> 6 / 3 + 1 -> "03"
    return parts[1] + "/" + monthNumber + "/" + parts[3];
  }

  // The answer to question id, read from the PDF's fields:
  //   tick-any  -> a list of the ticked options
  //   date      -> "DD/MM/YYYY" text, from the calendar box (or from the drop-down list when that is the one showing)
  //   tick box  -> "true" or "false"
  //   anything else -> its text ("" if blank, or an option group with nothing picked)
  function val(id) {
    var question = model[id];
    if (question.kind == "checks") return tickedOptions(id, question);
    if (question.kind == "date") {
      if (shown(id)) return d.getField(id).valueAsString;
      var listBox = d.getField(id + "__list");
      if (listBox) return dateFromList(listBox.valueAsString);
    }
    var field = d.getField(id);
    if (!field) return "";
    if (question.kind == "check") return field.value != OFF ? "true" : "false";
    return field.value == OFF ? "" : String(field.value);
  }

  // The answer to question id, or "" when the form has no such question (other forms lack some of the LC's questions).
  function v(id) {
    if (model[id]) return val(id);
    return "";
  }

  // --- "Applies only if" and "mandatory if" ----------------------------------------------------------------------

  // Does the answer (text, or list of ticked options) include one of the values?
  function matchesAny(answer, values) {
    if (typeof answer != "object") return has(values, answer);
    for (var k = 0; k < answer.length; k++) {
      if (has(values, answer[k])) return true;
    }
    return false;
  }

  // Does any of these conditions hold? Each condition is [question id, values, not]:
  //   not = 0: holds when the answer to that question is one of the values.     e.g. ["mode", ["Air"], 0]
  //   not = 1: holds when it is answered, but not with one of the values.       e.g. ["mode", ["Air"], 1]
  // Used for activeIf ("this question applies only if ...") and requiredIf ("this question is mandatory if ...").
  function any(conditions) {
    for (var k = 0; k < conditions.length; k++) {
      var questionId = conditions[k][0];
      var values = conditions[k][1];
      var negate = conditions[k][2];
      var answer = val(questionId);
      var matches = matchesAny(answer, values);
      if (negate) {
        if (!matches && !empty(answer)) return true;
      } else if (matches) {
        return true;
      }
    }
    return false;
  }

  // Must this question be answered right now? Always (always: true), or when one of its requiredIf conditions holds.
  function mandatory(id) {
    var question = model[id];
    if (question.always) return true;
    return any(question.requiredIf || []);
  }

  // --- Is the typed answer wrong? --------------------------------------------------------------------------------

  // The characters in text that are not allowed, each once, in order of appearance ([] when all are fine).
  function disallowedCharacters(text) {
    var found = text.match(new RegExp(OTHER_CHARACTERS, "g")) || [];
    var each = [];
    for (var k = 0; k < found.length; k++) {
      if (!has(each, found[k])) each.push(found[k]);
    }
    return each;
  }

  // What is wrong with the typed answer, as a sentence for the "bad" list; "" when it is fine or blank.
  // Three checks, in this order, and the first that fails wins:
  //   1. only the allowed characters             "remove ~ ^ (letters, digits and ...)"
  //   2. a date is a real date                   "not a real date (DD/MM/YYYY)"
  //   3. the question's own pattern (a regular expression and its message from the form file)
  // Only questions with a "check" in the rules table are checked at all.
  function wrong(id) {
    var question = model[id];
    var text = "";
    if (question.kind == "date") {
      text = val(id);
    } else {
      var field = d.getField(id);
      if (field) text = field.valueAsString;
    }
    if (!question.check || !text) return "";

    var disallowed = disallowedCharacters(text);
    if (disallowed.length) return "remove " + disallowed.join(" ") + " (letters, digits and . , - / ( ) ' : ? + # & @ % only)";

    if (question.kind == "date") return parseDate(text) ? "" : "not a real date (DD/MM/YYYY)";

    // question.check is [pattern, message], or just the number 1 ("allowed characters only", which was checked above).
    if (question.check.length && !new RegExp(question.check[0]).test(text)) return question.check[1];
    return "";
  }

  // ===================================================================================================================
  // THE RULES ACROSS ANSWERS. Each rule: what it checks (one sentence and an example), then its code. A rule that is
  // broken puts its message on the question: the box turns red, and Check form lists "<question>: <message>".
  // Rules 1-6 are the LC's own (the same as the cross-checks in pdf-template-studio's form/validate.ts); a form without
  // those questions skips them (v() gives "" for a question the form does not have). Rules 7-9 come from the form file
  // (FORM["checks"]), so any form can add its own.
  // ===================================================================================================================

  // Is this text a number such as "1,250.50"? ("abc" and "" are not.)
  function isNumber(text) {
    return /^[\d,]+(\.\d+)?$/.test(text);
  }

  // "1,250.50" -> 1250.5
  function toNumber(text) {
    return Number(text.replace(/,/g, ""));
  }

  // Runs every rule across answers. Returns what is wrong, by question id: {question id: message}.
  function across() {
    var problems = {};
    // The dates as real dates (null while blank or not a date, so a rule that needs both dates is skipped).
    var applicationDate = parseDate(v("application_date"));
    var shipmentDate = parseDate(v("latest_shipment_date"));
    var expiryDate = parseDate(v("expiry_date"));
    var amount = v("amount");
    var priceBasis = v("price_basis");

    // Rule 1: the LC must not expire before the latest shipment date.
    //         e.g. expiry 01/03/2026, latest shipment 15/03/2026 -> expiry_date: is before the latest shipment date
    if (shipmentDate && expiryDate && expiryDate < shipmentDate) {
      problems.expiry_date = "is before the latest shipment date";
    }
    // Rule 2: the LC must not expire before the application date (checked only when rule 1 is fine, so a question
    //         never shows two messages).
    //         e.g. application 10/03/2026, expiry 01/03/2026 (no shipment date yet) -> expiry_date: is before the application date
    else if (applicationDate && expiryDate && expiryDate < applicationDate) {
      problems.expiry_date = "is before the application date";
    }

    // Rule 3: the latest shipment date must not be before the application date.
    //         e.g. application 10/03/2026, latest shipment 05/03/2026 -> latest_shipment_date: is before the application date
    if (applicationDate && shipmentDate && shipmentDate < applicationDate) {
      problems.latest_shipment_date = "is before the application date";
    }

    // Rule 4: the application date must not be in the future.
    //         e.g. today is 27/11/2026, application 28/11/2026 -> application_date: is in the future
    if (applicationDate && applicationDate.getTime() > new Date().getTime()) {
      problems.application_date = "is in the future";
    }

    // Rule 5: the amount must be more than zero (only once it is a number).
    //         e.g. amount 0.00 -> amount: must be more than zero
    if (isNumber(amount) && !(toNumber(amount) > 0)) {
      problems.amount = "must be more than zero";
    }

    // Rule 6: "insurance for FOB/CFR/FCA/CPT" must be left blank when the price basis is CIF or CIP
    //         (with CIF and CIP the beneficiary arranges the insurance).
    //         e.g. price basis CIF and an insurance arrangement filled in ->
    //              insurance_arrangement: is only for FOB/CFR/FCA/CPT, but price basis is CIF (the beneficiary insures)
    if (v("insurance_arrangement") && (priceBasis == "CIF" || priceBasis == "CIP")) {
      problems.insurance_arrangement = "is only for FOB/CFR/FCA/CPT, but price basis is " + priceBasis + " (the beneficiary insures)";
    }

    // Rules 7-9: the form file's own checks. Each is {t: kind, a: question, m: message, ...}, tried in the order the
    // form file lists them (a later one replaces an earlier message on the same question).
    var formChecks = __CHECKS__;
    for (var j = 0; j < formChecks.length; j++) {
      var check = formChecks[j];

      // Rule 7 ("order"): date a must not be before date b (with s: true it must be after b: the same day is not enough).
      //         e.g. {t: "order", a: "expiry_date", b: "issue_date", m: "is before the issue date"},
      //         expiry 01/03/2026, issue 05/03/2026 -> expiry_date: is before the issue date
      if (check.t == "order") {
        var dateA = parseDate(v(check.a));
        var dateB = parseDate(v(check.b));
        if (dateA && dateB) {
          var tooEarly = check.s ? dateA <= dateB : dateA < dateB;
          if (tooEarly) problems[check.a] = check.m;
        }
      }

      // Rule 8 ("range"): number a must be between lo and hi.
      //         e.g. {t: "range", a: "tolerance", lo: 0, hi: 10, m: "must be between 0 and 10"}, tolerance 15 -> that message
      if (check.t == "range") {
        var rangeAnswer = v(check.a);
        if (isNumber(rangeAnswer)) {
          var rangeNumber = toNumber(rangeAnswer);
          if (rangeNumber < check.lo || rangeNumber > check.hi) problems[check.a] = check.m;
        }
      }

      // Rule 9 ("lengths"): a's digits (ignoring spaces, dashes ...) must be one of the allowed lengths, which can depend
      //         on the answer to b (e.g. an account number's length by currency; "*" = any other answer).
      //         e.g. {t: "lengths", a: "account", b: "currency", by: {"USD": [10], "*": [8, 9]}, m: "..."},
      //         currency USD and an account number of 9 digits -> that message
      if (check.t == "lengths") {
        var digits = v(check.a).replace(/\D/g, "");
        var otherAnswer = v(check.b);
        var allowedLengths = check.by.hasOwnProperty(otherAnswer) ? check.by[otherAnswer] : check.by["*"];
        if (digits && allowedLengths && allowedLengths.length && !has(allowedLengths, digits.length)) {
          problems[check.a] = check.m;
        }
      }
    }
    return problems;
  }

  // ===================================================================================================================
  // WRITING THE LOOK OF A BOX
  // ===================================================================================================================

  // Empties a box of a question that does not apply, so an answer can't stay behind in a locked question.
  //   field  the box;  kind  its question's kind;  boxName  the box's name.
  // Sets "cleared" when it really changed an answer (a second pass then re-checks the questions that read it).
  function clearAnswer(field, kind, boxName) {
    if (kind == "check" || kind == "checks" || kind == "radio") {
      if (field.value != OFF) {
        field.value = OFF;
        cleared = true;
      }
    } else if (field.type == "combobox" && /__list$/.test(field["name"])) {
      // A date's drop-down list: back to its first line, "Pick a date".
      if (field.currentValueIndices != 0) {
        field.currentValueIndices = 0;
        cleared = true;
      }
    } else if (field.value !== "" && field.value != null) {
      field.value = "";
      cleared = true;
    }
    delete state.v[boxName];   // the next change of this box is new to the next run
  }

  // A box of a question that does not apply: grey, locked (the caller does that), answer cleared.
  function paintGrey(field, kind, boxName) {
    clearAnswer(field, kind, boxName);
    field.lineWidth = 1;
    field.strokeColor = GREY_LINE;
    field.fillColor = GREY_FILL;
  }

  // A box of a question that applies. A problem (blank mandatory, or wrong): red outline, pink fill. Fine: black outline
  // and white fill; or, for an "underlined" question (just a line to write on): no outline, a transparent fill, and
  // only its underline.
  function paintActive(field, underlined, problem) {
    field.lineWidth = problem || !underlined ? 1 : 0;
    if (problem) {
      field.strokeColor = color.red;
      field.fillColor = PINK_FILL;
    } else if (underlined) {
      field.strokeColor = color.transparent;
      field.fillColor = color.transparent;
    } else {
      field.strokeColor = color.black;
      field.fillColor = color.white;
    }
  }

  // The names of the boxes on the page that belong to a question:
  //   tick-any  one box per option ("<id>__0", "<id>__1" ...)
  //   a date    its calendar box, or its drop-down list ("<id>__list") when the list is the one showing
  //   otherwise the question's own box
  function boxesOf(id, question) {
    var names = [id];
    if (question.kind == "checks") {
      names = [];
      for (var k = 0; k < question.options.length; k++) names.push(id + "__" + k);
    }
    if (question.kind == "date" && !shown(id) && d.getField(id + "__list")) names = [id + "__list"];
    return names;
  }

  // ===================================================================================================================
  // GO THROUGH EVERY QUESTION, in 5 steps, and colour (and lock) its boxes.
  // ===================================================================================================================
  var missing = [];        // labels of the mandatory questions still blank
  var bad = [];            // "<label>: <what is wrong>" for each wrong answer
  var firstProblem = "";   // the box of the first question with a problem
  var id, question, applies, required, problem, whatsWrong, boxNames, lookKey, field, boxName, wordsField, words;
  var calculateWas = d.calculate;
  d.calculate = false;   // every write below would otherwise run the calculation again
  try {
    // A second pass only if a box was cleared (a later question may read it). Three passes at most.
    for (var pass = 0; pass < 3; pass++) {
      missing = [];
      bad = [];
      firstProblem = "";
      cleared = false;
      var wrongAcross = across();   // what the rules across answers found, by question id

      for (id in model) {
        question = model[id];
        if (!question.hasRule && !question.check && !question.activeIf) continue;   // no rule, no format: nothing to do
        if (onlyThese && !onlyThese[id]) continue;                                  // this change can't affect it

        // Step 1: does the question apply? (activeIf in the form file, e.g. "only when Term is picked")
        applies = !question.activeIf || any(question.activeIf);

        // Step 2: is it mandatory now, and still blank? (always: true, or requiredIf in the form file)
        required = false;
        if (question.hasRule && applies) required = mandatory(id);
        if (required) {
          if (question.kind == "check") problem = val(id) != "true";   // a tick box is "blank" when not ticked
          else problem = empty(val(id));
        } else {
          problem = false;
        }
        if (problem) missing.push(question.label);

        // Step 3: is the answer wrong? (its format, or one of the rules across answers above)
        whatsWrong = "";
        if (applies) whatsWrong = wrong(id) || wrongAcross[id] || "";
        if (whatsWrong) {
          bad.push(question.label + ": " + whatsWrong);
          problem = true;
        }

        // Step 4: which boxes on the page are this question's (tick-any: one per option; a date: its list or its box)
        boxNames = boxesOf(id, question);
        if (problem && !firstProblem) firstProblem = boxNames[0];

        // Step 5: colour each box. Doesn't apply: grey, locked, answer cleared. Problem: red outline, pink fill.
        //         Fine: black outline (or just its underline), white fill.
        // lookKey sums up the look in two or three letters: "r" if marked Required, then "p" (problem), "o" (fine) or
        // "g" (greyed). A box that already has this look is skipped: every write to Acrobat is slow.
        lookKey = (required && problem ? "r" : "-") + (applies ? (problem ? "p" : "o") : "g");
        for (i = 0; i < boxNames.length; i++) {
          boxName = boxNames[i];
          field = d.getField(boxName);
          if (!field) continue;
          if (state.st[boxName] === lookKey) continue;
          state.st[boxName] = lookKey;
          // Required only while blank or wrong: Acrobat outlines Required boxes in red even when they are filled.
          if (question.hasRule && question.kind != "checks") field.required = !!(required && problem);
          if (question.activeIf) field.readonly = !applies;   // locked until it applies
          if (applies) paintActive(field, question.underlined, problem);
          else paintGrey(field, question.kind, boxName);
        }
      }

      // Amounts in words (a question with words: [amount id, currency id]), as the old bill of exchange wrote them.
      for (id in model) {
        question = model[id];
        if (!question.words) continue;
        if (onlyThese && !onlyThese[id]) continue;
        wordsField = d.getField(id);
        if (!wordsField) continue;
        words = lcWords(v(question.words[0]), v(question.words[1] || ""));
        if (wordsField.value != words) {
          wordsField.value = words;
          delete state.v[id];
        }
      }

      if (!cleared) break;
    }
  } catch (e) {
    console.println("lcRules: " + e);
  }
  d.calculate = calculateWas;

  missing.bad = bad;
  missing.first = firstProblem;   // the field of the first problem, for "Check form" to go to
  return missing;
}

// ---------------------------------------------------------------------------------------------------------------------
// lcWords(amount, currency): an amount in words.
//   "1,250.50", "USD" -> "USD One Thousand Two Hundred Fifty and Fifty cents only"
//   "" or text that is not an amount -> "" (the words stay blank until the amount is filled in)
// ---------------------------------------------------------------------------------------------------------------------
function lcWords(amount, currency) {
  var ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
              "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
  var TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];
  var SCALES = ["", " Thousand", " Million", " Billion", " Trillion"];   // the name of each group of 3 digits

  // Whole part and (up to 2-digit) cents part: "1250.5" -> "1250" and "5". No commas or spaces are allowed to remain.
  var amountText = String(amount).replace(/[, ]/g, "");
  var parts = /^(\d+)(?:\.(\d{1,2}))?$/.exec(amountText);
  if (!parts) return "";

  // 1 to 999 in words: 305 -> "Three Hundred Five", 42 -> "Forty Two".
  function belowThousand(number) {
    var hundreds = Math.floor(number / 100);
    var rest = number % 100;
    var pieces = [];
    if (hundreds) pieces.push(ONES[hundreds] + " Hundred");
    if (rest >= 20) {
      var tens = TENS[Math.floor(rest / 10)];
      if (rest % 10) tens = tens + " " + ONES[rest % 10];
      pieces.push(tens);
    } else if (rest) {
      pieces.push(ONES[rest]);
    }
    return pieces.join(" ");
  }

  // A string of digits in words: "1250" -> "One Thousand Two Hundred Fifty"; "" or "000" -> "Zero".
  // It works from the right in groups of 3 digits (units, thousands, millions ...) and skips an all-zero group.
  function digitsInWords(digits) {
    digits = digits.replace(/^0+/, "");
    if (!digits) return "Zero";
    var groups = [];
    for (var scale = 0; digits.length; scale++) {
      var group = +digits.slice(-3);
      digits = digits.slice(0, -3);
      if (group) groups.unshift(belowThousand(group) + SCALES[scale]);
    }
    return groups.join(" ");
  }

  var words = digitsInWords(parts[1]);
  if (parts[2] && +parts[2]) {
    // One digit after the point is tenths of a dollar: "0.5" means 50 cents, not 5.
    var cents = parts[2].length == 1 ? parts[2] + "0" : parts[2];
    words += " and " + digitsInWords(cents) + " cents";
  }
  return (currency ? currency + " " : "") + words + " only";
}

// ---------------------------------------------------------------------------------------------------------------------
// lcDates(d): Acrobat only. Shows each date's calendar box and hides its drop-down list.
// A date question has two boxes: the calendar box (works with JavaScript) and a plain drop-down list of real dates
// (the fallback for when JavaScript is off). The list below is filled in when the PDF is built: the ids of the date questions.
// ---------------------------------------------------------------------------------------------------------------------
function lcDates(d) {
  var dateIds = __DATES__;
  for (var i = 0; i < dateIds.length; i++) {
    var calendarBox = d.getField(dateIds[i]);
    if (!calendarBox) continue;
    calendarBox.display = display.visible;
    var listBox = d.getField(dateIds[i] + "__list");
    if (listBox) listBox.display = display.hidden;
  }
}

// When the warning before saving / printing was last closed. Some Acrobat versions (seen on Windows) fire the
// save / print events several times in a row; the warning then shows once, not once per event.
var lcWarnedAt = 0;

// On opening in Acrobat: show the calendars, and set every box's colour and lock.
if (typeof app != "undefined" && /^(Exchange|Reader)/.test(app.viewerType)) {
  lcDates(this);
  lcRules(this);
}

// =====================================================================================================================
// THE QR CODES' TEXT
//
// What this does: lcPayload(doc) reads every answered question and returns them as one piece of text (JSON), which
// the QR codes then carry. JSON is plain text that a computer can read back, like this:
//   {"form": "LC-01", "version": "1.0", "saved": "2026-11-27T10:30", "complete": true, "data": {"amount": "1,250.50", ...}}
// How answers look in it: a ticked tick box becomes true. A "tick any" question becomes the list of options that are
// ticked. A blank question is left out.
//
// How big it can be: one QR code holds 2,300 bytes (LC_QR_CAP). A longer text needs more codes, at most 16 (LC_QR_MAX):
// 16 is the most that "structured append" allows (that is the part of the QR standard that lets codes say "I am
// code 2 of 3"). lcDrawQr cuts the text into slices, one per code.
// The text is padded with spaces so it fills the codes it needs exactly: 2,300, 4,600 ... 36,800 bytes.
// Only if the answers are longer than 16 codes can hold, the long paragraphs are shortened (and listed in "truncated").
//
// The names FORM, VERSION, GROUPS and LONG in capitals below are filled in when the PDF is built (document_script in
// pdf_writer.py).
// =====================================================================================================================
var LC_QR_CAP = 2300;   // bytes in one QR code
var LC_QR_MAX = 16;     // most codes for one form

// The text as UTF-8 bytes, one character per byte (what really goes into the codes).
// Example: "A" is 1 byte, but a letter with an accent is 2 bytes, so the byte count can be bigger than the letter count.
function lcBytes(text) {
  return unescape(encodeURIComponent(text));
}

// How many codes this text needs (0 for no text). Example: 2,301 bytes -> 2 codes.
function lcCodes(text) {
  if (!text) return 0;
  return Math.ceil(lcBytes(text).length / LC_QR_CAP);
}

// ---------------------------------------------------------------------------------------------------------------------
// lcPayload(d): every answered question as JSON text (see above).
//   d  the PDF document.
// Returns the text, padded with spaces to fill whole codes.
// ---------------------------------------------------------------------------------------------------------------------
function lcPayload(d) {
  var GROUPS = {__GROUPS__};     // "tick any" questions: question id -> its list of options, in order
  var LONG_QUESTIONS = __LONG__; // the long paragraph questions, which may be shortened if the answers are too big
  var budget = LC_QR_MAX * LC_QR_CAP;   // the most bytes 16 codes can hold
  var data = {};                 // the answers: question id -> answer
  var truncated = [];            // ids of the questions that had to be shortened
  var i, n, field, partOfGroup, answer, check;
  var now = new Date();

  // 1. Go through every box in the PDF and note the answers.
  // The box's name is kept in the variable n and the line below is written in exactly this way on purpose: build_all.py
  // finds that line and adds a filter to it, so that one form of the joined PDF does not read another form's boxes.
  for (i = 0; i < d.numFields; i++) {
    n = d.getNthFieldName(i);
    // Skip the form's own helper boxes (their names start with two underscores), the date drop-down lists, and the
    // extra QR code pages' rows.
    if (/^__/.test(n) || /__list$/.test(n) || /__qrx_/.test(n)) continue;
    field = d.getField(n);
    if (!field || field.type == "button" || field.type == "signature") continue;

    // One option of a "tick any" question is named "<question>__<number>": add the option to the question's list.
    partOfGroup = /^(.+)__(\d+)$/.exec(n);
    if (partOfGroup && GROUPS[partOfGroup[1]]) {
      if (field.value != "Off") {
        if (!data[partOfGroup[1]]) data[partOfGroup[1]] = [];
        data[partOfGroup[1]].push(GROUPS[partOfGroup[1]][+partOfGroup[2]]);
      }
      continue;
    }
    // A single tick box: true when ticked, left out when not.
    if (field.type == "checkbox") {
      if (field.value != "Off") data[n] = true;
      continue;
    }
    // Option buttons give the picked option; text boxes give the text without blanks at the start and end.
    if (field.type == "radiobutton") {
      answer = field.value == "Off" ? "" : String(field.value);
    } else {
      answer = String(field.valueAsString).replace(/^\s+|\s+$/g, "");
    }
    if (answer !== "") data[n] = answer;
  }

  // 2. Is the form complete (nothing missing, nothing wrong)? Ask the rules engine.
  var complete = true;
  if (typeof lcRules == "function") {
    check = lcRules(d);
    complete = !check.length && !(check.bad || []).length;
  }

  // 3. Put it together. Two digits for a date part: 5 -> "05".
  function twoDigits(number) {
    return ("0" + number).slice(-2);
  }
  var saved = now.getFullYear() + "-" + twoDigits(now.getMonth() + 1) + "-" + twoDigits(now.getDate()) +
              "T" + twoDigits(now.getHours()) + ":" + twoDigits(now.getMinutes());
  var out = {"form": __FORM__, "version": __VERSION__, "saved": saved, "complete": complete, "data": data};

  // 4. 16 codes hold 36,800 bytes. Only if the answers are longer still: shorten the long paragraphs, one after the
  // other, until it fits, and say which ones in "truncated".
  var tooMany;
  for (i = 0; i < LONG_QUESTIONS.length && lcBytes(JSON.stringify(out)).length > budget; i++) {
    var longId = LONG_QUESTIONS[i];
    if (!data[longId]) continue;
    truncated.push(longId);
    out.truncated = truncated;
    // How many bytes are still too many (plus 3 for the "..." that marks the cut).
    tooMany = lcBytes(JSON.stringify(out)).length - budget + 3;
    if (tooMany < data[longId].length) data[longId] = data[longId].slice(0, data[longId].length - tooMany) + "...";
    else data[longId] = "...";
  }

  // 5. Pad with spaces up to whole codes (2,300 bytes each). Letters that take 2 or more bytes make the byte count
  // bigger than the character count, so that difference is taken off the number of spaces.
  var text = JSON.stringify(out);
  var byteCount = lcBytes(text).length;
  var wantedLength = Math.max(1, Math.ceil(byteCount / LC_QR_CAP)) * LC_QR_CAP - (byteCount - text.length);
  while (text.length < wantedLength) text += " ";
  return text;
}

// =====================================================================================================================
// THE QR CODE ENCODER (standard QR code, no library needed)
//
// What this does: lcQrMatrix(bytes, part) works out the picture of ONE QR code: a square grid of 177 x 177 tiny
// squares, each dark or light. It returns the grid as rows: grid[y][x] is true for a dark square.
//   bytes  the text as UTF-8 bytes, one character per byte (what lcBytes gives).
//   part   null for a single code, or [index, total, parity] for one of several codes. This is "structured append":
//          each code says "I am code <index> of <total>", and "parity" is a check number of the whole text (every byte
//          XORed together), so a scanner that knows structured append can join the codes in the right order. Any other
//          scanner just reads each code's text on its own, and the texts are joined in order.
// What kind of code: version 40 (the biggest, 177 x 177), error correction level M (about 15% of it can be damaged
// and it still reads), byte mode, mask 0. At most 2,329 bytes per code.
//
// How it is built, in order (the same steps as the QR standard):
//   1. Draw the fixed patterns every QR code has (the three big corner squares, the alignment squares, the dotted
//      lines, and the little strips that say what kind of code it is).
//   2. Turn the bytes into a long row of bits, and pad it to the size the code has room for.
//   3. Add error correction ("Reed-Solomon": extra check bytes worked out from the data, so a scanner can fix a
//      smudged or torn code).
//   4. Pour the bits into the free squares in a zigzag order.
//   5. Flip every second square ("mask 0"), which stops large plain areas that scanners find hard to read.
// The maths below must not be changed, or the codes will not scan.
// =====================================================================================================================
function lcQrMatrix(text, part) {
  var SIZE = 177;                    // squares across (and down) of a version 40 code
  var DATA_CODEWORDS = 2334;         // bytes of answers a version 40 / level M code holds (a "codeword" is one byte)
  var BLOCKS = 49;                   // the data is cut into 49 blocks, each with its own error correction
  var SHORT_BLOCKS = 18;             // the first 18 blocks have 47 data bytes; the other 31 have 48
  var ECC_PER_BLOCK = 28;            // error correction bytes added to each block
  var bytes = [];                    // the text as numbers 0 to 255
  var grid = [];                     // grid[y][x]: is this square dark?
  var isFixed = [];                  // isFixed[y][x]: is this square part of a fixed pattern (so data must not go there)?
  var i, j, x, y;

  for (i = 0; i < text.length; i++) bytes.push(text.charCodeAt(i) & 255);
  // Start with a grid of light squares, none of them fixed.
  for (y = 0; y < SIZE; y++) {
    grid.push([]);
    isFixed.push([]);
    for (x = 0; x < SIZE; x++) {
      grid[y].push(false);
      isFixed[y].push(false);
    }
  }

  // Paint one square of a fixed pattern.
  function setFixed(x, y, dark) {
    grid[y][x] = dark;
    isFixed[y][x] = true;
  }

  // Multiply two numbers "in GF(256)": the special arithmetic of Reed-Solomon, where every number is one byte and the
  // answer is one byte again (0x11D is the rule that keeps it inside a byte). Used only for the error correction.
  function multiply(a, b) {
    var product = 0;
    for (var k = 7; k >= 0; k--) {
      product = (product << 1) ^ ((product >>> 7) * 0x11D);
      product ^= ((b >>> k) & 1) * a;
    }
    return product;
  }

  // Bit number k of a number, as true / false.
  function bit(value, k) {
    return ((value >>> k) & 1) != 0;
  }

  // ---- 1. The fixed patterns ------------------------------------------------------------------------------------

  // The two dotted "timing" lines (row 6 and column 6): dark, light, dark, light ...
  for (i = 0; i < SIZE; i++) {
    setFixed(6, i, i % 2 == 0);
    setFixed(i, 6, i % 2 == 0);
  }

  // A "finder": the big square-in-a-square a scanner looks for, centred on (cx, cy), with its light border.
  // Measured from the middle in squares: distance 0 and 1 dark (the solid middle), 2 light, 3 dark, 4 light (the border).
  function drawFinder(cx, cy) {
    for (var dy = -4; dy <= 4; dy++) {
      for (var dx = -4; dx <= 4; dx++) {
        var distance = Math.max(Math.abs(dx), Math.abs(dy));
        var fx = cx + dx;
        var fy = cy + dy;
        if (fx >= 0 && fx < SIZE && fy >= 0 && fy < SIZE) setFixed(fx, fy, distance != 2 && distance != 4);
      }
    }
  }
  drawFinder(3, 3);               // top left
  drawFinder(SIZE - 4, 3);        // top right
  drawFinder(3, SIZE - 4);        // bottom left

  // "Alignment" patterns: small squares that help a scanner straighten a big code. Their centres are at every
  // combination of these positions, except the three that would land on a finder.
  var ALIGNMENT_AT = [6, 30, 58, 86, 114, 142, 170];
  var last = ALIGNMENT_AT.length - 1;
  for (i = 0; i < ALIGNMENT_AT.length; i++) {
    for (j = 0; j < ALIGNMENT_AT.length; j++) {
      if ((i == 0 && j == 0) || (i == 0 && j == last) || (i == last && j == 0)) continue;
      for (var ay = -2; ay <= 2; ay++) {
        for (var ax = -2; ax <= 2; ax++) {
          setFixed(ALIGNMENT_AT[i] + ax, ALIGNMENT_AT[j] + ay, Math.max(Math.abs(ax), Math.abs(ay)) != 1);
        }
      }
    }
  }

  // The "format" strip: 15 bits that say "error correction M, mask 0", written twice (next to two of the finders).
  // The 5 bits of information are all zero here (M is 00, mask 0 is 000), so the 10 check bits are zero too; the
  // standard then XORs the 15 bits with 0x5412 so the strip is never all light.
  var formatCheck = 0;
  for (i = 0; i < 10; i++) formatCheck = (formatCheck << 1) ^ ((formatCheck >>> 9) * 0x537);
  var formatBits = ((0 << 10) | formatCheck) ^ 0x5412;
  for (i = 0; i <= 5; i++) setFixed(8, i, bit(formatBits, i));
  setFixed(8, 7, bit(formatBits, 6));
  setFixed(8, 8, bit(formatBits, 7));
  setFixed(7, 8, bit(formatBits, 8));
  for (i = 9; i < 15; i++) setFixed(14 - i, 8, bit(formatBits, i));
  for (i = 0; i < 8; i++) setFixed(SIZE - 1 - i, 8, bit(formatBits, i));
  for (i = 8; i < 15; i++) setFixed(8, SIZE - 15 + i, bit(formatBits, i));
  setFixed(8, SIZE - 8, true);   // the one square that is always dark

  // The "version" strip: 18 bits that say "version 40" (12 check bits worked out from the number 40), written twice.
  var versionCheck = 40;
  for (i = 0; i < 12; i++) versionCheck = (versionCheck << 1) ^ ((versionCheck >>> 11) * 0x1F25);
  var versionBits = (40 << 12) | versionCheck;
  for (i = 0; i < 18; i++) {
    var vx = SIZE - 11 + i % 3;
    var vy = Math.floor(i / 3);
    setFixed(vx, vy, bit(versionBits, i));
    setFixed(vy, vx, bit(versionBits, i));
  }

  // ---- 2. The data bits ------------------------------------------------------------------------------------------
  // In order: (for one of several codes: mode 0011 = "structured append", this code's index, the total - 1, the
  // parity), then mode 0100 = "bytes follow", the length in 16 bits, the bytes, a terminator of up to 4 zero bits,
  // then padding to 2,334 bytes.
  var bits = [];
  var capacityBits = DATA_CODEWORDS * 8;
  // Add a number as n bits, biggest bit first.
  function putBits(value, count) {
    for (var k = count - 1; k >= 0; k--) bits.push((value >>> k) & 1);
  }
  if (part) {
    putBits(3, 4);
    putBits(part[0], 4);
    putBits(part[1] - 1, 4);
    putBits(part[2], 8);
  }
  putBits(4, 4);
  putBits(bytes.length, 16);
  for (i = 0; i < bytes.length; i++) putBits(bytes[i], 8);
  if (bits.length > capacityBits) throw new Error("too much text for one QR code (" + bytes.length + " bytes)");
  putBits(0, Math.min(4, capacityBits - bits.length));   // terminator
  while (bits.length % 8) bits.push(0);                   // finish the last byte
  // Eight bits at a time -> bytes ("data codewords").
  var data = [];
  for (i = 0; i < bits.length; i += 8) {
    var byteValue = 0;
    for (j = 0; j < 8; j++) byteValue = (byteValue << 1) | bits[i + j];
    data.push(byteValue);
  }
  // Fill what is left with the two padding bytes the standard asks for, 0xEC and 0x11 in turn.
  for (i = 0; data.length < DATA_CODEWORDS; i++) data.push(i % 2 ? 0x11 : 0xEC);

  // ---- 3. Error correction (Reed-Solomon) ---------------------------------------------------------------------
  // 49 blocks (18 of 47 data bytes and 31 of 48), each given 28 error correction bytes.
  // First the "generator": a list of 28 numbers that every block is divided by (worked out once).
  var generator = [];
  var root = 1;
  for (i = 0; i < ECC_PER_BLOCK - 1; i++) generator.push(0);
  generator.push(1);
  for (i = 0; i < ECC_PER_BLOCK; i++) {
    for (j = 0; j < ECC_PER_BLOCK; j++) {
      generator[j] = multiply(generator[j], root);
      if (j + 1 < ECC_PER_BLOCK) generator[j] ^= generator[j + 1];
    }
    root = multiply(root, 2);
  }
  // Then each block: its data bytes followed by its error correction bytes (the remainder of the division).
  var blocks = [];
  var position = 0;   // where this block starts in data
  for (i = 0; i < BLOCKS; i++) {
    var blockLength = i < SHORT_BLOCKS ? 47 : 48;
    var blockData = data.slice(position, position + blockLength);
    var ecc = [];
    position += blockLength;
    for (j = 0; j < ECC_PER_BLOCK; j++) ecc.push(0);
    for (j = 0; j < blockData.length; j++) {
      var factor = blockData[j] ^ ecc.shift();
      ecc.push(0);
      for (var eccIndex = 0; eccIndex < ECC_PER_BLOCK; eccIndex++) ecc[eccIndex] ^= multiply(generator[eccIndex], factor);
    }
    // A short block gets a -1 "no byte here" marker so that all blocks are equally long when interleaved below.
    if (i < SHORT_BLOCKS) blockData.push(-1);
    blocks.push(blockData.concat(ecc));
  }
  // Interleave: first byte of block 1, first byte of block 2 ... then the second byte of each block, and so on
  // (skipping the "no byte here" markers). This spreads a smudge over many blocks, so each can still be repaired.
  var codewords = [];
  for (i = 0; i < blocks[0].length; i++) {
    for (j = 0; j < BLOCKS; j++) {
      if (blocks[j][i] != -1) codewords.push(blocks[j][i]);
    }
  }

  // ---- 4. Place the bits, and 5. mask 0 -----------------------------------------------------------------------
  // The standard fills the grid two columns at a time, from the bottom right, going up and then down in turn (a
  // zigzag), and skips squares that belong to a fixed pattern. Column 6 is skipped (the timing line).
  var bitNumber = 0;
  for (var rightColumn = SIZE - 1; rightColumn >= 1; rightColumn -= 2) {
    if (rightColumn == 6) rightColumn = 5;
    for (var step = 0; step < SIZE; step++) {
      for (j = 0; j < 2; j++) {
        x = rightColumn - j;
        var goingUp = ((rightColumn + 1) & 2) == 0;
        y = goingUp ? SIZE - 1 - step : step;
        if (!isFixed[y][x] && bitNumber < codewords.length * 8) {
          grid[y][x] = ((codewords[bitNumber >>> 3] >>> (7 - (bitNumber & 7))) & 1) != 0;
          bitNumber++;
        }
      }
    }
  }
  // Mask 0: flip every square where x + y is even (only squares that are not fixed patterns).
  for (y = 0; y < SIZE; y++) {
    for (x = 0; x < SIZE; x++) {
      if (!isFixed[y][x] && (x + y) % 2 == 0) grid[y][x] = !grid[y][x];
    }
  }
  return grid;
}

// =====================================================================================================================
// THE PAGES THE CODES GO ON
//
// A code is drawn with text boxes, one box per row of the code. Each row box is read-only and holds the letter "n" in
// the ZapfDingbats font (which prints as a black square) for each dark square, and a space for each light square.
//   Codes 1 and 2 sit on the form's QR code page: rows "__qr1_0" ... "__qr1_176" and "__qr2_0" ... "__qr2_176".
//   Codes 3 to 16 go two to a page on extra pages, which exist only while they are needed. lcDrawQr copies the hidden
//   page template "qrx" (its rows are "__qrx_1_0" ... "__qrx_2_176") after the last page, with Template.spawn, and
//   deletes the extra pages it no longer needs. If the viewer refuses to delete a page, the page stays, empty and
//   marked "not used", and is left out of printing (see lcLastPage).
// The viewer renames a copied page's boxes (bRename: true), but each name still ends with the template's name, so
// lcExtra finds them by that ending.
// Do not write the call to get a field with the usual dot-and-name spelling for those boxes: build_all.py rewrites the
// usual spelling, to add the form's code in the joined PDF. The square-bracket spelling d["getField"](name) is left alone,
// and the names found are already complete.
// =====================================================================================================================

// lcExtra(d): finds the extra QR pages that exist now.
// Returns a list in page order: [{p: the start of that page's box names, page: its page number}].
function lcExtra(d) {
  var pages = [];
  var i, fieldName, nameParts, field;
  var qrBox = d.getField("__qr");
  var qrPage = qrBox && typeof qrBox.page == "number" ? qrBox.page : -1;   // the extras come after this page
  for (i = 0; i < d.numFields; i++) {
    fieldName = d.getNthFieldName(i);
    nameParts = /^(.*)__qrx_1_0$/.exec(fieldName);
    // Not the first row of a QR page, or the template's own row (its start is "" or just the form's code): skip.
    if (!nameParts || /^([A-Z]+\.)?$/.test(nameParts[1])) continue;
    field = d["getField"](fieldName);
    if (field && typeof field.page == "number" && field.page > qrPage && field.page < d.numPages) {
      pages.push({p: nameParts[1], page: field.page});
    }
  }
  pages.sort(function (first, second) { return first.page - second.page; });
  return pages;
}

// lcSlot(d, extraPages, j): the place for code number j (0 = the first code).
// Returns a function: what -> that slot's box, where what is a row number 0-176, or "label", or "frame".
// Example: for code 1 (j = 0), lcSlot(d, pages, 0)("label") is the box "__qr1_label".
function lcSlot(d, extraPages, j) {
  var prefix = null;       // null = a code on the form's own QR page; otherwise the start of an extra page's box names
  var rowName;             // the part of the box name that says which code of the page this is
  if (j < 2) {
    rowName = "__qr" + (j + 1);
  } else {
    rowName = "__qrx_" + ((j - 2) % 2 + 1);                       // two codes to an extra page: 1st and 2nd
    var page = extraPages[(j - 2) >> 1];                          // which extra page (undefined if it does not exist)
    prefix = page && page.p;
  }
  return function (what) {
    if (prefix === null) return d.getField(rowName + "_" + what);
    if (prefix === undefined) return null;
    return d["getField"](prefix + rowName + "_" + what);
  };
}

// How many extra pages n codes need. Example: 2 codes -> 0 extra pages; 3 or 4 codes -> 1; 5 or 6 -> 2.
function lcPagesFor(codeCount) {
  return codeCount > 2 ? Math.ceil((codeCount - 2) / 2) : 0;
}

// The last page of the form as printed: the QR code page, plus the extra pages that the codes of this text use.
function lcLastPage(d, text) {
  return d.getField("__qr").page + lcPagesFor(lcCodes(text));
}

// lcQrCheck(d, text): are the codes on the pages exactly the codes this text needs?
// Used before printing. Returns "" when all is well (every code in use has its first row drawn, and every other
// slot is empty); otherwise a sentence that says what is wrong, e.g. "QR code 2 is blank".
function lcQrCheck(d, text) {
  var needed = lcCodes(text);
  var extraPages = lcExtra(d);
  var j, firstRow;
  if (extraPages.length < lcPagesFor(needed)) return "the extra QR code pages are missing";
  for (j = 0; j < 2 + 2 * extraPages.length || j < needed; j++) {
    firstRow = lcSlot(d, extraPages, j)("0");
    if (!firstRow) return "QR code " + (j + 1) + " is missing";
    if ((firstRow.value !== "") != (j < needed)) {
      if (j < needed) return "QR code " + (j + 1) + " is blank";
      return "QR code " + (j + 1) + " is left over";
    }
  }
  return "";
}

// ---------------------------------------------------------------------------------------------------------------------
// lcDrawQr(d, text): draws the text as one QR code, or as many as it needs (at most 16, one per 2,300 bytes).
//   d     the PDF document.
//   text  what the codes should carry. "" clears every code and removes the extra pages.
// Returns how many codes it drew (0 for "").
// How: the text is cut into slices of equal size, one per code. Each code carries the structured-append header (its
// number, the total, the parity of the whole text), so a scanner that supports it joins them; any other scanner reads
// each slice and the slices are joined in order. Frames, and labels such as "QR code 1 of 3 (scan all 3 codes)",
// show only for codes in use.
// ---------------------------------------------------------------------------------------------------------------------
function lcDrawQr(d, text) {
  var byteString = lcBytes(text);
  var count = lcCodes(text);
  var sliceSize = count ? Math.ceil(byteString.length / count) : 0;
  var codes = [];          // one grid for each code
  var parity = 0;          // all the bytes XORed together
  var i, k, j, y, x, row, pages, newPages, slotBox, box;
  var calculateWas = d.calculate;
  var extraNeeded;         // how many extra pages these codes need
  if (count > LC_QR_MAX) throw new Error("the answers are too long for " + LC_QR_MAX + " QR codes (" + byteString.length + " bytes, at most " + LC_QR_MAX * LC_QR_CAP + ")");
  for (i = 0; i < byteString.length; i++) parity ^= byteString.charCodeAt(i) & 255;
  // Work out every code first, before anything on the form is touched: if the maths fails, the form is left as it was.
  for (k = 0; k < count; k++) {
    codes.push(lcQrMatrix(byteString.slice(k * sliceSize, (k + 1) * sliceSize), count > 1 ? [k, count, parity] : null));
  }

  // The label under a code. A code in use says which one it is; a slot not in use is blank, except the first slot of an
  // extra page that is left over, which says so.
  function labelFor(j) {
    if (!codes[j]) {
      if (j % 2 == 0 && j >= 2 + 2 * extraNeeded) return "(this page is not used)";
      return "";
    }
    if (count < 2) return "";
    var label = "QR code " + (j + 1) + " of " + count;
    if (j == 0) label += count == 2 ? " (scan both codes)" : " (scan all " + count + " codes)";
    return label;
  }

  d.calculate = false;   // thousands of rows are written: do not re-run the checks after each one
  try {
    pages = lcExtra(d);
    extraNeeded = lcPagesFor(count);
    // Add the extra pages that are needed.
    while (pages.length < extraNeeded) {
      d.getTemplate("qrx").spawn({nPage: d.numPages, bRename: true, bOverlay: false});
      newPages = lcExtra(d);
      if (newPages.length <= pages.length) throw new Error("the viewer did not add the page for QR code " + (2 * pages.length + 3));
      pages = newPages;
    }
    // Take away the extra pages that are not needed (if the viewer refuses, they stay, marked "not used").
    while (pages.length > extraNeeded) {
      try {
        d.deletePages(pages[pages.length - 1].page);
      } catch (e) {
        break;
      }
      newPages = lcExtra(d);
      if (newPages.length >= pages.length) break;
      pages = newPages;
    }
    // Every slot gets its code, or is emptied.
    for (j = 0; j < 2 + 2 * pages.length; j++) {
      slotBox = lcSlot(d, pages, j);
      for (y = 0; y < 177; y++) {
        row = "";
        // "n" (a black square in ZapfDingbats) for a dark square, a space for a light one.
        if (codes[j]) {
          for (x = 0; x < 177; x++) row += codes[j][y][x] ? "n" : " ";
        }
        slotBox(y).value = row;
      }
      box = slotBox("label");
      if (box) box.value = labelFor(j);
      box = slotBox("frame");
      if (box) box.display = codes[j] ? display.visible : display.hidden;
    }
  } finally {
    d.calculate = calculateWas;
  }
  return count;
}
"""[1:-1]

# THE PIPE-FORMAT TEXT (only for a form file with FORM["qrFormat"] == "pipe", e.g. forms/lc_pipe_form.py).
# pdf_writer.py adds this block to the end of the document script of such a form, and fills in __PIPE__ (the position
# table from the form file) and __GROUPS__ (the "tick any" questions' options). Other forms do not get it, so their PDFs
# are unchanged. It takes the place of lcPayload for that form: the "Generate QR Code" button (BUTTON_JS
# "generate-qr-pipe") puts lcPipeText(doc) into the ordinary QR code path (lcDrawQr, up to 16 codes) instead of the JSON
# text. lcPipeText is the 4 records of the old smart form's barcode, one after the other, with a new line between records.
# Nothing here touches the QR encoder or its drawing.
PIPE_JS = r"""
// =====================================================================================================================
// THE PIPE-DELIMITED RECORDS (the old smart form's barcode text), built from the form file's position table.
//
// What this does: instead of the JSON text, the QR codes of this form carry 4 "records". A record is one long line of
// positions, and every position ends with the "|" sign (a "pipe"), like this:
//   LC01|2026-03-05|USD|1250.50|...|
// What goes in each position is decided by the form file (FORM["pipe"]), which is pasted in below as lcPipe.
//
// lcPipe = [record 1's entries, record 2's entries, ...]. Each entry describes one position (the old "1_01" ... "4_03").
// An entry can be any ONE of these:
//   {"c": text}                         a fixed text, the same every time
//   {"id": q}                           the answer to question q, as typed. It can also have:
//                                         "max": cut the answer to this many characters
//                                         "as": "amount" (1250 -> 1250.00) or "date" (05/03/2026 -> 2026-03-05)
//                                         "codes": {answer: code}  (an answer that is not listed gives nothing)
//   {"lines": [q, ...]}                 each answer that is not blank, inside [ ]       e.g. [Line one][Line two]
//   {"join": [q, ...]}                  the answers that are not blank, with one space between
//   {"tpl": {"when": tick box, "parts": [...]}}   a sentence. Its parts are text with {q} marks (each is replaced by
//                                       the answer to q), or ["map", q, {answer: text}], or
//                                       ["list", q, separator, [[option, text], ...]], or ["if", q, text if answered, else text]
//   {"qty": {"on", "o", "c", "head", "tail"}}      "head IN n ORIGINALS AND m COPIES<tail>."
// Any entry may also have:
//   "if": [q, [answers]]    the position is blank unless the answer to q is one of these
//   "d"                     a text to use when the result is blank
//   "chop": true            wrap the result into lines (see lcPipeChop)
// =====================================================================================================================
var lcPipe = __PIPE__;

// The ids of the paragraph questions (the entries with "chop"): the only ones whose Enter key is kept. Worked out the
// first time it is needed (null until then).
var lcPipeLong = null;

// ---------------------------------------------------------------------------------------------------------------------
// lcPipeAnswers(d): every answer, by question id.
//   d  the PDF document.
// Returns {question id: answer}: text as typed (not trimmed); a ticked tick box is "true" (not there when not ticked);
// a "tick any" question is the list of ticked options.
//
// The records' own signs | [ ] { } and line breaks must never come from an answer. The keystroke filter refuses to type
// them, but a value put in by other means (an import, autofill, a pasted new line) skips that filter. So each one is
// turned into a space. Only the paragraph questions keep Enter: the records write it as {}, and any kind of line
// break there counts as one Enter (a carriage return, "\r").
// ---------------------------------------------------------------------------------------------------------------------
function lcPipeAnswers(d) {
  var GROUPS = {__GROUPS__};   // "tick any" questions: question id -> its list of options
  var answers = {};
  var i, j, n, field, partOfGroup, text, entry, k;

  // First time only: which questions are paragraph questions?
  if (!lcPipeLong) {
    lcPipeLong = {};
    for (i = 0; i < lcPipe.length; i++) {
      for (j = 0; j < lcPipe[i].length; j++) {
        entry = lcPipe[i][j];
        if (!entry.chop) continue;
        if (entry.id) lcPipeLong[entry.id] = 1;
        for (k = 0; entry.join && k < entry.join.length; k++) lcPipeLong[entry.join[k]] = 1;
      }
    }
  }

  // The box's name is kept in the variable n and the line below is written in exactly this way on purpose: build_all.py
  // finds that line and adds a filter to it, so that one form of the joined PDF does not read another form's boxes.
  for (i = 0; i < d.numFields; i++) {
    n = d.getNthFieldName(i);
    if (/^__/.test(n) || /__list$/.test(n)) continue;   // the form's own helper boxes and the date drop-down lists
    field = d.getField(n);
    if (!field || field.type == "button" || field.type == "signature") continue;

    // One option of a "tick any" question is named "<question>__<number>".
    partOfGroup = /^(.+)__(\d+)$/.exec(n);
    if (partOfGroup && GROUPS[partOfGroup[1]]) {
      if (field.value != "Off") {
        if (!answers[partOfGroup[1]]) answers[partOfGroup[1]] = [];
        answers[partOfGroup[1]].push(GROUPS[partOfGroup[1]][+partOfGroup[2]]);
      }
      continue;
    }
    if (field.type == "checkbox") {
      if (field.value != "Off") answers[n] = "true";
      continue;
    }
    if (field.type == "radiobutton") {
      text = field.value == "Off" ? "" : String(field.value);
    } else {
      text = String(field.valueAsString);
    }
    if (lcPipeLong[n]) {
      // A paragraph: every kind of line break becomes one carriage return (Enter); the other special signs become spaces.
      text = text.replace(/\r\n|\n/g, "\r").replace(/[|\[\]{}]/g, " ");
    } else {
      // An ordinary answer: the special signs and all line breaks become spaces.
      text = text.replace(/[|\[\]{}\r\n]/g, " ");
    }
    if (text !== "") answers[n] = text;
  }
  return answers;
}

// ---------------------------------------------------------------------------------------------------------------------
// lcPipeChop(text): long text in lines, as the old form wrote it.
//   Leading and trailing blanks and Enters are dropped.
//   Up to 65 characters: kept as one line (an Enter inside becomes {}).
//   Longer: cut at spaces into lines. Each line is padded with spaces to 65 characters and followed by {}.
//   A single word longer than 65 characters is cut at 65. With Enters inside, each paragraph is cut on its own.
// Returns "" for nothing.
// Example (with a line length of 10 instead of 65): "aaa bbb ccc ddd" -> "aaa bbb   {}ccc ddd"
// ---------------------------------------------------------------------------------------------------------------------
function lcPipeChop(text) {
  var MAX = 65;   // characters in a line

  // Without blanks at the start and the end.
  function trim(text) {
    return text.replace(/^\s+/, "").replace(/\s+$/, "");
  }
  // Without Enters (carriage returns) at the start and the end.
  function trimEnters(text) {
    return text.replace(/^\r+/, "").replace(/\r+$/, "");
  }
  // Adds spaces to the end until the line is MAX characters long.
  function padLine(line) {
    while (line.length < MAX) line += " ";
    return line;
  }
  // Text without spaces, cut into lines of MAX characters, each followed by {} (the last piece has none).
  function cutIntoLines(piece) {
    var result = "";
    while (piece.length > 0) {
      if (piece.length > MAX) {
        result += piece.slice(0, MAX) + "{}";
        piece = piece.slice(MAX);
      } else {
        result += piece;
        piece = "";
      }
    }
    return result;
  }
  // Text with spaces but no Enter inside: fills the lines word by word.
  function fillByWords(paragraph) {
    var words = paragraph.split(" ");
    var lines = [];        // the finished lines
    var line = "";         // the line being filled (each word is followed by a space)
    var result = "";
    var i;
    for (i = 0; i < words.length; i++) {
      if (words[i].length > MAX) words[i] = cutIntoLines(words[i]);   // a word too long for a line is cut first
    }
    for (i = 0; i < words.length; i++) {
      if ((line + words[i]).length > MAX) {
        // The word does not fit on this line.
        if (words[i].length <= MAX) {
          // Finish this line and try the same word again on a fresh one.
          i--;
          lines.push(padLine(line) + "{}");
          line = "";
        } else {
          // A cut-up long word: finish this line if it has something, then the word has its own line(s).
          if (line !== "") line = padLine(line) + "{}";
          lines.push(line + words[i] + " ");
          line = "";
        }
      } else {
        line += words[i] + " ";
      }
    }
    if (line !== "") lines.push(line);
    // Join the lines; the very last space (after the last word) is not wanted.
    for (i = 0; i < lines.length; i++) {
      if (i == lines.length - 1 && lines[i].slice(-1) == " ") result += lines[i].slice(0, lines[i].length - 1);
      else result += lines[i];
    }
    return result;
  }
  // Text with Enters inside: each paragraph on its own, with {} between paragraphs.
  // hasSpaces: the text has spaces, so fill by words (and do not trim); otherwise trim each paragraph and cut it.
  function paragraphs(whole, hasSpaces) {
    var parts = whole.split("\r");
    var result = "";
    var i;
    for (i = 0; i < parts.length; i++) {
      if (hasSpaces) {
        if (parts[i].length > MAX) parts[i] = fillByWords(parts[i]);
      } else {
        parts[i] = cutIntoLines(trim(parts[i]));
      }
      result += parts[i] + (i < parts.length - 1 ? "{}" : "");
    }
    return result;
  }

  if (text == null || text.length <= 0) return "";
  text = trim(trimEnters(text));
  if (text.length <= 0) return "";
  // Short enough for one line: as it is (each Enter inside becomes {}).
  if (text.length <= MAX) return trim(text.replace(/\r/g, "{}"));
  var hasSpace = text.indexOf(" ") > 0;
  var hasEnter = text.indexOf("\r") > 0;
  if (!hasSpace) return hasEnter ? paragraphs(text, false) : cutIntoLines(text);
  return hasEnter ? paragraphs(text, true) : fillByWords(text);
}

// ---------------------------------------------------------------------------------------------------------------------
// lcPipeValue(entry, answers): the text of ONE position (see the list of entry kinds at the top).
//   entry    one entry of lcPipe.
//   answers  the answers by question id (from lcPipeAnswers).
// Returns the text, without the "|" that follows it.
// ---------------------------------------------------------------------------------------------------------------------
function lcPipeValue(entry, answers) {
  var value = "";

  // The answer to question id as text ("" if there is none, or if it is a list).
  function answerOf(id) {
    var answer = answers[id];
    return typeof answer == "string" ? answer : "";
  }
  // Is item one of the items of list?
  function has(list, item) {
    for (var i = 0; i < list.length; i++) {
      if (list[i] == item) return true;
    }
    return false;
  }
  // Replaces every {question id} in the text by that question's answer.
  function fill(template) {
    return template.replace(/\{(\w+)\}/g, function (mark, id) { return answerOf(id); });
  }

  // {"lines": [q, ...]}: each answer that is not blank, inside [ ].
  function linesValue() {
    var result = "";
    for (var i = 0; i < entry.lines.length; i++) {
      if (answerOf(entry.lines[i]) !== "") result += "[" + answerOf(entry.lines[i]) + "]";
    }
    return result;
  }

  // {"join": [q, ...]}: the answers that are not blank, one space between.
  function joinValue() {
    var filled = [];
    for (var i = 0; i < entry.join.length; i++) {
      if (answerOf(entry.join[i]) !== "") filled.push(answerOf(entry.join[i]));
    }
    return filled.join(" ");
  }

  // {"tpl": ...}: a sentence made of parts. It is blank unless its tick box ("when") is ticked.
  function templateValue() {
    var template = entry.tpl;
    var result = "";
    var part, picks, ticked, m;
    if (answerOf(template.when) != "true") return "";
    for (var i = 0; i < template.parts.length; i++) {
      part = template.parts[i];
      if (typeof part == "string") {
        result += fill(part);                                    // plain text, with {question} marks
      } else if (part[0] == "map") {
        // ["map", q, {answer: text}]: the text that goes with the answer to q (nothing if the answer is not listed)
        result += fill(part[2].hasOwnProperty(answerOf(part[1])) ? part[2][answerOf(part[1])] : "");
      } else if (part[0] == "if") {
        // ["if", q, text if answered, text if not]
        result += fill(answerOf(part[1]) !== "" ? part[2] : part[3]);
      } else if (part[0] == "list") {
        // ["list", q, separator, [[option, text], ...]]: the texts of the ticked options, in the table's order.
        // No option ticked: no sentence at all.
        picks = [];
        ticked = answers[part[1]] || [];
        for (m = 0; m < part[3].length; m++) {
          if (has(ticked, part[3][m][0])) picks.push(part[3][m][1]);
        }
        if (!picks.length) return "";
        result += picks.join(part[2]);
      }
    }
    return result;
  }

  // {"qty": ...}: "<head> IN 2 ORIGINALS AND 1 COPY<tail>." from the number of originals (o) and copies (c).
  // Example: 2 originals, 1 copy -> " IN 2 ORIGINALS AND 1 COPY"; 1 original, no copies -> " IN 1 ORIGINAL".
  function quantityValue() {
    var qty = entry.qty;
    var originals = answerOf(qty.o);
    var copies = answerOf(qty.c);
    var tail, phrase;
    if (answerOf(qty.on) != "true" || (originals === "" && copies === "")) return "";
    tail = qty.tail && answerOf(qty.tail[0]) !== "" ? fill(qty.tail[1]) : "";
    if (originals == "0" && copies == "0") {
      phrase = "";
    } else if (originals === "" || originals == "0") {
      phrase = " IN " + copies + " " + (copies == "1" ? "COPY" : "COPIES");
    } else if (copies === "" || copies == "0") {
      phrase = " IN " + originals + " " + (originals == "1" ? "ORIGINAL" : "ORIGINALS");
    } else {
      phrase = " IN " + originals + " " + (originals == "1" ? "ORIGINAL" : "ORIGINALS") + " AND " + copies + " " + (copies == "1" ? "COPY" : "COPIES");
    }
    if (phrase !== "" || tail !== "") return qty.head + phrase + tail + ".";
    return "";
  }

  // {"id": q, ...}: the answer as typed, then shaped by "max", "as" and "codes".
  function answerValue() {
    var result = answerOf(entry.id);
    var dateParts;
    if (entry.max != null) result = result.slice(0, entry.max);
    if (entry.as == "amount") {
      // No commas. Always two decimals: 1250 -> 1250.00, 1250.5 -> 1250.50 (text that is not a number stays as it is).
      result = result.replace(/,/g, "");
      if (/^\d+$/.test(result)) result += ".00";
      else if (/^\d+\.\d$/.test(result)) result += "0";
    }
    if (entry.as == "date") {
      // DD/MM/YYYY -> YYYY-MM-DD (blank if it is not a date in that shape).
      dateParts = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(result);
      result = dateParts ? dateParts[3] + "-" + dateParts[2] + "-" + dateParts[1] : "";
    }
    if (entry.codes) result = entry.codes.hasOwnProperty(result) ? entry.codes[result] : "";
    return result;
  }

  // Only if the entry's "if" condition holds (or it has none).
  if (!entry["if"] || has(entry["if"][1], answerOf(entry["if"][0]))) {
    if (entry.c != null) value = entry.c;
    else if (entry.lines) value = linesValue();
    else if (entry.join) value = joinValue();
    else if (entry.tpl) value = templateValue();
    else if (entry.qty) value = quantityValue();
    else if (entry.id) value = answerValue();
    if (entry.chop) value = lcPipeChop(value);
  }
  // A blank result uses the entry's own "d" text, if it has one.
  if (value === "" && entry.d != null) value = entry.d;
  return value;
}

// ---------------------------------------------------------------------------------------------------------------------
// lcPipeRecords(d, answers): the records, as a list of text (one text per record, each position followed by "|").
//   d        the PDF document.
//   answers  optional. The answers to use; by default they are read from the PDF.
// ---------------------------------------------------------------------------------------------------------------------
function lcPipeRecords(d, answers) {
  var records = [];
  var i, j, record;
  answers = answers || lcPipeAnswers(d);
  for (i = 0; i < lcPipe.length; i++) {
    record = "";
    for (j = 0; j < lcPipe[i].length; j++) record += lcPipeValue(lcPipe[i][j], answers) + "|";
    records.push(record);
  }
  return records;
}

// What goes into the QR code: the records, a new line between them.
function lcPipeText(d) {
  return lcPipeRecords(d).join("\n");
}
"""[1:-1]

# THE BUTTON AND EVENT SCRIPTS. Each entry below is stored in the PDF as one action (what happens when a button is
# pressed, or the form is saved or printed). In each script, "this" is the PDF document.
#   check-form          the "Check form" button (top right of every page)
#   reset-form          the "Reset form" button (top right of every page)
#   generate-qr         the "Generate QR Code" button (QR page)
#   print-form          the "Print Form" button (QR page)
#   generate-qr-pipe    the same two buttons, for the pipe-format form (they use lcPipeText instead of lcPayload)
#   print-form-pipe
#   before-save         runs before the form is saved or printed
# They call the functions in DOCUMENT_JS (lcRules, lcPayload, lcDrawQr, lcDates ...).
# A few exact pieces of text are looked for by build_all.py when it joins all the forms into one PDF, so they must stay
# as they are: "getField(" (a dot before it), "this.print(true, 0, " and "this.resetForm();".
# The list of problems that three of the scripts show is built in the same way in each (a script cannot share code with
# another script, so it is written out each time): at most 15 lines, then "... and N more".
BUTTON_JS = {
    "check-form": r"""
// "CHECK FORM" BUTTON.
// What this does: lists what is still blank or wrong (at most 15 of each) and puts the cursor on the first problem.
// If there is nothing to fix, it says the form is ready.
// Example: 2 mandatory questions are blank and 1 answer is wrong -> one message that lists all 3 and says the red boxes
// are the ones to fix.
if (typeof lcRules != "function") {
  // The document script did not run (JavaScript is off, or the form is damaged), so nothing can be checked.
  app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was built from damaged files: build it again.", 1);
} else {
  var missing = lcRules(this);         // labels of the mandatory questions that are blank (it also has .bad and .first)
  var wrong = missing.bad || [];       // "<question>: <what is wrong>" for each wrong answer
  var messages = [];                   // the parts of the message to show

  // "- first\n- second ..." with at most 15 lines; if there are more: "- ... and 3 more".
  var bulletList = function (items) {
    var text = "- " + items.slice(0, 15).join("\n- ");
    if (items.length > 15) text += "\n- ... and " + (items.length - 15) + " more";
    return text;
  };

  if (missing.length) {
    messages.push(missing.length + " mandatory question" + (missing.length > 1 ? "s are" : " is") + " still blank:\n" + bulletList(missing));
  }
  if (wrong.length) {
    messages.push(wrong.length + " answer" + (wrong.length > 1 ? "s need" : " needs") + " correcting:\n" + bulletList(wrong));
  }

  if (messages.length) {
    app.alert("This form is not ready to send. The boxes concerned are outlined in red.\n\n" + messages.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
    // Put the cursor in the first box with a problem.
    var firstBox = missing.first && this.getField(missing.first);
    if (firstBox) firstBox.setFocus();
  } else {
    app.alert("All mandatory questions are answered and every answer is in the right format. You can save the form and send it.", 3);
  }
}
"""[1:-1],
    "reset-form": r"""
// "RESET FORM" BUTTON.
// What this does: asks "are you sure?" first. If yes: sets every answer back to how the form started, wipes the QR codes,
// and checks the form again (so the boxes get their starting colours).
// (app.alert returns 4 when the person presses Yes.)
if (app.alert("Are you sure you want to reset the form? All your answers will be cleared.", 2, 2) == 4) {
  this.resetForm();
  if (typeof lcDrawQr == "function") {
    try { lcDrawQr(this, ""); } catch (e) {}   // "" = draw no codes and remove the extra pages; a failure here does not matter
  }
  if (typeof lcDates == "function") lcDates(this);
  if (typeof lcRules == "function") lcRules(this);
}
"""[1:-1],
    "generate-qr": r"""
// "GENERATE QR CODE" BUTTON.
// What this does: refuses while anything is missing or wrong. Otherwise it makes the QR code from the answers (lcPayload
// makes the text, lcDrawQr draws the codes): one code, or as many as the answers need (at most 16; codes 3 and up go on
// extra pages after the QR code page, two to a page). Then it goes to the QR code page and says what it did.
if (typeof lcRules != "function") {
  app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was built from damaged files: build it again.", 1);
} else {
  var missing = lcRules(this);         // labels of the mandatory questions that are blank (it also has .bad and .first)
  var wrong = missing.bad || [];       // "<question>: <what is wrong>" for each wrong answer
  var messages = [];                   // the parts of the message to show

  // "- first\n- second ..." with at most 15 lines; if there are more: "- ... and 3 more".
  var bulletList = function (items) {
    var text = "- " + items.slice(0, 15).join("\n- ");
    if (items.length > 15) text += "\n- ... and " + (items.length - 15) + " more";
    return text;
  };

  if (missing.length) {
    messages.push(missing.length + " mandatory question" + (missing.length > 1 ? "s are" : " is") + " still blank:\n" + bulletList(missing));
  }
  if (wrong.length) {
    messages.push(wrong.length + " answer" + (wrong.length > 1 ? "s need" : " needs") + " correcting:\n" + bulletList(wrong));
  }

  if (messages.length) {
    // Something to fix: no code is made.
    app.alert("The QR code cannot be generated yet. The boxes concerned are outlined in red.\n\n" + messages.join("\n\n") + "\n\nPlease correct them, then press Generate QR Code again.", 1);
    var firstBox = missing.first && this.getField(missing.first);
    if (firstBox) firstBox.setFocus();
  } else {
    try {
      var qrBox = this.getField("__qr");          // the hidden box that keeps the text of the codes
      qrBox.value = lcPayload(this);
      var codeCount = lcDrawQr(this, qrBox.value);
      var shortened = [];                         // long answers that had to be cut to fit 16 codes
      try { this.pageNum = qrBox.page; } catch (e) {}   // a viewer may refuse to change page inside a click that added pages: the codes are drawn all the same
      try { shortened = JSON.parse(qrBox.value).truncated || []; } catch (e) {}
      if (codeCount == 1) {
        app.alert("The QR code has been generated from your answers (" + qrBox.value.length + " characters). Press Print Form to print the form with the QR code.", 3);
      } else {
        // Where the codes are: two on the QR code page and the rest, two to a page, on the extra pages after it.
        var whereAreThey;
        if (codeCount > 2) {
          whereAreThey = "two on the QR code page and the rest, two to a page, on the " + lcPagesFor(codeCount) + " page" + (lcPagesFor(codeCount) > 1 ? "s" : "") + " after it";
        } else {
          whereAreThey = "one under the other";
        }
        var cutNote = "";
        if (shortened.length) {
          cutNote = "\n\nEven " + codeCount + " codes are too small for everything you typed, so these long answers were shortened in the QR codes (the form itself is unchanged): " + shortened.join(", ") + ".";
        }
        app.alert("Your answers (" + qrBox.value.length + " characters) need " + codeCount + " QR codes, so " + codeCount + " codes have been generated: " + whereAreThey + ". The Bank scans all " + codeCount + " codes. Press Print Form to print the form with the QR codes." + cutNote, shortened.length ? 1 : 3);
      }
    } catch (e) {
      app.alert("The QR code could not be generated: " + e + "\nPlease send this message to the form's maintainer.", 1);
    }
  }
}
"""[1:-1],
    "print-form": r"""
// "PRINT FORM" BUTTON.
// What this does: prints only once the QR code exists and still matches the current answers, so the printed codes always
// carry the answers that are on the paper. That means: every code needed is on its page, none is left over, and the
// pages after the last code in use are not printed.
// Example: answers were changed after Generate QR Code was pressed -> "Your answers have changed ... press Generate QR Code again".
var qrBox = this.getField("__qr");
var textNow = typeof lcPayload == "function" ? lcPayload(this) : "";   // what the codes should say, with today's answers
var sameAnswers = false;      // do the codes on the form carry these answers?
var codesProblem = "";        // what is wrong with the codes on the pages ("" = nothing)
try { sameAnswers = JSON.stringify(JSON.parse(qrBox.value).data) == JSON.stringify(JSON.parse(textNow).data); } catch (e) {}
try { codesProblem = lcQrCheck(this, qrBox.value); } catch (e) { codesProblem = String(e); }
if (!/\S/.test(qrBox.value)) {
  app.alert("Please press Generate QR Code first, so the printed form carries the QR code.", 1);
} else if (!sameAnswers) {
  app.alert("Your answers have changed since the QR code was generated. Please press Generate QR Code again, then Print Form.", 1);
} else if (codesProblem) {
  app.alert("The QR codes in the form do not match your answers (" + codesProblem + "). Please press Generate QR Code again, then Print Form.", 1);
} else {
  this.print(true, 0, lcLastPage(this, qrBox.value), false, true);   // the form up to the last QR code page in use
}
"""[1:-1],
    # The pipe-format form's versions (FORM["qrFormat"] == "pipe"): the same buttons, with lcPipeText in place of lcPayload.
    "generate-qr-pipe": r"""
// "GENERATE QR CODE" BUTTON (pipe-format form).
// What this does: the same as the ordinary Generate QR Code button, but the QR codes hold the old smart form's 4
// pipe-delimited records (lcPipeText, a new line between records) instead of the JSON text. lcDrawQr does not pad or
// change that text. As many codes as the text needs (at most 16), on the same pages as the ordinary form.
if (typeof lcRules != "function") {
  app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was changed after it was built: ask the form's maintainer.", 1);
} else {
  var missing = lcRules(this);         // labels of the mandatory questions that are blank (it also has .bad and .first)
  var wrong = missing.bad || [];       // "<question>: <what is wrong>" for each wrong answer
  var messages = [];                   // the parts of the message to show

  // "- first\n- second ..." with at most 15 lines; if there are more: "- ... and 3 more".
  var bulletList = function (items) {
    var text = "- " + items.slice(0, 15).join("\n- ");
    if (items.length > 15) text += "\n- ... and " + (items.length - 15) + " more";
    return text;
  };

  if (missing.length) {
    messages.push(missing.length + " mandatory question" + (missing.length > 1 ? "s are" : " is") + " still blank:\n" + bulletList(missing));
  }
  if (wrong.length) {
    messages.push(wrong.length + " answer" + (wrong.length > 1 ? "s need" : " needs") + " correcting:\n" + bulletList(wrong));
  }

  if (messages.length) {
    // Something to fix: no code is made.
    app.alert("The QR code cannot be generated yet. The boxes concerned are outlined in red.\n\n" + messages.join("\n\n") + "\n\nPlease correct them, then press Generate QR Code again.", 1);
    var firstBox = missing.first && this.getField(missing.first);
    if (firstBox) firstBox.setFocus();
  } else {
    try {
      var qrBox = this.getField("__qr");          // the hidden box that keeps the text of the codes
      var recordsText = lcPipeText(this);
      qrBox.value = recordsText;
      var codeCount = lcDrawQr(this, recordsText);
      try { this.pageNum = qrBox.page; } catch (e) {}   // a viewer may refuse to change page inside a click that added pages: the codes are drawn all the same
      if (codeCount == 1) {
        app.alert("The QR code has been generated from your answers (" + recordsText.length + " characters). Press Print Form to print the form with the QR code.", 3);
      } else {
        // Where the codes are: two on the QR code page and the rest, two to a page, on the extra pages after it.
        var whereAreThey;
        if (codeCount > 2) {
          whereAreThey = ": two on the QR code page and the rest, two to a page, on the " + lcPagesFor(codeCount) + " page" + (lcPagesFor(codeCount) > 1 ? "s" : "") + " after it";
        } else {
          whereAreThey = ", one under the other";
        }
        app.alert("Your answers (" + recordsText.length + " characters) need " + codeCount + " QR codes, so " + codeCount + " codes have been generated" + whereAreThey + ". The Bank scans all " + codeCount + " codes. Press Print Form to print the form with the QR codes.", 3);
      }
    } catch (e) {
      app.alert("The QR code could not be generated: " + e + "\nPlease send this message to the form's maintainer.", 1);
    }
  }
}
"""[1:-1],
    "print-form-pipe": r"""
// "PRINT FORM" BUTTON (pipe-format form).
// What this does: prints only once the QR codes exist and still carry the current records, every code needed is on its
// page and none is left over. The hidden box may keep, change or drop the new lines between records (the records
// hold none themselves), so the comparison, and the count of codes, use the current records, not the stored text.
var qrBox = this.getField("__qr");
var recordsNow = typeof lcPipeText == "function" ? lcPipeText(this) : "";   // what the codes should say, with today's answers
var sameAnswers = false;      // do the codes on the form carry these records?
var codesProblem = "";        // what is wrong with the codes on the pages ("" = nothing)
try { sameAnswers = String(qrBox.value).replace(/[\r\n]/g, "") == recordsNow.replace(/[\r\n]/g, ""); } catch (e) {}
try { codesProblem = lcQrCheck(this, recordsNow); } catch (e) { codesProblem = String(e); }
if (!/\S/.test(qrBox.value)) {
  app.alert("Please press Generate QR Code first, so the printed form carries the QR code.", 1);
} else if (!sameAnswers) {
  app.alert("Your answers have changed since the QR code was generated. Please press Generate QR Code again, then Print Form.", 1);
} else if (codesProblem) {
  app.alert("The QR codes in the form do not match your answers (" + codesProblem + "). Please press Generate QR Code again, then Print Form.", 1);
} else {
  this.print(true, 0, lcLastPage(this, recordsNow), false, true);   // the form up to the last QR code page in use
}
"""[1:-1],
    "before-save": r"""
// BEFORE SAVING OR PRINTING.
// What this does: shows the same list as Check form, but only if something is missing or wrong. It adds a warning when QR
// codes were generated and the pages no longer hold them all (lcQrCheck). It only warns: it does not stop the save or print.
if (typeof lcRules != "function") {
  app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was built from damaged files: build it again.", 1);
} else {
  var missing = lcRules(this);         // labels of the mandatory questions that are blank (it also has .bad and .first)
  var wrong = missing.bad || [];       // "<question>: <what is wrong>" for each wrong answer
  var messages = [];                   // the parts of the message to show

  // "- first\n- second ..." with at most 15 lines; if there are more: "- ... and 3 more".
  var bulletList = function (items) {
    var text = "- " + items.slice(0, 15).join("\n- ");
    if (items.length > 15) text += "\n- ... and " + (items.length - 15) + " more";
    return text;
  };

  if (missing.length) {
    messages.push(missing.length + " mandatory question" + (missing.length > 1 ? "s are" : " is") + " still blank:\n" + bulletList(missing));
  }
  if (wrong.length) {
    messages.push(wrong.length + " answer" + (wrong.length > 1 ? "s need" : " needs") + " correcting:\n" + bulletList(wrong));
  }

  // If QR codes were generated: are they all still on the pages?
  try {
    var qrBox = this.getField("__qr");
    var codesProblem = qrBox && /\S/.test(qrBox.value) && typeof lcQrCheck == "function" ? lcQrCheck(this, qrBox.value) : "";
    if (codesProblem) messages.push("The QR codes in the form are not complete (" + codesProblem + "). Press Generate QR Code again.");
  } catch (e) {}

  // Shown once: an event that fires again within 3 seconds of the warning closing is a repeat, not a new save / print.
  if (messages.length && new Date().getTime() - lcWarnedAt > 3000) {
    app.alert((event.name == "WillPrint" ? "Before printing: " : "Before saving: ") + "this form is not ready to send. The boxes concerned are outlined in red.\n\n" + messages.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
    lcWarnedAt = new Date().getTime();
  }
}
"""[1:-1],
}
