"""TERMS: the old smart form's terms and conditions pages -> terms.json (used by build_all.py).

    python smartform/make_terms.py

Reads the text Acrobat drew on the old terms pages (data/raw/*TermsAndConditions*.layout.json, from harvest.py),
puts it back in reading order (left column, then right column; a number such as "1." or "(a)" joined to its text)
and saves it as paragraphs.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = {"LC": (["LCTermsAndConditions"], "Terms and Conditions: Irrevocable Documentary Credit"),
           "EBLC": (["EBLCTermsAndConditions", "EBLCTermsAndConditions1"], "Terms and Conditions: Handling / Financing of Documents under Export Documentary Credit"),
           "OBC": (["OBCTermsAndConditions"], "Terms and Conditions: Export Documentary Collection")}


def clean(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("–", "-").replace(" ", " ")
    return re.sub(r"[ \t]+", " ", s).strip()


def paragraphs(section):
    items = [it for it in json.load(open(os.path.join(HERE, "data", "raw", f"{section}.layout.json")))["base"]
             if it["cls"] == "draw" and it["vis"] and not it["master"] and (it.get("text") or "").strip()]
    number = re.compile(r"\s*\(?[a-z0-9ivx]{1,4}[.)]\s*")
    # a paragraph number is drawn a point or two lower than its text: sort it just before
    items.sort(key=lambda it: (it["page"], it["x"] > 290, it["y"] - (5 if number.fullmatch(it["text"]) else 0), it["x"]))
    out, last = [], None
    for it in items:
        text = clean(it["text"])
        if re.fullmatch(r"TERMS AND CONDITIONS.*", text.split("\n")[0].strip()):
            continue   # the page title: build_all.py writes its own
        key = (it["page"], it["x"] > 290, round(it["y"] / 4))
        if last and key == last and out:
            out[-1] += " " + text
        else:
            out.append(text)
        last = key
    result = []
    for p in out:   # long texts drawn as one box keep their own line breaks as paragraphs
        result += [clean(x) for x in re.split(r"\n\s*\n|\n(?=\s*(?:\(?[a-z0-9ivx]{1,4}[.)]\s))", p) if clean(x)]
    joined = []   # a number drawn on its own ("2.") belongs to the paragraph after it
    for p in result:
        if joined and re.fullmatch(r"\(?[a-z0-9ivx]{1,4}[.)]", joined[-1]):
            joined[-1] += " " + p
        else:
            joined.append(p)
    return joined


terms = {key: {"title": title, "paragraphs": [p for s in sections for p in paragraphs(s)]} for key, (sections, title) in SOURCES.items()}
json.dump(terms, open(os.path.join(os.path.dirname(HERE), "terms.json"), "w"), indent=1, ensure_ascii=False)
for k, v in terms.items():
    print(k, len(v["paragraphs"]), "paragraphs", sum(len(p) for p in v["paragraphs"]), "characters")
