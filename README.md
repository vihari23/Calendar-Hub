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

## App icon maintenance

The installed app icon has one source of truth: `static/icon-source.png` (an optimized rendering of the original design). The standard-library script `scripts/icon_render.py` generates the 180px Apple touch icon and 192px/512px manifest icons on every publish. No third-party image tooling is needed. The browser favicon uses the generated 192px PNG. Changes to `static/sw.js` use a versioned cache identifier so installed apps refresh their offline assets.

## iPhone Home Screen widgets (Scriptable)

The Hub now publishes a **true iPhone Home Screen widget** through Scriptable, using `scriptable/CalendarHubWidget.js`. Open https://vihari23.github.io/Calendar-Hub/widget-setup.html on your iPhone in Safari for the copy/install guide.

When run normally in Scriptable, the widget script exposes **Manage calendars + colors** (add custom HTTPS ICS subscriptions, assign colors, rename and remove) and **Manage widget views** (select calendars independently for each named widget view). All custom ICS URLs/settings are stored **locally on the iPhone**. Built-in feeds use the Hub's public `widget.json`; custom ICS feeds are downloaded directly by your iPhone, with a 90-minute on-device cache and offline fallback.

To place widgets: Home Screen → ＋ → Scriptable → Medium/Large → Edit Widget → select the script → enter a view ID such as `all`, `culture`, `entertainment`, or `home` in **Parameter**. Add multiple widgets with different parameters. Tapping a widget opens a scrollable on-device agenda.

The widget is **not a custom native iOS app extension**; it relies on Scriptable, and iOS ultimately controls refresh frequency. Complex RRULEs and time-zone rules in arbitrary external ICS feeds may require using Apple Calendar for authoritative date rendering. Private calendar URLs never appear in the public Hub.

**Widget privacy:** custom feeds and colors are saved only in Scriptable's local library directory. To see a new ICS feed in your widgets, use Scriptable → Calendar Hub Widget → Manage calendars + colors. Each widget uses the view named by its widget **Parameter**. The Calendar Hub's public dashboard does **not** automatically include your locally added calendars. Scriptable widgets display a limited event preview; tapping the widget opens the fully scrollable on-device agenda. For recurring feeds with complex RRULEs or time zones, double-check dates against Apple Calendar.

## Full-page iPhone widget (iOS 27+)

A separate [Scripting full-page portrait widget](scripting/README.md) is available. Download the generated [importable project ZIP](https://vihari23.github.io/Calendar-Hub/CalendarHubFullPage.zip) or import the project from `https://github.com/vihari23/Calendar-Hub/tree/main/scripting` in the Scripting iPhone app. Installation is device-dependent: desktop tests passing does not verify actual iPhone rendering.

**Easier import (no ZIP):** [One-tap Scripting remote import](https://scripting.fun/import_scripts?urls=%5B%22https%3A%2F%2Fgithub.com%2Fvihari23%2FCalendar-Hub%2Ftree%2Fmain%2Fscripting%22%5D) or download [CalendarHubFullPage.scripting](https://vihari23.github.io/Calendar-Hub/CalendarHubFullPage.scripting). The regular ZIP is retained for advanced inspection and remote import by URL; avoid relying on the iOS file picker to treat it as a Scripting script.
