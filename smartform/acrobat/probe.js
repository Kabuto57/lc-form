// PROBE: run inside Adobe Acrobat on the vendor's Trade-Smartform.pdf. Finds the old form's rules by trying them:
// for one section (__ONLY) it records every field's state (mandatory, access, shown, value), then sets each tick box,
// option, drop-down choice and text box in turn, fires its own scripts, and records what changed elsewhere.
// Events whose scripts could show a message box are not fired (a box would block Acrobat on screen).
if (global.TS) { try { global.TS.dirty = false; global.TS.closeDoc(true); } catch (e) {} }
global.TS = app.openDoc({cPath: __PATH, bHidden: true});
var D = global.TS;
var X = D.xfa, F = X.form.form1, L = X.layout;
var SECTIONS = ["MainPage","LC","LCTermsAndConditions","LC_Amendment","EBLC","EBLCTermsAndConditions","EBLCTermsAndConditions1","OBC","OBCTermsAndConditions","DBRP","BEOBC","BEEBLC","BEGeneric","SBLC","SBLCA","BG","BGA","EXPORT"];
var sec = __ONLY;
function tryv(f) { try { return f(); } catch (e) { return null; } }
for (var j = 0; j < SECTIONS.length; j++) F[SECTIONS[j]].presence = (SECTIONS[j] == sec ? "visible" : "hidden");
L.relayout(); X.form.execCalculate();
function shown(n) { var c = n; while (c && c.className != "form") { var p = tryv(function(){ return c.presence; }); if (p && p != "visible") return 0; c = c.parent; } return 1; }
var nodes = [];
(function walk(n) { var k, kids = n.nodes; for (k = 0; k < kids.length; k++) { var c = kids.item(k);
  if (c.className == "field" || c.className == "exclGroup" || c.className == "draw" || c.className == "subform") nodes.push(c);
  if (c.className == "subform" || c.className == "exclGroup" || c.className == "subformSet") walk(c); } })(F[sec]);
function state() { var s = {}; for (var i = 0; i < nodes.length; i++) { var n = nodes[i];
  if (n.className == "draw" || n.className == "subform") { s[n.somExpression] = [null, null, n.presence == "visible" ? 1 : 0, null]; continue; }
  s[n.somExpression] = [tryv(function(){ return n.mandatory; }), tryv(function(){ return n.access; }), shown(n), tryv(function(){ return n.className == "exclGroup" ? null : n.rawValue; })]; } return s; }
function diff(a, b) { var o = {}, k, any = 0; for (k in b) { var x = a[k] || [], y = b[k];
  if (x[0] != y[0] || x[1] != y[1] || x[2] != y[2] || x[3] != y[3]) { o[k] = [x, y]; any = 1; } } return any ? o : null; }
// Fires an event only if none of its scripts can show a message box (that would block Acrobat on screen).
function quiet(n, act) { var k, kids = n.nodes, ok = true, any = false;
  for (k = 0; k < kids.length; k++) { var e = kids.item(k); if (e.className != "event" || e.activity != act) continue; any = true;
    var s = tryv(function(){ return e.resolveNode("script").value; }) || ""; if (/messageBox|alert|setFocus|print\(|exportData|saveAs|Show\(|checkValue|plusNumeric|validateDate|dateFormatChange|ompare|checkOnExpiryDate|versionCheck/.test(s)) ok = false; }
  if (any && ok) tryv(function(){ n.execEvent(act); }); }
function fire(n, v, text) {
  X.event.newText = text == null ? (v == null ? "" : String(v)) : text; X.event.change = X.event.newText; X.event.prevText = "";
  n.rawValue = v;
  quiet(n, "change"); quiet(n, "click"); quiet(n, "exit");
  if (n.className == "field" && n.parent.className == "exclGroup") { var g = n.parent; quiet(g, "change"); quiet(g, "click"); }
}
var base = state(), probes = [];
for (var i = 0; i < nodes.length; i++) {
  if (nodes[i].className == "draw" || nodes[i].className == "subform") continue;
  var n = nodes[i], ui = n.className == "field" ? tryv(function(){ return n.ui.oneOfChild.className; }) : "exclGroup";
  var vals = [], k;
  if (ui == "checkButton") { var on = tryv(function(){ return n.items.nodes.item(0).value; }); if (on == null) on = "1"; vals.push([on, null]); }
  else if (ui == "choiceList") { for (k = 0; k < n.length; k++) vals.push([n.getSaveItem(k), n.getDisplayItem(k)]); }
  else if (ui == "textEdit" || ui == "numericEdit" || ui == "dateTimeEdit") vals.push([ui == "textEdit" ? "A1" : ui == "numericEdit" ? "5" : "2026-12-01", null]);
  else continue;
  if (n.className == "field" && n.parent.className == "exclGroup") continue; // radios: probed through the field itself below
  for (var q = 0; q < vals.length; q++) {
    var before = base[n.somExpression] ? base[n.somExpression][3] : null, pre = state();
    fire(n, vals[q][0], vals[q][1]);
    var post = state(); delete post[n.somExpression]; var d = diff(pre, post); if (d) probes.push({ som: n.somExpression, value: vals[q][0], diff: d });
    fire(n, before, null);
  }
}
// radio options: each option field of each exclGroup
for (var i = 0; i < nodes.length; i++) { var g = nodes[i]; if (g.className != "exclGroup") continue;
  var opts = g.nodes, k;
  for (k = 0; k < opts.length; k++) { var o = opts.item(k); if (o.className != "field") continue;
    var on = tryv(function(){ return o.items.nodes.item(0).value; });
    var before = tryv(function(){ return g.rawValue; }), pre = state();
    g.rawValue = on; quiet(o, "change"); quiet(o, "click"); quiet(g, "change"); quiet(g, "click");
    var post = state(); delete post[g.somExpression]; for (var z = 0; z < opts.length; z++) delete post[opts.item(z).somExpression];
    var d = diff(pre, post); if (d) probes.push({ som: g.somExpression, value: on, option: o.somExpression, diff: d });
    g.rawValue = before; quiet(o, "change"); quiet(g, "change"); quiet(o, "click");
  } }
var after = diff(base, state());
var out = {}; out[sec] = { base: base, probes: probes, leftover: after };
return JSON.stringify(out[sec]);
