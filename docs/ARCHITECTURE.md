# Hub architecture

`config/feeds.json` → `scripts/build.py` (read-only HTTPS fetch + RFC5545 parsing + freshness checks) → `dist/status.json` and `dist/index.html` → GitHub Actions → GitHub Pages if enabled.

Sources: Panchangam (monthly), OTT (daily), and Arizona Bulk Trash (daily). Source repositories retain independent deployment. No API tokens, database, backend, extra Python packages or personally identifying input.

A GitHub Actions job runs tests before monitoring. It writes the health report, publishes degraded-status pages when Pages is enabled, and fails after publishing if any enabled feed is unhealthy. Static dashboard checkboxes use browser localStorage for personal view preferences; they do not modify ICS files.

The monitoring parser supports the Phoenix-focused event dates and UTF-8 folded iCalendar lines; event times using unknown TZID values are omitted from the upcoming-events preview rather than guessing a timezone.
