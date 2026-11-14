"""Unit and offline integration checks for the four public ICS generators."""
import json
import tempfile
from datetime import datetime
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo
from projects.build_feeds import build,normalize,ics,parse_adot

class FeedTests(unittest.TestCase):
    def test_time_and_date_validation(self):
        e=normalize({"title":"test","start":"2026-11-14T10:00:00-07:00","end":"2026-11-14T11:00:00-07:00"})
        self.assertFalse(e["all_day"])
        with self.assertRaises(ValueError):
            normalize({"title":"bad","start":"2026-11-14T11:00:00-07:00","end":"2026-11-14T10:00:00-07:00"})
    def test_all_four_calendars_offline(self):
        with tempfile.TemporaryDirectory() as d:
            results=build(d,datetime(2026,11,14,12,0,tzinfo=ZoneInfo("America/Phoenix")),network=False)
            self.assertEqual(len(results),4)
            for slug,stats in results.items():
                raw=(Path(d)/(slug+".ics")).read_bytes()
                self.assertTrue(raw.startswith(b"BEGIN:VCALENDAR\r\n"))
                self.assertTrue(raw.endswith(b"END:VCALENDAR\r\n"))
                self.assertEqual(raw.count(b"BEGIN:VEVENT"),raw.count(b"END:VEVENT"))
                self.assertGreater(stats["events"],0)
                self.assertTrue(all(len(line)<=75 for line in raw.split(b"\r\n")))
    def test_stable_event_ids(self):
        e=normalize({"title":"One","start":"2026-11-14","end":"2026-11-15"})
        a=ics("One","example",[e],datetime(2026,11,14,tzinfo=ZoneInfo("America/Phoenix")))
        b=ics("One","example",[e],datetime(2026,11,15,tzinfo=ZoneInfo("America/Phoenix")))
        self.assertEqual(a.split(b"UID:")[1].split(b"\r\n")[0],b.split(b"UID:")[1].split(b"\r\n")[0])
    def test_adot_never_guesses_missing_dates(self):
        self.assertEqual(parse_adot("<h1>generic</h1>",datetime(2026,11,14,tzinfo=ZoneInfo("America/Phoenix")))[0],[])

if __name__=="__main__":
    unittest.main()
