// Runs the PDF's own rules script (lcRules) on a stand-in for Acrobat and checks the rules work:  npm test
// (Acrobat itself isn't scriptable from here; this runs the exact JavaScript stored in out/LC-Application.pdf.)
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { PDFArray, PDFCheckBox, PDFDict, PDFDocument, PDFDropdown, PDFName, PDFRadioGroup, PDFRawStream, PDFTextField, decodePDFRawStream } from "pdf-lib";
import { LC, LC_SAMPLE } from "./src/lc.ts";

const doc = await PDFDocument.load(readFileSync("out/LC-Application.pdf"));
assert.equal(doc.getPageCount(), 5);
assert.equal(doc.getForm().getFields().length, 297);

// The document script "lcRules" (one stream in the catalog's /Names /JavaScript).
const names = doc.catalog.lookup(PDFName.of("Names"), PDFDict).lookup(PDFName.of("JavaScript"), PDFDict).lookup(PDFName.of("Names"), PDFArray);
const stream = names.lookup(1, PDFDict).lookup(PDFName.of("JS"), PDFRawStream);
const script = new TextDecoder("latin1").decode(decodePDFRawStream(stream).decode());

const dates = new Set(LC.template.sections.flatMap(s => s.fields).filter(f => f.kind === "date").map(f => f.id));
type Stub = { name: string; type: string; value: string; display: number; readonly?: boolean; strokeColor?: unknown; currentValueIndices?: number; readonly valueAsString: string };
const fields: Record<string, Stub> = {};
for (const f of doc.getForm().getFields()) {
  const name = f.getName();
  const [type, value] =
    f instanceof PDFTextField ? ["text", f.getText() ?? ""] :
    f instanceof PDFDropdown ? ["combobox", f.getSelected()[0] ?? ""] :
    f instanceof PDFRadioGroup ? ["radiobutton", f.getSelected() ?? "Off"] :
    f instanceof PDFCheckBox ? ["checkbox", f.isChecked() ? "Yes" : "Off"] : ["button", ""];
  // Dates as Acrobat shows them with JavaScript on: the calendar box, not the drop-down list.
  fields[name] = { name, type, value, display: name.endsWith("__list") ? 1 : 0, get valueAsString() { return String(this.value); } };
}
const d = { getField: (n: string) => fields[n] ?? null };
const lcRules = (): string[] & { bad: string[] } => new Function("color", "console", "display", "app", `${script}; return lcRules(this);`)
  .call(d, { red: "red", black: "black", white: "white", transparent: "none" }, { println: (m: string) => { throw new Error(m); } }, { visible: 0, hidden: 1 }, undefined);
const set = (id: string, v: string | boolean) => { fields[id].value = v === true ? "Yes" : v === false ? "Off" : v; };

// 1. Blank form: the always-mandatory questions are missing, conditional ones aren't.
let m = lcRules();
assert.ok(m.includes("Applicant name") && m.includes("Goods description (if space is insufficient, attach additional information with Company's stamp, signed by authorised signors)"));
assert.ok(!m.includes("Percentage of invoice value (%)"));
assert.equal(fields.applicant_name.strokeColor, "red");
assert.equal(fields.drafts_percent.readonly, true, "locked until Drafts is ticked");

// 2. Ticking Drafts makes its questions mandatory and unlocks them.
set("drafts", true); m = lcRules();
assert.ok(m.includes("Percentage of invoice value (%)") && m.includes("Drafts at"));
assert.equal(fields.drafts_percent.readonly, false);

// 3. Wrong formats and cross-checks are reported.
set("amount", "12a"); set("expiry_date", "01/01/2026"); set("latest_shipment_date", "02/01/2026"); m = lcRules();
assert.ok(m.bad.some(b => b.startsWith("Amount:")));
assert.ok(m.bad.includes("Date of expiry (in beneficiary's country): is before the latest shipment date"));

// 4. A complete, correct application: nothing missing, nothing wrong.
for (const k in fields) if (!k.startsWith("__")) set(k, fields[k].type === "checkbox" || fields[k].type === "radiobutton" ? "Off" : "");
for (const [k, v] of Object.entries(LC_SAMPLE)) set(k, v as string | boolean);
m = lcRules();
assert.deepEqual([...m], []); assert.deepEqual(m.bad, []);
assert.equal(fields.applicant_name.strokeColor, "black");

// 5. Clearing a mandatory answer turns it red again.
set("applicant_name", ""); m = lcRules();
assert.deepEqual([...m], ["Applicant name"]);
console.log("PASS: 5 pages, 297 fields, rules engine checks OK");
