"""Reads each typed sample's QR code(s) from its scanned last page, the way the Bank would, and times it.

    ../.venv/bin/python run_qr.py      -> results/qr.json

Uses lc-form's own reader (read_qr.py: codes_in + join), so this is exactly what the Bank's side does.
"""
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.dont_write_bytecode = True
from read_qr import codes_in, join   # noqa: E402


def main():
    results = {}
    for folder in sorted(glob.glob(os.path.join(HERE, "samples", "*-typed-*"))):
        name = os.path.basename(folder)
        start = time.perf_counter()
        try:
            payload, n = join(codes_in(os.path.join(folder, "page-4.jpg")))
            data, error = payload["data"], None
        except SystemExit as e:   # read_qr stops with a message when it can't read the code(s)
            data, n, error = {}, 0, str(e)
        seconds = time.perf_counter() - start
        results[name] = {"answers": data, "seconds": round(seconds, 3), "codes": n, "error": error}
        print(f"{name}: {n} code(s), {seconds:.2f} s", error or "")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "qr.json"), "w") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
