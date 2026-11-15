"""Ekta Mandir importer regression tests: source dates, stale detail times, and exclusion."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from projects.ekta_events import auto_from_ekta, detail_times

NOW = datetime(2026, 11, 14, 17, 0, tzinfo=ZoneInfo("America/Phoenix"))
URL = "https://www.ektamandiraz.org/religious-events"


def card(day, month, weekday, title, path):
    return (f'<section><span>{day}</span><span>{month}</span>'
            f'<span>{weekday}</span><h4><a href="{path}">{title}</a></h4></section>')


class EktaImporterTests(unittest.TestCase):
    def test_official_cards_publish_future_special_events(self):
        html = ('<nav>EktaMandir Event Calendar 2026</nav>'
                + card("15", "November", "Sunday", "Yoga Classes", "/yoga")
                + card("21", "November", "Saturday", "Balaji Abishek", "/balaji")
                + card("29", "November", "Sunday", "Sundarakand", "/sundarakand")
                + card("01", "December", "Tuesday", "Pradosham – Shiva Abhishekam", "/pradosham")
                + card("19", "December", "Saturday", "Balaji Abishek", "/balaji")
                + card("27", "December", "Sunday", "Sundarakand", "/sundarakand")
                + card("16", "January", "Saturday", "Balaji Abishek", "/balaji"))
        def fetch(url):
            if url == URL:
                return html
            if url.endswith("/balaji"):
                return '<div>Date Nov 21 2025 Time 5:00 pm - 7:00 pm</div>'
            if url == "https://www.ektamandiraz.org/":
                return "<h2>November 2026 Events</h2><h2>TatTvanAsi – 15th November</h2>"
            return '<div>Details pending</div>'
        events = auto_from_ekta(URL, NOW, fetch)
        titles = [e["title"] for e in events]
        days = [e["start"].date().isoformat() for e in events]
        self.assertEqual(len(events), 7)
        self.assertNotIn("Ekta Mandir — Yoga Classes", titles)
        self.assertIn("2027-01-16", days)
        self.assertIn("2026-11-15", days)
        self.assertTrue(all(not e["all_day"] for e in events))
        self.assertTrue(all(e["start"].hour == 8 for e in events))
        self.assertTrue(any("NOT a confirmed ceremony time" in e["description"] for e in events))

    def test_absent_year_is_not_fabricated(self):
        page = card("21", "November", "Saturday", "Balaji Abishek", "/balaji")
        with self.assertRaisesRegex(ValueError, "calendar year"):
            auto_from_ekta(URL, NOW, lambda url: page)

    def test_detail_time_requires_exact_date(self):
        from datetime import date
        self.assertIsNone(detail_times("Date Nov 21 2025 Time 5:00 pm - 7:00 pm", date(2026, 11, 21)))
        self.assertEqual(
            detail_times("Date Nov 21 2026 Time 5:00 pm - 7:00 pm", date(2026, 11, 21))[0].hour,17)

    def test_weekday_must_match(self):
        page = "EktaMandir Event Calendar 2026" + card(
            "21", "November", "Sunday", "Balaji Abishek", "/balaji")
        results = auto_from_ekta(URL, NOW, lambda url: page)
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
