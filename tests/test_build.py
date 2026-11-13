import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from scripts.build import load_config,parse_calendar,check_feed,build

NOW=datetime(2026,11,13,21,0,tzinfo=timezone.utc)
def sample(stamp="20261113T200000Z",uid=True):
    parts=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Example//EN","BEGIN:VEVENT"]
    if uid: parts+=["UID:x@example.org"]
    parts+=["DTSTAMP:"+stamp,"DTSTART;TZID=America/Phoenix:20261114T080000","SUMMARY:Test event","END:VEVENT","END:VCALENDAR"]
    return ("\r\n".join(parts)+"\r\n").encode()
def item():
    return dict(id="example",name="Example",description="Example calendar",kind="Test",url="https://raw.githubusercontent.com/vihari23/X/main/a.ics",source_repository="https://github.com/vihari23/X",expected_update="daily",max_age_hours=72,min_events=1,enabled=True)

class MonitorTests(unittest.TestCase):
    def test_parser(self):
        r=parse_calendar(sample(),NOW,1)
        self.assertEqual(r["events"],1)
        self.assertEqual(r["upcoming"][0]["date"],"2026-11-14")
        self.assertEqual(r["age_hours"],1)
    def test_folding(self):
        s=sample().replace(b"SUMMARY:Test",b"SUMMARY:Te\r\n st")
        self.assertEqual(parse_calendar(s,NOW,1)["upcoming"][0]["name"],"Test event")
    def test_invalid(self):
        with self.assertRaises(ValueError):parse_calendar(b"bad",NOW,1)
    def test_missing_uid(self):
        with self.assertRaises(ValueError):parse_calendar(sample(uid=False),NOW,1)
    def test_stale(self):
        self.assertEqual(check_feed(item(),NOW,lambda _:sample("20260901T000000Z"))["status"],"stale")
    def test_network_error(self):
        def fail(url):raise ValueError("service unavailable")
        self.assertEqual(check_feed(item(),NOW,fail)["status"],"error")
    def test_disabled(self):
        f=item();f["enabled"]=False
        self.assertEqual(check_feed(f,NOW,lambda _:None)["status"],"disabled")
    def test_generated_site_and_report(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);config=p/"feeds.json";config.write_text(json.dumps(dict(schema_version=1,hub_name="Test Hub",look_ahead_days=45,feeds=[item()])))
            status=build(config,p/"site",NOW,lambda _:sample())
            self.assertTrue(status["healthy"])
            self.assertIn("Test event",(p/"site"/"index.html").read_text())
            self.assertTrue((p/"site"/"status.json").exists())
    def test_valid_config(self):
        load_config(Path("config/feeds.json"))
    def test_blocks_http(self):
        with tempfile.TemporaryDirectory() as t:
            f=item();f["url"]="http://example.com/a.ics"
            p=Path(t)/"x.json";p.write_text(json.dumps(dict(schema_version=1,look_ahead_days=45,feeds=[f])))
            with self.assertRaises(ValueError):load_config(p)
    def test_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"x.json";p.write_text(json.dumps(dict(schema_version=1,look_ahead_days=45,feeds=[item(),item()])))
            with self.assertRaises(ValueError):load_config(p)

if __name__=="__main__":
    unittest.main()
