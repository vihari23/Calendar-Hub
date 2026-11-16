# Verified public-event ICS projects

Four independent calendar projects live in this repository because the available GitHub integration cannot create separate repositories. Every subproject owns its source registry and curated event ledger in \`project.json\`; feed generation is centralized to avoid duplicated iCalendar bugs. Public feeds never contain private data.

- \`arizona-telugu\`: Phoenix-metro Telugu/Telangana cultural events. General Indian/Tamil/Kannada programs are excluded.
- \`phoenix-temples\`: special temple functions only. Weekly and daily pujas are intentionally excluded.
- \`workday-releases\`: curated Workday release dates, weekly release-note and What's New report checks, weekly Sandbox refresh verification reminders, and 2027 R1/R2 Preview planning checkpoints. All estimated or recurring entries are visibly tentative; exact tenant refresh dates require Workday Community verification.
- \`phoenix-road-closures\`: ADOT-reported timed full closures, not live traffic. Re-check AZ511 before driving.

## Live and manual data policy

The \`events\` ledger contains individually verified event details and source links; completed events stay as a small audit/history trail. Each generator attempt also inspects official/public sources. Only structured JSON-LD Event records with explicit start/end dates, Arizona location, and calendar-specific topic filters can be automatically added. Directory sites that cannot be safely interpreted are listed as **discovery only**, not falsely treated as crawled and verified.

Road closure discovery reads ADOT's current weekend advisory and publishes only closures with both explicit start and end times. When source pages are blocked, stale, missing, or inconsistent, no dates are invented; the \`source-status.json\` file reports warnings.

## Local tests

\`\`\`sh
python -m unittest projects.test_feeds -v
python -m projects.build_feeds --offline --out /tmp/cal-test
\`\`\`

## Publication

The Calendar Hub's daily GitHub Actions publishing workflow runs all generators before the existing hub monitor and publishes \`feeds/*.ics\` through the same GitHub Pages deployment. These are **four separate subscribable ICS calendars**, though they share the hosting repository.

Adding a feed to Apple Calendar must be performed on the person's iPhone/Mac: Settings → Apps → Calendar → Calendar Accounts → Add Account → Other → Add Subscribed Calendar (labels vary by iOS version), then paste the published URL. This GitHub workflow cannot tap the Apple Calendar UI or remotely subscribe on the device.


Workday recurrence generator: `projects/workday_recurrences.py`. Weekly entries represent scheduled CHECKS, not validated tenant events. Source dates may change, and no automatic claim of Workday Community access is made. The public calendar remains a single unchanged subscribable ICS feed.
