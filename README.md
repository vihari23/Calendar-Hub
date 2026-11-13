# Vihari Calendar Hub

A standalone, **read-only** monitoring dashboard for three public Apple Calendar ICS subscriptions.

- Phoenix Telugu Panchangam
- India OTT Releases
- Arizona Home Bulk Trash

**Personal Important Dates is private and is not monitored or published here.**

The dashboard reads the published ICS URLs, checks freshness and calendar structure, lists upcoming public events, and provides subscription links. It never edits the original calendars.

After enabling **Settings → Pages → Source: GitHub Actions**, run **Actions → Monitor Calendar Feeds and Publish Hub → Run workflow** or push a change to `main` to publish the dashboard.

The dashboard is published by the existing monitoring workflow; enabling Pages alone does not trigger an immediate deployment.

Expected site: https://vihari23.github.io/Calendar-Hub/

**Maintenance:** edit `config/feeds.json` to add a public ICS feed, then view `Actions` to check monitoring. Daily check at 9:30 AM Phoenix (16:30 UTC); GitHub scheduling can be delayed. Detailed procedures are in `docs/MAINTENANCE.md`.

## iPhone Home Screen app

Calendar Hub is a lightweight Progressive Web App (PWA), not an App Store app. Open https://vihari23.github.io/Calendar-Hub/ in **Safari** on iPhone, then tap **Share → Add to Home Screen → Add**. Launching the Home Screen icon opens an app-style standalone view without Safari's usual address bar.

The `static/` directory contains the manifest, service worker and icons. The generator copies these assets into the published site. Offline viewing shows the last cached dashboard with a clear warning; the `status.json` health report is **not** cached. To update the PWA's cached asset bundle after changing the app shell, increment the `CACHE` version in `static/sw.js`.

There is no native iOS Home Screen **widget** or Apple Calendar control; this is a standalone Home Screen app icon linked to the dashboard.
