# Vihari Calendar Hub

A standalone, **read-only** monitoring dashboard for three public Apple Calendar ICS subscriptions.

- Phoenix Telugu Panchangam
- India OTT Releases
- Arizona Home Bulk Trash

**Personal Important Dates is private and is not monitored or published here.**

The dashboard reads the published ICS URLs, checks freshness and calendar structure, lists upcoming public events, and provides subscription links. It never edits the original calendars.

After first successful workflow run, enable GitHub Pages from **Settings → Pages → Source: GitHub Actions**.

Expected site: https://vihari23.github.io/Calendar-Hub/

**Maintenance:** edit `config/feeds.json` to add a public ICS feed, then view `Actions` to check monitoring. Daily check at 9:30 AM Phoenix (16:30 UTC); GitHub scheduling can be delayed. Detailed procedures are in `docs/MAINTENANCE.md`.
