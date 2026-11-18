"""Reads the vendor form's XFA template: finds the element behind each harvested SOM path, and its styling."""
import re
import xml.etree.ElementTree as ET

CONTAINERS = {"subform", "field", "draw", "exclGroup", "subformSet", "area", "pageSet", "pageArea", "contentArea"}
MM = 72 / 25.4


def tag(e):
    return e.tag.split("}")[-1]


def length(s, default=0.0):
    """An XFA measurement ("3.5mm", "8pt", "0.25in") in points."""
    if s is None or s == "":
        return default
    m = re.match(r"^\s*(-?[\d.]+)\s*(mm|pt|in|cm)?\s*$", s)
    if not m:
        return default
    v = float(m.group(1))
    return {"mm": v * MM, "cm": v * MM * 10, "in": v * 72, "pt": v, None: v * 72}[m.group(2)]


class Template:
    def __init__(self, path):
        self.root = ET.parse(path).getroot()
        self.by_som = {}
        self.parent = {c: p for p in self.root.iter() for c in p}
        form1 = next(e for e in self.root if tag(e) == "subform")
        self._index(form1, "xfa[0].form[0]." + "form1[0]")

    def _index(self, e, som):
        self.by_som[som] = e
        counts = {}
        for c in e:
            t = tag(c)
            if t not in CONTAINERS:
                continue
            name = c.get("name")
            key = name if name else "#" + t
            i = counts.get(key, 0)
            counts[key] = i + 1
            self._index(c, f"{som}.{key}[{i}]")

    def find(self, som):
        """The template element for a harvested SOM path (a repeated instance maps to its definition)."""
        if som in self.by_som:
            return self.by_som[som]
        parts = som.split(".")
        for k in range(len(parts) - 1, 0, -1):   # repeated subform instances: try index 0 from the right
            trial = parts[:k] + [re.sub(r"\[\d+\]$", "[0]", parts[k])] + parts[k + 1:]
            if ".".join(trial) in self.by_som:
                return self.by_som[".".join(trial)]
            parts = trial
        # unnamed subforms can be numbered differently at run time: match them with any number
        pieces = [r"#subform\[\d+\]" if p.startswith("#subform[") else re.escape(p) for p in parts]
        pat = re.compile("^" + r"\.".join(pieces) + "$")
        hits = [k for k in self.by_som if pat.match(k)]
        return self.by_som[hits[0]] if len(hits) == 1 else None


def child(e, *names):
    """The first descendant along a chain of child tags (e.g. child(field, "ui", "textEdit"))."""
    for n in names:
        if e is None:
            return None
        e = next((c for c in e if tag(c) == n), None)
    return e


def kids(e, name):
    return [c for c in e if tag(c) == name] if e is not None else []
