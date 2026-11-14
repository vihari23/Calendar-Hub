"""Build four source-backed ICS calendars. Python standard library only."""
import argparse
from datetime import datetime, date, timedelta, timezone
from html.parser import HTMLParser
from html import unescape
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

TZ=ZoneInfo("America/Phoenix")
UTC=timezone.utc
ROOT=Path(__file__).resolve().parent
SLUGS=("arizona-telugu","phoenix-temples","workday-releases","phoenix-road-closures")
MAX_BYTES=1_500_000
CITIES=("arizona","phoenix","tempe","glendale","peoria","scottsdale","chandler","mesa","gilbert","surprise","goodyear","avondale","queen creek")
TELUGU=("telugu","telangana","bathukamma","ugadi","sankranti","tollywood","sri rama kalyan","ram miriyala")
SPECIAL=("ugadi","kalyanam","kalyanotsavam","brahmotsavam","rathotsavam","navaratri","navratri","shivarathri","shivaratri","vaikunta","dussehra","vijayadashami","deepavali","diwali","chandi homam","maharudram","kar thika","karthika","anniversary celebrations")

def fetch(url):
    parsed=urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only HTTPS source URLs are allowed")
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; VihariCalendarHub/1.0)","Accept":"text/html,application/ld+json,*/*"})
    with urlopen(req,timeout=15) as response:
        data=response.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:
        raise ValueError("Source exceeds size limit")
    return data.decode("utf-8","replace")

class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts=[]
        self._json=None
        self.lines=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="script" and "ld+json" in a.get("type","").lower():
            self._json=[]
        if tag in ("p","li","br","h1","h2","h3"):
            self.lines.append("\n")
        if tag=="a" and a.get("href"):
            self.links.append(a["href"])
    def handle_data(self,data):
        if self._json is not None:
            self._json.append(data)
        else:
            self.lines.append(data)
    def handle_endtag(self,tag):
        if tag=="script" and self._json is not None:
            self.scripts.append("".join(self._json))
            self._json=None
        if tag in ("p","li","h1","h2","h3"):
            self.lines.append("\n")

def walk_events(obj):
    if isinstance(obj,list):
        for value in obj: yield from walk_events(value)
    elif isinstance(obj,dict):
        types=obj.get("@type",[])
        types=[types] if isinstance(types,str) else types
        if any(t.lower().endswith("event") for t in types if isinstance(t,str)):
            yield obj
        for k,v in obj.items():
            if isinstance(v,(dict,list)):
                yield from walk_events(v)

def read_iso(value):
    if not isinstance(value,str) or not value:
        raise ValueError("Missing start or end time")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
        return date.fromisoformat(value), True
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:
        dt=dt.replace(tzinfo=TZ)
    return dt.astimezone(TZ), False

def normalize(event):
    title=str(event["title"]).strip()
    start,all_day=read_iso(event["start"])
    end_value=event.get("end")
    if not end_value:
        if all_day:
            end=start+timedelta(days=1)
        else:
            raise ValueError("Timed event without verified end")
    else:
        end,end_day=read_iso(end_value)
        if end_day!=all_day:
            raise ValueError("Mismatched start/end type")
    if end<=start:
        raise ValueError("Event must end after it starts")
    link=str(event.get("url",""))
    if link and urlsplit(link).scheme!="https":
        raise ValueError("Event source must be HTTPS")
    return dict(title=title,start=start,end=end,all_day=all_day,
                location=str(event.get("location","")),url=link,
                description=str(event.get("description","")),source=str(event.get("source","")))

def auto_from_jsonld(url,kind):
    parser=Collector()
    parser.feed(fetch(url))
    output=[]
    for raw in parser.scripts:
        try: data=json.loads(unescape(raw))
        except (ValueError,TypeError): continue
        for item in walk_events(data):
            try:
                title=str(item["name"])
                desc=str(item.get("description",""))
                loc=item.get("location",{})
                if isinstance(loc,list): loc=loc[0] if loc else {}
                if isinstance(loc,dict):
                    a=loc.get("address",{})
                    where=" ".join(str(v) for v in a.values()) if isinstance(a,dict) else str(a)
                    where=(str(loc.get("name",""))+" "+where).strip()
                else: where=str(loc)
                if not any(city in (where+" "+title).lower() for city in CITIES):
                    continue
                corpus=(title+" "+desc+" "+str(item.get("organizer",""))).lower()
                if kind=="arizona-telugu" and not any(k in corpus for k in TELUGU):
                    continue
                if kind=="phoenix-temples" and not any(k in corpus for k in SPECIAL):
                    continue
                event={"title":title,"start":item["startDate"],"end":item.get("endDate"),
                       "location":where,"url":str(item.get("url",url)),"description":desc[:700],
                       "source":url}
                output.append(normalize(event))
            except (ValueError,TypeError,KeyError,OverflowError):
                continue
    return output

def parse_adot(news_page,now):
    homepage=Collector();homepage.feed(news_page)
    path=next((h for h in homepage.links if "/news/adots-weekend-freeway-travel-advisory-" in h.lower()),None)
    if not path:
        return [],"No current ADOT weekend advisory link found"
    url=urljoin("https://azdot.gov",path)
    if urlsplit(url).hostname!="azdot.gov":
        raise ValueError("ADOT link outside official domain")
    article=Collector(); article.feed(fetch(url))
    raw=" ".join("".join(article.lines).split())
    # Find the advisory date range in the official article, not the system clock.
    title_match=re.search(r"advisory\s*\(\s*([A-Za-z]{3,9})\.?\s*(\d{1,2})\s*[-–]\s*(\d{1,2})\s*\)",raw,re.I)
    if not title_match:
        raise ValueError("ADOT advisory date range not found; refusing guessed dates")
    month=datetime.strptime(title_match.group(1)[:3],"%b").month
    d1=int(title_match.group(2))
    year=now.year
    # Year transition: a December page can be checked in January.
    if now.month==1 and month==12: year-=1
    if now.month==12 and month==1: year+=1
    first=date(year,month,d1)
    day_by_name={}
    for i in range(5):
        d=first+timedelta(days=i)
        day_by_name[d.strftime("%a").lower()]=d
    time_re=re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\s*(Fri|Sat|Sun|Mon|Tue|Wed|Thu)\b",re.I)
    output=[]
    for line in "".join(article.lines).splitlines():
        s=" ".join(line.split())
        if not re.search(r"\bclosed\b",s,re.I):
            continue
        matches=list(time_re.finditer(s))
        if len(matches)<2:
            continue
        def convert(m):
            day=day_by_name.get(m.group(4).lower())
            if day is None: raise ValueError("Weekday not in advisory")
            hour=int(m.group(1))%12+(12 if m.group(3).lower().startswith("p") else 0)
            return datetime(day.year,day.month,day.day,hour,int(m.group(2) or 0),tzinfo=TZ)
        try:
            start=convert(matches[0]);end=convert(matches[1])
            if end<=start: continue
        except (ValueError,OverflowError):
            continue
        head=s[:matches[0].start()].strip(" :-,.;")
        if not re.search(r"\b(?:I-\d+|Loop\s+\d+|SR\s+\d+|US\s+\d+)\b",head,re.I):
            continue
        output.append(normalize({"title":"ADOT closure: "+head[:140],
            "start":start.isoformat(),"end":end.isoformat(),"location":"Phoenix metro, Arizona",
            "url":url,"description":s[:950]+" | Dates/times may change; check ADOT/AZ511 before travel.",
            "source":"Arizona Department of Transportation"}))
    if not output:
        return [],"Advisory found but no precisely timed full closures parsed"
    return output,f"{len(output)} timed closures extracted from {url}"

def auto_from_wzdx(now):
    """Read official AZ511 WZDx public data, accepting only verified nearby closures."""
    url="https://az511.com/api/wzdx"
    req=Request(url,headers={"User-Agent":"VihariCalendarHub/1.0","Accept":"application/json"})
    with urlopen(req,timeout=25) as response:
        blob=response.read(20000001)
    if len(blob)>20000000: raise ValueError("AZ511 data exceeds 20MB")
    data=json.loads(blob)
    if data.get("type")!="FeatureCollection": raise ValueError("Unexpected AZ511 data format")
    results=[]
    for feature in data.get("features",[]):
        try:
            props=feature["properties"];core=props.get("core_details") or {}
            if not isinstance(core,dict):continue
            a=core.get("start_date") or props.get("start_date")
            b=core.get("end_date") or props.get("end_date")
            if not a or not b:continue
            start,day1=read_iso(a);end,day2=read_iso(b)
            if day1 or day2 or end<=start or end<now-timedelta(hours=12) or start>now+timedelta(days=35) or end-start>timedelta(days=7):continue
            if not (core.get("is_start_date_verified") and core.get("is_end_date_verified")):continue
            roads=core.get("road_names") or props.get("road_names") or []
            name="; ".join(str(x) for x in roads[:2]) if isinstance(roads,list) else str(roads)
            desc=str(core.get("description") or props.get("description") or "")
            impact=props.get("vehicle_impact",core.get("vehicle_impact",""))
            if impact!="all-lanes-closed" and "full closure" not in (name+" "+desc).lower():continue
            if not re.search(r"\b(?:I-\d+|Loop\s+\d+|SR\s+\d+|US\s+\d+)\b",name+" "+desc,re.I):continue
            def coords(value):
                if isinstance(value,list):
                    if len(value)>1 and isinstance(value[0],(int,float)) and isinstance(value[1],(int,float)):
                        yield value[0],value[1]
                    else:
                        for node in value:yield from coords(node)
            if not any(-113.1<=lon<=-111 and 32.8<=lat<=34 for lon,lat in coords((feature.get("geometry") or {}).get("coordinates",[]))):continue
            results.append(normalize({"title":"AZ511 closure: "+name[:130],"start":start.isoformat(),"end":end.isoformat(),"location":name+", Phoenix metro, AZ","url":"https://az511.gov/","description":desc[:800]+" Verify with AZ511 before travel.","source":url}))
        except (KeyError,TypeError,ValueError,OverflowError):continue
    return results

def esc(text):
    return str(text).replace("\\","\\\\").replace("\n","\\n").replace(",","\\,").replace(";","\\;").replace("\r","")

def fold(line):
    parts=[];cur=""
    for ch in line:
        candidate=cur+ch
        if len(candidate.encode("utf-8"))> (74 if parts else 75):
            parts.append(cur)
            cur=" "+ch
        else:
            cur=candidate
    parts.append(cur)
    return "\r\n".join(parts)+"\r\n"

def ics(name,slug,events,now):
    lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Vihari Calendar Hub//Verified Events//EN",
           "CALSCALE:GREGORIAN","METHOD:PUBLISH","X-WR-CALNAME:"+esc(name),
           "X-WR-TIMEZONE:America/Phoenix","REFRESH-INTERVAL;VALUE=DURATION:PT12H"]
    unique={}
    for e in events:
        key=(e["title"].casefold(),str(e["start"]))
        if key not in unique: unique[key]=e
    for e in sorted(unique.values(),key=lambda e:str(e["start"])):
        ident=hashlib.sha256((slug+"|"+e["title"].casefold()+"|"+str(e["start"])).encode()).hexdigest()[:24]
        if e["all_day"]:
            start="DTSTART;VALUE=DATE:"+e["start"].strftime("%Y%m%d")
            end="DTEND;VALUE=DATE:"+e["end"].strftime("%Y%m%d")
        else:
            start="DTSTART:"+e["start"].astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
            end="DTEND:"+e["end"].astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        lines.extend(["BEGIN:VEVENT","UID:"+ident+"@vihari-calendar-hub",
          "DTSTAMP:"+now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ"),
          "SUMMARY:"+esc(e["title"]),start,end,
          "DESCRIPTION:"+esc((e.get("description","")+" Source: "+e.get("source","")).strip()),
          "LOCATION:"+esc(e.get("location","")),
          "URL:"+e.get("url",""),"STATUS:CONFIRMED","END:VEVENT"])
    lines.append("END:VCALENDAR")
    return "".join(fold(line) for line in lines).encode("utf-8")

def build(out,now=None,network=True):
    now=now or datetime.now(TZ)
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    report={}
    for slug in SLUGS:
        manifest=json.loads((ROOT/slug/"project.json").read_text(encoding="utf-8"))
        events=[]
        for event in manifest["events"]:
            events.append(normalize(event))
        discovered=0; errors=[]
        if network and slug in ("arizona-telugu","phoenix-temples"):
            for source in manifest["sources"]:
                if source.get("import")!="jsonld":
                    continue
                try:
                    newer=auto_from_jsonld(source["url"],slug)
                    events.extend(newer);discovered+=len(newer)
                except Exception as exc:
                    errors.append(source["url"]+": "+str(exc)[:100])
        if network and slug=="phoenix-road-closures":
            try:
                newer=auto_from_wzdx(now)
                events.extend(newer);discovered+=len(newer)
                if not newer: errors.append("AZ511: no independently verified new full freeway closures")
            except Exception as exc:
                errors.append("AZ511 WZDx: "+str(exc)[:160])
            try:
                news=fetch("https://azdot.gov/adot-news")
                newer,info=parse_adot(news,now)
                events.extend(newer);discovered+=len(newer)
                if not newer: errors.append(info)
            except Exception as exc:
                errors.append("ADOT advisory: "+str(exc)[:130])
        content=ics(manifest["name"],slug,events,now)
        (out/(slug+".ics")).write_bytes(content)
        report[slug]={"events":content.count(b"BEGIN:VEVENT"),"auto_discovered":discovered,
            "source_checks":sum(s.get("import")=="jsonld" for s in manifest["sources"]),
            "warnings":errors,"generated_utc":now.astimezone(UTC).isoformat()}
        print(slug,report[slug])
    (out/"source-status.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    return report

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",default="dist/feeds")
    p.add_argument("--offline",action="store_true")
    args=p.parse_args()
    build(args.out,network=not args.offline)
