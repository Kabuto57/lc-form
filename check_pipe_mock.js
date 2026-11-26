// Runs the JavaScript of a built PDF (the document script, and a button's script) outside Acrobat, against a minimal
// fake of Acrobat's document: fields that hold a value, and nothing else. Used by check_pipe.py; not needed to build.
// Input (stdin, JSON): {mode, script, button, types: {field name: type}, cases: [{field name: value}, ...]}
//   mode "records":  returns, for each case, lcPipeRecords(doc)   (the 4 pipe records)
//   mode "print":    each case {values, gen, stored, after}: optionally presses Generate QR Code (gen), sets the hidden "__qr" to
//                    stored (how the viewer kept the text), changes the answers in after, then presses Print Form; says if it printed
//   mode "generate": runs the button script (Generate QR Code) and returns, for each case, the alerts it showed,
//                    the text it put in the hidden field "__qr", and the rows of each QR code it drew
const fs = require("node:fs");
const vm = require("node:vm");

const input = JSON.parse(fs.readFileSync(0, "utf8"));

// A fake of Acrobat's document: fields that hold a value, and pages (the hidden template "qrx" holds the fields of the extra QR
// code pages; spawn copies them onto a new page, deletePages takes a page and its fields away), like proof_multiqr.py's stand-in.
function makeDoc(types, values, alerts) {
  const pages = [], tmpl = { id: "template" };
  let fields = [], idx = {};
  const refresh = () => { idx = {}; for (const f of fields) idx[f.name] = f; };
  function mk(name, type, pg) {
    const f = { name, type, pg, display: 0, readonly: false, required: false };
    let v = name in values ? values[name] : type === "radiobutton" || type === "checkbox" ? "Off" : "";
    Object.defineProperty(f, "value", { get: () => v, set: (x) => { v = x; }, enumerable: true });
    Object.defineProperty(f, "valueAsString", { get: () => String(v) });
    Object.defineProperty(f, "page", { get: () => pages.indexOf(f.pg) });
    f.setFocus = () => {};
    return f;
  }
  const count = Math.max(...Object.values(types).map((t) => t[1])) + 1;
  for (let i = 0; i < count; i++) pages.push({ id: "p" + i });
  for (const [name, [type, page]] of Object.entries(types)) fields.push(mk(name, type, page >= 0 ? pages[page] : tmpl));
  refresh();
  const doc = {
    get numFields() { return fields.length; }, getNthFieldName: (i) => fields[i].name, getField: (n) => idx[n] || null,
    get numPages() { return pages.length; },
    fields_by: (n) => idx[n] || null, allFields: () => fields,
    calculate: true, pageNum: 0, resetForm() {}, print(...a) { this.printed = a; },
    getTemplate(n) {
      if (n !== "qrx") throw new Error("no template " + n);
      return { spawn(o) {
        const pg = { id: "s" + pages.length }, at = Math.min(o.nPage, pages.length);
        pages.splice(at, 0, pg);
        for (const f of fields.filter((f) => f.pg === tmpl && f.name.startsWith("__qrx_"))) fields.push(Object.assign(mk("P" + at + ".qrx." + f.name, f.type, pg), { display: f.display }));
        refresh();
      } };
    },
    deletePages(n) { const gone = pages.splice(typeof n == "number" ? n : n.nStart, 1)[0]; fields = fields.filter((f) => f.pg !== gone); refresh(); },
  };
  return doc;
}

const alerts = [];
const ctx = {
  app: { viewerType: "none", viewerVersion: 0, alert: (m) => { alerts.push(String(m)); return 4; }, setTimeOut() {} },
  console: { println() {} },
  color: { red: ["RGB", 1, 0, 0], black: ["G", 0], white: ["G", 1], transparent: ["T"] },
  display: { visible: 0, hidden: 1 },
  event: { name: "" },
};
vm.createContext(ctx);
vm.runInContext(input.script, ctx, { filename: "document-script.js" });

const out = [];
for (const values of input.cases) {
  const spec = input.mode === "print" ? values : null;   // print: {values, gen, stored, after}
  const doc = makeDoc(input.types, spec ? spec.values : values, alerts);
  ctx.__d = doc;
  if (input.mode === "records") {
    out.push(vm.runInContext("lcPipeRecords(__d)", ctx));
  } else if (input.mode === "print") {
    alerts.length = 0;
    if (spec.gen) vm.runInContext(`(function () {\n${input.button}\n}).call(__d);`, ctx, { filename: "generate-button.js" });
    if (spec.stored !== null) doc.getField("__qr").value = spec.stored;
    for (const [k, v] of Object.entries(spec.after)) doc.getField(k).value = v;
    alerts.length = 0;
    vm.runInContext(`(function () {\n${input.printer}\n}).call(__d);`, ctx, { filename: "print-button.js" });
    out.push({ alerts: alerts.slice(), printed: !!doc.printed, last: doc.printed ? doc.printed[2] : null });
  } else {
    alerts.length = 0;
    vm.runInContext(`(function () {\n${input.button}\n}).call(__d);`, ctx, { filename: "generate-button.js" });
    const codes = [], rowsOf = (pre) => { const rows = []; for (let y = 0; y < 177; y++) { const f = doc.fields_by(pre + y); if (!f) return null; rows.push(String(f.value)); } return rows; };
    const slots = [rowsOf("__qr1_"), rowsOf("__qr2_")];
    const extra = {};
    for (const f of doc.allFields()) { const m = /__qrx_([12])_0$/.exec(f.name); if (m && f.page >= 0) extra[f.page] = extra[f.page] || {}, extra[f.page][m[1]] = f.name.slice(0, -1); }
    for (const pg of Object.keys(extra).map(Number).sort((a, b) => a - b)) for (const k of [1, 2]) slots.push(extra[pg][k] ? (() => { const rows = []; for (let y = 0; y < 177; y++) rows.push(String(doc.getField(extra[pg][k] + y).value)); return rows; })() : null);
    for (const rows of slots) if (rows && rows.some((r) => r.trim() !== "")) codes.push(rows);
    out.push({ alerts: alerts.slice(), qr: String(doc.getField("__qr").value), codes });
  }
}
process.stdout.write(JSON.stringify(out));
