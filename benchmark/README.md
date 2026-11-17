# LC form: QR code vs AI reading

10 fake filled-in LC applications (4 typed with QR code, 6 handwritten; clean / medium / poor scans), read back by
the form's QR code and by Gemini, scored against the true answers. Result: `LC-QR-vs-AI.xlsx`.

Run from this folder (inside lc-form; uses its `.venv`: pikepdf, Pillow, zxing-cpp):

    ../.venv/bin/python make_samples.py           # samples/<form>/page-1..4.jpg, truth.json, qr.txt
    ../.venv/bin/python run_qr.py                 # results/qr.json
    ../.venv/bin/python run_gemini.py gemini-3.7-flash   # results/<model>/*.json (key in .env, never committed)
    ../.venv/bin/python score.py                  # results/report.md, scores.json
    ../.venv/bin/python make_crops.py             # screenshots/ (pictures for the workbook)
    python3 build_excel.py                                # LC-QR-vs-AI.xlsx (needs openpyxl)

Free-tier Gemini: one request per form, one every 15 s, rate-limit waits as Google says, answers cached on disk.
`render.swift` renders PDF pages with macOS PDFKit; typed forms are flattened first (PDFKit redraws auto-size
boxes itself and clips long answers; Acrobat prints the saved look).
