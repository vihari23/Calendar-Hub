"""Verify source-backed temple events are present in the generated ICS."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from projects.build_feeds import ics, normalize
from projects.temple_reconciliation import reconcile, read_ics_events

NOW = datetime(2026, 11, 14, 12, tzinfo=ZoneInfo("America/Phoenix"))
TITLE = "Ekta Mandir — Balaji Abishek"
FLYER = "https://www.ektamandiraz.org/november-flyer.jpeg"


def event(at="10:15"):
    hh, mm = map(int, at.split(":"))
    return normalize({
        "title": TITLE,
        "start": f"2026-11-21T{at}:00-07:00",
        "end": f"2026-11-21T{(hh+1):02d}:{mm:02d}:00-07:00",
        "url": FLYER,
    })


def manifest():
    return {"events": [], "verified_flyer_events": [{
        "calendar_title": TITLE, "date": "2026-11-21",
        "start_time": "10:15", "source_url": FLYER,
    }]}


class TempleReconciliationTests(unittest.TestCase):
    def test_verified_present_and_utc_to_phoenix_time(self):
        item = event()
        body = ics("Temples", "temples", [item], NOW)
        self.assertEqual(read_ics_events(body)[0]["time"], "10:15")
        result = reconcile(manifest(), body, NOW)
        self.assertTrue(result["verified_passed"])
        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["verified_failures"], 0)

    def test_missing_verified_event_is_flagged(self):
        result = reconcile(manifest(), ics("Temples", "temples", [], NOW), NOW)
        self.assertFalse(result["verified_passed"])
        self.assertEqual(result["missing"][0]["date"], "2026-11-21")

    def test_time_conflict_is_flagged(self):
        result = reconcile(manifest(), ics("Temples", "temples", [event("09:00")], NOW), NOW)
        self.assertEqual(result["time_conflicts"][0]["expected_time"], "10:15")
        self.assertEqual(result["time_conflicts"][0]["calendar_time"], "09:00")

    def test_same_title_and_day_different_ics_starts_are_duplicates(self):
        body = ics("Temples", "temples", [event("09:00"), event("10:15")], NOW)
        result = reconcile(manifest(), body, NOW)
        self.assertEqual(result["duplicates"][0]["found"], 2)
        self.assertFalse(result["verified_passed"])

    def test_collapsed_duplicate_sources_are_separately_reported(self):
        item = event()
        result = reconcile(manifest(), ics("Temples", "temples", [item], NOW),
                           NOW, input_events=[item, item])
        self.assertTrue(result["verified_passed"])
        self.assertEqual(result["source_duplicates_removed"][0]["count"], 2)

    def test_ocr_only_findings_are_never_verified_missing(self):
        audit = [{"name": "Poster", "status": "partial", "warnings": ["One image blocked"],
                  "candidates": [{"date": "2026-11-24",
                                  "title": "Satyanarayana Puja",
                                  "origin": "https://temple.org/flyer.jpeg"}]}]
        result = reconcile({"events": [], "verified_flyer_events": []},
                           ics("Temples", "temples", [], NOW), NOW, source_audits=audit)
        self.assertTrue(result["verified_passed"])
        self.assertEqual(result["ocr_review"][0]["status"], "possible_missing_needs_review")
        self.assertEqual(result["source_coverage_gaps"][0]["status"], "partial")

    def test_expired_same_day_event_is_not_falsely_missing(self):
        later = datetime(2026, 11, 21, 13, tzinfo=ZoneInfo("America/Phoenix"))
        result = reconcile(manifest(), ics("Temples", "temples", [], later), later)
        self.assertEqual(result["verified_expected"], 0)
        self.assertTrue(result["verified_passed"])

    def test_manifest_verification_uses_event_end_not_just_date(self):
        later = datetime(2026, 11, 21, 13, tzinfo=ZoneInfo("America/Phoenix"))
        j = {"events": [{"title": TITLE, "start": "2026-11-21T10:15:00-07:00",
                         "end": "2026-11-21T11:15:00-07:00"}]}
        result = reconcile(j, ics("Temples", "temples", [], later), later)
        self.assertTrue(result["verified_passed"])

    def test_past_verified_events_are_not_falsely_missing(self):
        old = {"events": [], "verified_flyer_events": [{
            "calendar_title": TITLE, "date": "2026-11-10",
            "start_time": "10:15", "source_url": FLYER,
        }]}
        result = reconcile(old, ics("Temples", "temples", [], NOW), NOW)
        self.assertEqual(result["verified_expected"], 0)
        self.assertTrue(result["verified_passed"])


if __name__ == "__main__":
    unittest.main()
