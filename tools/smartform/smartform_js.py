"""The JavaScript stored in the trade forms PDF (Acrobat runs it). Plain ASCII only.

DOCUMENT_JS is the one document-level script ("smRules"): the rules engine for all 13 forms, the keystroke filters,
the QR code text and the QR encoder (lcQrMatrix, the same as lc-form's acrobat_js.py). __MODEL__ is filled in by
build_smartform.py with every form's fields and rules (see convert.py, rules_for, for what each rule means).
BUTTON_JS holds the buttons' scripts; __FORM__ is the form they belong to.
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from acrobat_js import DOCUMENT_JS as LC_JS   # noqa: E402  reuse lc-form's QR encoder

QR_MATRIX = LC_JS[LC_JS.index("function lcQrMatrix("):LC_JS.index("// lcDrawQr(doc, text)")]

DOCUMENT_JS = r"""
// THE TRADE FORMS RULES ENGINE (runs inside Acrobat). SM holds, for each form, its fields and rules:
//   k kind (text long date number select check radio), l label, n PDF field name, p hidden part it belongs to,
//   r rules: always, req / nreq / open / lock / show / hide = [[trigger id, [values]]] ("*" = any answer,
//   "on" = ticked), locked_at_open; parts: pictures (labels and lines) that show only when their rule holds.
// A question only counts when it applies: shown and unlocked, and its trigger applies too.
var SM = __MODEL__;
function smForm(name) { var c = String(name).split("_")[0]; return SM.byCode[c]; }
function smFld(d, F, id) { var m = SM.forms[F].f[id]; return m ? d.getField(m.n) : null; }
function smVal(d, F, id) {
  var m = SM.forms[F].f[id], f = m ? d.getField(m.n) : null, v;
  if (!f) return "";
  if (m.k == "check") return f.value != "Off" ? "on" : "";
  v = f.value; if (v == "Off" || v == null) return "";
  return String(m.k == "radio" || m.k == "select" ? v : f.valueAsString).replace(/^\s+|\s+$/g, "");
}
function smHolds(d, F, c, seen) {
  var t = c[0], v, i, w;
  if (!SM.forms[F].f[t] || !smActive(d, F, t, seen)) return false;
  v = smVal(d, F, t);
  for (i = 0; i < c[1].length; i++) { w = c[1][i]; if (w == "*" ? v !== "" : w == "on" ? v == "on" : v == w) return true; }
  return false;
}
function smAny(d, F, list, seen) { for (var i = 0; i < (list || []).length; i++) if (smHolds(d, F, list[i], seen)) return true; return false; }
function smPartShown(d, F, p, seen) { var r = (SM.forms[F].parts[p] || {}).r || {}; return r.show ? smAny(d, F, r.show, seen) : r.hide ? !smAny(d, F, r.hide, seen) : false; }
function smShown(d, F, id, seen) {
  var m = SM.forms[F].f[id], r = m.r || {};
  if (m.p && !smPartShown(d, F, m.p, seen)) return false;
  return r.show ? smAny(d, F, r.show, seen) : r.hide ? !smAny(d, F, r.hide, seen) : true;
}
function smOpen(d, F, id, seen) { var r = SM.forms[F].f[id].r || {}; return r.open ? smAny(d, F, r.open, seen) : r.lock ? !smAny(d, F, r.lock, seen) : !r.locked_at_open; }
function smActive(d, F, id, seen) {
  seen = seen || {}; if (seen[id]) return true; seen[id] = 1;
  var a = smShown(d, F, id, seen) && smOpen(d, F, id, seen); delete seen[id]; return a;
}
function smMandatory(d, F, id) {
  var r = SM.forms[F].f[id].r || {};
  if (!smActive(d, F, id)) return false;
  if (r.req && smAny(d, F, r.req)) return true;
  return !!r.always && !(r.nreq && smAny(d, F, r.nreq));
}
function smDay(s) { var x = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(s), k = x && new Date(+x[3], x[2] - 1, +x[1]); return k && k.getDate() == +x[1] && k.getMonth() == x[2] - 1 ? k : null; }
// What is wrong with a typed answer ("" = nothing).
function smWrong(d, F, id) {
  var m = SM.forms[F].f[id], v = smVal(d, F, id);
  if (!v) return "";
  if (m.ks && m.ks.indexOf("S") >= 0 && /[^a-zA-Z0-9\s,.:'+()?\-\/]/.test(v)) return "has characters a SWIFT message can't carry (letters, digits and , . : ' + ( ) ? - / only)";
  return typeof SMX != "undefined" && SMX[F] ? SMX[F](d, F, id, v) || "" : "";
}
// Runs every rule of form F: colours, locks, shows / hides. Returns the missing questions (.bad: wrong answers,
// .first: the field to put the cursor on).
function smRun(d, F) {
  var S = SM.forms[F], missing = [], bad = [], first = "", id, m, act, shown, open, req, problem, why, f, p, calc = d.calculate;
  if (!S) return missing;
  d.calculate = false;
  try {
    for (p in S.parts) { f = d.getField(S.parts[p].n); if (f) f.display = smPartShown(d, F, p) ? display.visible : display.hidden; }
    for (var i = 0; i < S.order.length; i++) {
      id = S.order[i]; m = S.f[id]; f = d.getField(m.n); if (!f) continue;
      shown = smShown(d, F, id); open = smOpen(d, F, id); act = shown && open;
      req = act && smMandatory(d, F, id);
      problem = req && smVal(d, F, id) === "";
      why = act ? smWrong(d, F, id) : "";
      if (problem) missing.push(m.l);
      if (why) { bad.push(m.l + ": " + why); problem = true; }
      if (problem && !first) first = m.n;
      f.display = shown ? (m.screen ? display.noPrint : display.visible) : display.hidden;
      if (m.r && (m.r.open || m.r.lock || m.r.show || m.r.hide || m.p) && !act) smClear(f, m.k);
      f.readonly = !open;
      f.required = false;
      f.fillColor = problem ? ["RGB", 1, 0.78, 0.78] : !open && m.r && (m.r.open || m.r.lock) ? ["G", 0.9] : color.transparent;
    }
  } catch (e) { console.println("smRun " + F + ": " + e); }
  d.calculate = calc;
  missing.bad = bad; missing.first = first;
  return missing;
}
function smClear(f, k) {
  if (k == "check" || k == "radio") { if (f.value != "Off") f.value = "Off"; }
  else if (f.value !== "" && f.value != null) f.value = "";
}
// A tick box, option or list changed: apply its "set" rules (the old form filled some answers in), then re-check.
function smChanged(d, name) {
  var F = smForm(name); if (!F) return;
  var S = SM.forms[F], id = String(name).slice(S.prefix.length), sets = (S.sets || {})[id] || [], v = smVal(d, F, id), i, g;
  for (i = 0; i < sets.length; i++) if (sets[i][0] == v || (sets[i][0] == "on" && v == "on")) { g = smFld(d, F, sets[i][1]); if (g) g.value = sets[i][2]; }
  smRun(d, F);
}
// Keystrokes, as the old form's change scripts: U upper case, S SWIFT characters only, D digits, N digits and .,
// A letters and digits, T no ~; plus a length limit.
function smKey(spec, limit) {
  if (event.willCommit) return;
  var c = String(event.change), bad = null;
  if (spec.indexOf("U") >= 0) c = c.toUpperCase();
  if (spec.indexOf("S") >= 0) bad = /[^a-zA-Z0-9\s,.:'+()?\-\/]/g;
  if (spec.indexOf("D") >= 0) bad = /[^0-9]/g;
  if (spec.indexOf("N") >= 0) bad = /[^0-9.]/g;
  if (spec.indexOf("A") >= 0) bad = /[^A-Za-z0-9]/g;
  if (bad) c = c.replace(bad, "");
  if (spec.indexOf("T") >= 0) c = c.replace(/~/g, "");
  if (limit) { var v = String(event.value), all = v.slice(0, event.selStart) + c + v.slice(event.selEnd); if (all.length > limit) c = ""; }
  event.change = c;
}
// THE QR CODE TEXT of form F: {"form", "version", "saved", "complete", "data": {question id: answer}}.
function smPayload(d, F) {
  var S = SM.forms[F], data = {}, i, id, v, t = new Date(), m = smRun(d, F);
  for (i = 0; i < S.order.length; i++) { id = S.order[i]; if (S.f[id].noqr) continue; v = smVal(d, F, id); if (v !== "") data[id] = S.f[id].k == "check" ? true : v; }
  function pad(x) { return ("0" + x).slice(-2); }
  return JSON.stringify({"form": S.code, "version": SM.version, "saved": t.getFullYear() + "-" + pad(t.getMonth() + 1) + "-" + pad(t.getDate()) + "T" + pad(t.getHours()) + ":" + pad(t.getMinutes()),
                         "complete": !m.length && !m.bad.length, "data": data});
}
// Draws form F's QR code(s) into its row fields ("QR_<code>_<k>_<row>"); text longer than one code goes in two.
function smDrawQr(d, F, text) {
  var S = SM.forms[F], ONE = 2329, s = unescape(encodeURIComponent(text)), parts = [], codes = [], parity = 0, i, k, y, x, row, calc = d.calculate;
  if (s.length > 2 * ONE) throw new Error("the answers are too long for two QR codes (" + s.length + " characters, at most " + 2 * ONE + ")");
  for (i = 0; i < s.length; i++) parity ^= s.charCodeAt(i) & 255;
  if (s.length > ONE) parts = [s.slice(0, Math.ceil(s.length / 2)), s.slice(Math.ceil(s.length / 2))]; else if (s.length) parts = [s];
  for (k = 0; k < parts.length; k++) codes.push(lcQrMatrix(parts[k], parts.length > 1 ? [k, parts.length, parity] : null));
  d.calculate = false;
  try {
    for (k = 1; k <= 2; k++) {
      for (y = 0; y < 177; y++) { row = ""; if (codes[k - 1]) for (x = 0; x < 177; x++) row += codes[k - 1][y][x] ? "n" : " ";
        d.getField("QR_" + S.code + "_" + k + "_" + y).value = row; }
      d.getField("QR_" + S.code + "_" + k + "_label").value = codes.length > 1 ? "QR code " + k + " of 2 (scan both)" : codes.length ? "Scan this QR code" : "";
    }
  } finally { d.calculate = calc; }
  return codes.length;
}
function smList(a) { return "- " + a.slice(0, 15).join("\n- ") + (a.length > 15 ? "\n- ... and " + (a.length - 15) + " more" : ""); }
function smProblems(d, F, intro) {
  var m = smRun(d, F), t = [];
  if (m.length) t.push(m.length + " mandatory field" + (m.length > 1 ? "s are" : " is") + " still blank:\n" + smList(m));
  if (m.bad.length) t.push(m.bad.length + " answer" + (m.bad.length > 1 ? "s need" : " needs") + " correcting:\n" + smList(m.bad));
  if (!t.length) return false;
  app.alert(intro + " The fields concerned are shaded red.\n\n" + t.join("\n\n"), 1);
  var g = m.first && d.getField(m.first); if (g) try { g.setFocus(); } catch (e) {}
  return true;
}
""" + QR_MATRIX + r"""
// On opening: every form's colours, locks and shown parts.
if (typeof app != "undefined" && /^(Exchange|Reader)/.test(app.viewerType)) { for (var smF in SM.forms) smRun(this, smF); }
"""

BUTTON_JS = {
    "menu": r"""this.pageNum = 0;""",
    "goto": r"""this.pageNum = __PAGE__;""",
    "open-form": r"""
// Menu: the old form asks for the terms tick box before opening a form.
var t = this.getField("MENU_agree");
if (t && t.value == "Off") app.alert("Please tick the box at the bottom of this page to agree to the terms before you choose a form.", 1);
else this.pageNum = __PAGE__;
"""[1:],
    "check": r"""
if (typeof smRun != "function") app.alert("The form's checks did not start. Open the form in Adobe Acrobat or Reader and allow JavaScript (Preferences > JavaScript > Enable Acrobat JavaScript), then reopen it.", 1);
else if (!smProblems(this, "__FORM__", "This form is not complete yet.")) app.alert("All mandatory fields are filled in and every answer is in the right format.", 3);
"""[1:],
    "reset": r"""
if (app.alert("Reset this form? All its answers will be cleared.", 2, 2) == 4) {
  var S = SM.forms["__FORM__"], names = [], id;
  for (id in S.f) names.push(S.f[id].n);
  this.resetForm(names); smDrawQr(this, "__FORM__", ""); smRun(this, "__FORM__"); }
"""[1:],
    "print": r"""
// "Confirm & Print Form": refuses while anything is missing or wrong; otherwise makes the QR code from the answers
// and prints this form's pages (and its terms).
if (typeof smRun != "function") app.alert("The form's checks did not start. Open the form in Adobe Acrobat or Reader and allow JavaScript (Preferences > JavaScript > Enable Acrobat JavaScript), then reopen it.", 1);
else if (!smProblems(this, "__FORM__", "Please enter the mandatory fields highlighted in red colour.")) {
  try { var n = smDrawQr(this, "__FORM__", smPayload(this, "__FORM__"));
    this.print({bUI: true, nStart: __FIRST__, nEnd: __LAST__, bShrinkToFit: true}); }
  catch (e) { app.alert("The QR code could not be made: " + e, 1); } }
"""[1:],
    "save": r"""app.execMenuItem("SaveAs");""",
}

for _name, _text in [("DOCUMENT_JS", DOCUMENT_JS)] + list(BUTTON_JS.items()):
    _bad = sorted({c for c in _text if ord(c) > 126 or (ord(c) < 32 and c not in "\n\t")})
    if _bad:
        raise SystemExit(f"smartform_js.py {_name}: characters that break Acrobat: {_bad!r}")
