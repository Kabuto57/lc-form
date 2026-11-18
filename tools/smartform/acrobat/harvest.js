// HARVEST: run inside Adobe Acrobat (Acrobat's "do script") on the vendor's Trade-Smartform.pdf.
// For one section (__ONLY), it records where everything is drawn after Acrobat lays the form out:
//   base    every field, text and box on every page (header/footer included), with its position in points
//   hidden  each part that starts hidden, laid out on its own (shown alone), and whether showing it moves
//           anything else ("shifted")
// __PREREVEAL lists hidden parts to show before measuring (parts that push the rest down get their room this way).
// Positions are from the top-left of the page's content area (header/footer items: of the page).
if (global.TS) { try { global.TS.dirty = false; global.TS.closeDoc(true); } catch (e) {} }
global.TS = app.openDoc({cPath: __PATH, bHidden: true});
var D = global.TS, X = D.xfa, F = X.form.form1, L = X.layout;
var SECTIONS = ["MainPage","LC","LCTermsAndConditions","LC_Amendment","EBLC","EBLCTermsAndConditions","EBLCTermsAndConditions1","OBC","OBCTermsAndConditions","DBRP","BEOBC","BEEBLC","BEGeneric","SBLC","SBLCA","BG","BGA","EXPORT"];
var sec = __ONLY, PRE = typeof __PREREVEAL != "undefined" ? __PREREVEAL : [];
var TECH = /barcode|Bcode|Dummy|FieldsList|subfrmMandatory|subfieldsCheck|HiddenField|btnShow|btnHide|Code3of9|BlankPage|^Button3$|Cif$|^txtPrint$|^txt(LC|EBLC|OBC|DBRP|LCA|SBLC|SBLCA|BG|BGA|EXPORT)$/i;
function tryv(f) { try { return f(); } catch (e) { return null; } }
function parseU(s) { if (!s) return 0; var m = /^([\d.\-]+)(mm|in|pt|cm)?$/.exec(String(s)); if (!m) return 0; var v = +m[1];
  return m[2] == "mm" ? v * 72 / 25.4 : m[2] == "in" ? v * 72 : m[2] == "cm" ? v * 720 / 25.4 : v; }
function abs(n, pg) {
  var x = 0, y = 0, c = n;
  while (c && c.className != "form" && c.className != "pageSet" && c.className != "pageArea") {
    if (c.className == "exclGroup") { var cc = c; x += parseU(tryv(function(){ return cc.x; })); y += parseU(tryv(function(){ return cc.y; })); c = c.parent; continue; }
    var off = pg - L.page(c); if (off < 0) off = 0;
    x += L.x(c, "pt", off); y += L.y(c, "pt", off); c = c.parent;
  }
  return [x, y];
}
function shown(n) { var c = n; while (c && c.className != "form" && c.className != "pageSet") { var cc = c, p = tryv(function(){ return cc.presence; }); if (p && p != "visible") return 0; c = c.parent; } return 1; }
var REVEALED = {};
function revealedUnder(n) { var c = n; while (c && c.className != "form") { if (REVEALED[c.somExpression]) return 1; c = c.parent; } return 0; }
function item(n, pg, master) {
  var a = abs(n, pg), off = pg - L.page(n); if (off < 0) off = 0;
  var r = { som: n.somExpression, cls: n.className, page: pg, x: +a[0].toFixed(2), y: +a[1].toFixed(2),
            w: +L.w(n, "pt", off).toFixed(2), h: +L.h(n, "pt", off).toFixed(2), master: master ? 1 : 0, vis: shown(n), pre: revealedUnder(n) };
  if (n.className == "draw") r.text = tryv(function(){ return n.rawValue; });
  if (n.className == "field") { r.caption = tryv(function(){ return n.caption.value.oneOfChild.value; });
    r.ui = tryv(function(){ return n.ui.oneOfChild.className; }); r.value = tryv(function(){ return n.rawValue; });
    r.items = tryv(function(){ var o = [], k; for (k = 0; k < n.length; k++) o.push([n.getDisplayItem(k), n.getSaveItem(k)]); return o; });
    if (n.parent.className == "exclGroup") r.group = n.parent.somExpression; }
  return r;
}
function collect(withMaster) { var all = [], cnt = L.pageCount(), p, k, m;
  for (p = 0; p < cnt; p++) {
    if (withMaster) { m = L.pageContent(p, "", true); for (k = 0; k < m.length; k++) { var n = m.item(k); if (n.className == "field" || n.className == "draw" || n.className == "subform") all.push(item(n, p + 1, true)); } }
    m = L.pageContent(p, "", false); for (k = 0; k < m.length; k++) { var n = m.item(k); if (n.className == "field" || n.className == "draw" || n.className == "subform") all.push(item(n, p + 1, false)); } }
  return all; }
function revealAll(H, saved) {   // shows H and every hidden part inside it (not the technical ones)
  if (H.presence == "hidden" || H.presence == "invisible") { saved.push([H, H.presence]); H.presence = "visible"; REVEALED[H.somExpression] = 1; }
  if (H.className == "field" || H.className == "draw") return; var k, kids = H.nodes;
  for (k = 0; k < kids.length; k++) { var c = kids.item(k); if ((c.className == "subform" || c.className == "field" || c.className == "draw" || c.className == "exclGroup") && !TECH.test(c.name)) revealAll(c, saved); } }

for (var j = 0; j < SECTIONS.length; j++) F[SECTIONS[j]].presence = (SECTIONS[j] == sec ? "visible" : "hidden");
L.relayout(); X.form.execCalculate();
var keep = [];
for (var i = 0; i < PRE.length; i++) { var h = X.resolveNode(PRE[i]); if (h) revealAll(h, keep); }
L.relayout();
var base = collect(true), pages = L.pageCount(), pos = {}, i;
for (i = 0; i < base.length; i++) if (base[i].vis && !base[i].master) pos[base[i].som + "@" + base[i].page] = base[i];
var tops = [];
(function find(n) { var k, kids = n.nodes; for (k = 0; k < kids.length; k++) { var c = kids.item(k);
  if (c.className != "subform" && c.className != "field" && c.className != "draw" && c.className != "exclGroup" && c.className != "subformSet") continue;
  if (TECH.test(c.name)) continue;
  if (c.presence == "hidden" || c.presence == "invisible") { tops.push(c); continue; }
  if (c.className != "field" && c.className != "draw") find(c); } })(F[sec]);
var hidden = [];
for (i = 0; i < tops.length; i++) {
  var H = tops[i], hs = H.somExpression, saved = [];
  revealAll(H, saved); L.relayout();
  var now = collect(false), mine = [], shifted = 0;
  for (var q = 0; q < now.length; q++) { var it = now[q];
    if (it.som.indexOf(hs) == 0) { mine.push(it); continue; }
    var b = pos[it.som + "@" + it.page]; if (it.vis && (!b || Math.abs(b.x - it.x) > 0.5 || Math.abs(b.y - it.y) > 0.5)) shifted++; }
  hidden.push({ som: hs, cls: H.className, shifted: shifted, pages: L.pageCount(), items: mine });
  for (var z = saved.length - 1; z >= 0; z--) { saved[z][0].presence = saved[z][1]; delete REVEALED[saved[z][0].somExpression]; }
  L.relayout();
}
return JSON.stringify({ section: sec, pages: pages, prereveal: PRE, base: base, hidden: hidden });
