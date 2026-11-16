"""Source-labeled Workday calendar cadence and release-planning checkpoints.

This calendar is public and not connected to any customer's Workday tenants.
Weekly publication entries are reminders of the *usual* timetable, not a
claim that an individual edition has been published or a tenant refreshed.
Projected major-release checkpoints are planning estimates, never official dates.
"""
from datetime import date, datetime, timedelta

RELEASE_SCHEDULE = (
    "https://doc.workday.com/admin-guide/en-us/about-workday-documentation/"
    "workday-documentation---in-depth/workday-release-schedule.html"
)
RELEASE_FAQ = (
    "https://doc.workday.com/admin-guide/en-us/about-workday-documentation/"
    "about-workday-release-notes/faq--release-notes-.html"
)
TENANT_INFO = (
    "https://www.workday.com/content/dam/web/en-us/documents/datasheets/"
    "workday-tenants-datasheet.pdf"
)
HORIZON_DAYS = 365


def _entry(title, day, url, description, *, tentative=True, source="Workday documentation"):
    return {
        "title": title,
        "start": day.isoformat(),
        "end": (day + timedelta(days=1)).isoformat(),
        "location": "Workday (review tenant-specific notices)",
        "url": url,
        "description": description,
        "source": source,
        "tentative": tentative,
    }


def _dates_weekday(first, last, weekday):
    day = first + timedelta(days=(weekday - first.weekday()) % 7)
    while day <= last:
        yield day
        day += timedelta(days=7)


def build_workday_events(curated, now, *, horizon_days=HORIZON_DAYS):
    """Return advisory calendar events through 365 days, plus source dates.

    Curated production dates come from a named independent institution and
    remain marked tentative pending authenticated global release verification.
    Do not infer or publish an actual tenant refresh from any projection.
    """
    today = now.date() if isinstance(now, datetime) else now
    end = today + timedelta(days=horizon_days)
    out = []

    # Weekly Workday publication timetable: exceptions can shift dates.
    for day in _dates_weekday(today, end, 2):  # Wednesdays
        out.append(_entry(
            "Workday Release Center — Wednesday notes (usual schedule)", day,
            RELEASE_SCHEDULE,
            "Check Release Center for Feature, Coming Soon, Fix, and Retirement notes. "
            "Usual Wednesday publication, not individually confirmed; exceptions/holidays occur. "
            "Review HCM, Payroll, Benefits, Integrations, Security, and Workday Extend impacts.",
        ))
    for day in _dates_weekday(today, end, 4):  # Fridays
        out.append(_entry(
            "Workday What's New report — weekly availability check", day,
            RELEASE_SCHEDULE,
            "Workday's What's New in Workday report is normally delivered to Preview/"
            "Production tenants on Friday. Confirm availability inside your tenant; "
            "it covers feature notes, not all Fix/Retirement notes. "
            "Actual tenant publication and feature availability are not verified here.",
        ))
        out.append(_entry(
            "Workday Release Center — Friday notes (usual schedule)", day,
            RELEASE_SCHEDULE,
            "Normal Friday Release Center update for Features, Fixes, Retirements "
            "and Coming Soon. Check documentation announcement exceptions. "
            "Sandbox refresh schedules vary by tenant; this is NOT a refresh confirmation.",
        ))

    # Production dates are curated/published by a named university. Schedule
    # projections are a *separate* layer and must never be treated as official.
    for item in curated:
        title = item.get("title", "")
        if "2027 R" not in title or "release" not in title.lower():
            continue
        prod = date.fromisoformat(item["start"][:10])
        name = title.split("—")[0].strip()
        preview = prod - timedelta(weeks=5)
        proposed = [
            (preview - timedelta(days=10),
             f"{name} — preview release notes check (projected)",
             RELEASE_FAQ,
             "Planning estimate based on the usual Wednesday publication roughly "
             "one week before Preview. Not a confirmed release-note publication."),
            (preview - timedelta(days=8),
             f"{name} — first What's New report check (projected)",
             RELEASE_FAQ,
             "Planning estimate based on the usual Friday tenant report about one "
             "week before Preview. Check the actual tenant for publication."),
            (preview - timedelta(days=1),
             f"{name} — Sandbox Preview refresh watch (estimated)",
             TENANT_INFO,
             "Approximate planning checkpoint only. Workday refreshes Sandbox "
             "Preview twice yearly; exact refresh dates require Workday Community/"
             "tenant notice. DO NOT treat this as a scheduled or confirmed refresh."),
            (preview,
             f"{name} — Preview testing start (estimated)",
             RELEASE_FAQ,
             "Approximate five-week-before-Production Preview planning date, "
             "NOT a Workday-confirmed Preview start. Verify release schedule and "
             "test Payroll, HCM, Benefits, security, integrations, and reports."),
        ]
        for day, event_name, url, desc in proposed:
            if today <= day <= end:
                out.append(_entry(event_name, day, url, desc))

    # Workday publishes roadmaps in October (following year's R1) and April
    # (current year's R2). The exact day is NOT publicly specified. These
    # are prompts on the first day of the MONTH, not publication dates.
    for year in range(today.year, end.year + 1):
        for month, label in (
            (4, f"{year} R2"),
            (10, f"{year + 1} R1"),
        ):
            day = date(year, month, 1)
            if today <= day <= end:
                out.append(_entry(
                    f"Workday {label} roadmap — publication month check",
                    day, RELEASE_SCHEDULE,
                    f"Workday targets {day.strftime('%B')} for {label} roadmap "
                    "publication; day 1 is a reminder to check, NOT the roadmap's "
                    "confirmed publication date.",
                ))
    return out
