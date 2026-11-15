"""End-to-end extraction fixtures: HTML, official PDFs, scanned PDFs, image flyers, source coverage."""
import io
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
import fitz

from projects.temple_extraction import (
    scan_source, extract_pdf, ocr_image, extract_candidates, asset_candidates, safe_url,
)

NOW=datetime(2026,11,14,12,0,tzinfo=ZoneInfo("America/Phoenix"))
BASE="https://example-temple.org/events"

def png_sample():
    img=Image.new("RGB",(1400,300),"white")
    draw=ImageDraw.Draw(img)
    try:
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",42)
    except OSError:
        font=ImageFont.load_default()
    draw.text((60,90),"Nov 21, 2026 Siva Annabhishekam",fill="black",font=font)
    output=io.BytesIO()
    img.save(output,format="PNG")
    return output.getvalue()

def pdf_sample(scanned=False):
    doc=fitz.open()
    page=doc.new_page()
    if scanned:
        image=png_sample()
        page.insert_image(fitz.Rect(15,15,555,160),stream=image)
    else:
        page.insert_text((72,72),"Nov 21, 2026 Siva Annabhishekam",fontsize=20)
    data=doc.tobytes()
    doc.close()
    return data

class TempleExtractionTests(unittest.TestCase):
    def test_date_requires_explicit_year_and_special_event(self):
        good=extract_candidates("Nov 21, 2026 - Siva Annabhishekam",NOW,BASE)
        self.assertTrue(good)
        self.assertFalse(good[0]["auto_publish"])
        self.assertEqual(good[0]["date"],"2026-11-21")
        self.assertEqual(extract_candidates("Nov 21 Siva Annabhishekam",NOW,BASE),[])
        self.assertEqual(extract_candidates("Nov 21, 2025 Siva Annabhishekam",NOW,BASE),[])
        self.assertEqual(extract_candidates("Nov 21, 2026 regular weekly puja",NOW,BASE),[])
    def test_official_source_restriction(self):
        self.assertIsNone(safe_url(BASE,"http://example-temple.org/files/flyer.pdf","example-temple.org"))
        self.assertIsNone(safe_url(BASE,"https://evil.org/flyer.pdf","example-temple.org"))
        self.assertEqual(safe_url(BASE,"/files/calendar.pdf","example-temple.org"),
                         "https://example-temple.org/files/calendar.pdf")
    def test_pdf_embedded_text_and_page_count(self):
        text,pages,ocr=extract_pdf(pdf_sample())
        self.assertEqual(pages,1)
        self.assertIn("Siva Annabhishekam",text)
        self.assertGreaterEqual(ocr,0)
    def test_scanned_pdf_ocr(self):
        text,pages,ocr=extract_pdf(pdf_sample(scanned=True))
        self.assertEqual(pages,1)
        self.assertEqual(ocr,1)
        self.assertIn("2026",text)
    def test_image_flyer_ocr(self):
        text,used=ocr_image(png_sample())
        self.assertTrue(used)
        self.assertIn("2026",text)
    def test_full_source_html_pdf_image_and_review_queue(self):
        html=('<html><h2>Temple special events</h2>'
              '<p>Nov 21, 2026 - Siva Annabhishekam</p>'
              '<a href="/uploads/2026-calendar.pdf">Download 2026 calendar PDF</a>'
              '<img alt="2026 festival flyer" src="/uploads/festival.png"></html>').encode()
        data={BASE:(html,"text/html"),
              "https://example-temple.org/uploads/2026-calendar.pdf":(pdf_sample(),"application/pdf"),
              "https://example-temple.org/uploads/festival.png":(png_sample(),"image/png")}
        def fake_fetch(url,limit):
            return data[url]
        report=scan_source({"name":"Fixture Temple","url":BASE},NOW,fetcher=fake_fetch)
        self.assertTrue(report["html_checked"])
        self.assertEqual(report["pdf_scanned"],1)
        self.assertEqual(report["images_ocr"],1)
        self.assertEqual(report["assets_checked"],2)
        self.assertGreaterEqual(report["candidate_count"],1)
        self.assertEqual(report["auto_published"],0)
        self.assertIn(report["status"],("review_needed","partial"))
    def test_homepage_november_poster_with_generic_filename(self):
        homepage="https://example-temple.org/"
        flyer=homepage+"wp-content/uploads/2026/11/WhatsApp-Image-2026-10-31.jpeg"
        html=('<html><h2>November 2026 Events</h2>'
              '<img alt="Temple schedule" src="/wp-content/uploads/2026/11/WhatsApp-Image-2026-10-31.jpeg">'
              '</html>').encode()
        def fake_fetch(url,limit):
            if url==homepage:return html,"text/html"
            if url==flyer:return png_sample(),"image/png"
            raise AssertionError("Unexpected URL: "+url)
        report=scan_source({"name":"Official homepage","url":homepage},NOW,fetcher=fake_fetch)
        self.assertEqual(report["images_ocr"],1)
        self.assertEqual(report["assets_checked"],1)
        self.assertEqual(report["assets_scanned"][0]["url"],flyer)

    def test_blocked_site_is_reported_not_silently_accepted(self):
        def reject(url,limit):raise RuntimeError("HTTP Error 403: Forbidden")
        x=scan_source({"name":"Block","url":BASE},NOW,fetcher=reject)
        self.assertEqual(x["status"],"blocked")
        self.assertEqual(x["candidate_count"],0)

if __name__=="__main__":
    unittest.main()
