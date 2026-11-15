"""Official dated-list importers for Sri Bhakta Hanuman and Sri Lalitha temples.

These sources do not reliably expose JSON-LD Event records. Never turn
weekday-only recurring services or yearless monthly grids into future events.
"""
from datetime import datetime, date, time, timedelta
from html.parser import HTMLParser
import re
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Phoenix")
WEEKDAY = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
NUMERIC = re.compile(r"(?<!\d)(\d{1,2})[-/](\d{1,2})[-/](20\d{2})(?:\s*,\s*("+WEEKDAY+r"))?",re.I)
MONTH = re.compile(r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?\s*,?\s*(20\d{2})\b",re.I)
TOPIC = re.compile(
    r"navaratri|navratri|utsav|celebrat|jayanti|deepavali|diwali|"
    r"yugadi|ugadi|ram[ao]? navami|kalyan|special (?:puja|pooja)|"
    r"abhishe[kc]|homam|havan|rudra|sundara\s*kand|"
    r"puja|pooja|vijayadashami|dussehra|durga ashtami|"
    r"maha navami|sarva pitru amavasya|ay(y)?appa|ganapathi",re.I)
REGULAR = re.compile(
    r"\b(?:every|weekly|regular|\d(?:st|nd|rd|th) (?:Saturday|Sunday)|"
    r"ann[a]?\s*da[an]n?am|donation|classes|temple hours)\b",re.I)
CLOCK_RANGE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*(?:-|–|—|to)\s*"
    r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",re.I)


class TextLines(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self.hidden += 1
        if not self.hidden and tag in ("p","div","li","br","tr","td","th","h1","h2","h3","h4","h5","h6"):
            self.parts.append("\n")
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):
            self.hidden = max(0,self.hidden-1)
        if not self.hidden and tag in ("p","div","li","tr","td","th","h1","h2","h3","h4","h5","h6"):
            self.parts.append("\n")
    def handle_data(self,data):
        if not self.hidden: self.parts.append(data)
    def lines(self):
        joined="".join(self.parts)
        return [re.sub(r"\s+"," ",row).strip() for row in joined.splitlines() if row.strip()]


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row = None
        self.cell = None
        self.hidden = 0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style","noscript"):
            self.hidden += 1
        if self.hidden:return
        if tag=="tr":self.row=[]
        if tag in ("td","th") and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if not self.hidden and self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ("script","style","noscript"):
            self.hidden=max(0,self.hidden-1);return
        if tag in ("td","th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()));self.cell=None
        if tag=="tr" and self.row is not None:
            if self.row:self.rows.append(self.row)
            self.row=None


def _clock(hour,minute,ampm):
    h=int(hour)%12 + (12 if ampm.lower()=="pm" else 0)
    return time(h,int(minute or 0))


def _range(text):
    match=CLOCK_RANGE.search(text)
    if not match:return None
    a,b,c,d,e,f=match.groups()
    start,end=_clock(a,b,c),_clock(d,e,f)
    return (start,end) if end>start else None


def _normalize(title,when,url,source,description,raw_time=None):
    from projects.build_feeds import normalize
    start,end=raw_time or (time(8),time(9))
    if raw_time:
        description+=" Official page provides matching start and end times."
    else:
        description+=" 8:00–9:00 AM is a default calendar window, NOT a confirmed event time. Check the temple before attending."
    return normalize({
        "title":title,
        "start":datetime.combine(when,start,TZ).isoformat(),
        "end":datetime.combine(when,end,TZ).isoformat(),
        "location":"Phoenix, Arizona, USA","url":url,"source":source,
        "description":description
    })


def _within(when,now):
    return now.date()<=when<=now.date()+timedelta(days=180)


def hanuman_from_html(html,url,now):
    reader=TextLines()
    reader.feed(html)
    lines=reader.lines()
    all_dates=[]
    events=[]
    seen=set()
    for i,line in enumerate(lines):
        m=NUMERIC.search(line)
        if not m: continue
        try:
            when=date(int(m.group(3)),int(m.group(1)),int(m.group(2)))
        except ValueError:continue
        if m.group(4) and when.strftime("%A").lower()!=m.group(4).lower():continue
        all_dates.append(when)
        if not _within(when,now):continue
        # Each official program item is listed under a complete date, and a
        # new dated heading terminates the current list.
        collected=[]
        for following in lines[i+1:i+24]:
            if NUMERIC.search(following) or re.search(r"\bWeekly Regular Events\b|\bTemple Hours\b",following,re.I):
                break
            if TOPIC.search(following) and not REGULAR.search(following):
                collected.append(following)
        for item in collected[:4]:
            summary=re.sub(r"^\s*\d{1,2}:\d{2}\s*(?:AM|PM)\s*[:–-]?\s*","",item,flags=re.I)
            summary=summary.strip(" -–:")
            if len(summary)<5:continue
            key=(when,summary.casefold())
            if key in seen:continue
            seen.add(key)
            events.append(_normalize("Sri Bhakta Hanuman Temple — "+summary[:105],when,url,
                  "Sri Bhakta Hanuman Temple",
                  "Dated entry from the official upcoming-program schedule. Listed detail: "+item[:240]+".",
                  _range(item)))
    return {"events":events,"dated_count":len(set(all_dates)),
            "latest_date":max(all_dates).isoformat() if all_dates else None,
            "status":"future_events" if events else ("outdated_schedule" if all_dates and max(all_dates)<now.date()
                       else "no_qualifying_events" if all_dates else "no_dated_events")}


def lalitha_from_html(html,url,now):
    rows=TableRows();rows.feed(html)
    all_dates=[]
    events=[]
    seen=set()
    # Official Upcoming Events table has date as the first cell. The weekly
    # regular-service table has weekday names and is never expanded.
    for row in rows.rows:
        if len(row)<2:continue
        m=MONTH.search(row[0])
        if not m:continue
        try:
            when=datetime.strptime(" ".join(m.groups()),"%b %d %Y").date() if len(m.group(1))==3 else date(int(m.group(3)),datetime.strptime(m.group(1)[:3],"%b").month,int(m.group(2)))
        except ValueError:
            continue
        all_dates.append(when)
        if not _within(when,now):continue
        title=row[1].strip()
        if not TOPIC.search(title) or REGULAR.search(title):continue
        key=(when,title.casefold())
        if key in seen:continue
        seen.add(key)
        detail=" ".join(row[2:])
        events.append(_normalize("Sri Lalitha Temple — "+title[:110],when,url,
            "Sri Lalitha Temple",
            "Official temple-event table dated "+when.isoformat()+". "+detail[:250],_range(detail)))
    return {"events":events,"dated_count":len(set(all_dates)),
            "latest_date":max(all_dates).isoformat() if all_dates else None,
            "status":"future_events" if events else ("outdated_schedule" if all_dates and max(all_dates)<now.date()
                       else "no_qualifying_events" if all_dates else "no_dated_events")}


def import_dated_temple(source,now,fetcher=None):
    """Return event results and an auditable freshness assessment.

    Use the same first-party source fetcher as the full-scan stage: some
    servers reject the narrower generic JSON-LD importer request.
    """
    if fetcher is None:
        from projects.temple_extraction import fetch_bytes
        def fetcher(url):
            body,_=fetch_bytes(url,2_000_000)
            return body.decode("utf-8","replace")
    html=fetcher(source["url"])
    fn={"hanuman_html":hanuman_from_html,"lalitha_html":lalitha_from_html}[source["import"]]
    result=fn(html,source["url"],now)
    result["warnings"]=[]
    if result["status"]=="outdated_schedule":
        result["warnings"].append("Latest explicitly dated program is "+result["latest_date"]+
            "; no verified upcoming special events. Do not expand weekly services into invented dates.")
    if result["status"]=="no_dated_events":
        result["warnings"].append("No explicit-year event rows found; source layout may have changed.")
    return result
