// THE RULES ENGINE (runs inside Acrobat). Built into the PDF as the document script "lcRules".
// lcRules(doc) checks every question and colours its box:
//   blank or wrong mandatory answer -> red outline, pink fill, marked Required
//   answered and right              -> black outline, white fill
//   doesn't apply yet               -> greyed out, locked, and its answer cleared
// It returns the list of missing questions, plus .bad (wrong answers) and .first (where to put the cursor).
// lcDates(doc) shows each date's calendar box and hides its drop-down list (Acrobat only).
// __MODEL__ is filled in by lcbuild/scripts.py with the rules table built from lc.py; __DATES__ with the date
// question ids. Acrobat's JavaScript is old-style: var, no arrow functions.
function lcRules(d) {
var M = __MODEL__;
function has(list, x) { for (var i = 0; i < list.length; i++) if (list[i] == x) return true; return false; }

// The answer to question id, read from the PDF's fields.
function val(id) {
  var m = M[id], f, a = [], i;
  if (m.kind == "checks") { for (i = 0; i < m.options.length; i++) { f = d.getField(id + "__" + i); if (f && f.value != "Off") a.push(m.options[i]); } return a; }
  if (m.kind == "date" && shown(id)) return d.getField(id).valueAsString;
  if (m.kind == "date" && d.getField(id + "__list")) { a = /^(\d\d) (\w{3}) (\d{4})$/.exec(d.getField(id + "__list").valueAsString);
    return a ? a[1] + "/" + ("0" + ("JanFebMarAprMayJunJulAugSepOctNovDec".indexOf(a[2]) / 3 + 1)).slice(-2) + "/" + a[3] : ""; }
  f = d.getField(id); if (!f) return "";
  if (m.kind == "check") return f.value != "Off" ? "true" : "false";
  return f.value == "Off" ? "" : String(f.value);
}
function shown(id) { var f = d.getField(id); return !!f && f.display != 1; } // 1 = display.hidden
function empty(x) { return typeof x == "object" ? !x.length : x === ""; }

// Does any of these rules hold?
function any(rules) {
  var i, j, x, hit;
  for (i = 0; i < rules.length; i++) {
    x = val(rules[i][0]); hit = false;
    if (typeof x == "object") { for (j = 0; j < x.length; j++) if (has(rules[i][1], x[j])) hit = true; } else hit = has(rules[i][1], x);
    if (rules[i][2] ? !hit && !empty(x) : hit) return true;
  }
  return false;
}
function mandatory(id) { var m = M[id]; return m.always ? true : any(m.requiredIf || []); }

// What is wrong with a typed answer, or "".
function wrong(id) {
  var m = M[id], f = d.getField(id), s = m.kind == "date" ? val(id) : f ? f.valueAsString : "", x, k;
  if (!m.check || !s) return "";
  x = s.match(new RegExp("[^A-Za-z0-9 .,\\-/()':?+#&@%\\r\\n]", "g"));
  if (x) { k = []; for (var i = 0; i < x.length; i++) if (!has(k, x[i])) k.push(x[i]); return "remove " + k.join(" ") + " (letters, digits and . , - / ( ) ' : ? + # & @ % only)"; }
  if (m.kind == "date") { x = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(s); k = x && new Date(+x[3], x[2] - 1, +x[1]); return k && k.getDate() == +x[1] && k.getMonth() == x[2] - 1 ? "" : "not a real date (DD/MM/YYYY)"; }
  return m.check.length && !new RegExp(m.check[0]).test(s) ? m.check[1] : "";
}

// A real DD/MM/YYYY date as a Date, or null.
function day(s) { var x = /^(\d\d)\/(\d\d)\/(\d{4})$/.exec(s), k = x && new Date(+x[3], x[2] - 1, +x[1]); return k && k.getDate() == +x[1] && k.getMonth() == x[2] - 1 ? k : null; }
function v(id) { return M[id] ? val(id) : ""; }

// Checks across answers (the same as cross-checks in form/validate.ts). Skipped when a form doesn't have the fields.
function across() {
  var X = {}, A = day(v("application_date")), S = day(v("latest_shipment_date")), E = day(v("expiry_date")), a = v("amount"), pb = v("price_basis");
  if (S && E && E < S) X.expiry_date = "is before the latest shipment date";
  else if (A && E && E < A) X.expiry_date = "is before the application date";
  if (A && S && S < A) X.latest_shipment_date = "is before the application date";
  if (A && A.getTime() > new Date().getTime()) X.application_date = "is in the future";
  if (/^[\d,]+(\.\d+)?$/.test(a) && !(Number(a.replace(/,/g, "")) > 0)) X.amount = "must be more than zero";
  if (v("insurance_arrangement") && (pb == "CIF" || pb == "CIP")) X.insurance_arrangement = "is only for FOB/CFR/FCA/CPT, but price basis is " + pb + " (the beneficiary insures)";
  return X;
}

// Clears a question's box, so an answer can't stay behind in a question that doesn't apply.
function clear(f, kind) {
  if (kind == "check" || kind == "checks" || kind == "radio") { if (f.value != "Off") f.value = "Off"; }
  else if (f.type == "combobox" && /__list$/.test(f["name"])) { if (f.currentValueIndices != 0) f.currentValueIndices = 0; } // a date list: back to "Pick a date"
  else if (f.value !== "" && f.value != null) f.value = "";
}

// Go through every question: work out its state, then colour (and lock) its boxes.
var missing = [], bad = [], first = "", id, m, applies, required, problem, whatsWrong, names, i, f, X;
try {
X = across();
for (id in M) {
  m = M[id]; if (!m.hasRule && !m.check && !m.activeIf) continue;
  applies = !m.activeIf || any(m.activeIf);
  required = m.hasRule && applies ? mandatory(id) : false;
  problem = required && (m.kind == "check" ? val(id) != "true" : empty(val(id)));
  if (problem) missing.push(m.label);
  whatsWrong = applies ? wrong(id) || X[id] || "" : ""; if (whatsWrong) { bad.push(m.label + ": " + whatsWrong); problem = true; }
  names = [id]; if (m.kind == "checks") { names = []; for (i = 0; i < m.options.length; i++) names.push(id + "__" + i); }
  if (m.kind == "date" && !shown(id) && d.getField(id + "__list")) names = [id + "__list"];
  if (problem && !first) first = names[0];
  for (i = 0; i < names.length; i++) {
    f = d.getField(names[i]); if (!f) continue;
    if (m.hasRule && m.kind != "checks") f.required = !!(required && problem); // only while blank or wrong: Acrobat outlines Required boxes in red even when filled
    if (m.activeIf) f.readonly = !applies;                                                   // locked until it applies
    if (!applies) { clear(f, m.kind); f.lineWidth = 1; f.strokeColor = ["G", 0.6]; f.fillColor = ["G", 0.86]; continue; } // grey, cleared
    f.lineWidth = problem || !m.underlined ? 1 : 0;
    f.strokeColor = problem ? color.red : m.underlined ? color.transparent : color.black;    // red when blank or wrong
    f.fillColor = problem ? ["RGB", 1, 0.88, 0.88] : m.underlined ? color.transparent : color.white;
  }
}
} catch (e) { console.println("lcRules: " + e); }
missing.bad = bad;
missing.first = first; // the field of the first problem, for "Check form" to go to
return missing;
}

// Acrobat only: show each date's calendar box and hide its drop-down list.
function lcDates(d) {
  var D = __DATES__, i, t, p;
  for (i = 0; i < D.length; i++) { t = d.getField(D[i]); if (!t) continue; t.display = display.visible;
    p = d.getField(D[i] + "__list"); if (p) p.display = display.hidden; }
}
// On opening in Acrobat: show the calendars, and set every box's colour and lock.
if (typeof app != "undefined" && /^(Exchange|Reader)/.test(app.viewerType)) { lcDates(this); lcRules(this); }
// THE QR CODE'S TEXT. lcPayload(doc) returns every answered question as JSON:
//   {"form": "LC-01", "version": "1.0", "saved": "...", "complete": true, "data": {field id: answer, ...}}
// Tick boxes become true; "tick any" questions become lists of the ticked options. The text is padded with spaces
// to 2,300 characters so the code is always the same size. __GROUPS__, __LONG__, __FORM__ and __VERSION__ are
// filled in by lcbuild/scripts.py.
function lcPayload(d) {
var G = {__GROUPS__}, LONG = __LONG__, CAP = 2300;
var data = {}, i, n, f, k, v, g, m, out, cut = [], ok = true, t = new Date();
for (i = 0; i < d.numFields; i++) {
  n = d.getNthFieldName(i); if (/^__/.test(n) || /__list$/.test(n)) continue;
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
// A QR code holds about 2,300 characters: if the answers are longer, shorten the two long paragraphs and say so.
for (i = 0; i < LONG.length && JSON.stringify(out).length > CAP; i++) {
  k = LONG[i]; if (!data[k]) continue;
  cut.push(k); out.truncated = cut;
  v = JSON.stringify(out).length - CAP + 3;
  data[k] = v < data[k].length ? data[k].slice(0, data[k].length - v) + "..." : "...";
}
// Padded with spaces to the full length: the QR code is then always the same size (version 40) and fills its frame.
v = JSON.stringify(out); while (v.length < CAP) v += " ";
return v;
}
// THE QR CODE ENCODER AND DRAWING (standard QR code, no library needed).
// lcQrMatrix(text) returns the 177 x 177 grid of a version 40 QR code (true = dark square).
// lcDrawQr(doc, text) writes each row into one of the read-only text boxes "__qr_0" ... "__qr_176" on the
// QR page, as the letter "n" in the ZapfDingbats font (which prints as a black square) for each dark square.
// QR code (version 40, error correction M, byte mode, mask 0) drawn without Acrobat's barcode feature:
// one comb text field per row ("__qr_0" ... "__qr_176"), dark modules as ZapfDingbats "n" (a black square).
function lcQrMatrix(text) {
  var N = 177, i, j, x, y, m = [], f = [], bytes = [], s = unescape(encodeURIComponent(text));
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
  // Data: mode 0100, 16-bit length, the bytes, terminator, padding to 2,334 data codewords.
  var bits = [], cap = 2334 * 8;
  function put(v, n) { for (var k = n - 1; k >= 0; k--) bits.push((v >>> k) & 1); }
  put(4, 4); put(bytes.length, 16); for (i = 0; i < bytes.length; i++) put(bytes[i], 8);
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
function lcDrawQr(d, text) {
  var m = lcQrMatrix(text), y, x, s, calc = d.calculate;
  d.calculate = false; // 177 rows: don't re-run the checks after each one
  try { for (y = 0; y < m.length; y++) { s = ""; for (x = 0; x < m.length; x++) s += m[y][x] ? "n" : " "; d.getField("__qr_" + y).value = s; } }
  finally { d.calculate = calc; }
}
