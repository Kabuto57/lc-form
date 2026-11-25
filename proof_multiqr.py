#!/usr/bin/env python3
"""PROOF THAT GENERATE QR CODE MAKES AS MANY CODES AS THE ANSWERS NEED (up to 16).      python proof_multiqr.py

Acrobat can't be driven from here, so this runs the form's own JavaScript (the document script read back out of the
built PDF, not a copy) under Node, with a small stand-in for Acrobat's document (fields, pages, Template.spawn,
deletePages), then reads every QR code the script drew and decodes it with an independent decoder (zxing-cpp, a test
tool only: it is not a dependency of the build). It checks, for payloads of about 2,000 / 4,000 / 9,000 / 15,300
characters, that:  1, 2, 4 and 7 codes come out; each code carries the structured-append header (index, total, parity of
the whole text); the codes joined in order equal the payload exactly; nothing is shortened up to 16 codes; beyond 16
the long paragraphs are shortened and listed in "truncated"; shrinking the answers leaves no stale code on any page
(also when the viewer refuses deletePages); and the check Print Form uses notices a missing or blanked code.

Needs: node on the PATH, and zxing-cpp + pillow in the Python that runs this (zxing-cpp is NOT in requirements.txt).
The stand-in's page-renaming of Template.spawn(bRename: true) is a guess (Acrobat is not here): it is run in 3 styles.
"""
import io
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import zlib

import pikepdf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "forms"))

HARNESS = r"""
const fs = require("fs"), vm = require("vm");
const D = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const style = process.argv[3], blockDelete = process.argv[4] === "1";
const P = D.prefix, SFX = D.suffix;                // "" and "" for one form on its own; "LC." and "_LC" in the joined PDF
global.display = {visible: 0, hidden: 1, noPrint: 2, noView: 3};
global.color = {red: ["RGB", 1, 0, 0], black: ["G", 0], white: ["G", 1], transparent: ["T"]};
global.console = console;
const alerts = [], printed = [];
global.event = {name: "WillSave"};
const pages = [];                       // the pages in the document (objects); a template is not in this list
const tmpl = {id: "template"};
let fields = [];                        // {name, type, value, display, pg}
function mk(name, type, pg) {
  const f = {name: name, type: type, value: type == "checkbox" || type == "radiobutton" ? "Off" : "", display: 0, pg: pg};
  Object.defineProperty(f, "page", {get() { return pages.indexOf(f.pg); }});
  Object.defineProperty(f, "valueAsString", {get() { return String(f.value); }});
  return f;
}
for (let i = 0; i < D.numPages; i++) pages.push({id: "p" + i});
for (const f of D.fields) fields.push(mk(f.name, f.type, f.page >= 0 ? pages[f.page] : tmpl));
const byName = () => { const m = {}; for (const f of fields) m[f.name] = f; return m; };
let idx = byName();
const refresh = () => { idx = byName(); };
const doc = {
  calculate: true, pageNum: 0,
  get numPages() { return pages.length; },
  get numFields() { return fields.length; },
  getNthFieldName(i) { return fields[i].name; },
  getField(n) { return idx[n] || null; },
  print(...a) { printed.push(a); },
  resetForm(list) { for (const f of fields) if (f.type == "text" && (!list || f.name.startsWith(list[0] + "."))) f.value = ""; },   // (pages' renamed fields may not be caught: lcDrawQr clears them)
  getTemplate(n) {
    if (n !== D.template || !D.hasTemplate) throw new Error("no template " + n);
    return {spawn(o) {
      if (o.bRename !== true) throw new Error("bRename must be true");
      const pg = {id: "s" + pages.length}, at = Math.min(o.nPage, pages.length);
      pages.splice(at, 0, pg);
      const pre = style == "A" ? "P" + at + "." + D.template + "." : style == "B" ? "P" + at + "." + D.template + ".Form." : D.template + at + "_";
      for (const f of fields.filter(f => f.pg === tmpl && f.name.startsWith(P + "__qrx_"))) fields.push(Object.assign(mk(pre + f.name, f.type, pg), {display: f.display}));
      refresh();
    }};
  },
  deletePages(n) {
    if (blockDelete) throw new Error("deletePages is not allowed");
    const k = typeof n == "number" ? n : n.nStart;
    const gone = pages.splice(k, 1)[0];
    fields = fields.filter(f => f.pg !== gone);
    refresh();
  },
};
vm.runInThisContext(D.script);   // (app does not exist yet, so the on-open line of the script does not run)
global.app = {viewerType: "Reader", viewerVersion: "0", alert(m, i) { alerts.push(m); return 4; }};
global["lcRules" + SFX] = function () { const a = []; a.bad = []; a.first = ""; return a; };   // the rules engine is not under test here
const press = (name) => { alerts.length = 0; printed.length = 0; global["lcWarnedAt"] = 0; new Function(D.buttons[name]).call(doc); return {alerts: alerts.slice(), printed: printed.slice()}; };
const get = (n) => doc.getField(P + n);
const state = (label, text) => {
  const rows = {};
  for (const f of fields) {
    const m = /^(.*)__(qr[12]|qrx_[12])_(\d+)$/.exec(f.name);
    if (!m || f.pg === tmpl) continue;
    if (f.value !== "") (rows[(m[1] === P ? "" : m[1]) + m[2]] = rows[(m[1] === P ? "" : m[1]) + m[2]] || {})[m[3]] = f.value;
  }
  const own = f => f.pg !== tmpl && f.name.indexOf("__qr") >= 0;
  return {label: label, numPages: pages.length, rows: rows,
          check: global["lcQrCheck" + SFX] ? global["lcQrCheck" + SFX](doc, text) : "",
          last: global["lcLastPage" + SFX] ? global["lcLastPage" + SFX](doc, text) : get("__qr").page, qrPage: get("__qr").page,
          labels: fields.filter(f => /_label$/.test(f.name) && own(f) && f.value !== "").map(f => [f.name, f.value]),
          frames: fields.filter(f => /_frame$/.test(f.name) && own(f)).map(f => [f.name, f.display])};
};
const out = [];
for (const step of JSON.parse(fs.readFileSync(process.argv[5], "utf8"))) {
  for (const k of Object.keys(step.set)) get(k).value = step.set[k];
  let err = "", pressed = null, n = 0;
  if (step.reset) { press("reset-form"); }
  else { try { pressed = press("generate-qr"); } catch (e) { err = String(e); } }
  const text = String(get("__qr").value);
  const s = state(step.label, text);
  s.payload = text; s.err = err; s.n = text ? Math.ceil(Buffer.from(text, "latin1").length / 2300) : 0;
  s.generate = pressed;
  if (!step.reset && !err) {
    s.print = press("print-form");                       // right after Generate: prints, from the first form page to the last code page
    s.save = press("before-save");                       // nothing to warn about
    if (step.tamper) {                                   // negative cases: blanking a code must be noticed, and Print Form must refuse
      s.tamper = {};
      for (const c of step.tamper) {
        const keep = fields.filter(f => f.name.endsWith(c.field)).map(f => [f, f.value]);
        for (const [f] of keep) f.value = "";
        s.tamper[c.field] = {check: global["lcQrCheck" + SFX](doc, text), print: press("print-form"), save: press("before-save")};
        for (const [f, v] of keep) f.value = v;
      }
      const k = step.stale, was = get(k).value;
      get(k).value = was + " X";                         // answers changed after Generate: Print Form must refuse
      s.stale = press("print-form");
      get(k).value = was;
    }
  }
  out.push(s);
}
fs.writeFileSync(process.argv[6], JSON.stringify(out));
"""


def load_pdf_for_harness(pdf_bytes, joined_code=None):
    """What the Node stand-in needs from a built PDF: the form's document script, the button scripts, and its fields (name,
    kind, page number). For the joined PDF (joined_code = "LC"): that form's fields as "LC.name", scripts as scoped by
    build_all.py, the menu page 0 and the form's pages 1.., and every other form's fields too (so lcExtra has to ignore them)."""
    pdf = pikepdf.open(io.BytesIO(pdf_bytes))
    fields = []
    if joined_code:
        tpl = {str(n): p for n, p in zip(*[iter(pdf.Root.Names.Templates.Names)] * 2)}
        index = {p.objgen: int(n.split("_")[1]) + 1 for n, p in tpl.items() if n.startswith(joined_code + "_") and n[len(joined_code) + 1:].isdigit()}
        numPages = 1 + len(index)
        top = [(str(t.T) + ".", list(t.Kids)) for t in pdf.Root.AcroForm.Fields if "/Kids" in t and "/T" in t and str(t.T) not in ("ACCEPT", "OPEN")]
    else:
        index = {p.objgen: i for i, p in enumerate(pdf.pages)}
        numPages = len(pdf.pages)
        top = [("", list(pdf.Root.AcroForm.Fields))]
    by_name = {}
    for prefix, kids in top:
        for f in kids:
            flags = int(f.get("/Ff", 0))
            ft = str(f.get("/FT", ""))
            kind = ("button" if flags & 65536 else "radiobutton" if flags & 32768 else "checkbox") if ft == "/Btn" else \
                   "combobox" if ft == "/Ch" else "text"
            widgets = f.get("/Kids", [])
            page = index.get(widgets[0].P.objgen, -1) if widgets and "/P" in widgets[0] else -1
            fields.append({"name": prefix + str(f.T), "type": kind, "page": page if prefix in ("", f"{joined_code}.") else -1})
            by_name[prefix + str(f.T)] = f
    code = (joined_code + ".") if joined_code else ""
    if joined_code:
        names = pdf.Root.Names.JavaScript.Names
        script = next(str(names[i + 1].JS.read_bytes().decode("latin-1")) if isinstance(names[i + 1].JS, pikepdf.Stream) else str(names[i + 1].JS)
                      for i in range(0, len(names), 2) if str(names[i]).endswith(" " + joined_code))
    else:
        script = zlib.decompress(pdf.Root.Names.JavaScript.Names[1].JS.read_raw_bytes()).decode("latin-1")

    def js(action):
        return action.read_bytes().decode("latin-1") if isinstance(action, pikepdf.Stream) else str(action)
    buttons = {"generate-qr": js(by_name[code + "__generate_qr"].Kids[0].A.JS), "print-form": js(by_name[code + "__print_form"].Kids[0].A.JS),
               "reset-form": js(by_name[code + "__reset_form"].Kids[0].A.JS)}
    # before-save is the document's WS/WP action in a form on its own (the joined PDF has none: its Root.AA is not carried over)
    buttons["before-save"] = js(pdf.Root.AA.WS.JS) if "/AA" in pdf.Root else "var x = 1;"
    templates = pdf.Root.get("/Names", {}).get("/Templates")
    return {"script": script, "fields": fields, "numPages": numPages, "hasTemplate": bool(templates), "buttons": buttons,
            "prefix": code, "suffix": ("_" + joined_code) if joined_code else "", "template": (joined_code + "_qrx") if joined_code else "qrx"}


def text_of(rng, n, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz0123456789 .,-/()':?+#&@%\n"):
    return "".join(rng.choice(alphabet) for _ in range(n)).strip() or "X"


def read_matrix(rows):
    return [[1 if c == "n" else 0 for c in (rows.get(str(y), "").ljust(177))] for y in range(177)]


def decode(matrix):
    """Draw one code (modules 5 px, 4 modules of white margin) and decode it with zxing-cpp. Returns the bytes."""
    import zxingcpp
    from PIL import Image
    scale, q, n = 5, 4, len(matrix)
    img = Image.new("L", ((n + 2 * q) * scale,) * 2, 255)
    px = img.load()
    for y in range(n):
        for x in range(n):
            if matrix[y][x]:
                for dy in range(scale):
                    for dx in range(scale):
                        px[(x + q) * scale + dx, (y + q) * scale + dy] = 0
    res = zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.QRCode)
    assert len(res) == 1, f"decoder found {len(res)} codes"
    return res[0].bytes


def header_of(matrix):
    """The structured-append header (index, total, parity) of a version 40 / mask 0 / level M code, read straight from the
    matrix by an independent walk of the data modules (not the encoder's own code)."""
    N = 177
    func = [[False] * N for _ in range(N)]

    def mark(x0, y0, x1, y1):
        for y in range(max(0, y0), min(N, y1 + 1)):
            for x in range(max(0, x0), min(N, x1 + 1)):
                func[y][x] = True
    mark(0, 0, 8, 8); mark(N - 8, 0, N - 1, 8); mark(0, N - 8, 8, N - 1)   # finders + separators + format
    for i in range(N):
        func[6][i] = func[i][6] = True
    A = [6, 30, 58, 86, 114, 142, 170]
    for i, ax in enumerate(A):
        for j, ay in enumerate(A):
            if (i == 0 and j == 0) or (i == 0 and j == 6) or (i == 6 and j == 0):
                continue
            mark(ax - 2, ay - 2, ax + 2, ay + 2)
    mark(N - 11, 0, N - 9, 5); mark(0, N - 11, 5, N - 9)   # version info
    bits = []
    right = N - 1
    while right >= 1:
        if right == 6:
            right = 5
        up = ((right + 1) & 2) == 0
        for vert in range(N):
            y = N - 1 - vert if up else vert
            for j in range(2):
                x = right - j
                if not func[y][x]:
                    bits.append(matrix[y][x] ^ (1 if (x + y) % 2 == 0 else 0))
        right -= 2
    # de-interleave: 49 blocks, the first 18 have 47 data codewords, the other 31 have 48
    words = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits) - 7, 8)]
    lens = [47] * 18 + [48] * 31
    blocks = [[] for _ in lens]
    pos = 0
    for i in range(48):
        for b, ln in enumerate(lens):
            if i < ln:
                blocks[b].append(words[pos]); pos += 1
    data = [w for b in blocks for w in b]
    s = "".join(f"{w:08b}" for w in data[:6])
    assert s[:4] == "0011", f"no structured-append mode in {s[:4]}"
    return int(s[4:8], 2), int(s[8:12], 2) + 1, int(s[12:20], 2)


def run(info, steps, style, block_delete):
    with tempfile.TemporaryDirectory() as tmp:
        files = {n: os.path.join(tmp, n) for n in ("h.js", "d.json", "s.json", "o.json")}
        open(files["h.js"], "w").write(HARNESS)
        json.dump(info, open(files["d.json"], "w"))
        json.dump(steps, open(files["s.json"], "w"))
        r = subprocess.run(["node", files["h.js"], files["d.json"], style, "1" if block_delete else "0", files["s.json"], files["o.json"]],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        return json.load(open(files["o.json"]))


def check_step(st, want, info, block):
    """The problems found in one step's outcome (an empty list = it passed)."""
    notes = []
    n, payload, joined_pdf = st["n"], st["payload"], bool(info["prefix"])
    form_pages = info["numPages"]
    first_page = 1 if joined_pdf else 0                      # the joined PDF prints from page 1 (page 0 is the menu)
    if n != want["expect"]:
        notes.append(f"codes {n}, wanted {want['expect']}")
    if st["err"]:
        notes.append(st["err"])
    if n and not st["err"]:
        main_keys = sorted(k for k in st["rows"] if k in ("qr1", "qr2"))
        extra_keys = sorted((k for k in st["rows"] if "qrx" in k), key=lambda k: (int(re.search(r"(\d+)", k).group(1)), k[-1]))
        drawn = main_keys + extra_keys
        if len(drawn) != n:
            notes.append(f"{len(drawn)} codes drawn, {n} wanted")
        whole, joined, parities = payload.encode("utf-8"), b"", set()
        for j, k in enumerate(drawn):
            matrix = read_matrix(st["rows"][k])
            raw = decode(matrix)
            i, total, parity = header_of(matrix) if n > 1 else (0, 1, None)
            if n > 1 and (i, total) != (j, n):
                notes.append(f"code {j + 1}: header says {i + 1} of {total}")
            parities.add(parity)
            joined += raw
        if joined != whole:
            notes.append(f"joined text differs ({len(joined)} vs {len(whole)} bytes)")
        if n > 1:
            want_parity = 0
            for b in whole:
                want_parity ^= b
            if parities != {want_parity}:
                notes.append(f"parity {parities}, wanted {want_parity}")
        data = json.loads(payload)
        if n < 16 and "truncated" in data:
            notes.append(f"truncated {data['truncated']} with only {n} codes")
        if "cut" in want and data.get("truncated") != want["cut"]:
            notes.append(f"truncated is {data.get('truncated')}, wanted {want['cut']}")
        if len(payload) != n * 2300:
            notes.append(f"payload {len(payload)} characters, not padded to {n * 2300}")
        generated = " ".join(st["generate"]["alerts"])
        if len(st["generate"]["alerts"]) != 1 or (n > 1 and f"{n} QR codes" not in generated) or ("cut" in want) != ("shortened" in generated):
            notes.append(f"Generate's message is wrong: {generated[:90]!r}")
        # Print Form right after Generate: prints the form up to the last code in use, nothing more
        last = st["qrPage"] + max(0, (n - 1) // 2)
        if st["print"]["alerts"] or st["print"]["printed"] != [[True, first_page, last, False, True]]:
            notes.append(f"Print Form: {st['print']}, wanted one print of pages {first_page}-{last}")
        if st["last"] != last:
            notes.append(f"last page {st['last']}, wanted {last}")
        if st["save"]["alerts"]:
            notes.append(f"before-save warned: {st['save']['alerts']}")
        for field, t in (st.get("tamper") or {}).items():   # a blanked code must be noticed by the check, Print Form and saving
            if not t["check"] or t["print"]["printed"] or not any("do not match" in a for a in t["print"]["alerts"]):
                notes.append(f"blanking {field} was not stopped by Print Form: {t['print']}")
            if not joined_pdf and not any("not complete" in a for a in t["save"]["alerts"]):
                notes.append(f"blanking {field} was not warned about before saving")
        if st.get("stale") and (st["stale"]["printed"] or not any("answers have changed" in a for a in st["stale"]["alerts"])):
            notes.append("Print Form printed codes older than the answers")
    # nothing stale on any page: only the codes in use have rows, frames and labels
    if len(st["rows"]) != n:
        notes.append(f"{len(st['rows'])} slots have rows, {n} should")
    shown = sum(1 for _, d in st["frames"] if d == 0)
    if shown != max(0, n - 1):
        notes.append(f"{shown} frames visible, {max(0, n - 1)} should be")
    if sum(1 for _, v in st["labels"] if "not used" not in v) != (n if n > 1 else 0):
        notes.append("labels wrong: " + str(st["labels"]))
    extra_pages = st["numPages"] - form_pages
    if not block and extra_pages != max(0, (n - 1) // 2):
        notes.append(f"{extra_pages} extra pages, wanted {max(0, (n - 1) // 2)}")
    if block and extra_pages > max(0, (n - 1) // 2) and not any("not used" in v for _, v in st["labels"]):
        notes.append("a page left behind by a refused delete should say it is not used")
    if st["check"]:
        notes.append("check says: " + st["check"])
    return notes


def main():
    import zxingcpp  # noqa: F401  (fails early, clearly, when the decoder is missing)
    import build_all
    import pdf_writer
    from build import load_form
    spec = load_form("lc_form.py")
    standalone = load_pdf_for_harness(pdf_writer.build(spec.FORM, spec.DEFAULTS))
    # the joined PDF is built by build_all.py (python build_all.py first); the LC form's part of it is tested the same way
    joined = None
    if os.path.exists(build_all.OUT):
        joined = load_pdf_for_harness(open(build_all.OUT, "rb").read(), "LC")
    rng = random.Random(7)
    longs = [q["id"] for s in spec.FORM["sections"] for q in s["fields"] if q["kind"] == "long"]
    texts = {q["id"]: q["max"] for s in spec.FORM["sections"] for q in s["fields"] if q["kind"] == "text" and q.get("max", 0) >= 30}
    assert "goods_description" in longs and "additional_conditions" in longs
    base = {k: "" for k in longs + list(texts)}

    def answers(goods, cond, others=0):
        a = {"goods_description": text_of(rng, goods), "additional_conditions": text_of(rng, cond)}
        for k in list(texts)[:others]:
            a[k] = text_of(rng, texts[k])
        return a

    def step(label, a, **kw):
        return {"label": label, "set": {**base, **a}, "stale": list(texts)[0], **kw}
    bite = [{"field": "__qrx_1_0"}, {"field": "__qr1_0"}, {"field": "__qr2_0"}]
    steps = [
        step("2000", answers(900, 900), expect=1),
        step("4000", answers(1900, 1900), expect=2),
        step("9000", answers(4400, 4400), expect=4, tamper=bite),
        step("15300 (LC worst case)", answers(6500, 6500, others=len(texts)), expect=7, tamper=bite),
        step("back to 4000", answers(1900, 1900), expect=2),
        step("back to 2000", answers(900, 900), expect=1),
        step("oversized: 2 x 30000 chars", {"goods_description": text_of(rng, 30000), "additional_conditions": text_of(rng, 30000)}, expect=16, cut=["goods_description"], tamper=bite),
        step("oversized: 2 x 40000 chars", {"goods_description": text_of(rng, 40000), "additional_conditions": text_of(rng, 40000)}, expect=16, cut=["goods_description", "additional_conditions"]),
        step("back to 2000 after 16 codes", answers(900, 900), expect=1),
        {"label": "reset", "set": {}, "reset": True, "expect": 0},
    ]
    failures = checked = 0
    for what, info in (("one form", standalone), ("joined PDF", joined)):
        if info is None:
            print("NOTE: out/Trade-Application-Forms.pdf not built: run python build_all.py first to test the joined PDF too")
            continue
        for style in "ABC":
            for block in (False, True):
                for st, want in zip(run(info, steps, style, block), steps):
                    notes = check_step(st, want, info, block)
                    checked += 1
                    failures += bool(notes)
                    print(("FAIL " if notes else "PASS ") + f"[{what}, rename {style}, deletePages {'blocked' if block else 'allowed'}] {want['label']:30} codes={st['n']:2} pages={st['numPages']}"
                          + ("  " + "; ".join(notes) if notes else ""))
    print(f"ALL PASS ({checked} steps)" if not failures else f"{failures} of {checked} steps FAILED")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
