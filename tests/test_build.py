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
    def test_without_dtstamp_uses_verified_publication(self):
        raw=sample().replace(b"DTSTAMP:20261113T200000Z\r\n",b"")
        published=datetime(2026,11,13,18,0,tzinfo=timezone.utc)
        r=check_feed(item(),NOW,lambda _:raw,publish_getter=lambda _:published)
        self.assertEqual(r["status"],"healthy")
        self.assertEqual(r["freshness_basis"],"github_actions_success")

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
            from zipfile import ZipFile
            archive=p/"site"/"CalendarHubFullPage.zip"
            with ZipFile(archive) as bundle:
                self.assertEqual(set(bundle.namelist()),{
                    "script.json","index.tsx","widget.tsx","core.ts","settings.ts","README.md"})
                self.assertEqual(json.loads(bundle.read("script.json"))["name"],"Vihari Calendar Hub Full Page")
                self.assertIn(b"systemExtraLargePortrait",bundle.read("widget.tsx"))
                self.assertIn(b"appGroupDocumentsDirectory",bundle.read("settings.ts"))
            widget=json.loads((p/"site"/"widget.json").read_text())
            self.assertEqual(widget["schema_version"],1)
            self.assertEqual(len(widget["feeds"]),1)
            self.assertEqual(widget["feeds"][0]["upcoming"][0]["name"],"Test event")
            self.assertTrue((p/"site"/"widget-setup.html").exists())
            self.assertIn("Manage widget views",(p/"site"/"widget-setup.html").read_text())
            self.assertTrue((p/"site"/"CalendarHubWidget.js").exists())
            self.assertIn('URLScheme.forRunningScript',(p/"site"/"CalendarHubWidget.js").read_text())
            self.assertTrue((p/"site"/"status.json").exists())
            html=(p/"site"/"index.html").read_text(encoding="utf8")
            self.assertIn('href="./manifest.webmanifest"',html)
            self.assertIn('rel="apple-touch-icon"',html)
            self.assertIn('serviceWorker.register("./sw.js"',html)
            self.assertIn('Offline',html)
            manifest=json.loads((p/"site"/"manifest.webmanifest").read_text())
            self.assertEqual(manifest["display"],"standalone")
            self.assertEqual(manifest["start_url"],"./")
            self.assertEqual(manifest["scope"],"./")
            self.assertEqual(len(manifest["icons"]),2)
            for name in ("icon-192.png","icon-512.png","apple-touch-icon.png"):
                self.assertTrue((p/"site"/name).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                import struct
                dimension=struct.unpack(">II",(p/"site"/name).read_bytes()[16:24])
                self.assertEqual(dimension,(int(name.split("-")[1].split(".")[0]) if name.startswith("icon-") else 180,)*2)
            self.assertIn('CACHE = "calendar-hub-shell-v2"',(p/"site"/"sw.js").read_text())
    def test_pwa_has_no_private_feed_urls(self):
        app=Path("static/manifest.webmanifest").read_text()
        self.assertNotIn("Personal Important Dates",app)
        self.assertNotIn("Calendar-Hub/status.json",Path("static/sw.js").read_text())
    def test_icon_source_is_valid(self):
        from scripts.icon_render import _decode_indexed_png
        width,height,pixels=_decode_indexed_png(Path("static/icon-source.png"))
        self.assertEqual((width,height),(96,96))
        self.assertEqual(len(pixels),96)

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
