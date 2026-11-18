"""Asks a Gemini model to read each sample's 3 question pages into JSON, and times it.

    ../.venv/bin/python run_gemini.py --list-models               which models this key can use
    ../.venv/bin/python run_gemini.py MODEL --only 01             one trial request
    ../.venv/bin/python run_gemini.py MODEL                       every sample not done yet

The key comes from GEMINI_API_KEY, or from a line GEMINI_API_KEY=... in .env in this folder. It is never printed.

Free-tier limits (per Google Cloud project, not per key): about 5 requests a minute and 20 a day for the Flash models.
So: ONE request per form (all 3 pages in it), at most one request every 15 seconds, on a rate-limit error wait as long
as Google says (at most 2 retries), never retry other errors, and save every answer to results/<model>/<sample>.json
so a re-run never spends quota on a form already done. Standard library only (no Google SDK).
"""
import base64
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "forms"))
sys.dont_write_bytecode = True
import lc_form   # noqa: E402

API = "https://generativelanguage.googleapis.com/v1beta"
GAP = 15          # seconds between requests (5 a minute allowed)
RETRIES = 2


def key():
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"]
    path = os.path.join(HERE, ".env")
    if os.path.exists(path):
        for line in open(path):
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("No key: put GEMINI_API_KEY=... in .env in this folder (it is git-ignored and never printed).")


def call(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key()})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def list_models():
    for m in call(f"{API}/models?pageSize=200")["models"]:
        if "generateContent" in m.get("supportedGenerationMethods", []):
            print(m["name"].split("/", 1)[1], "-", m.get("displayName", ""))


def questions_text():
    """Every question the AI must look for: number, id, label, kind and options, in form order."""
    lines = []
    for s, section in enumerate(lc_form.FORM["sections"], 1):
        lines.append(f"Section {s}: {section['title']}")
        for i, q in enumerate(section["fields"], 1):
            kind = q["kind"]
            what = {"text": "text", "long": "text (paragraph)", "date": 'date "DD/MM/YYYY"', "check": "tick box: true if ticked",
                    "radio": "pick one, exactly one of", "select": "one of", "checks": "list of every ticked option, from"}[kind]
            opts = f" {json.dumps(q['options'])}" if q.get("options") and kind != "check" else ""
            lines.append(f'  {s}.{i} "{q["id"]}": {q["label"]} -> {what}{opts}')
    return "\n".join(lines)


PROMPT = """You are reading a scanned, filled-in bank form: "Irrevocable Documentary Credit Application" (3 pages of
questions). It may be typed or handwritten, and the scan may be tilted, blurred or dark.

Return ONE JSON object with the answers the applicant gave. Keys are the question ids below. Rules:
- Include ONLY questions that have an answer on the form. Leave out blank questions (no key, no null, no "").
- Copy text exactly as written (letters, digits, punctuation), in upper case. Don't correct spelling or add words.
- Dates: "DD/MM/YYYY" (e.g. written "6/11/2026" or "6 NOV 2026" -> "06/11/2026").
- Pick-one and drop-down questions: the option text exactly as listed (a handwritten answer in a drop-down box
  that matches an option -> that option's exact text).
- Tick boxes (one box): true if ticked or crossed. Tick-any questions: a list of the ticked options' exact text.
- Section 4 "For Bank Use Only" is filled by the Bank: include it only if something is written there.

Questions (number, id, label -> how to answer):
"""


def ask(model, folder):
    parts = [{"text": PROMPT + questions_text()}]
    for page in (1, 2, 3):
        with open(os.path.join(folder, f"page-{page}.jpg"), "rb") as f:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(f.read()).decode()}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    for attempt in range(RETRIES + 1):
        start = time.perf_counter()
        try:
            reply = call(f"{API}/models/{model}:generateContent", body)
            seconds = time.perf_counter() - start
            text = "".join(p.get("text", "") for p in reply["candidates"][0]["content"]["parts"] if not p.get("thought"))
            return {"answers": json.loads(text), "seconds": round(seconds, 2), "usage": reply.get("usageMetadata", {}),
                    "attempts": attempt + 1, "error": None}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            if e.code == 429 and attempt < RETRIES:
                wait = re.search(r'"retryDelay":\s*"(\d+)', detail)
                wait = int(wait.group(1)) + 2 if wait else 60
                print(f"  rate limited, waiting {wait} s (retry {attempt + 1} of {RETRIES})")
                time.sleep(wait)
                continue
            return {"answers": {}, "seconds": None, "attempts": attempt + 1, "error": f"HTTP {e.code}: {detail[:400]}"}
        except (ValueError, KeyError, IndexError) as e:   # no usable JSON in the reply
            return {"answers": {}, "seconds": round(time.perf_counter() - start, 2), "attempts": attempt + 1,
                    "error": f"bad reply: {e}"}


def main():
    if "--list-models" in sys.argv:
        return list_models()
    model = sys.argv[1]
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    out_dir = os.path.join(HERE, "results", model)
    os.makedirs(out_dir, exist_ok=True)
    last = 0.0
    for folder in sorted(glob.glob(os.path.join(HERE, "samples", "*"))):
        name = os.path.basename(folder)
        out = os.path.join(out_dir, name + ".json")
        if (only and not name.startswith(only)) or (os.path.exists(out) and not json.load(open(out)).get("error")):
            continue
        time.sleep(max(0.0, GAP - (time.time() - last)))
        last = time.time()
        print(f"{name} ...", flush=True)
        result = ask(model, folder)
        with open(out, "w") as f:
            json.dump(result, f, indent=1, ensure_ascii=False)
        print(f"  {len(result['answers'])} answers, {result['seconds']} s", result["error"] or "")
        if result["error"] and "HTTP 429" in result["error"]:
            print("Still rate limited: stopping (finished samples are saved; run again later to continue).")
            break


if __name__ == "__main__":
    main()
