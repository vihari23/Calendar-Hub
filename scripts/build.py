"""Read-only health monitor for public calendar subscriptions. Python 3.11+ stdlib."""
import argparse
from datetime import datetime, date, timezone, timedelta
from html import escape as html_escape
import json
import shutil
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

PHOENIX=ZoneInfo("America/Phoenix")
UTC=timezone.utc
MAX_BYTES=3_000_000
ALLOWED_HOSTS={"vihari23.github.io","raw.githubusercontent.com"}
ID_RE=re.compile(r"^[a-z][a-z0-9_-]{1,39}$")
STAMP_RE=re.compile(r"^\d{8}T\d{6}Z$")

def load_config(path):
    cfg=json.loads(Path(path).read_text(encoding="utf8"))
    if cfg.get("schema_version") != 1 or not isinstance(cfg.get("feeds"),list) or not cfg["feeds"]:
        raise ValueError("Invalid feed configuration")
    ids=set()
    for f in cfg["feeds"]:
        fid=f.get("id")
        if not isinstance(fid,str) or not ID_RE.fullmatch(fid) or fid in ids:
            raise ValueError("Invalid or duplicate feed ID")
        ids.add(fid)
        for key in ("name","description","kind","url","source_repository"):
            if not isinstance(f.get(key),str) or not f[key].strip():
                raise ValueError(f"{fid}: missing {key}")
        u=urlsplit(f["url"])
        if u.scheme!="https" or u.hostname not in ALLOWED_HOSTS or u.username or u.password or u.port or u.query or u.fragment:
            raise ValueError(f"{fid}: feed URL must be a public allowlisted HTTPS resource")
        v=urlsplit(f["source_repository"])
        if v.scheme!="https" or v.hostname!="github.com":
            raise ValueError(f"{fid}: source repository must be public GitHub")
        if not isinstance(f.get("enabled"),bool) or f.get("expected_update") not in ("daily","weekly","monthly"):
            raise ValueError(f"{fid}: invalid metadata")
        for key,low,high in (("max_age_hours",1,2160),("min_events",1,200000)):
            val=f.get(key)
            if type(val) is not int or not low<=val<=high:
                raise ValueError(f"{fid}: invalid {key}")
    if type(cfg.get("look_ahead_days")) is not int or not 1<=cfg["look_ahead_days"]<=365:
        raise ValueError("Invalid look_ahead_days")
    return cfg

def unfold(raw):
    if not raw.startswith(b"BEGIN:VCALENDAR\r\n") or not raw.endswith(b"END:VCALENDAR\r\n"):
        raise ValueError("ICS must have RFC5545 VCALENDAR boundaries")
    if len(raw)>MAX_BYTES:
        raise ValueError("ICS too large")
    text=raw.decode("utf-8-sig")
    out=[]
    for line in text.split("\r\n"):
        if line.startswith((" ","\t")) and out:
            out[-1]+=line[1:]
        else:
            out.append(line)
    return out

def display_date(line):
    try:
        meta,value=line.split(":",1)
        if not meta.startswith("DTSTART"):
            return None
        if value.endswith("Z"):
            return datetime.strptime(value,"%Y%m%dT%H%M%SZ").replace(tzinfo=UTC).astimezone(PHOENIX)
        if len(value)==8:
            return datetime.strptime(value,"%Y%m%d").replace(tzinfo=PHOENIX)
        if "TZID=" in meta and "TZID=America/Phoenix" not in meta:
            return None
        return datetime.strptime(value,"%Y%m%dT%H%M%S").replace(tzinfo=PHOENIX)
    except ValueError:
        return None

def parse_calendar(raw,now,min_events):
    lines=unfold(raw)
    if lines.count("BEGIN:VEVENT")!=lines.count("END:VEVENT"):
        raise ValueError("VEVENT boundaries mismatch")
    evs=[]
    current=None
    for line in lines:
        if line=="BEGIN:VEVENT":
            if current is not None:
                raise ValueError("Nested event")
            current={}
        elif line=="END:VEVENT":
            if current is None:
                raise ValueError("Unexpected event end")
            evs.append(current)
            current=None
        elif current is not None and ":" in line:
            k,v=line.split(":",1)
            field=k.split(";",1)[0]
            if field not in current:
                current[field]=v
                if field=="DTSTART":
                    current["_dtstart"]=line
    if current is not None or len(evs)<min_events:
        raise ValueError(f"Insufficient events: {len(evs)} vs minimum {min_events}")
    if any(not (e.get("UID") and e.get("SUMMARY") and e.get("DTSTART")) for e in evs):
        raise ValueError("Event missing UID, DTSTART or SUMMARY")
    stamps=[]
    for e in evs:
        s=e.get("DTSTAMP","")
        if STAMP_RE.fullmatch(s):
            stamps.append(datetime.strptime(s,"%Y%m%dT%H%M%SZ").replace(tzinfo=UTC))
    latest=max(stamps) if stamps else None
    if latest and latest>now+timedelta(hours=12):
        raise ValueError("Feed generation timestamp is in the future")
    window_end=(now+timedelta(days=365)).astimezone(PHOENIX).date()
    today=now.astimezone(PHOENIX).date()
    upcoming=[]
    for e in evs:
        d=display_date(e.get("_dtstart",""))
        if d and today<=d.date()<=window_end:
            title=(e["SUMMARY"].replace("\\n"," ").replace("\\N"," ").replace("\\, ",", ").replace("\\,",",").replace("\\;",";").replace("\\\\","\\"))
            upcoming.append({"date":d.date().isoformat(),"start":d.isoformat(),"name":title})
    upcoming.sort(key=lambda x:(x["start"],x["name"]))
    return {"events":len(evs),"last_generated_utc":latest.isoformat() if latest else None,
            "age_hours":round((now-latest).total_seconds()/3600,1) if latest else None,
            "upcoming":upcoming}

def download(url):
    req=Request(url,headers={"User-Agent":"VihariCalendarHub/1.0","Accept":"text/calendar,text/plain,*/*"})
    with urlopen(req,timeout=25) as response:
        if response.status!=200:
            raise ValueError(f"HTTP {response.status}")
        data=response.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:
        raise ValueError("Download exceeds 3 MB")
    return data

def recent_successful_publication(repo_url):
    """Fallback for calendars without DTSTAMP: last successful public Actions run.

    This establishes recent publication activity, not a verified per-event timestamp.
    """
    parsed=urlsplit(repo_url)
    parts=parsed.path.strip("/").split("/")
    if parsed.scheme!="https" or parsed.hostname!="github.com" or len(parts)!=2 or not all(parts):
        raise ValueError("GitHub source repository URL invalid")
    api=f"https://api.github.com/repos/{parts[0]}/{parts[1]}/actions/runs?per_page=30&status=success"
    req=Request(api,headers={"User-Agent":"VihariCalendarHub/1.0","Accept":"application/vnd.github+json"})
    with urlopen(req,timeout=20) as response:
        data=json.load(response)
    successful=[]
    for run in data.get("workflow_runs",[]):
        if run.get("conclusion")=="success" and run.get("status")=="completed":
            stamp=run.get("updated_at")
            if stamp:
                successful.append(datetime.fromisoformat(stamp.replace("Z","+00:00")))
    if not successful:
        raise ValueError("No completed successful GitHub Actions runs found")
    return max(successful)

def check_feed(f,now,getter=download,publish_getter=recent_successful_publication):
    result={k:f[k] for k in ("id","name","description","kind","url","source_repository","expected_update")}
    result.update(status="unverified",detail="Not checked",events=0,upcoming=[],checked_at_utc=now.isoformat())
    if not f["enabled"]:
        result.update(status="disabled",detail="Monitoring disabled")
        return result
    try:
        found=parse_calendar(getter(f["url"]),now,f["min_events"])
        result.update(found)
        if found["age_hours"] is None:
            published=publish_getter(f["source_repository"])
            age=round((now-published).total_seconds()/3600,1)
            if age < -12:
                raise ValueError("GitHub publication timestamp is in the future")
            result.update(last_generated_utc=None,last_published_utc=published.isoformat(),
                          age_hours=age,freshness_basis="github_actions_success")
            detail="ICS validated; freshness inferred from latest successful GitHub Actions publication (no valid event DTSTAMP)"
        else:
            age=found["age_hours"]
            result.update(freshness_basis="ics_dtstamp")
            detail="ICS validated; event generation timestamp verified"
        result.update(status=("stale" if age>f["max_age_hours"] else "healthy"),
                      detail=("Feed publication/generation is older than configured threshold" if age>f["max_age_hours"] else detail))
    except Exception as exc:
        result.update(status="error",detail=str(exc)[:220])
    return result

def dashboard(cfg,status):
    safe=lambda s:html_escape(str(s),quote=True)
    readings=status["feeds"]
    cards=[]
    agenda=[]
    today=datetime.fromisoformat(status["checked_at_utc"]).astimezone(PHOENIX).date()
    horizon=today+timedelta(days=cfg["look_ahead_days"])
    for f in readings:
        cards.append('<article data-feed="'+safe(f["id"])+'"><div class="top"><span>'+safe(f["kind"])+'</span><strong class="'+safe(f["status"])+'">'+safe(f["status"])+'</strong></div><h2>'+safe(f["name"])+'</h2><p>'+safe(f["description"])+'</p><p class="quiet">'+safe(f["detail"])+'</p><dl><dt>Events</dt><dd>'+str(f["events"])+'</dd><dt>Last generation / publication</dt><dd>'+safe(str(f.get("age_hours","unknown"))+" hours ago")+'</dd></dl><p><a href="'+safe(f["url"])+'">Subscription ICS</a> · <a href="'+safe(f["source_repository"])+'">Source repository</a></p></article>')
        for e in f["upcoming"]:
            if today<=date.fromisoformat(e["date"])<=horizon:
                agenda.append((e["start"],f["id"],f["name"],e))
    agenda.sort(key=lambda x:x[0])
    rows=['<li data-feed="'+safe(fid)+'"><time>'+safe(e["date"])+'</time><span>'+safe(e["name"])+'<small>'+safe(name)+'</small></span></li>' for _,fid,name,e in agenda[:150]]
    filters=['<label><input type="checkbox" data-choice="'+safe(f["id"])+'" checked> '+safe(f["name"])+'</label>' for f in readings]
    good=sum(f["status"]=="healthy" for f in readings)
    page=r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><meta name="theme-color" content="#0d286e"><meta name="application-name" content="Calendar Hub"><meta name="apple-mobile-web-app-title" content="Calendar Hub"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="default"><link rel="manifest" href="./manifest.webmanifest"><link rel="icon" type="image/svg+xml" href="./icon.svg"><link rel="apple-touch-icon" sizes="180x180" href="./apple-touch-icon.png">
<style>
:root{color-scheme:light dark}*{box-sizing:border-box}body{font:16px/1.55 system-ui,-apple-system,sans-serif;background:light-dark(#f7f9fb,#121826);color:light-dark(#1b2737,#e8edf7);margin:0}main{max-width:1060px;margin:40px auto;padding:0 18px}h1{font-size:clamp(30px,5vw,48px);margin:6px 0}h2{font-size:20px;margin:10px 0}.muted,.quiet,small,dt{color:light-dark(#66748a,#afbcd0)}.muted{font-size:14px}.metric{padding:16px;border-radius:12px;background:light-dark(white,#20293a);border:1px solid light-dark(#e0e5ed,#354358);flex:1}.metric b{font-size:26px;display:block}.metrics{display:flex;gap:12px;margin:22px 0;flex-wrap:wrap}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:13px}.cards article,.filterbox,.events li{padding:20px;border:1px solid light-dark(#e0e5ed,#354358);border-radius:14px;background:light-dark(white,#20293a)}.cards article{min-width:0;overflow-wrap:anywhere}.top{display:flex;justify-content:space-between;gap:10px;font-size:12px;color:light-dark(#66748a,#afbcd0)}.top strong{border-radius:12px;padding:3px 10px;text-transform:capitalize;background:#e5ebf1;color:#3a4657}.top strong.healthy{background:#def8e7;color:#116437}.top strong.stale,.top strong.error{background:#ffe5dd;color:#923324}.cards dl{display:flex;gap:20px;align-items:baseline}.cards dd{font-weight:650;margin:0 15px 0 0}.cards a,a{color:light-dark(#1458a8,#9fc7ff)}.filterbox{margin:22px 0;padding:14px 20px}.filters{display:flex;flex-wrap:wrap;gap:16px}.filters label{cursor:pointer}.events{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:10px}.events li{display:flex;gap:15px;padding:12px}.events time{font-size:13px;white-space:nowrap;font-weight:700}.events small{display:block;font-size:12px;margin-top:4px}footer{margin:30px 0 50px;font-size:13px;color:light-dark(#66748a,#afbcd0)}[hidden]{display:none!important}
</style></head><body><main><p id="connectivity" role="status" hidden style="padding:12px;border-radius:9px;background:#b45309;color:white;font-weight:650">Offline — showing the last saved dashboard. Calendar health and dates may be outdated.</p><p class="muted">PUBLIC CALENDAR HEALTH MONITOR</p><h1>__TITLE__</h1><p class="muted">Read-only · Checked __CHECKED__ · America/Phoenix calendar view</p><div class="metrics"><div class="metric"><b>__HEALTH__</b>Healthy feeds</div><div class="metric"><b>__COUNT__</b>Total events</div><div class="metric"><b>__UPCOMING__</b>Upcoming __DAYS__ days</div></div><section class="cards">__CARDS__</section><section class="filterbox"><strong>Show selected calendars in this dashboard</strong><div class="filters">__FILTERS__</div><p class="muted">These filters affect only this website, not Apple Calendar or your ICS subscriptions.</p></section><h2>Upcoming public events</h2><ol class="events">__EVENTS__</ol><footer>Personal dates and addresses are intentionally excluded. A healthy feed means its public ICS is readable, structured and recently generated; it does not independently verify every source event date.<p><a href="./status.json">Machine-readable health report</a> · <a href="https://github.com/vihari23/Calendar-Hub">Manage on GitHub</a></p></footer></main>
<script>
const widgets=[...document.querySelectorAll('[data-choice]')];const key="vihari-hub-filters-v1";let saved;try{saved=JSON.parse(localStorage.getItem(key)||"null")}catch(e){saved=null}if(Array.isArray(saved))widgets.forEach(x=>x.checked=saved.includes(x.dataset.choice));function apply(){const current=new Set(widgets.filter(x=>x.checked).map(x=>x.dataset.choice));document.querySelectorAll('[data-feed]').forEach(x=>x.hidden=!current.has(x.dataset.feed));try{localStorage.setItem(key,JSON.stringify([...current]))}catch(e){}}widgets.forEach(x=>x.addEventListener("change",apply));apply();
const offlineBanner=document.getElementById("connectivity");function displayConnectivity(){offlineBanner.hidden=navigator.onLine}window.addEventListener("online",displayConnectivity);window.addEventListener("offline",displayConnectivity);displayConnectivity();
if("serviceWorker" in navigator){window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js",{scope:"./"}).catch(()=>{}))}
</script></body></html>"""
    values={"__TITLE__":safe(cfg["hub_name"]),"__CHECKED__":safe(status["checked_at_utc"]), "__HEALTH__":f"{good}/{len(readings)}",
            "__COUNT__":str(sum(f["events"] for f in readings)),"__UPCOMING__":str(len(agenda)),"__DAYS__":str(cfg["look_ahead_days"]),
            "__CARDS__":"".join(cards),"__FILTERS__":"".join(filters),"__EVENTS__":"".join(rows) or "<li>No upcoming events in this period.</li>"}
    for k,v in values.items():
        page=page.replace(k,v)
    return page

def build(config,output,now=None,getter=download):
    cfg=load_config(config)
    now=now or datetime.now(UTC)
    report={"schema_version":1,"checked_at_utc":now.isoformat(),
            "feeds":[check_feed(f,now,getter) for f in cfg["feeds"]]}
    report["healthy"]=all(f["status"] in ("healthy","disabled") for f in report["feeds"])
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    (output/"status.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    (output/"index.html").write_text(dashboard(cfg,report),encoding="utf8")
    # Keep PWA assets in one tracked directory so Pages and local builds match.
    assets=Path(__file__).resolve().parents[1]/"static"
    for name in ("manifest.webmanifest","sw.js","icon.svg","icon-192.png","icon-512.png","apple-touch-icon.png"):
        source=assets/name
        if not source.is_file():
            raise FileNotFoundError(f"Missing required PWA asset: {source}")
        shutil.copyfile(source,output/name)
    for f in report["feeds"]:
        print(f'{f["name"]}: {f["status"]} ({f["events"]} events) - {f["detail"]}')
    return report

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,default=Path("config/feeds.json"))
    parser.add_argument("--out",type=Path,default=Path("dist"))
    args=parser.parse_args()
    build(args.config,args.out)
