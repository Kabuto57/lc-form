#!/usr/bin/env python3
"""CHECK THE ONE-PDF MENU (build_all.py): every form's pages stay in the PDF, so switching forms needs nothing the free
Reader refuses.      python build_all.py && python check_joined.py

Reads out/Trade-Application-Forms.pdf and checks (1) its structure: all 13 forms present, every form's pages ordinary
pages (only the 13 extra QR code pages are templates), a menu link and a bookmark for each form, a plain Main menu jump on
every form page; (2) the document's own JavaScript under Node (a small stand-in for Acrobat's document, with all 13 forms'
scripts loaded together): the menu link goes to each form's first page (and asks to tick the terms box first), Print Form
prints exactly that form's pages, a long answer (3 codes) puts an extra page right after that form's QR code page and moves
the later forms down without breaking their Print Form range, extra pages of two forms do not get mixed up, and Reset form
clears one form and leaves the others. Needs node on the PATH. Template.spawn is modelled as Adobe documents it
(bOverlay false: the new page goes BEFORE page nPage); the field renaming is a guess, as in proof_multiqr.py."""
import io
import json
import os
import subprocess
import sys
import tempfile

import pikepdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "forms"))
import build_all  # noqa: E402
from build import load_form  # noqa: E402
from pdf_writer import build  # noqa: E402
from proof_multiqr import load_pdf_for_harness, text_of  # noqa: E402

HARNESS = r"""
const fs = require("fs"), vm = require("vm");
const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
global.display = {visible: 0, hidden: 1, noPrint: 2, noView: 3};
global.color = {red: ["RGB", 1, 0, 0], black: ["G", 0], white: ["G", 1], transparent: ["T"]};
global.event = {name: "WillSave"};
const pages = [], tmpl = {id: "template"}, alerts = [], printed = [];
let fields = [], idx = {};
const refresh = () => { idx = {}; for (const f of fields) idx[f.name] = f; };
function mk(name, type, pg) {
  const f = {name, type, value: type == "checkbox" || type == "radiobutton" ? "Off" : "", display: 0, pg};
  Object.defineProperty(f, "page", {get() { return pages.indexOf(f.pg); }});
  Object.defineProperty(f, "valueAsString", {get() { return String(f.value); }});
  f.setFocus = () => {};
  return f;
}
for (let i = 0; i < D.numPages; i++) pages.push({id: "p" + i});
for (const f of D.fields) fields.push(mk(f.name, f.type, f.page >= 0 ? pages[f.page] : tmpl));
refresh();
const doc = {
  calculate: true, pageNum: 0,
  get numPages() { return pages.length; }, get numFields() { return fields.length; },
  getNthFieldName(i) { return fields[i].name; }, getField(n) { return idx[n] || null; },
  print(...a) { printed.push(a); },
  resetForm(list) { for (const f of fields) if (f.type == "text" && f.pg !== tmpl && f.name.startsWith(list[0] + ".")) f.value = ""; },
  getTemplate(n) {
    const prefix = n.slice(0, -4) + ".";
    return {spawn(o) {
      if (o.bRename !== true) throw new Error("bRename must be true");
      const at = Math.min(o.nPage, pages.length), pg = {id: "s" + at + "_" + pages.length};
      pages.splice(at, 0, pg);   // bOverlay false: inserted BEFORE page nPage
      for (const f of fields.filter(f => f.pg === tmpl && f.name.startsWith(prefix + "__qrx_"))) fields.push(Object.assign(mk("P" + at + "." + n + "." + f.name, f.type, pg), {display: f.display}));
      refresh();
    }};
  },
  deletePages(n) {
    const gone = pages.splice(typeof n == "number" ? n : n.nStart, 1)[0];
    fields = fields.filter(f => f.pg !== gone); refresh();
  },
};
for (const s of Object.values(D.scripts)) vm.runInThisContext(s);
global.app = {viewerType: "Reader", viewerVersion: "0", alert(m) { alerts.push(m); return 4; }};
for (const code of Object.keys(D.scripts)) global["lcRules_" + code] = function () { const a = []; a.bad = []; a.first = ""; return a; };
global.theDoc = doc;
const first = (code) => Math.min(...fields.filter(f => f.name.startsWith(code + ".") && f.pg !== tmpl).map(f => f.page));
const ran = [];
for (const code of Object.keys(D.scripts)) { const stub = global["lcRules_" + code]; global["lcRules_" + code] = function () { ran.push(code); return stub(); }; }
const out = [];
for (const st of JSON.parse(fs.readFileSync(process.argv[3], "utf8"))) {
  alerts.length = 0; printed.length = 0; global.lcWarnedAt = 0;
  for (const k of Object.keys(st.set || {})) doc.getField(k).value = st.set[k];
  let err = "";
  try {
    if (st.calc) {   // every form's calculation runs, as in Acrobat when a value changes: which forms' rules ran?
      const at = st.page, where = at === 0 ? 0 : at.startsWith("first:") ? first(at.slice(6)) : at.startsWith("extra:") ? doc.getField(at.slice(6) + ".__qr").page + 1 : doc.getField(at.slice(3) + ".__qr").page;
      doc.pageNum = where; ran.length = 0;
      global.event = {source: st.source ? {name: st.source} : null};
      for (const code of Object.keys(D.scripts)) new Function(D.calcs[code]).call(doc);
      global.event = {name: "WillSave"};
    } else if (st.go) vm.runInThisContext(D.menu + '\nopenForm(theDoc, "' + st.go + '");');
    else if (st.press) new Function(D.buttons[st.code][st.press]).call(doc);
  } catch (e) { err = String(e); }
  const info = {};
  for (const c of Object.keys(D.scripts)) info[c] = {first: first(c), qr: doc.getField(c + ".__qr").page, value: String(doc.getField(c + ".__qr").value).length};
  out.push({label: st.label, err, alerts: alerts.slice(), printed: printed.slice(), numPages: pages.length, pageNum: doc.pageNum, forms: info,
            answer: st.look ? doc.getField(st.look).value : null, ran: ran.slice()});
}
fs.writeFileSync(process.argv[4], JSON.stringify(out));
"""


def structure(pdf, codes):
    tops = [str(f.T) for f in pdf.Root.AcroForm.Fields]
    assert sorted(tops) == sorted(codes + ["ACCEPT"]), tops   # no OPEN field: nothing keeps a "which form is open" state
    assert [str(n) for n in pdf.Root.Names.Templates.Names[::2]] == sorted(c + "_qrx" for c in codes), "templates are not just the extra QR pages"
    menu_actions = [str(a.A.JS) for a in pdf.pages[0].obj.Annots if a.get("/Subtype") == "/Link"]
    assert sorted(menu_actions) == sorted(f'openForm(this, "{c}");' for c in codes), menu_actions   # one link per form
    with pdf.open_outline() as outline:
        marks = [str(i.action.JS) for i in outline.root if i.action is not None and "/JS" in i.action]
    assert sorted(marks) == sorted(menu_actions), "bookmarks"
    for n, page in enumerate(pdf.pages):
        if n:   # every form page: a plain jump to page 0, no script
            jumps = [a.A for a in page.obj.Annots if a.get("/Subtype") == "/Link" and a.A.get("/S") == "/GoTo"]
            assert any(j.D[0].objgen == pdf.pages[0].obj.objgen for j in jumps), f"page {n}: no Main menu jump"
    js = next(str(x.JS) for n, x in zip(*[iter(pdf.Root.Names.JavaScript.Names)] * 2) if str(n) == "00 menu")
    for gone in ("deletePages", "spawn", "hidden", "showForm", "showMenu", "OPEN"):
        assert gone not in js, f"the menu script still uses {gone}"
    return js


def main():
    pdf = pikepdf.open(build_all.OUT)
    codes = [c for _, forms in build_all.MENU for _, c in forms]
    menu = structure(pdf, codes)
    info = {c: load_pdf_for_harness(open(build_all.OUT, "rb").read(), c) for c in codes}
    base = info[codes[0]]
    fields = [f for f in base["fields"] if f["name"] != "OPEN"] + [{"name": "ACCEPT", "type": "checkbox", "page": 0}]
    total = 1 + sum(len(pikepdf.open(io.BytesIO(build(sp.FORM, sp.DEFAULTS))).pages)   # the menu + every form built on its own
                    for sp in (load_form(f) for _, forms in build_all.MENU for f, _ in forms))
    assert base["numPages"] == len(pdf.pages) == total, (base["numPages"], total)
    longest = {}
    for file, code in [f for _, forms in build_all.MENU for f in forms]:
        qs = [q for s in load_form(file).FORM["sections"] for q in s["fields"] if q["kind"] in ("text", "long")]
        longest[code] = code + "." + max(qs, key=lambda q: q.get("max") or 0)["id"]
    import random
    rng = random.Random(7)
    big = lambda c: {longest[c]: text_of(rng, 6000)}   # 3 codes
    small = lambda c: {longest[c]: text_of(rng, 500)}   # 1 code
    A, B, C = "LC", "BG", "SBLC"   # an early, a middle and a late form
    steps = [
        {"label": "go, terms not ticked", "go": B},
        {"label": "go, ticked", "go": B, "set": {"ACCEPT": "Yes"}},
        {"label": "go LC", "go": A}, {"label": "go SBLC", "go": C},
        {"label": "BG: 1 code", "code": B, "press": "generate-qr", "set": small(B)},
        {"label": "BG: print 1 code", "code": B, "press": "print-form"},
        {"label": "SBLC: 1 code", "code": C, "press": "generate-qr", "set": small(C)},
        {"label": "SBLC: print", "code": C, "press": "print-form"},
        {"label": "BG: 3 codes", "code": B, "press": "generate-qr", "set": big(B)},
        {"label": "BG: print 3 codes", "code": B, "press": "print-form"},
        {"label": "SBLC: print after BG grew", "code": C, "press": "print-form"},
        {"label": "go SBLC after BG grew", "go": C},
        {"label": "LC: 3 codes (BG has extras too)", "code": A, "press": "generate-qr", "set": big(A)},
        {"label": "LC: print", "code": A, "press": "print-form"},
        {"label": "BG: print again", "code": B, "press": "print-form"},
        {"label": "SBLC: print again", "code": C, "press": "print-form"},
        {"label": "calc: BG box, on BG", "calc": 1, "source": B + ".other_x", "page": "first:" + B},
        {"label": "calc: LC box, on BG", "calc": 1, "source": A + ".other_x", "page": "first:" + B},
        {"label": "calc: no source, on BG", "calc": 1, "source": None, "page": "first:" + B},
        {"label": "calc: no source, BG QR page", "calc": 1, "source": None, "page": "qr:" + B},
        {"label": "calc: no source, BG extra page", "calc": 1, "source": None, "page": "extra:" + B},
        {"label": "calc: no source, SBLC first page", "calc": 1, "source": None, "page": "first:" + C},
        {"label": "calc: no source, menu page", "calc": 1, "source": None, "page": 0},
        {"label": "reset BG", "code": B, "press": "reset-form", "look": longest[B]},
        {"label": "LC answer still there", "look": longest[A]},
    ]
    calcs = {}
    for f in pdf.Root.AcroForm.Fields:   # each form's hidden __checks calculation script
        if str(f.T) in codes:
            box = next(x for x in f.Kids if str(x.T) == "__checks")
            calcs[str(f.T)] = str((box if "/AA" in box else box.Kids[0]).AA.C.JS)
    with tempfile.TemporaryDirectory() as tmp:
        d, s, o = (os.path.join(tmp, n) for n in ("d.json", "s.json", "o.json"))
        h = os.path.join(tmp, "h.js")
        open(h, "w").write(HARNESS)
        json.dump({"fields": fields, "numPages": base["numPages"], "menu": menu, "scripts": {c: info[c]["script"] for c in codes},
                   "buttons": {c: info[c]["buttons"] for c in codes}, "calcs": calcs}, open(d, "w"))
        json.dump(steps, open(s, "w"))
        r = subprocess.run(["node", h, d, s, o], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        res = {x["label"]: x for x in json.load(open(o))}
    problems = []

    def want(cond, msg):
        if not cond:
            problems.append(msg)
    r = res["go, terms not ticked"]
    want(len(r["alerts"]) == 1 and "tick the box" in r["alerts"][0] and r["pageNum"] == 0, f"terms box not asked for: {r}")
    for label, code in (("go, ticked", B), ("go LC", A), ("go SBLC", C)):
        r = res[label]
        want(not r["err"] and not r["alerts"] and r["pageNum"] == r["forms"][code]["first"], f"{label}: page {r['pageNum']}, form starts at {r['forms'][code]['first']} {r['err']}")

    def printed_ok(label, code, extra):
        r = res[label]
        f = r["forms"][code]
        want(not r["alerts"] and r["printed"] == [[True, f["first"], f["qr"] + extra, False, True]], f"{label}: {r['printed']} {r['alerts']}, wanted {f['first']}-{f['qr'] + extra}")
    printed_ok("BG: print 1 code", B, 0)
    printed_ok("SBLC: print", C, 0)
    want(res["BG: 1 code"]["numPages"] == total and res["SBLC: 1 code"]["numPages"] == total, "1 code must not add pages")
    r0, r1 = res["SBLC: print"], res["BG: 3 codes"]
    want(r1["numPages"] == total + 1, f"BG 3 codes: {r1['numPages']} pages, wanted {total + 1}")
    want(r1["forms"][B]["first"] == r0["forms"][B]["first"], "BG moved itself")
    want(r1["forms"][C]["first"] == r0["forms"][C]["first"] + 1, "SBLC did not move down by 1 page")
    want(r1["forms"][C]["first"] == r1["forms"][B]["qr"] + 2, "BG's extra page is not between BG's QR page and the next form")
    printed_ok("BG: print 3 codes", B, 1)
    printed_ok("SBLC: print after BG grew", C, 0)
    want(res["go SBLC after BG grew"]["pageNum"] == res["go SBLC after BG grew"]["forms"][C]["first"], "menu link to SBLC after BG grew")
    rl = res["LC: 3 codes (BG has extras too)"]
    want(rl["numPages"] == total + 2, f"LC 3 codes: {rl['numPages']} pages, wanted {total + 2}")
    rp = res["LC: print"]
    want(rp["printed"] == [[True, rp["forms"][A]["first"], rp["forms"][A]["qr"] + 1, False, True]] and not rp["alerts"], f"LC print {rp['printed']} {rp['alerts']}")
    printed_ok("BG: print again", B, 1)
    printed_ok("SBLC: print again", C, 0)
    for label, ran in (("calc: BG box, on BG", [B]), ("calc: LC box, on BG", [A]), ("calc: no source, on BG", [B]), ("calc: no source, BG QR page", [B]),
                       ("calc: no source, BG extra page", [B]), ("calc: no source, SBLC first page", [C]), ("calc: no source, menu page", [])):
        want(res[label]["ran"] == ran and not res[label]["err"], f"{label}: rules ran for {res[label]['ran']} {res[label]['err']}, wanted {ran}")
    rr = res["reset BG"]
    want(rr["answer"] == "" and rr["numPages"] == total + 1, f"reset BG: answer {rr['answer'][:10]!r}, pages {rr['numPages']} (LC's extra stays)")
    want(len(res["LC answer still there"]["answer"]) == 6000, "reset BG cleared LC's answer")
    if problems:
        print("FAIL\n" + "\n".join(problems))
        sys.exit(1)
    print("PASS: 13 forms, %d pages, menu links, Print Form ranges, extra pages in the middle, Reset form (%d steps)" % (total, len(steps)))


if __name__ == "__main__":
    main()
