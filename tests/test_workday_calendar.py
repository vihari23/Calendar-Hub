"""Regression tests for Workday publication cadence and planned release dates."""
import json
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from projects.workday_recurrences import build_workday_events
from projects.build_feeds import build


class WorkdayCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.curated = json.loads(
            Path("projects/workday-releases/project.json").read_text()
        )["events"]
        cls.now = datetime(2026, 11, 15, 12, 0,
                           tzinfo=ZoneInfo("America/Phoenix"))

    def test_key_2027_release_checkpoints(self):
        events = build_workday_events(self.curated, self.now)
        names = {(e["title"], e["start"]) for e in events}
        required = {
            ("Workday 2027 R1 — preview release notes check (projected)", "2027-01-27"),
            ("Workday 2027 R1 — first What's New report check (projected)", "2027-01-29"),
            ("Workday 2027 R1 — Sandbox Preview refresh watch (estimated)", "2027-02-05"),
            ("Workday 2027 R1 — Preview testing start (estimated)", "2027-02-06"),
            ("Workday 2027 R2 — preview release notes check (projected)", "2027-07-28"),
            ("Workday 2027 R2 — first What's New report check (projected)", "2027-07-30"),
            ("Workday 2027 R2 — Sandbox Preview refresh watch (estimated)", "2027-08-06"),
            ("Workday 2027 R2 — Preview testing start (estimated)", "2027-08-07"),
            ("Workday 2027 R2 roadmap — publication month check", "2027-04-01"),
            ("Workday 2028 R1 roadmap — publication month check", "2027-10-01"),
        }
        self.assertTrue(required.issubset(names), required - names)

    def test_every_reminder_is_tentative_and_weeklies_present(self):
        events = build_workday_events(self.curated, self.now)
        self.assertTrue(all(e["tentative"] for e in events))
        fridays = [e for e in events if e["title"].startswith("Workday What's New report")]
        wednesdays = [e for e in events if "Wednesday notes" in e["title"]]
        sandboxes = [e for e in events if "Sandbox — weekly" in e["title"]]
        self.assertGreaterEqual(len(fridays), 52)
        self.assertEqual(len(fridays), len(sandboxes))
        self.assertGreaterEqual(len(wednesdays), 52)
        self.assertTrue(all(date.fromisoformat(e["start"]) <= self.now.date().replace(
            year=self.now.year + 1) for e in events))

    def test_release_timing_is_source_labeled_not_confirmed(self):
        events = build_workday_events(self.curated, self.now)
        for item in events:
            if "refresh" in item["title"].lower():
                self.assertIn("not", item["description"].lower())
                self.assertTrue(item["tentative"])
            if "Preview testing" in item["title"]:
                self.assertIn("NOT a Workday-confirmed", item["description"])

    def test_rolling_horizon_and_no_false_global_release(self):
        later = date(2027, 11, 14)
        events = build_workday_events(self.curated, later)
        self.assertFalse(any("2027 R1 —" in e["title"] for e in events))
        self.assertTrue(all(date.fromisoformat(e["start"]) >= later for e in events))


if __name__ == "__main__":
    unittest.main()
