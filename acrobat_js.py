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
// THE QR CODES' TEXT. lcPayload(doc) returns every answered question as JSON:
//   {"form": "LC-01", "version": "1.0", "saved": "...", "complete": true, "data": {field id: answer, ...}}
// Tick boxes become true; "tick any" questions become lists of the ticked options. One QR code holds 2,300 bytes of it
// (LC_QR_CAP); longer answers take as many codes as they need, at most 16 (LC_QR_MAX, the most that "structured append"
// allows; lcDrawQr splits the text). The text is padded with spaces to fill the codes it needs: 2,300, 4,600 ... 36,800
// bytes. Only beyond 16 codes are the long paragraphs shortened (and listed in "truncated"). __GROUPS__, __LONG__,
// __FORM__ and __VERSION__ are filled in by document_script (step 2).
var LC_QR_CAP = 2300, LC_QR_MAX = 16;
// The text as UTF-8 bytes, one character per byte (what goes into the codes).
function lcBytes(s) { return unescape(encodeURIComponent(s)); }
// How many codes this text needs (0 for no text).
function lcCodes(s) { return s ? Math.ceil(lcBytes(s).length / LC_QR_CAP) : 0; }
function lcPayload(d) {
var G = {__GROUPS__}, LONG = __LONG__, CAP = LC_QR_CAP, BUDGET = LC_QR_MAX * LC_QR_CAP;
var data = {}, i, n, f, k, v, g, m, out, cut = [], ok = true, t = new Date();
for (i = 0; i < d.numFields; i++) {
  n = d.getNthFieldName(i); if (/^__/.test(n) || /__list$/.test(n) || /__qrx_/.test(n)) continue;
  f = d.getField(n); if (!f || f.type == "button" || f.type == "signature") continue;
  g = /^(.+)__(\d+)$/.exec(n);
  if (g && G[g[1]]) { if (f.value != "Off") { if (!data[g[1]]) data[g[1]] = []; data[g[1]].push(G[g[1]][+g[2]]); } continue; }
  if (f.type == "checkbox") { if (f.value != "Off") data[n] = true; continue; }
  v = f.type == "radiobutton" ? (f.value == "Off" ? "" : String(f.value)) : String(f.valueAsString).replace(/^\s+|\s+$/g, "");
  if (v !== "") data[n] = v;
}
if (typeof lcRules == "function") { m = lcRules(d); ok = !m.length && !(m.bad || []).length; }
function pad(x) { return ("0" + x).slice(-2); }
out = {"form": __FORM__, "version": __VERSION__, "saved": t.getFullYear() + "-" + pad(t.getMonth() + 1) + "-" + pad(t.getDate()) + "T" + pad(t.getHours()) + ":" + pad(t.getMinutes()), "complete": ok, "data": data};
// 16 codes hold 36,800 bytes: only if the answers are longer still, shorten the long paragraphs (in order) and say so.
for (i = 0; i < LONG.length && lcBytes(JSON.stringify(out)).length > BUDGET; i++) {
  k = LONG[i]; if (!data[k]) continue;
  cut.push(k); out.truncated = cut;
  v = lcBytes(JSON.stringify(out)).length - BUDGET + 3;
  data[k] = v < data[k].length ? data[k].slice(0, data[k].length - v) + "..." : "...";
}
// Padded with spaces to fill the codes it needs (2,300 bytes each).
v = JSON.stringify(out); n = lcBytes(v).length; m = Math.max(1, Math.ceil(n / CAP)) * CAP - (n - v.length);
while (v.length < m) v += " ";
return v;
}
// THE QR CODE ENCODER AND DRAWING (standard QR code, no library needed).
// lcQrMatrix(bytes, part) returns the 177 x 177 grid of a version 40 QR code (true = dark square). bytes is the
// text as UTF-8 bytes (one character per byte). part is null for a single code, or [index, total, parity] for
// one of several codes ("structured append", part of the QR standard: each code says it is code k of n, n at
// most 16, so a scanner that supports it joins them; any other scanner reads each code's text, and the texts are
// joined in order). Version 40, error correction M, byte mode, mask 0; at most 2,329 bytes per code.
function lcQrMatrix(s, part) {
  var N = 177, i, j, x, y, m = [], f = [], bytes = [];
  for (i = 0; i < s.length; i++) bytes.push(s.charCodeAt(i) & 255);
  for (y = 0; y < N; y++) { m.push([]); f.push([]); for (x = 0; x < N; x++) { m[y].push(false); f[y].push(false); } }
  function set(x, y, dark) { m[y][x] = dark; f[y][x] = true; }
  function mul(a, b) { var z = 0; for (var k = 7; k >= 0; k--) { z = (z << 1) ^ ((z >>> 7) * 0x11D); z ^= ((b >>> k) & 1) * a; } return z; }
  // Function patterns: timing, finders, alignment, format area, version, dark module.
  for (i = 0; i < N; i++) { set(6, i, i % 2 == 0); set(i, 6, i % 2 == 0); }
  function finder(cx, cy) { for (var dy = -4; dy <= 4; dy++) for (var dx = -4; dx <= 4; dx++) {
    var d = Math.max(Math.abs(dx), Math.abs(dy)), xx = cx + dx, yy = cy + dy;
    if (xx >= 0 && xx < N && yy >= 0 && yy < N) set(xx, yy, d != 2 && d != 4); } }
  finder(3, 3); finder(N - 4, 3); finder(3, N - 4);
  var A = [6, 30, 58, 86, 114, 142, 170];
  for (i = 0; i < A.length; i++) for (j = 0; j < A.length; j++) {
    if ((i == 0 && j == 0) || (i == 0 && j == A.length - 1) || (i == A.length - 1 && j == 0)) continue;
    for (var dy = -2; dy <= 2; dy++) for (var dx = -2; dx <= 2; dx++) set(A[i] + dx, A[j] + dy, Math.max(Math.abs(dx), Math.abs(dy)) != 1);
  }
  var rem = 0, fmt; for (i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
  fmt = ((0 << 10) | rem) ^ 0x5412; // error correction M (00), mask 0
  function bit(v, k) { return ((v >>> k) & 1) != 0; }
  for (i = 0; i <= 5; i++) set(8, i, bit(fmt, i));
  set(8, 7, bit(fmt, 6)); set(8, 8, bit(fmt, 7)); set(7, 8, bit(fmt, 8));
  for (i = 9; i < 15; i++) set(14 - i, 8, bit(fmt, i));
  for (i = 0; i < 8; i++) set(N - 1 - i, 8, bit(fmt, i));
  for (i = 8; i < 15; i++) set(8, N - 15 + i, bit(fmt, i));
  set(8, N - 8, true);
  rem = 40; for (i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1F25);
  var ver = (40 << 12) | rem;
  for (i = 0; i < 18; i++) { var a = N - 11 + i % 3, b = Math.floor(i / 3); set(a, b, bit(ver, i)); set(b, a, bit(ver, i)); }
  // Data: (for one of several codes: mode 0011, its index, the total - 1, the parity of all the text), then mode
  // 0100, 16-bit length, the bytes, terminator, padding to 2,334 data codewords.
  var bits = [], cap = 2334 * 8;
  function put(v, n) { for (var k = n - 1; k >= 0; k--) bits.push((v >>> k) & 1); }
  if (part) { put(3, 4); put(part[0], 4); put(part[1] - 1, 4); put(part[2], 8); }
  put(4, 4); put(bytes.length, 16); for (i = 0; i < bytes.length; i++) put(bytes[i], 8);
  if (bits.length > cap) throw new Error("too much text for one QR code (" + bytes.length + " bytes)");
  put(0, Math.min(4, cap - bits.length)); while (bits.length % 8) bits.push(0);
  var data = []; for (i = 0; i < bits.length; i += 8) { var v = 0; for (j = 0; j < 8; j++) v = (v << 1) | bits[i + j]; data.push(v); }
  for (i = 0; data.length < 2334; i++) data.push(i % 2 ? 0x11 : 0xEC);
  // Reed-Solomon: 49 blocks (18 of 47 + 31 of 48 data codewords), 28 error-correction codewords each.
  var div = [], root = 1; for (i = 0; i < 27; i++) div.push(0); div.push(1);
  for (i = 0; i < 28; i++) { for (j = 0; j < 28; j++) { div[j] = mul(div[j], root); if (j + 1 < 28) div[j] ^= div[j + 1]; } root = mul(root, 2); }
  var blocks = [], k = 0;
  for (i = 0; i < 49; i++) {
    var len = i < 18 ? 47 : 48, dat = data.slice(k, k + len), ecc = []; k += len;
    for (j = 0; j < 28; j++) ecc.push(0);
    for (j = 0; j < dat.length; j++) { var fct = dat[j] ^ ecc.shift(); ecc.push(0); for (var t = 0; t < 28; t++) ecc[t] ^= mul(div[t], fct); }
    if (i < 18) dat.push(-1);
    blocks.push(dat.concat(ecc));
  }
  var all = [];
  for (i = 0; i < blocks[0].length; i++) for (j = 0; j < 49; j++) if (blocks[j][i] != -1) all.push(blocks[j][i]);
  // Place the codewords in the zigzag, then mask 0 ((x + y) even flips).
  var n = 0;
  for (var right = N - 1; right >= 1; right -= 2) {
    if (right == 6) right = 5;
    for (var vert = 0; vert < N; vert++) for (j = 0; j < 2; j++) {
      x = right - j; var up = ((right + 1) & 2) == 0; y = up ? N - 1 - vert : vert;
      if (!f[y][x] && n < all.length * 8) { m[y][x] = ((all[n >>> 3] >>> (7 - (n & 7))) & 1) != 0; n++; }
    }
  }
  for (y = 0; y < N; y++) for (x = 0; x < N; x++) if (!f[y][x] && (x + y) % 2 == 0) m[y][x] = !m[y][x];
  return m;
}
// THE PAGES THE CODES GO ON. Codes 1 and 2 sit on the form's QR code page (rows "__qr1_0" ... "__qr1_176", "__qr2_..."),
// each row a read-only text box holding the letter "n" in the ZapfDingbats font (which prints as a black square) for each
// dark square. Codes 3 to 16 go two to a page on extra pages, which exist only while needed: lcDrawQr copies the hidden page
// template "qrx" (rows "__qrx_1_0" ... "__qrx_2_176") after the last page with Template.spawn, and deletes the pages it no
// longer needs (when the viewer refuses to delete one, the page stays, empty and marked "not used", and is left out of
// printing: lcLastPage). A spawned page's fields are renamed by the viewer (bRename: true) but still end in the template's
// name, so lcExtra finds them by that ending. Don't write "getField(" for those fields: build_all.py rewrites it
// to add the form's code in the joined PDF; d["getField"](name) is left alone, and the names found are already complete.
// lcExtra(doc) returns the spawned pages' field-name prefixes, in page order: [{p: prefix, page: page number}].
function lcExtra(d) {
  var out = [], i, nm, m, f, q = d.getField("__qr"), first = q && typeof q.page == "number" ? q.page : -1;
  for (i = 0; i < d.numFields; i++) {
    nm = d.getNthFieldName(i); m = /^(.*)__qrx_1_0$/.exec(nm);
    if (!m || /^([A-Z]+\.)?$/.test(m[1])) continue;     // not a row, or the template's own row ("" or the form's code)
    f = d["getField"](nm);
    if (f && typeof f.page == "number" && f.page > first && f.page < d.numPages) out.push({p: m[1], page: f.page});
  }
  out.sort(function (a, b) { return a.page - b.page; });
  return out;
}
// Code j (0 = first) as a function: x -> the field "<row>" or "label" or "frame" of its slot.
function lcSlot(d, pg, j) {
  var t = j < 2 ? "__qr" + (j + 1) : "__qrx_" + ((j - 2) % 2 + 1), p = j < 2 ? null : pg[(j - 2) >> 1] && pg[(j - 2) >> 1].p;
  return function (x) { return p === null ? d.getField(t + "_" + x) : p === undefined ? null : d["getField"](p + t + "_" + x); };
}
// Extra pages that n codes need.
function lcPagesFor(n) { return n > 2 ? Math.ceil((n - 2) / 2) : 0; }
// The last page of the form as printed: the QR code page, plus the extra pages the codes of this text use.
function lcLastPage(d, text) { return d.getField("__qr").page + lcPagesFor(lcCodes(text)); }
// "" when the codes on the pages are exactly those of this text (every code in use has its first row drawn, every other
// slot is empty); otherwise what is wrong. Used before printing.
function lcQrCheck(d, text) {
  var n = lcCodes(text), pg = lcExtra(d), j, f;
  if (pg.length < lcPagesFor(n)) return "the extra QR code pages are missing";
  for (j = 0; j < 2 + 2 * pg.length || j < n; j++) {
    f = lcSlot(d, pg, j)("0");
    if (!f) return "QR code " + (j + 1) + " is missing";
    if ((f.value !== "") != (j < n)) return j < n ? "QR code " + (j + 1) + " is blank" : "QR code " + (j + 1) + " is left over";
  }
  return "";
}
// lcDrawQr(doc, text) draws text as one QR code, or as many as it needs (at most 16, one per 2,300 bytes), and returns how
// many (0 for ""; lcDrawQr(doc, "") clears everything and removes the extra pages). The text is cut into consecutive
// equal slices; each code carries the structured-append header (its index, the total, the parity of the whole text), so a
// scanner that supports it joins them, and any other scanner reads each slice and the slices are joined in order. The
// frames, and the labels "QR code 1 of 3 (scan all 3 codes)", show only for codes in use.
function lcDrawQr(d, text) {
  var s = lcBytes(text), n = lcCodes(text), size = n ? Math.ceil(s.length / n) : 0, codes = [], parity = 0, i, k, j, y, x, row, pg, f, g, put, calc = d.calculate, more;
  if (n > LC_QR_MAX) throw new Error("the answers are too long for " + LC_QR_MAX + " QR codes (" + s.length + " bytes, at most " + LC_QR_MAX * LC_QR_CAP + ")");
  for (i = 0; i < s.length; i++) parity ^= s.charCodeAt(i) & 255;
  for (k = 0; k < n; k++) codes.push(lcQrMatrix(s.slice(k * size, (k + 1) * size), n > 1 ? [k, n, parity] : null));   // all made before anything is touched
  d.calculate = false; // thousands of rows: don't re-run the checks after each one
  try {
    pg = lcExtra(d);
    for (more = lcPagesFor(n); pg.length < more; ) {                // add the pages that are needed
      d.getTemplate("qrx").spawn({nPage: d.numPages, bRename: true, bOverlay: false});
      g = lcExtra(d); if (g.length <= pg.length) throw new Error("the viewer did not add the page for QR code " + (2 * pg.length + 3));
      pg = g;
    }
    while (pg.length > more) {                                      // take away the pages that are not
      try { d.deletePages(pg[pg.length - 1].page); } catch (e) { break; }
      g = lcExtra(d); if (g.length >= pg.length) break;
      pg = g;
    }
    for (j = 0; j < 2 + 2 * pg.length; j++) {                       // every slot: its code, or empty
      put = lcSlot(d, pg, j);
      for (y = 0; y < 177; y++) { row = ""; if (codes[j]) for (x = 0; x < 177; x++) row += codes[j][y][x] ? "n" : " ";
        put(y).value = row; }
      if (f = put("label")) f.value = !codes[j] ? (j % 2 == 0 && j >= 2 + 2 * more ? "(this page is not used)" : "") : n < 2 ? "" : "QR code " + (j + 1) + " of " + n + (j == 0 ? (n == 2 ? " (scan both codes)" : " (scan all " + n + " codes)") : "");
      if (f = put("frame")) f.display = codes[j] ? display.visible : display.hidden;
    }
  } finally { d.calculate = calc; }
  return n;
}
"""[1:-1]

# THE PIPE-FORMAT TEXT (only for a form file with FORM["qrFormat"] == "pipe", e.g. forms/lc_pipe_form.py). pdf_writer.py
# appends this block to the document script of such a form and fills in __PIPE__ (the position table from the form file)
# and __GROUPS__. Other forms do not get it, so their PDFs are unchanged. It replaces lcPayload for that form: the
# "Generate QR Code" button (BUTTON_JS "generate-qr-pipe") puts lcPipeText(doc) into the ordinary QR code path (lcDrawQr, up to 16 codes)
# instead of the JSON text. lcPipeText is the 4 records of the old smart form's barcode, one after the other, with a newline
# between records. Nothing here touches the QR encoder or its drawing.
PIPE_JS = r"""
// THE PIPE-DELIMITED RECORDS (the old smart form's barcode text), built from the form file's position table.
// lcPipe = [record 1 entries, record 2 entries, ...]. Each entry describes one position (the old "1_01" ... "4_03"):
//   {"c": text}                         a fixed text
//   {"id": q}                           the answer as typed; also "max": cut to this many characters, "as": "amount" or "date",
//                                       "codes": {answer: code} (an answer not listed gives nothing)
//   {"lines": [q, ...]}                 each non-blank answer in [ ]
//   {"join": [q, ...]}                  the non-blank answers, one space between
//   {"tpl": {"when": tick box, "parts": [...]}}   a sentence: text with {q} answers, ["map", q, {answer: text}],
//                                       ["list", q, separator, [[option, text], ...]], ["if", q, text if answered, else text]
//   {"qty": {"on", "o", "c", "head", "tail"}}      "head IN n ORIGINALS AND m COPIES<tail>."
// Any entry may also have "if": [q, [answers]] (blank unless the answer is one of these), "d" (used when the result is
// blank), "chop": true (wrap in lines, see lcPipeChop). Every position ends with "|".
var lcPipe = __PIPE__;
// The answers by question id: text as typed (not trimmed), a tick box "true" (absent when not ticked), "tick any" a list.
// The records' own characters | [ ] { } and line breaks must never come from an answer (the keystroke filter refuses them, but a
// value set by FDF import, autofill or a pasted newline skips it): they become a space. Only the paragraph boxes (the entries
// with "chop" on one answer) keep Enter, which the records write as {}: any line break there is one Enter (CR).
var lcPipeLong = null;
function lcPipeAnswers(d) {
var G = {__GROUPS__}, A = {}, i, j, n, f, g, v, e;
if (!lcPipeLong) {
  lcPipeLong = {};
  for (i = 0; i < lcPipe.length; i++) for (j = 0; j < lcPipe[i].length; j++) {
    e = lcPipe[i][j]; if (!e.chop) continue;
    if (e.id) lcPipeLong[e.id] = 1;
    for (g = 0; e.join && g < e.join.length; g++) lcPipeLong[e.join[g]] = 1;
  }
}
for (i = 0; i < d.numFields; i++) {
  n = d.getNthFieldName(i); if (/^__/.test(n) || /__list$/.test(n)) continue;
  f = d.getField(n); if (!f || f.type == "button" || f.type == "signature") continue;
  g = /^(.+)__(\d+)$/.exec(n);
  if (g && G[g[1]]) { if (f.value != "Off") { if (!A[g[1]]) A[g[1]] = []; A[g[1]].push(G[g[1]][+g[2]]); } continue; }
  if (f.type == "checkbox") { if (f.value != "Off") A[n] = "true"; continue; }
  v = f.type == "radiobutton" ? (f.value == "Off" ? "" : String(f.value)) : String(f.valueAsString);
  v = lcPipeLong[n] ? v.replace(/\r\n|\n/g, "\r").replace(/[|\[\]{}]/g, " ") : v.replace(/[|\[\]{}\r\n]/g, " ");
  if (v !== "") A[n] = v;
}
return A;
}
// Long text in lines, as the old form wrote it: leading and trailing blanks and Enter dropped; up to 65 characters as is
// (Enter becomes {}); longer: cut at spaces into lines padded with spaces to 65 characters, each followed by {} (a word longer
// than 65 is cut at 65; with Enter, each paragraph is cut on its own). Returns "" for nothing.
function lcPipeChop(s) {
var MAX = 65;
function trim(x) { return x.replace(/^\s+/, "").replace(/\s+$/, ""); }
function lr(x) { return x.replace(/^\r+/, "").replace(/\r+$/, ""); }
function cut(x) { var r = ""; while (x.length > 0) { if (x.length > MAX) { r += x.slice(0, MAX) + "{}"; x = x.slice(MAX); } else { r += x; x = ""; } } return r; }
function words(x) {   // no Enter inside: fill lines word by word
  var w = x.split(" "), fin = [], res = "", i, r = "";
  for (i = 0; i < w.length; i++) if (w[i].length > MAX) w[i] = cut(w[i]);
  for (i = 0; i < w.length; i++) {
    if ((res + w[i]).length > MAX) {
      if (w[i].length <= MAX) { i--; while (res.length < MAX) res += " "; fin.push(res + "{}"); res = ""; }
      else { if (res !== "") { while (res.length < MAX) res += " "; res += "{}"; } fin.push(res + w[i] + " "); res = ""; }
    } else res += w[i] + " ";
  }
  if (res !== "") fin.push(res);
  for (i = 0; i < fin.length; i++) r += (i == fin.length - 1 && fin[i].slice(-1) == " ") ? fin[i].slice(0, fin[i].length - 1) : fin[i];
  return r;
}
function paragraphs(x, byWords) {   // Enter inside: each paragraph on its own (byWords: the text has spaces; no trimming then)
  var a = x.split("\r"), r = "", i;
  for (i = 0; i < a.length; i++) {
    if (byWords) { if (a[i].length > MAX) a[i] = words(a[i]); }
    else a[i] = cut(trim(a[i]));
    r += a[i] + (i < a.length - 1 ? "{}" : "");
  }
  return r;
}
if (s == null || s.length <= 0) return "";
s = trim(lr(s)); if (s.length <= 0) return "";
if (s.length <= MAX) return trim(s.replace(/\r/g, "{}"));
if (s.indexOf(" ") <= 0) return s.indexOf("\r") <= 0 ? cut(s) : paragraphs(s, false);
return s.indexOf("\r") <= 0 ? words(s) : paragraphs(s, true);
}
// One position's text.
function lcPipeValue(e, A) {
function a(id) { var x = A[id]; return typeof x == "string" ? x : ""; }
function has(list, x) { for (var i = 0; i < list.length; i++) if (list[i] == x) return true; return false; }
function fill(t) { return t.replace(/\{(\w+)\}/g, function (m, id) { return a(id); }); }
var v = "", i, x, p, o, c, ph, tail, out, picks, q, m;
if (!e["if"] || has(e["if"][1], a(e["if"][0]))) {
  if (e.c != null) v = e.c;
  else if (e.lines) { for (i = 0; i < e.lines.length; i++) if (a(e.lines[i]) !== "") v += "[" + a(e.lines[i]) + "]"; }
  else if (e.join) { x = []; for (i = 0; i < e.join.length; i++) if (a(e.join[i]) !== "") x.push(a(e.join[i])); v = x.join(" "); }
  else if (e.tpl) {
    q = e.tpl; out = ""; if (a(q.when) == "true") for (i = 0; i < q.parts.length; i++) {
      p = q.parts[i];
      if (typeof p == "string") out += fill(p);
      else if (p[0] == "map") out += fill(p[2].hasOwnProperty(a(p[1])) ? p[2][a(p[1])] : "");
      else if (p[0] == "if") out += fill(a(p[1]) !== "" ? p[2] : p[3]);
      else if (p[0] == "list") {   // ticked options in the table's order; none ticked: no sentence at all
        picks = []; x = A[p[1]] || [];
        for (m = 0; m < p[3].length; m++) if (has(x, p[3][m][0])) picks.push(p[3][m][1]);
        if (!picks.length) { out = ""; break; }
        out += picks.join(p[2]);
      }
    }
    v = out;
  }
  else if (e.qty) {
    q = e.qty; o = a(q.o); c = a(q.c);
    if (a(q.on) == "true" && (o !== "" || c !== "")) {
      tail = q.tail && a(q.tail[0]) !== "" ? fill(q.tail[1]) : "";
      if (o == "0" && c == "0") ph = "";
      else if (o === "" || o == "0") ph = " IN " + c + " " + (c == "1" ? "COPY" : "COPIES");
      else if (c === "" || c == "0") ph = " IN " + o + " " + (o == "1" ? "ORIGINAL" : "ORIGINALS");
      else ph = " IN " + o + " " + (o == "1" ? "ORIGINAL" : "ORIGINALS") + " AND " + c + " " + (c == "1" ? "COPY" : "COPIES");
      if (ph !== "" || tail !== "") v = q.head + ph + tail + ".";
    }
  }
  else if (e.id) {
    v = a(e.id);
    if (e.max != null) v = v.slice(0, e.max);
    if (e.as == "amount") { v = v.replace(/,/g, ""); if (/^\d+$/.test(v)) v += ".00"; else if (/^\d+\.\d$/.test(v)) v += "0"; }
    if (e.as == "date") { x = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(v); v = x ? x[3] + "-" + x[2] + "-" + x[1] : ""; }
    if (e.codes) v = e.codes.hasOwnProperty(v) ? e.codes[v] : "";
  }
  if (e.chop) v = lcPipeChop(v);
}
if (v === "" && e.d != null) v = e.d;
return v;
}
// The records, as an array of text. A = the answers (default: read from the PDF).
function lcPipeRecords(d, A) {
var R = [], i, j, r;
A = A || lcPipeAnswers(d);
for (i = 0; i < lcPipe.length; i++) { r = ""; for (j = 0; j < lcPipe[i].length; j++) r += lcPipeValue(lcPipe[i][j], A) + "|"; R.push(r); }
return R;
}
// What goes into the QR code: the records, a newline between them.
function lcPipeText(d) { return lcPipeRecords(d).join("\n"); }
"""[1:-1]

# THE BUTTON AND EVENT SCRIPTS. Each section below, after its "// ==== name ====" line, is stored in the PDF
# as one action. The lines before the first marker (this header) are not stored.
#   check-form    the "Check form" button (top right of every page)
#   reset-form    the "Reset form" button (top right of every page)
#   generate-qr   the "Generate QR Code" button (QR page)
#   print-form    the "Print Form" button (QR page)
#   before-save   runs before the form is saved or printed
# They call the functions in DOCUMENT_JS (lcRules, lcPayload, lcDrawQr, lcDates).
BUTTON_JS = {
    "check-form": r"""
// "CHECK FORM" BUTTON: lists what is missing or wrong (at most 15 of each) and puts the cursor on the first
// problem; otherwise says the form is ready.
if (typeof lcRules != "function") app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was built from damaged files: build it again.", 1);
else {
var m = lcRules(this), b = m.bad || [], t = [];
var list = function (a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("This form is not ready to send. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
  var g = m.first && this.getField(m.first); if (g) g.setFocus(); }
else app.alert("All mandatory questions are answered and every answer is in the right format. You can save the form and send it.", 3);
}
"""[1:-1],
    "reset-form": r"""
// "RESET FORM" BUTTON: asks first, then sets every answer back to how the form started, and re-checks.
if (app.alert("Are you sure you want to reset the form? All your answers will be cleared.", 2, 2) == 4) {
this.resetForm(); if (typeof lcDrawQr == "function") try { lcDrawQr(this, ""); } catch (e) {} if (typeof lcDates == "function") lcDates(this); if (typeof lcRules == "function") lcRules(this); }
"""[1:-1],
    "generate-qr": r"""
// "GENERATE QR CODE" BUTTON: refuses while anything is missing or wrong; otherwise makes the QR code from the
// answers (lcPayload, lcDrawQr): one code, or as many as the answers need (at most 16; codes 3 and up go on extra pages
// after the QR code page, two to a page). Then it goes to the QR code page.
if (typeof lcRules != "function") app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was built from damaged files: build it again.", 1);
else {
var m = lcRules(this), b = m.bad || [], t = [];
var list = function (a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("The QR code cannot be generated yet. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them, then press Generate QR Code again.", 1);
  var g = m.first && this.getField(m.first); if (g) g.setFocus(); }
else { try { var q = this.getField("__qr"); q.value = lcPayload(this); var n = lcDrawQr(this, q.value), cut = [];
  try { this.pageNum = q.page; } catch (e) {}   // a viewer may refuse to change page inside a click that added pages: the codes are drawn all the same
  try { cut = JSON.parse(q.value).truncated || []; } catch (e) {}
  if (n == 1) app.alert("The QR code has been generated from your answers (" + q.value.length + " characters). Press Print Form to print the form with the QR code.", 3);
  else app.alert("Your answers (" + q.value.length + " characters) need " + n + " QR codes, so " + n + " codes have been generated: " + (n > 2 ? "two on the QR code page and the rest, two to a page, on the " + lcPagesFor(n) + " page" + (lcPagesFor(n) > 1 ? "s" : "") + " after it" : "one under the other") + ". The Bank scans all " + n + " codes. Press Print Form to print the form with the QR codes." +
    (cut.length ? "\n\nEven " + n + " codes are too small for everything you typed, so these long answers were shortened in the QR codes (the form itself is unchanged): " + cut.join(", ") + "." : ""), cut.length ? 1 : 3); }
  catch (e) { app.alert("The QR code could not be generated: " + e + "\nPlease send this message to the form's maintainer.", 1); } }
}
"""[1:-1],
    "print-form": r"""
// "PRINT FORM" BUTTON: prints only once the QR code exists and still matches the current answers, so the
// printed codes always carry the answers on the paper: every code needed is on its page, none is left over, and the
// pages after the last code in use are not printed.
var q = this.getField("__qr"), now = typeof lcPayload == "function" ? lcPayload(this) : "", same = false, bad = "";
try { same = JSON.stringify(JSON.parse(q.value).data) == JSON.stringify(JSON.parse(now).data); } catch (e) {}
try { bad = lcQrCheck(this, q.value); } catch (e) { bad = String(e); }
if (!/\S/.test(q.value)) app.alert("Please press Generate QR Code first, so the printed form carries the QR code.", 1);
else if (!same) app.alert("Your answers have changed since the QR code was generated. Please press Generate QR Code again, then Print Form.", 1);
else if (bad) app.alert("The QR codes in the form do not match your answers (" + bad + "). Please press Generate QR Code again, then Print Form.", 1);
else this.print(true, 0, lcLastPage(this, q.value), false, true);   // the form to the last QR code page in use
"""[1:-1],
    # The pipe-format form's versions (FORM["qrFormat"] == "pipe"): the same buttons, with lcPipeText in place of lcPayload.
    "generate-qr-pipe": r"""
// "GENERATE QR CODE" BUTTON (pipe-format form): as the ordinary one, but the QR codes hold the old smart form's 4 pipe-delimited
// records (lcPipeText, a newline between records) instead of the JSON. lcDrawQr does not pad or change the text; as many codes
// as the text needs (at most 16), the same pages as the ordinary form.
if (typeof lcRules != "function") app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was changed after it was built: ask the form's maintainer.", 1);
else {
var m = lcRules(this), b = m.bad || [], t = [];
var list = function (a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
if (t.length) { app.alert("The QR code cannot be generated yet. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them, then press Generate QR Code again.", 1);
  var g = m.first && this.getField(m.first); if (g) g.setFocus(); }
else { try { var q = this.getField("__qr"), x = lcPipeText(this); q.value = x; var n = lcDrawQr(this, x);
  try { this.pageNum = q.page; } catch (e) {}   // a viewer may refuse to change page inside a click that added pages: the codes are drawn all the same
  if (n == 1) app.alert("The QR code has been generated from your answers (" + x.length + " characters). Press Print Form to print the form with the QR code.", 3);
  else app.alert("Your answers (" + x.length + " characters) need " + n + " QR codes, so " + n + " codes have been generated" + (n > 2 ? ": two on the QR code page and the rest, two to a page, on the " + lcPagesFor(n) + " page" + (lcPagesFor(n) > 1 ? "s" : "") + " after it" : ", one under the other") + ". The Bank scans all " + n + " codes. Press Print Form to print the form with the QR codes.", 3); }
  catch (e) { app.alert("The QR code could not be generated: " + e + "\nPlease send this message to the form's maintainer.", 1); } }
}
"""[1:-1],
    "print-form-pipe": r"""
// "PRINT FORM" BUTTON (pipe-format form): prints only once the QR codes exist and still carry the current records, every code
// needed is on its page and none is left over. The hidden box may keep, change or drop the newlines between records (the records
// hold none), so the comparison, and the code count, use the current records, not the stored text.
var q = this.getField("__qr"), now = typeof lcPipeText == "function" ? lcPipeText(this) : "", same = false, bad = "";
try { same = String(q.value).replace(/[\r\n]/g, "") == now.replace(/[\r\n]/g, ""); } catch (e) {}
try { bad = lcQrCheck(this, now); } catch (e) { bad = String(e); }
if (!/\S/.test(q.value)) app.alert("Please press Generate QR Code first, so the printed form carries the QR code.", 1);
else if (!same) app.alert("Your answers have changed since the QR code was generated. Please press Generate QR Code again, then Print Form.", 1);
else if (bad) app.alert("The QR codes in the form do not match your answers (" + bad + "). Please press Generate QR Code again, then Print Form.", 1);
else this.print(true, 0, lcLastPage(this, now), false, true);   // the form to the last QR code page in use
"""[1:-1],
    "before-save": r"""
// BEFORE SAVING OR PRINTING: the same list as Check form, shown only if something is missing or wrong, plus a warning
// when QR codes were generated and the pages no longer hold them all (lcQrCheck). It warns but doesn't stop the save or print.
if (typeof lcRules != "function") app.alert("The form's checks did not start, so nothing has been checked yet. Open the form in Adobe Acrobat or Acrobat Reader and allow JavaScript (the yellow bar's Options, or Preferences > JavaScript > Enable Acrobat JavaScript), then close and reopen the form. If it still happens, the form was built from damaged files: build it again.", 1);
else {
var m = lcRules(this), b = m.bad || [], t = [];
var list = function (a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
if (m.length) t.push(m.length + " mandatory question" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + list(m));
if (b.length) t.push(b.length + " answer" + (b.length > 1 ? "s need" : " needs") + " correcting:\n" + list(b));
try { var qf = this.getField("__qr"), qb = qf && /\S/.test(qf.value) && typeof lcQrCheck == "function" ? lcQrCheck(this, qf.value) : ""; if (qb) t.push("The QR codes in the form are not complete (" + qb + "). Press Generate QR Code again."); } catch (e) {}
// Shown once: an event that fires again within 3 seconds of the warning closing is a repeat, not a new save / print.
if (t.length && new Date().getTime() - lcWarnedAt > 3000) {
  app.alert((event.name == "WillPrint" ? "Before printing: " : "Before saving: ") + "this form is not ready to send. The boxes concerned are outlined in red.\n\n" + t.join("\n\n") + "\n\nPlease correct them before you send the form.", 1);
  lcWarnedAt = new Date().getTime(); }

}
"""[1:-1],
}
