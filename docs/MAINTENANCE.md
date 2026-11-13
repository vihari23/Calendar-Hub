# Maintaining the Calendar Hub

## Add or edit feeds

Edit **only `config/feeds.json`** for typical changes. Give each feed a unique stable `id`; use a publicly reachable HTTPS ICS URL; provide source repository, name, expected update cadence, staleness threshold and minimum event count. Do **not** add private calendar subscription URLs or home addresses.

Run `python -m unittest discover -s tests -v` locally, then commit. On push, GitHub Actions runs the tests, downloads source calendars, generates `index.html` and `status.json`, and publishes the site if Pages is enabled.

GitHub Pages: **Settings → Pages → Build and deployment → Source: GitHub Actions**. Site: https://vihari23.github.io/Calendar-Hub/.

## Status meanings

- **healthy:** ICS loads, is structurally valid, contains enough events and its newest `DTSTAMP` is fresh.
- **stale:** ICS is readable but last generation exceeds `max_age_hours`.
- **error:** unable to read/parse feed or insufficient events.
- **disabled:** ignored from monitoring via `enabled: false`.

These are feed-health checks, **not** guarantees of correctness for individual release dates or city collection schedules. Apple Calendar may refresh on a different cadence.

## Troubleshooting and rollback

Open **Actions → Monitor Calendar Feeds and Publish Hub** and inspect the latest run. On failure, view the `calendar-health-report` artifact and the `status.json` feed detail. Fix the issue **in the original source project** if necessary. The Hub does not edit source calendars.

To roll back an erroneous hub change, use GitHub's Revert on the commit or restore the last working `config/feeds.json`. A hub outage doesn't affect existing ICS subscriptions.

The health report includes public event titles only. Personal Important Dates and private family events are excluded. The site's calendar checkboxes filter the website only, not the Apple Calendar app.

The job runs daily at **16:30 UTC = 9:30 AM Phoenix**, with timing subject to GitHub Actions delays. It will alert via GitHub workflow notifications if a source fails and notifications are enabled.

## PWA and iOS installation

The PWA source files live in `static/`. When you change app design or assets, keep `static/manifest.webmanifest`, the three PNG icons and `static/sw.js` together; `scripts/build.py` copies them to `dist/`. Bump the service worker `CACHE` identifier to invalidate old shell assets. To test, open the site in Safari on an iPhone and use **Share → Add to Home Screen**. The app launches in standalone mode; it is not a Home Screen widget.

The service worker caches the HTML shell for **offline fallback only**; online navigation fetches a fresh dashboard. It does not cache `status.json`. Offline data is visibly labeled as a potentially outdated snapshot.
