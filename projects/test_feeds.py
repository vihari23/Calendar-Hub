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
                if slug in ("arizona-telugu","phoenix-temples"):
                    self.assertEqual(stats["events"],0)
                    self.assertIn(b"X-VIHARI-GENERATED-UTC:",raw)
                else:
                    self.assertGreater(stats["events"],0)
                self.assertTrue(all(len(line)<=75 for line in raw.split(b"\r\n")))
    def test_empty_ics_preserves_calendar_name_and_generation_time(self):
        content=ics("Empty calendar","empty",[],datetime(2026,11,14,12,0,tzinfo=ZoneInfo("America/Phoenix")))
        self.assertIn(b"X-VIHARI-GENERATED-UTC:20261114T190000Z",content)
        self.assertIn(b"X-WR-CALNAME:Empty calendar",content)
        self.assertNotIn(b"BEGIN:VEVENT",content)
        self.assertTrue(content.endswith(b"END:VCALENDAR\\r\\n".decode("unicode_escape").encode()))
    def test_utc_timed_events_apple_compatible(self):
        e=normalize({"title":"Road","start":"2026-11-13T21:00:00-07:00","end":"2026-11-16T05:00:00-07:00"})
        content=ics("Road","test",[e],datetime(2026,11,14,tzinfo=ZoneInfo("America/Phoenix")))
        self.assertIn(b"DTSTART:20261114T040000Z",content)
        self.assertIn(b"DTEND:20261116T120000Z",content)
        self.assertNotIn(b"DTSTART;TZID=",content)
    def test_az511_verified_closure_only(self):
        from unittest.mock import patch
        from io import BytesIO
        from projects.build_feeds import auto_from_wzdx
        core={"road_names":["I-10 eastbound"],"description":"I-10 full closure",
              "start_date":"2026-11-15T03:00:00Z","end_date":"2026-11-16T11:00:00Z",
              "is_start_date_verified":True,"is_end_date_verified":True}
        feature={"type":"Feature","properties":{"core_details":core,"vehicle_impact":"all-lanes-closed"},
                 "geometry":{"type":"LineString","coordinates":[[-112.1,33.5],[-112.09,33.5]]}}
        payload=json.dumps({"type":"FeatureCollection","features":[feature]}).encode()
        with patch("projects.build_feeds.urlopen",return_value=BytesIO(payload)):
            result=auto_from_wzdx(datetime(2026,11,14,12,tzinfo=ZoneInfo("America/Phoenix")))
        self.assertEqual(len(result),1)
        self.assertIn("I-10",result[0]["title"])
    def test_stable_event_ids(self):
        e=normalize({"title":"One","start":"2026-11-14","end":"2026-11-15"})
        a=ics("One","example",[e],datetime(2026,11,14,tzinfo=ZoneInfo("America/Phoenix")))
        b=ics("One","example",[e],datetime(2026,11,15,tzinfo=ZoneInfo("America/Phoenix")))
        self.assertEqual(a.split(b"UID:")[1].split(b"\r\n")[0],b.split(b"UID:")[1].split(b"\r\n")[0])
    def test_adot_never_guesses_missing_dates(self):
        self.assertEqual(parse_adot("<h1>generic</h1>",datetime(2026,11,14,tzinfo=ZoneInfo("America/Phoenix")))[0],[])

if __name__=="__main__":
    unittest.main()
