# Full-page iPhone Calendar Hub — Scripting (iOS 27+)

**Status:** Source code + automated validation. **Not device-certified** until you preview and place the widget on an iPhone running iOS 27 with Scripting 3.2.1 or later. Preview dimensions simulate 300 × 628 pt; actual widget dimensions vary by device.

## Why not Scriptable?

Scriptable currently documents the iPhone Large widget and iPad Extra Large. Scripting's official documentation explicitly supports the **`systemExtraLargePortrait`** family for iPhone iOS 27. This widget takes an entire Home Screen page. It does not allow continuous scrolling *inside* the widget.

## Installation

1. Install/update [Scripting](https://scriptingapp.github.io/) on the iPhone.
2. Create a new Scripting script project named **Calendar Hub Full Page**.
3. Add **four files** from this folder to that project: `index.tsx`, `widget.tsx`, `core.ts`, `settings.ts` (preserve exact names).
4. Run `index.tsx` in Scripting to add new ICS calendar URLs and choose colors. Local settings are written to Scripting's **App Group** folder, which widgets can read; they do not go to public GitHub.
5. Create a named widget view (for example `family`) and toggle which calendars belong to it.
6. Use **Preview XL portrait widget** inside the Scripting settings to validate size and rendering on the device.
7. Add the **extra-large portrait** Scripting widget to your iPhone Home Screen, select the Calendar Hub Full Page project, and in **Parameter**, enter `all`, `culture`, `entertainment`, `home`, or the new view ID. Add multiple widgets with different parameters if desired.
8. Tap **Open scrollable Calendar Hub** to use the web dashboard for scrolling. The dashboard currently includes only the public feeds, not privately added ICS URLs.

### Constraints and safeguards

- Basic ICS VEVENTs and simple monthly/yearly RRULE are supported. Complex recurrence, RDATE, EXDATE and non-Phoenix time zones need checking in Apple Calendar and are not guaranteed.
- Home Screen widgets update at iOS/WidgetKit's discretion, not at a guaranteed hourly rate.
- Public source data comes from `https://vihari23.github.io/Calendar-Hub/widget.json`; custom URLs are fetched on-device.
- The widget is **not** part of the Calendar Hub PWA installation. It uses the separate Scripting app.
- The source code and automated tests are not a substitute for physical-device rendering and installation tests.

### References

- [Scripting systemExtraLargePortrait documentation](https://scriptingapp.github.io/guide/Changelog/3.2.1/System%20Shortcut%20Widget%20Buttons%20(iOS%2027%2B))
- [Scripting Widget API](https://scriptingapp.github.io/guide/Widget/Widget%20API)
- [Scripting FileManager App Group](https://scriptingapp.github.io/guide/Utilities/FileManager)
