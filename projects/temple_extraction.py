"""Source-by-source Phoenix temple inspection: HTML, PDFs, image flyers and JavaScript portals.

Only trusted first-party HTML events with an explicit year are auto-published.
OCR/PDF results are extracted into review candidates, never silently treated as confirmed.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import io
import json
import re
import subprocess

import fitz
from PIL import Image

MAX_PAGE_BYTES=2_000_000
MAX_ASSET_BYTES=9_000_000
MAX_PDF_PAGES=18
MAX_IMAGE_ASSETS=6
MAX_PDF_ASSETS=2
MAX_REVIEW_PER_SOURCE=12
ASSET_HOSTS={"static.wixstatic.com","images.squarespace-cdn.com","static1.squarespace.com",
             "images.ctfassets.net","cdn.prod.website-files.com"}
SPECIAL=re.compile(
    r"\b(?:kalyanotsavam|kalyanam|kalyan|utsavam|utsav|abhishekam|annabhishekam|"
    r"mandala puja|tulasi vivah|ugadi|yugadi|navaratri|maha ?shivaratri|"
    r"sivarathri|sri rama navami|chandi|brahmotsavam|rathotsavam|deepavali|"
    r"diwali|janmashtami|annual celebration|special celebration|homam)\b",re.I)
RECURRING=re.compile(r"\b(?:every|weekly|monthly|1st saturday|2nd saturday|3rd saturday|"
                     r"4th saturday|every purnima|regular services|daily)\b",re.I)
MONTHS="jan feb mar apr may jun jul aug sep oct nov dec".split()
MONTH_RE=r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
MONTH_DATE=re.compile(r"\b("+MONTH_RE+r")\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(20\d{2})\b",re.I)
DATE_MONTH=re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+("+MONTH_RE+r")[,]?\s+(20\d{2})\b",re.I)
ISO_DATE=re.compile(r"\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b")
US_DATE=re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b")
ASSET_SUFFIX=re.compile(r"\.(?:pdf|png|jpe?g|webp)(?:$|\?)",re.I)
KEYWORDS=re.compile(r"event|calendar|202[6-9]|flyer|festival|celebrat|program|schedule|puja|utsav|panchang",re.I)
SKIP=re.compile(r"(?:logo|icon|favicon|background|gopuram|gallery|galleryimage|banner-blank|headerbg)",re.I)

def safe_url(base,url,source_host):
    candidate=urljoin(base,(url or "").strip())
    p=urlsplit(candidate)
    if p.scheme!="https" or p.username or p.password or p.port:
        return None
    host=(p.hostname or "").lower()
    source_host=source_host.removeprefix("www.")
    if host.removeprefix("www.") not in {source_host} and host not in ASSET_HOSTS:
        return None
    if len(candidate)>700:
        return None
    return candidate

def fetch_bytes(url,limit=MAX_ASSET_BYTES):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; VihariCalendarHub/2.0)",
        "Accept":"text/html,application/pdf,image/*,*/*"})
    with urlopen(req,timeout=18) as response:
        content_type=(response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        body=response.read(limit+1)
    if len(body)>limit: raise ValueError("Document exceeds allowed size")
    return body,content_type

class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text=[];self.items=[];self.skip=0;self._json=None;self.jsonld=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag in ("style","noscript"):
            self.skip+=1
        if tag=="script":
            if "ld+json" in d.get("type","").lower():self._json=[]
            else:self.skip+=1
        if tag in ("p","div","article","section","h1","h2","h3","h4","li","tr","br"):
            self.text.append("\n")
        if tag=="a" and d.get("href"):
            self.items.append(("link",d["href"],d.get("title","")))
        if tag in ("img","source"):
            link=d.get("data-src") or d.get("src")
            if not link and d.get("srcset"):link=d["srcset"].split(",")[0].strip().split(" ")[0]
            if link:self.items.append(("image",link,d.get("alt","")+" "+d.get("title","")))
    def handle_endtag(self,tag):
        if tag in ("style","noscript") and self.skip:self.skip-=1
        if tag=="script":
            if self._json is not None:
                self.jsonld.append("".join(self._json));self._json=None
            elif self.skip:self.skip-=1
        if tag in ("p","div","article","section","h1","h2","h3","h4","li","tr"):
            self.text.append("\n")
    def handle_data(self,data):
        if self._json is not None:self._json.append(data)
        elif not self.skip:self.text.append(data)

def ocr_png(png):
    proc=subprocess.run(["tesseract","stdin","stdout","-l","eng","--psm","6"],
                        input=png,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40)
    if proc.returncode:
        raise ValueError("Tesseract OCR failed: "+proc.stderr.decode("utf-8","replace")[:130])
    return proc.stdout.decode("utf-8","replace")

def ocr_image(body):
    Image.MAX_IMAGE_PIXELS=12_000_000
    with Image.open(io.BytesIO(body)) as img:
        img.load()
        if img.width<250 or img.height<200:
            return "",False
        img.thumbnail((1800,1800))
        rgb=img.convert("RGB")
        output=io.BytesIO()
        rgb.save(output,format="PNG")
    return ocr_png(output.getvalue()),True

def extract_pdf(body,full_ocr=True):
    if not body.startswith(b"%PDF"):
        raise ValueError("PDF signature mismatch")
    doc=fitz.open(stream=body,filetype="pdf")
    page_count=len(doc)
    if len(doc)>MAX_PDF_PAGES:
        raise ValueError(f"PDF has {len(doc)} pages; exceeds {MAX_PDF_PAGES}-page limit")
    parts=[];ocr_count=0
    for p in doc:
        visible=p.get_text(sort=True)
        parts.append("Page "+str(p.number+1)+"\n"+visible)
        if full_ocr or len(visible.strip())<250:
            # OCR is a fallback for scanned or image-backed pages.
            pix=p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
            scanned=ocr_png(pix.tobytes("png"))
            parts.append("Page "+str(p.number+1)+" OCR\n"+scanned)
            ocr_count+=1
    doc.close()
    return "\n".join(parts),page_count,ocr_count

def explicit_dates(line):
    dates=[]
    for m in MONTH_DATE.finditer(line):
        month=MONTHS.index(m.group(1)[:3].lower())+1
        try:dates.append(date(int(m.group(3)),month,int(m.group(2))))
        except ValueError:pass
    for m in DATE_MONTH.finditer(line):
        month=MONTHS.index(m.group(2)[:3].lower())+1
        try:dates.append(date(int(m.group(3)),month,int(m.group(1))))
        except ValueError:pass
    for m in ISO_DATE.finditer(line):
        try:dates.append(date(int(m.group(1)),int(m.group(2)),int(m.group(3))))
        except ValueError:pass
    for m in US_DATE.finditer(line):
        try:dates.append(date(int(m.group(3)),int(m.group(1)),int(m.group(2))))
        except ValueError:pass
    return list(dict.fromkeys(dates))

def extract_candidates(text,now,origin,kind="html",max_days=180,topic_pattern=None):
    """Return candidate dates only where explicit YEAR and special-event wording coexist.

    No inherited year, no weekday-derived date, no recurrence expansion.
    """
    pattern=topic_pattern or SPECIAL
    out=[];seen=set()
    lines=[re.sub(r"\s+"," ",x).strip() for x in text.splitlines() if x.strip()]
    for i,line in enumerate(lines):
        if len(line)>400:continue
        context=" ".join(lines[max(0,i-1):min(len(lines),i+2)])[:500]
        if not pattern.search(context) or RECURRING.search(context):
            continue
        found=[d for d in explicit_dates(line) if now.date()<=d<=now.date()+timedelta(days=max_days)]
        match=pattern.search(context)
        if not match:continue
        title=context[match.start():match.end()+70].split(" | ")[0].strip(" :-,.")
        title=re.sub(r"\s+"," ",title)[:105]
        if len(title)<8:continue
        if found:
            for d in found:
                key=(d.isoformat(),title.lower())
                if key in seen:continue
                seen.add(key)
                out.append({"date":d.isoformat(),"title":title,"origin":origin,"kind":kind,
                            "auto_publish":False,"reason":"Requires human confirmation of date-title association"})
        elif kind in ("pdf","image") and len(line)>12:
            # Images often put the event name and month/year on different lines.
            # Record the extracted title, but never infer missing dates.
            key=(None,title.lower())
            if key not in seen:
                seen.add(key)
                out.append({"date":None,"title":title,"origin":origin,"kind":kind,
                            "auto_publish":False,
                            "reason":"Event name extracted; exact date not established from image or PDF"})
    return out[:MAX_REVIEW_PER_SOURCE]

def asset_candidates(items,base,source_host):
    possible={}
    for kind,url,desc in items:
        safe=safe_url(base,url,source_host)
        if not safe:continue
        parsed=urlsplit(safe)
        is_pdf=parsed.path.lower().endswith(".pdf")
        is_image=bool(re.search(r"\.(?:png|jpg|jpeg|webp)(?:$|/)",parsed.path,re.I)) or (
            "static.wixstatic.com" in (parsed.hostname or "") and "/media/" in parsed.path)
        if not(is_pdf or is_image):continue
        score=len(KEYWORDS.findall(desc+" "+parsed.path.split("/")[-1]))
        if SKIP.search(desc+" "+parsed.path.split("/")[-1]):score-=3
        if score<=0:continue
        if re.search(r"/fill/w_(?:[1-9]|[1-9][0-9]),",parsed.path):continue
        old=possible.get(safe)
        if not old or old[0]<score:possible[safe]=(score,"pdf" if is_pdf else "image")
    assets=sorted(possible.items(),key=lambda x:(-x[1][0],x[0]))
    pdfs=[(url,t) for url,t in assets if t[1]=="pdf"][:MAX_PDF_ASSETS]
    images=[(url,t) for url,t in assets if t[1]=="image"][:MAX_IMAGE_ASSETS]
    return [(url,kind[1]) for url,kind in pdfs+images]

def scan_source(source,now,fetcher=fetch_bytes,browser=None,topic_pattern=None):
    url=source["url"];host=urlsplit(url).hostname or ""
    report={"name":source["name"],"url":url,"status":"unverified","html_checked":False,
            "pdf_scanned":0,"pdf_pages_ocr":0,"images_ocr":0,"assets_found":0,
            "assets_checked":0,"candidate_count":0,"candidates":[],
            "warnings":[],"auto_published":0}
    try:
        main_limit=MAX_ASSET_BYTES if urlsplit(url).path.lower().endswith(".pdf") else MAX_PAGE_BYTES
        page,typ=fetcher(url,main_limit)
        if typ=="application/pdf" or page.startswith(b"%PDF"):
            text,pages,ocr=extract_pdf(page)
            report["pdf_scanned"]+=1;report["pdf_pages_ocr"]+=ocr
            report["candidates"]=extract_candidates(text,now,url,"pdf",topic_pattern=topic_pattern)
            report["status"]="review_needed" if report["candidates"] else "no_verified_events"
            report["candidate_count"]=len(report["candidates"])
            return report
        if not(typ.startswith("text/") or b"<html" in page[:1000].lower()):
            raise ValueError("Unexpected main-page content type: "+typ)
        html=page.decode("utf-8","replace")
        parser=Page();parser.feed(html)
        visible="\n".join(parser.text)
        report["html_checked"]=True
        if ("enable javascript" in visible.lower() or len(visible.strip())<80) and browser:
            html=browser(url)
            parser=Page();parser.feed(html)
            visible="\n".join(parser.text)
            report["browser_rendered"]=True
        report["candidates"]=extract_candidates(visible,now,url,"html",topic_pattern=topic_pattern)
        candidates=asset_candidates(parser.items,url,host)
        # Sources with a directly linked PDF or image but generic filenames
        # should still get scanned when the anchor says 'Download calendar'.
        report["assets_found"]=len(candidates)
        report["asset_scan_limited"]=len(candidates)>=MAX_IMAGE_ASSETS+MAX_PDF_ASSETS
        report["assets_scanned"]=[]
        for link,kind in candidates:
            try:
                body,ctype=fetcher(link,MAX_ASSET_BYTES)
                report["assets_checked"]+=1
                report["assets_scanned"].append({"url":link,"type":kind,"content_type":ctype})
                if kind=="pdf" and (body.startswith(b"%PDF") or "pdf" in ctype):
                    text,pages,ocr=extract_pdf(body)
                    report["pdf_scanned"]+=1;report["pdf_pages_ocr"]+=ocr
                elif kind=="image" and (ctype.startswith("image/") or body[:4] in (b"\x89PNG",b"RIFF") or body[:3]==b"\xff\xd8\xff"):
                    text,used=ocr_image(body)
                    report["images_ocr"]+=int(used)
                else:
                    report["warnings"].append("Asset unexpected content type: "+link[:180])
                    continue
                report["candidates"]+=extract_candidates(text,now,link,kind,topic_pattern=topic_pattern)
            except Exception as e:
                report["warnings"].append(kind+" "+link[:130]+": "+str(e)[:130])
        # Deduplicate and bound output size.
        dedup={}
        for c in report["candidates"]:dedup[(c["date"],c["title"].lower())]=c
        report["candidates"]=list(dedup.values())[:MAX_REVIEW_PER_SOURCE]
        report["candidate_count"]=len(report["candidates"])
        report["status"]="partial" if report["warnings"] else (
            "review_needed" if report["candidates"] else "no_verified_events")
    except Exception as e:
        report["status"]="blocked" if ("403" in str(e) or "429" in str(e)) else "error"
        report["warnings"].append(str(e)[:200])
    return report
