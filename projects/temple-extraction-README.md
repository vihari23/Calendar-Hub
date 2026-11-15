# Phoenix Temple Document Extraction

Daily source-by-source checks inspect each of the temple's official pages in the registry, along with bounded same-site PDFs and image flyers (plus known image-CDN hosts). The pipeline extracts text from HTML, PyMuPDF PDF text, scanned PDF pages (Tesseract), and PNG/JPEG/WebP flyers (Tesseract).

**Publication safety:** This scan is a discovery/review system. It never auto-publishes dates detected by OCR or extracted using nearby text because date/title association can be ambiguous. Only separately verified manifest events and the existing official structured-event importers are published. Review candidates are published to `feeds/temple-review.json` and source diagnostics to `feeds/source-status.json`.

**Coverage:** Scans a maximum of 2 PDFs (18 pages per PDF) and 6 images per registered source per run. The report records each inspected asset, page count, OCR count, skipped candidates, errors and 403-blocked pages. Sites requiring login, anti-bot bypasses, or browser-only dynamic rendering may remain incomplete. This is transparent, bounded extraction, not a guarantee that every event online has been indexed.

**Adding a verified event:** Confirm title, exact date and time (or mark date-only), venue, official organizer link, and year. Add the entry to `projects/phoenix-temples/project.json` under `events`. Do not auto-publish OCR candidates without corroboration.

**Local tests:** `pip install -r projects/requirements-temples.txt` and `python -m unittest projects.test_temple_extraction -v`. For OCR tests install the system `tesseract` binary.

**Source-specific dated importers:** Sri Bhakta Hanuman Temple's upcoming programs and Sri Lalitha Temple's explicit-year Upcoming Events table are parsed with `projects/dated_temple_events.py`. Only explicitly dated future special events are eligible. Day-of-week mismatches, undated month grids, and recurring weekday schedules never generate future dates. An absent or out-of-date event schedule is not disguised as a healthy event import: `feeds/temple-review.json` records `dated_schedule_status`, `latest_explicit_event_date`, `dated_entries_found`, and `auto_published`. The publisher warns on stale calendars and fails its public verification if the source-specific importer does not produce diagnostics. When ceremony hours are not confirmed, 08:00–09:00 is clearly labeled as an unverified reminder window.


## Flyer-to-ICS completeness validation

The publishing pipeline now writes **`feeds/temple-reconciliation.json`** alongside
`temple-review.json`. It independently parses the generated Phoenix Temple ICS,
compares the confirmed `projects/phoenix-temples/project.json` curated event
registry and `verified_flyer_events` ledger, and reports:

- `missing`: a confirmed, still-relevant event absent from generated ICS;
- `duplicates`: two ICS events with the same title and date;
- `source_duplicates_removed`: duplicate importer inputs collapsed by the ICS generator;
- `time_conflicts`: a confirmed flyer start time differs from the generated ICS time;
- `ocr_review`: image/PDF-only discoveries that may indicate missing events, **not verified**;
- `source_coverage_gaps`: incomplete, inaccessible, or outdated source pages.

The verified ledger tracks exact `calendar_title`, `date`, `start_time`
(`HH:MM`, America/Phoenix), `source_name`, and official `source_url`.
Add a ledger entry **only after individually checking the organizer's poster**;
unknown ending times may use a clearly marked calendar-only display window.
The system skips ended calendar events to avoid false missing warnings.

GitHub Actions validates the live, publicly deployed reconciliation report and
fails post-deployment validation if `verified_passed` is false. This makes the
diagnostic report accessible even when validation fails. OCR-only findings never
autopublish or fail verified-source reconciliation without independent confirmation.

Run tests with:

```bash
python -m unittest projects.test_temple_reconciliation -v
```

A syntactically healthy ICS or a completed image scan does not imply full
completeness. The audit is restricted to accessible registered source pages,
bounded image/PDF scans, and manually verified poster events.
