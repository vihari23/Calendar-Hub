"""Read-only discovery audits for the Telugu community and Workday calendars.

All OCR, PDF and HTML findings go to a review queue. A public webpage is never
evidence that a release date is globally confirmed. Existing ICS URLs are stable.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from html.parser import HTMLParser

from projects.temple_extraction import (
    Page, extract_candidates, explicit_dates, fetch_bytes, scan_source
)

TELUGU_EVENT = re.compile(
    r"(?:Telugu|Telangana|Andhra|Bathukamma|Ugadi|Sankranti|Tollywood|"
    r"తెలుగు|తెలంగాణ|బతుకమ్మ|ఉగాది|సంక్రాంతి|TANA|NATS|TTA|AZTA)"
    r"(?:\b|$)", re.I)
RELEASE = re.compile(r"\b(20\d{2})\s*R([12])\s*(?:Feature\s+)?Release\b", re.I)
RELEASE_ALT = re.compile(r"\b(?:Release\s+)?(20\d{2})\s*R([12])\b", re.I)
CURATED = re.compile(r"Workday\s+(20\d{2})\s+R([12])", re.I)

def _audit_telugu_source(src, now, scanner):
    return scanner(src, now, topic_pattern=TELUGU_EVENT)

def audit_telugu(sources, now, scanner=scan_source):
    """Scan every registered source, including previously manual-only directories."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(lambda src: _audit_telugu_source(src,now,scanner),sources))
    findings=[]
    for item in rows:
        findings.extend(item.get("candidates",[]))
    # Keep the per-source records complete, including blocks and all failures.
    return {
        "generated_utc":now.isoformat(),"registered_sources":len(sources),
        "checked_sources":len(rows),
        "sources_accessible":sum(x["status"] not in ("blocked","error","unverified") for x in rows),
        "pdf_files_extracted":sum(x.get("pdf_scanned",0) for x in rows),
        "pdf_pages_ocr":sum(x.get("pdf_pages_ocr",0) for x in rows),
        "images_ocr":sum(x.get("images_ocr",0) for x in rows),
        "source_audits":rows,
        "candidate_count":len(findings),"candidates":findings[:120],
        "requires_human_review":True,
        "note":"Unverified posters, PDFs and plain text never auto-publish; confirm Telugu relevance, dates, place and organizer before entry."
    }

def extract_workday_milestones(text):
    """Extract institution-published dated R1/R2 release lines, never monthly maintenance."""
    found={}
    for line in text.splitlines():
        sentence=" ".join(line.split())
        m=RELEASE.search(sentence) or RELEASE_ALT.search(sentence)
        if not m or "feature release" not in sentence.lower():
            continue
        d=explicit_dates(sentence)
        if len(d)!=1:
            continue
        release_year=int(m.group(1))
        if d[0].year != release_year:
            continue
        key=f"{release_year}R{m.group(2)}"
        found[key]={"key":key,"date":d[0].isoformat(),"excerpt":sentence[:260]}
    return list(found.values())

def audit_workday(sources, events, now, fetcher=fetch_bytes):
    manifest={}
    for e in events:
        m=CURATED.search(e["title"])
        if m:
            manifest[f"{m.group(1)}R{m.group(2)}"]=e["start"][:10]
    rows=[]; detected={}
    for src in sources:
        row={"name":src["name"],"url":src["url"],"status":"unverified",
             "release_dates":[],"warnings":[],"source_type":"institutional"
             if "Williams" in src["name"] else "official_documentation"}
        try:
            data,ctype=fetcher(src["url"],2_000_000)
            if not (ctype.startswith("text/") or b"<html" in data[:1000].lower()):
                raise ValueError("Unexpected Workday source content type: "+ctype)
            page=Page(); page.feed(data.decode("utf-8","replace"))
            visible="\n".join(page.text)
            row["status"]="accessible"
            row["release_dates"]=extract_workday_milestones(visible)
            if len(visible.strip())<80:
                row["status"]="incomplete"
                row["warnings"].append("Page contains little accessible text; may require authentication or rendering.")
            for entry in row["release_dates"]:
                if "Williams" in src["name"]:
                    detected[entry["key"]]=entry["date"]
        except Exception as exc:
            row["status"]="blocked" if "403" in str(exc) or "429" in str(exc) else "error"
            row["warnings"].append(str(exc)[:180])
        rows.append(row)
    differences=[]
    for release_key,expected in manifest.items():
        if release_key in detected and detected[release_key]!=expected:
            differences.append({"release":release_key,"published_date":expected,
                                "institutional_source_date":detected[release_key],
                                "action":"Review; no automatic changes to tentative published milestones"})
    return {
        "generated_utc":now.isoformat(),
        "registered_sources":len(sources),"source_audits":rows,
        "checked_sources":len(rows),
        "sources_accessible":sum(x["status"]=="accessible" for x in rows),
        "curated_dates":manifest,"institutional_date_matches":detected,
        "date_differences":differences,
        "requires_human_review":True,
        "note":"Workday public release dates may differ by tenant; an institution's maintenance page is not global Workday confirmation."
    }
