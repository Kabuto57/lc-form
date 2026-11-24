#!/usr/bin/env python3
"""LAG CHECK: how long does one field commit take in Acrobat?   (macOS, Adobe Acrobat Pro, a person at the screen)

    python tools/lag_check.py out/LC-Application.pdf out/Trade-Application-Forms.pdf

Opens each PDF in Acrobat the way a person does (`open -a`: a PDF opened by a script's app.openDoc does not always get
its document scripts), then simulates what happens when someone types in a box and clicks the next one:
    calc   = the value is committed (Acrobat runs the calculations: the hidden __checks fields)
    blur   = the box's Lost-Focus script (the document function lcRules, called with the field's name)
    commit = calc + blur, in ms. Three fields are tried (a plain text box, the amount, a date); the average of 10 each.
A joined PDF (Trade-Application-Forms.pdf) is first told to open the LC form (ticks the terms box, calls showForm).
To compare before and after a change, run it on the PDF built before and on the one built after (copy the "before" PDF
elsewhere first: a build overwrites out/).
Only the document it opened is closed (without saving); other open documents are never touched. If Acrobat shows a
prompt (Grant Access, a message box), the check gives up after 5 minutes: close the prompt and run it again.
"""
import os
import subprocess
import sys
import time

APP = "Adobe Acrobat"
FIND = 'var d = null, i; for (i = 0; i < app.activeDocs.length; i++) if (app.activeDocs[i].path.indexOf("__PATH__") >= 0) d = app.activeDocs[i];'
READY = FIND + ' d ? typeof d.__FN__ : "nodoc";'
JS = FIND + r"""
var out = [];
try {
  var JOINED = __JOINED__, pre = JOINED ? "LC." : "", fn = JOINED ? "lcRules_LC" : "lcRules";
  if (JOINED) { d.getField("ACCEPT").checkThisBox(0, true); d.showForm(d, "LC"); }
  var tests = [["applicant_name", function (i) { return "Acme " + i; }], ["amount", function (i) { return String(1000 + i); }],
               ["application_date", function (i) { return "0" + (1 + (i + 2) % 9) + "/01/2026"; }]];
  for (var k = 0; k < tests.length; k++) {
    var name = pre + tests[k][0], f = d.getField(name), calc = 0, blur = 0, N = 10, t;
    if (!f) { out.push(tests[k][0] + ": no such field"); continue; }
    for (i = -2; i < N; i++) {
      t = Date.now(); f.value = tests[k][1](i); t = Date.now() - t; if (i >= 0) calc += t;
      t = Date.now(); d[fn](d, name); t = Date.now() - t; if (i >= 0) blur += t;
    }
    out.push(tests[k][0] + ": calc " + (calc / N).toFixed(0) + " ms, blur " + (blur / N).toFixed(0) + " ms, commit " + ((calc + blur) / N).toFixed(0) + " ms");
  }
} catch (e) { out.push("ERR " + e); }
out.join("\n");
"""
CLOSE = FIND + " if (d) { d.dirty = false; d.closeDoc(true); } 'closed';"


def run(js, path, joined, wait=300):
    js = js.replace("__PATH__", path).replace("__JOINED__", "true" if joined else "false").replace("__FN__", "showForm" if joined else "lcRules")
    js = " ".join(line.strip() for line in js.strip().splitlines())
    script = ('on run argv\nset js to item 1 of argv\nset r to ""\nwith timeout of %d seconds\ntell application "%s"\nset r to do script js\n'
              'end tell\nend timeout\nreturn r\nend run' % (wait, APP))
    r = subprocess.run(["osascript", "-e", script, js], capture_output=True, text=True, timeout=wait + 30)
    return (r.stdout + r.stderr).strip()


def measure(pdf):
    path = os.path.abspath(pdf)
    joined = "Trade-Application-Forms" in path
    run(CLOSE, path, joined)   # a copy of this very file already open (e.g. from an earlier run) would be reused
    subprocess.run(["open", "-a", APP, path], check=True)
    for _ in range(int(os.environ.get("LAG_WAIT", 60))):   # seconds to wait until its document scripts are loaded
        if run(READY, path, joined, 30) == "function":
            break
        time.sleep(1)
    else:
        return "the document's scripts did not load in time (set LAG_WAIT=seconds to wait longer) (is JavaScript on in Acrobat? a prompt on screen?)"
    try:
        return run(JS, path, joined)
    finally:
        run(CLOSE, path, joined)


if __name__ == "__main__":
    for pdf in sys.argv[1:] or ["out/LC-Application.pdf", "out/Trade-Application-Forms.pdf"]:
        print(os.path.basename(pdf))
        print("  " + measure(pdf).replace("\n", "\n  "))
