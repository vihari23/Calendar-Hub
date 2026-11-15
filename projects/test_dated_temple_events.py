"""Regression tests for date-specific temple importers and stale source handling."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from projects.dated_temple_events import (
    hanuman_from_html, lalitha_from_html, import_dated_temple
)

NOW=datetime(2026,11,14,17,0,tzinfo=ZoneInfo("America/Phoenix"))
HAN_URL="https://www.hanumantempleaz.org/upcomingevents"
LAL_URL="https://srilalithatemple.org/temple-events/"

class DatedTempleImporterTests(unittest.TestCase):
    def test_hanuman_official_october_listing_is_outdated(self):
        html = """<h3>Upcoming Programs</h3>
        <ul><li>10-11-2026, Sunday<ul><li>NAVARATRI BEGINS</li></ul></li>
        <li>10-20-2026, Tuesday<ul><li>VIJAYADASHAMI / DUSSEHRA</li></ul></li></ul>
        <h4>Weekly Regular Events</h4>
        <p>Every Tuesday - Hanuman Vada Mala Pooja</p>"""
        result=hanuman_from_html(html,HAN_URL,NOW)
        self.assertEqual(result["events"],[])
        self.assertEqual(result["status"],"outdated_schedule")
        self.assertEqual(result["latest_date"],"2026-10-20")

    def test_hanuman_future_dated_special_service_publishes(self):
        html = """<h3>Upcoming Programs</h3>
        <ul><li>11-21-2026, Saturday<ul>
        <li>HANUMAAN SPECIAL PUJA</li><li>ANNA DAANAM</li></ul></li>
        <li>11-22-2026, Sunday<ul><li>Regular Temple Hours</li></ul></li></ul>
        <h4>Weekly Regular Events</h4><p>Every Tuesday - Hanuman Pooja</p>"""
        result=hanuman_from_html(html,HAN_URL,NOW)
        self.assertEqual(result["status"],"future_events")
        self.assertEqual(len(result["events"]),1)
        self.assertEqual(result["events"][0]["start"].date().isoformat(),"2026-11-21")
        self.assertFalse(result["events"][0]["all_day"])
        self.assertEqual(result["events"][0]["start"].hour,8)

    def test_hanuman_future_wrong_weekday_cannot_publish(self):
        html="<ul><li>11-21-2026, Sunday<ul><li>HANUMAAN SPECIAL PUJA</li></ul></li></ul>"
        result=hanuman_from_html(html,HAN_URL,NOW)
        self.assertEqual(result["events"],[])
        self.assertEqual(result["status"],"no_dated_events")

    def test_lalitha_march_table_outdated_not_recurring(self):
        html="""<h2>Upcoming Events</h2><table>
        <tr><th>Date</th><th>Festival</th><th>Time</th></tr>
        <tr><td>Mar 19th, 2026</td><td>Ugadhi Celebrations</td><td>7:00 PM</td></tr>
        <tr><td>Mar 26th, 2026</td><td>Sri Sitarama Kalyanotsavam</td><td>6:00 PM - 8:00 PM</td></tr>
        <tr><td>Mar 27th, 2026</td><td>2nd Anniversary Celebrations</td><td>Details TBA</td></tr></table>
        <h2>Temple Events Schedule</h2>
        <table><tr><td>Every Friday</td><td>07:00 PM</td><td>Lalitha Abhishekam</td></tr></table>
        <h3>May Events Calendar</h3>"""
        result=lalitha_from_html(html,LAL_URL,NOW)
        self.assertEqual(result["events"],[])
        self.assertEqual(result["latest_date"],"2026-03-27")
        self.assertEqual(result["status"],"outdated_schedule")

    def test_lalitha_future_explicit_date_and_time(self):
        html="""<table>
        <tr><th>Date</th><th>Festival</th><th>Time</th></tr>
        <tr><td>Nov 21st, 2026</td><td>Sri Sitarama Kalyanotsavam</td><td>6:00 PM - 8:00 PM</td></tr>
        <tr><td>Every Friday</td><td>Lalitha Abhishekam</td><td>7:00 PM</td></tr></table>"""
        result=lalitha_from_html(html,LAL_URL,NOW)
        self.assertEqual(len(result["events"]),1)
        self.assertEqual(result["events"][0]["start"].hour,18)
        self.assertEqual(result["events"][0]["end"].hour,20)
        self.assertEqual(result["status"],"future_events")

    def test_importer_tracks_stale_date_as_warning(self):
        source={"name":"Sri Lalitha Temple","url":LAL_URL,"import":"lalitha_html"}
        html='<table><tr><td>Mar 27th, 2026</td><td>2nd Anniversary Celebrations</td></tr></table>'
        result=import_dated_temple(source,NOW,lambda url: html)
        self.assertEqual(result["status"],"outdated_schedule")
        self.assertIn("2026-03-27",result["warnings"][0])
        self.assertEqual(result["events"],[])


if __name__=="__main__":
    unittest.main()
