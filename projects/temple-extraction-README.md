# Phoenix Temple Document Extraction

Daily source-by-source checks inspect each of the temple's official pages in the registry, along with bounded same-site PDFs and image flyers (plus known image-CDN hosts). The pipeline extracts text from HTML, PyMuPDF PDF text, scanned PDF pages (Tesseract), and PNG/JPEG/WebP flyers (Tesseract).

**Publication safety:** This scan is a discovery/review system. It never auto-publishes dates detected by OCR or extracted using nearby text because date/title association can be ambiguous. Only separately verified manifest events and the existing official structured-event importers are published. Review candidates are published to `feeds/temple-review.json` and source diagnostics to `feeds/source-status.json`.

**Coverage:** Scans a maximum of 2 PDFs (18 pages per PDF) and 6 images per registered source per run. The report records each inspected asset, page count, OCR count, skipped candidates, errors and 403-blocked pages. Sites requiring login, anti-bot bypasses, or browser-only dynamic rendering may remain incomplete. This is transparent, bounded extraction, not a guarantee that every event online has been indexed.

**Adding a verified event:** Confirm title, exact date and time (or mark date-only), venue, official organizer link, and year. Add the entry to `projects/phoenix-temples/project.json` under `events`. Do not auto-publish OCR candidates without corroboration.

**Local tests:** `pip install -r projects/requirements-temples.txt` and `python -m unittest projects.test_temple_extraction -v`. For OCR tests install the system `tesseract` binary.
