"""Tests for independent Telugu, Workday and road source verification."""
import json
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from projects.source_audits import audit_telugu, audit_workday, extract_workday_milestones
from projects.temple_extraction import extract_candidates
from projects.source_audits import TELUGU_EVENT

NOW=datetime(2026,11,14,12,0,tzinfo=ZoneInfo("America/Phoenix"))

class AuditTests(unittest.TestCase):
    def test_telugu_ocr_review_never_auto_published(self):
        candidates=extract_candidates(
            "Nov 22, 2026 - Telangana Bathukamma cultural program",
            NOW,"https://example.org/flyer.png","image",
            topic_pattern=TELUGU_EVENT)
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0]["date"],"2026-11-22")
        self.assertFalse(candidates[0]["auto_publish"])
        self.assertEqual(extract_candidates("Nov 22, 2026 - French language class",
                                           NOW,"https://example.org/flyer.png","image",
                                           topic_pattern=TELUGU_EVENT),[])
    def test_all_telugu_sources_are_audited_even_when_blocked(self):
        sources=[{"name":"Telugu A","url":"https://example.org/a"},
                 {"name":"Telugu B","url":"https://example.org/b"},
                 {"name":"Telugu C","url":"https://example.org/c"}]
        def fake_scan(src,now,topic_pattern=None):
            if src["name"]=="Telugu B":
                return {"name":src["name"],"status":"blocked","warnings":["HTTP 403"],
                        "candidates":[],"pdf_scanned":0,"images_ocr":0}
            return {"name":src["name"],"status":"review_needed","warnings":[],
                    "candidates":[{"date":None,"title":"Bathukamma","auto_publish":False}],
                    "pdf_scanned":1,"images_ocr":1}
        report=audit_telugu(sources,NOW,scanner=fake_scan)
        self.assertEqual(report["checked_sources"],3)
        self.assertEqual(report["sources_accessible"],2)
        self.assertEqual(report["candidate_count"],2)
        self.assertTrue(report["requires_human_review"])
    def test_workday_2027_feature_release_parser(self):
        html_text=(
          "Saturday, March 13, 2027 - 2 a.m. to 5 a.m. ET (2027R1 Feature Release)\n"
          "Saturday, September 11, 2027 - 2 a.m. to 5 a.m. ET (2027R2 Feature Release)\n"
          "Saturday, April 17, 2027 - Monthly Maintenance\n")
        found=extract_workday_milestones(html_text)
        self.assertEqual({x["key"]:x["date"] for x in found},
                         {"2027R1":"2027-03-13","2027R2":"2027-09-11"})
    def test_workday_date_change_flagged_not_auto_published(self):
        sources=[{"name":"Williams College Workday planned maintenance calendar",
                  "url":"https://example.org/workday"}]
        events=[{"title":"Workday 2027 R1 — planned release","start":"2027-03-13"}]
        html=b"<html><li>Saturday, March 20, 2027 - 2027R1 Feature Release</li></html>"
        def fetch(url,limit):
            return html,"text/html"
        audit=audit_workday(sources,events,NOW,fetcher=fetch)
        self.assertEqual(audit["checked_sources"],1)
        self.assertEqual(audit["sources_accessible"],1)
        self.assertEqual(len(audit["date_differences"]),1)
        self.assertEqual(audit["date_differences"][0]["institutional_source_date"],"2027-03-20")
        self.assertTrue(audit["requires_human_review"])
    def test_workday_blocked_page_not_reported_as_verified(self):
        def reject(url,limit):raise RuntimeError("HTTP Error 403: Forbidden")
        audit=audit_workday([{"name":"Workday official","url":"https://example.org"}],[],NOW,fetcher=reject)
        self.assertEqual(audit["sources_accessible"],0)
        self.assertEqual(audit["source_audits"][0]["status"],"blocked")

if __name__=="__main__":
    unittest.main()
