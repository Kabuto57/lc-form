// Runs the JavaScript of a built PDF (the document script, and a button's script) outside Acrobat, against a minimal
// fake of Acrobat's document: fields that hold a value, and nothing else. Used by check_pipe.py; not needed to build.
// Input (stdin, JSON): {mode, script, button, types: {field name: type}, cases: [{field name: value}, ...]}
//   mode "records":  returns, for each case, lcPipeRecords(doc)   (the 4 pipe records)
//   mode "print":    runs the Print Form button's script and says whether it printed (the field "__qr" holds the stored text)
//   mode "generate": runs the button script (Generate QR Code) and returns, for each case, the alerts it showed,
//                    the text it put in the hidden field "__qr", and the rows of each QR code it drew
const fs = require("node:fs");
const vm = require("node:vm");

const input = JSON.parse(fs.readFileSync(0, "utf8"));

function makeDoc(types, values, alerts) {
  const fields = {};
  for (const [name, type] of Object.entries(types)) {
    const f = { name, type, display: 0, readonly: false, required: false };
    let v = name in values ? values[name] : type === "radiobutton" || type === "checkbox" ? "Off" : "";
    Object.defineProperty(f, "value", { get: () => v, set: (x) => { v = x; }, enumerable: true });
    Object.defineProperty(f, "valueAsString", { get: () => String(v) });
    f.setFocus = () => {};
    fields[name] = f;
  }
  const names = Object.keys(fields);
  return {
    numFields: names.length, getNthFieldName: (i) => names[i], getField: (n) => fields[n] || null,
    calculate: true, pageNum: 0, numPages: 4, fields,
    resetForm() {}, print() { this.printed = true; },
  };
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
  const doc = makeDoc(input.types, values, alerts);
  ctx.__d = doc;
  if (input.mode === "records") {
    out.push(vm.runInContext("lcPipeRecords(__d)", ctx));
  } else if (input.mode === "print") {
    alerts.length = 0;
    vm.runInContext(`(function () {\n${input.printer}\n}).call(__d);`, ctx, { filename: "print-button.js" });
    out.push({ alerts: alerts.slice(), printed: !!doc.printed });
  } else {
    alerts.length = 0;
    vm.runInContext(`(function () {\n${input.button}\n}).call(__d);`, ctx, { filename: "generate-button.js" });
    const codes = [];
    for (const k of [1, 2]) {
      const rows = [];
      for (let y = 0; y < 177; y++) rows.push(String(doc.fields[`__qr${k}_${y}`].value));
      if (rows.some((r) => r.trim() !== "")) codes.push(rows);
    }
    out.push({ alerts: alerts.slice(), qr: String(doc.fields["__qr"].value), codes });
  }
}
process.stdout.write(JSON.stringify(out));
