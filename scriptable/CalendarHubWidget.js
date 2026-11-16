// Calendar Hub Widget — Scriptable for iOS
// Manage feeds, colors and independent widget views by running this script inside Scriptable.
// Data and custom ICS URLs are stored ONLY in the Scriptable app's local library directory.
// Tap a Home Screen widget to open a full scrollable on-device agenda.
// Help: https://vihari23.github.io/Calendar-Hub/widget-setup.html
const HUB="https://vihari23.github.io/Calendar-Hub/";
const HUB_DATA=HUB+"widget.json";
const FM=FileManager.local();
const SETTINGS=FM.joinPath(FM.libraryDirectory(),"vihari-hub-widget-settings-v1.json");
const CACHE=FM.joinPath(FM.libraryDirectory(),"vihari-hub-widget-cache-v1.json");
const PAL=[
 ["Gold","#F8C76A"],["Purple","#C5A5FF"],["Teal","#73E0C1"],
 ["Sky blue","#8FD5FF"],["Coral","#FF9C82"],["Pink","#FFABD0"],
 ["Lime","#C8E999"],["White","#F2F5FC"],["Orange","#FFA84D"]
];
const DEFAULT_FEEDS=[
 {id:"panchangam",name:"Phoenix Panchangam",kind:"hub",color:"#F8C76A"},
 {id:"india_ott",name:"India OTT Releases",kind:"hub",color:"#C5A5FF"},
 {id:"bulk_trash",name:"Arizona Bulk Trash",kind:"hub",color:"#73E0C1"},
 {id:"arizona-telugu",name:"AZ Telugu Events",kind:"hub",color:"#F8C76A"},
 {id:"phoenix-temples",name:"Phoenix Temples",kind:"hub",color:"#C5A5FF"},
 {id:"workday-releases",name:"Workday Releases",kind:"hub",color:"#8FD5FF"},
 {id:"phoenix-road-closures",name:"Phoenix Road Closures",kind:"hub",color:"#FF9C82"}
];
const INITIAL_VIEWS=[
 {id:"all",name:"All Subscribed Calendars",feeds:DEFAULT_FEEDS.map(f=>f.id),dailyPanchangam:false},
 {id:"culture",name:"Panchangam",feeds:["panchangam"],dailyPanchangam:true},
 {id:"entertainment",name:"India OTT",feeds:["india_ott"]},
 {id:"home",name:"Home & Trash",feeds:["bulk_trash"]},
 {id:"workday",name:"Workday Releases",feeds:["workday-releases"]}
];
const MONTH=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function readJSON(path,fallback){
 try {return FM.fileExists(path)?JSON.parse(FM.readString(path)):fallback;}catch(e){return fallback;}
}
function defaults(){
 return {version:1,feeds:DEFAULT_FEEDS.map(f=>Object.assign({},f)),
  views:INITIAL_VIEWS.map(v=>({id:v.id,name:v.name,feeds:v.feeds.slice(),dailyPanchangam:!!v.dailyPanchangam}))};
}
function saveSettings(s){FM.writeString(SETTINGS,JSON.stringify(s,null,2));}
function loadSettings(){
 const s=readJSON(SETTINGS,null);
 if(!s||s.version!==1||!Array.isArray(s.feeds)||!Array.isArray(s.views)){
   const fresh=defaults();saveSettings(fresh);return fresh;
 }
 // Add newly available Hub calendars without overwriting the user's custom
 // feed colors, edited views, and selections. One-time migration only.
 if(!s.workdayHubMigrationV1){
   const original=["panchangam","india_ott","bulk_trash"];
   const all=s.views.find(v=>v.id==="all");
   const pristineAll=!!(all&&all.feeds.length===3&&original.every(id=>all.feeds.includes(id)));
   for(const entry of DEFAULT_FEEDS){
     if(!s.feeds.some(f=>f.id===entry.id)){
       s.feeds.push(Object.assign({},entry));
       if(pristineAll)all.feeds.push(entry.id);
     }
   }
   if(!s.views.some(v=>v.id==="workday"))
     s.views.push({id:"workday",name:"Workday Releases",feeds:["workday-releases"],dailyPanchangam:false});
   s.workdayHubMigrationV1=true;
   saveSettings(s);
 }
 return s;
}
function cleanHex(value){
 const s=String(value||"").trim().toUpperCase();
 if(/^#[0-9A-F]{6}$/.test(s))return s;
 if(/^[0-9A-F]{6}$/.test(s))return "#"+s;
 return null;
}
function safeURL(text){
 try{
  const value=String(text).trim().replace(/^webcal:\/\//i,"https://");
  const m=/^https:\/\/([^\/?#]+)(?:[\/?#]|$)/i.exec(value);
  if(!m||m[1].includes("@"))return null;
  const host=m[1].split(":")[0].toLowerCase();
  if(host==="localhost"||host.endsWith(".local")||/^(127\.|10\.|192\.168\.|169\.254\.)/.test(host))return null;
  return value;
 }catch(e){return null;}
}
function slug(s){return String(s).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,26)||"calendar";}
function uniqueId(s,base){
 let id=slug(base),n=2;
 while(s.feeds.some(f=>f.id===id)||s.views.some(v=>v.id===id)){id=slug(base)+"-"+n++;}return id;
}
function dayFromICS(str){
 const m=String(str||"").match(/^(\d{4})(\d\d)(\d\d)(?:T(\d\d)(\d\d)(\d\d)?(Z)?)?$/);
 if(!m)return null;
 const y=+m[1],mo=+m[2],d=+m[3],hr=+(m[4]||0),min=+(m[5]||0),sec=+(m[6]||0);
 const utc=new Date(Date.UTC(y,mo-1,d,hr,min,sec));
 if(utc.getUTCFullYear()!==y||utc.getUTCMonth()!==mo-1||utc.getUTCDate()!==d)return null;
 // UTC instants are converted to Phoenix civil date; other times keep the calendar's declared date.
 if(m[7])return new Date(utc.getTime()-7*3600000).toISOString().slice(0,10);
 return String(m[1])+"-"+m[2]+"-"+m[3];
}
function getDay(day){return new Date(day+"T00:00:00Z");}
function dayISO(date){return date.toISOString().slice(0,10);}
function delta(a,b){return Math.round((getDay(a)-getDay(b))/86400000);}
function addDays(iso,n){return dayISO(new Date(getDay(iso).getTime()+n*86400000));}
function todayPhoenix(){return dayISO(new Date(Date.now()-7*3600000));}
function unesc(s){return String(s||"").replace(/\\[nN]/g," ").replace(/\\([,;\\])/g,"$1").trim();}
function splitProperty(line){
 const p=line.indexOf(":");
 if(p<0)return null;
 return {key:line.slice(0,p).split(";")[0].toUpperCase(),value:line.slice(p+1)};
}
function rruleAllowed(rule,origin,candidate){
 const seg={};for(const part of String(rule||"").split(";")){const p=part.indexOf("=");if(p>0)seg[part.slice(0,p).toUpperCase()]=part.slice(p+1).toUpperCase();}
 const freq=seg.FREQ,iv=Math.max(1,Math.min(100,+seg.INTERVAL||1));
 if(!["DAILY","WEEKLY","MONTHLY","YEARLY"].includes(freq)||candidate<origin)return false;
 const date=getDay(candidate),start=getDay(origin);
 const months=(date.getUTCFullYear()-start.getUTCFullYear())*12+date.getUTCMonth()-start.getUTCMonth();
 const days=delta(candidate,origin);
 if(seg.UNTIL){const end=dayFromICS(seg.UNTIL);if(end&&candidate>end)return false;}
 let eligible=false;
 if(freq==="DAILY")eligible=days%iv===0;
 if(freq==="WEEKLY"){
  // WKST=MO is the common iCalendar default.
  const base=addDays(origin,-((start.getUTCDay()+6)%7));
  const cbase=addDays(candidate,-((date.getUTCDay()+6)%7));
  eligible=(delta(cbase,base)/7)%iv===0;
 }
 if(freq==="MONTHLY")eligible=months%iv===0;
 if(freq==="YEARLY")eligible=(date.getUTCFullYear()-start.getUTCFullYear())%iv===0;
 if(!eligible)return false;
 if(seg.BYMONTH&&!seg.BYMONTH.split(",").some(v=>+v===date.getUTCMonth()+1))return false;
 if(seg.BYMONTHDAY&&!seg.BYMONTHDAY.split(",").some(v=>+v===date.getUTCDate()))return false;
 const daysMap=["SU","MO","TU","WE","TH","FR","SA"];
 if(seg.BYDAY&&!seg.BYDAY.split(",").some(v=>v===daysMap[date.getUTCDay()]))return false;
 if(freq==="WEEKLY"&&!seg.BYDAY&&date.getUTCDay()!==start.getUTCDay())return false;
 if(freq==="MONTHLY"&&!seg.BYDAY&&!seg.BYMONTHDAY&&date.getUTCDate()!==start.getUTCDate())return false;
 if(freq==="YEARLY"){
  if(!seg.BYMONTH&&date.getUTCMonth()!==start.getUTCMonth())return false;
  if(!seg.BYMONTHDAY&&!seg.BYDAY&&date.getUTCDate()!==start.getUTCDate())return false;
 }
 // COUNT with combinations requiring enumeration is intentionally not guessed.
 if(seg.COUNT){
  const count=+seg.COUNT;
  if(!count||count<1)return false;
  if(freq==="DAILY"&&!seg.BYDAY&&!seg.BYMONTH&&!seg.BYMONTHDAY&&Math.floor(days/iv)+1>count)return false;
  if(freq==="MONTHLY"&&!seg.BYDAY&&!seg.BYMONTH&&!seg.BYMONTHDAY&&Math.floor(months/iv)+1>count)return false;
  if(freq==="YEARLY"&&!seg.BYDAY&&!seg.BYMONTH&&!seg.BYMONTHDAY&&Math.floor((date.getUTCFullYear()-start.getUTCFullYear())/iv)+1>count)return false;
 }
 return true;
}
function parseICS(source,start,end){
 const text=String(source||"");
 if(text.length>3_000_000)throw Error("ICS file exceeds 3 MB");
 if(!/BEGIN:VCALENDAR/i.test(text)||!/END:VCALENDAR/i.test(text))throw Error("Not a valid iCalendar feed");
 const lines=text.replace(/\r\n/g,"\n").replace(/\r/g,"\n").split("\n");
 const unfolded=[];for(const line of lines){if(/^[ \t]/.test(line)&&unfolded.length)unfolded[unfolded.length-1]+=line.slice(1);else unfolded.push(line);}
 let current=null;const raw=[];let count=0;
 for(const line of unfolded){
  if(line==="BEGIN:VEVENT"){if(++count>7000)throw Error("ICS has too many events");current={ex:[],rd:[]};}
  else if(line==="END:VEVENT"){if(current)raw.push(current);current=null;}
  else if(current){
   const pair=splitProperty(line);if(!pair)continue;
   const k=pair.key,v=pair.value;
   if(k==="DTSTART")current.start=dayFromICS(v);
   else if(k==="SUMMARY")current.title=unesc(v);
   else if(k==="UID")current.uid=v;
   else if(k==="STATUS")current.cancelled=v==="CANCELLED";
   else if(k==="RRULE")current.rule=v;
   else if(k==="RECURRENCE-ID")current.recurrence=dayFromICS(v);
   else if(k==="EXDATE")current.ex.push(...v.split(",").map(dayFromICS).filter(Boolean));
   else if(k==="RDATE")current.rd.push(...v.split(",").map(dayFromICS).filter(Boolean));
  }
 }
 const exceptions=new Map(),items=[],seen=new Set();
 const key=(u,d)=>String(u||"")+"|"+d;
 for(const ev of raw)if(ev.recurrence&&ev.uid)exceptions.set(key(ev.uid,ev.recurrence),true);
 function insert(ev,iso){
  if(!iso||iso<start||iso>end||ev.cancelled||!ev.title)return;
  const k=key(ev.uid,iso);if(seen.has(k))return;seen.add(k);
  items.push({date:iso,name:ev.title});
 }
 for(const ev of raw){
  if(!ev.start||!ev.title||ev.cancelled)continue;
  if(ev.recurrence){insert(ev,ev.start);continue;}
  const omit=new Set(ev.ex);
  const add=(iso)=>{if(!omit.has(iso)&&!exceptions.has(key(ev.uid,iso)))insert(ev,iso);};
  add(ev.start);
  for(const rd of ev.rd)add(rd);
  if(ev.rule){
   const from=ev.start>start?ev.start:start;
   for(let date=from;date<=end;date=addDays(date,1)){
    if(date!==ev.start&&rruleAllowed(ev.rule,ev.start,date))add(date);
   }
  }
 }
 items.sort((a,b)=>a.date.localeCompare(b.date)||a.name.localeCompare(b.name));
 return items.slice(0,600);
}
function escapeHTML(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
async function alert(title,message){const a=new Alert();a.title=title;a.message=message;a.addAction("OK");await a.presentAlert();}
async function choose(title,values){
 const a=new Alert();a.title=title;for(const v of values)a.addAction(v);a.addCancelAction("Back");
 return await a.presentSheet();
}
async function fields(title,labels,defaults){
 const a=new Alert();a.title=title;labels.forEach((label,i)=>a.addTextField(label,String(defaults[i]||"")));
 a.addAction("Save");a.addCancelAction("Cancel");
 if(await a.presentAlert()<0)return null;
 return labels.map((_,i)=>a.textFieldValue(i).trim());
}
async function pickColor(current){
 const options=PAL.map(([name,hex])=>name+"  "+hex).concat(["Custom hex…"]);
 const idx=await choose("Calendar color",options);
 if(idx<0)return null;
 if(idx<PAL.length)return PAL[idx][1];
 const entry=await fields("Custom color",["Hex color (#RRGGBB)"],[current||"#8FD5FF"]);
 if(!entry)return null;
 const color=cleanHex(entry[0]);
 if(!color)await alert("Invalid color","Use six hex digits, for example #82C3FA");
 return color;
}
async function addFeed(s){
 if(s.feeds.length>=20){await alert("Limit reached","Maximum 20 calendars to keep widgets responsive.");return;}
 const x=await fields("Add an ICS calendar",["Calendar name","HTTPS ICS subscription URL"],["","https://"]);
 if(!x)return;
 const name=x[0],url=safeURL(x[1]);
 if(!name||!url){await alert("Invalid feed","Enter a calendar name and a valid HTTPS URL.");return;}
 const color=await pickColor("#8FD5FF");
 if(!color)return;
 const id=uniqueId(s,name);
 s.feeds.push({id,name,kind:"ics",url,color});
 s.views.find(v=>v.id==="all")?.feeds.push(id);
 saveSettings(s);
 await alert("Calendar saved","This feed stays on your iPhone. It is included in the All Calendars widget. Create other widget views to include it selectively.");
}
async function editFeed(s,index){
 const f=s.feeds[index];if(!f)return;
 const choice=await choose(f.name,[ "Rename",f.kind==="ics"?"Change ICS URL":"Source: public Calendar Hub","Change calendar color","Test calendar feed","Remove calendar"]);
 if(choice<0)return;
 if(choice===0){const v=await fields("Rename calendar",["Calendar name"],[f.name]);if(v&&v[0])f.name=v[0];}
 if(choice===1&&f.kind==="ics"){const v=await fields("Change ICS URL",["HTTPS ICS URL"],[f.url]);if(v){const url=safeURL(v[0]);if(url)f.url=url;else await alert("Invalid URL","Use a valid HTTPS URL.");}}
 if(choice===1&&f.kind!=="ics")await alert("Built-in calendar","This feed is monitored by Calendar Hub. Its ICS source can be changed in the GitHub Hub configuration.");
 if(choice===2){const c=await pickColor(f.color);if(c)f.color=c;}
 if(choice===3){
  if(f.kind==="ics"){
   const result=await readICS(f,{custom:{}},true);
   await alert(result.healthy?"Feed works":"Feed check failed",result.healthy?(result.events.length+" upcoming events found."):(result.error||"Unable to read this ICS URL."));
  }else await alert("Hub feed","The source is monitored by the public Calendar Hub.");
 }
 if(choice===4){
  const i=await choose("Remove "+f.name+"?",["Remove this calendar"]);
  if(i===0){s.feeds.splice(index,1);for(const v of s.views)v.feeds=v.feeds.filter(x=>x!==f.id);}
 }
 saveSettings(s);
}
async function manageFeeds(s){
 while(true){
  const options=["＋ Add ICS calendar"].concat(s.feeds.map(f=>"● "+f.name+"  "+f.color));
  const i=await choose("Calendars and colors",options);
  if(i<0)return;if(i===0)await addFeed(s);else await editFeed(s,i-1);
 }
}
async function editView(s,index){
 let view=s.views[index];
 if(!view)return;
 while(true){
  const options=["Rename this widget view","Delete this widget view",view.dailyPanchangam?"✓ Show daily Panchangam entries":"○ Show daily Panchangam entries"].concat(
   s.feeds.map(f=>(view.feeds.includes(f.id)?"✓  ":"○  ")+f.name));
  const i=await choose("View: "+view.name+" ("+view.id+")",options);
  if(i<0)return;
  if(i===0){const a=await fields("Rename view",["View name"],[view.name]);if(a&&a[0])view.name=a[0];}
  else if(i===1){
   if(view.id==="all"){await alert("Default view","The all view cannot be deleted. You may still select its calendars.");}
   else if(await choose("Delete view "+view.id+"?",["Delete view"])===0){s.views.splice(index,1);saveSettings(s);return;}
  }else if(i===2){view.dailyPanchangam=!view.dailyPanchangam;
  }else{
   const id=s.feeds[i-3].id;
   view.feeds=view.feeds.includes(id)?view.feeds.filter(f=>f!==id):view.feeds.concat(id);
  }
  saveSettings(s);
 }
}
async function manageViews(s){
 while(true){
  const idx=await choose("Widget views",["＋ Create a widget view"].concat(s.views.map(v=>v.name+" · "+v.id)));
  if(idx<0)return;
  if(idx===0){
   const x=await fields("New widget view",["View name","Short widget parameter"],["My calendars","my-view"]);
   if(!x)return;
   const id=slug(x[1]);
   if(!x[0]||s.views.some(v=>v.id===id)){await alert("Invalid view","Choose a name and unique widget parameter.");continue;}
   s.views.push({id,name:x[0],feeds:[],dailyPanchangam:false});saveSettings(s);
   await editView(s,s.views.length-1);
  }else await editView(s,idx-1);
 }
}
function viewFor(s,parameter){
 const id=String(parameter||"all").trim().toLowerCase();
 return s.views.find(v=>v.id===id)||s.views[0]||{id:"all",name:"All calendars",feeds:s.feeds.map(f=>f.id)};
}
async function readPublic(cache,force){
 const old=cache.public;
 if(!force&&old&&Date.now()-old.fetched<45*60000)return old;
 try{
  const req=new Request(HUB_DATA);req.timeoutInterval=14;
  const json=await req.loadJSON();
  if(json.schema_version!==1||!Array.isArray(json.feeds))throw Error("Hub response invalid");
  const item={fetched:Date.now(),data:json,healthy:true};cache.public=item;return item;
 }catch(e){return old?Object.assign({},old,{healthy:false}):{fetched:0,data:null,healthy:false};}
}
async function readICS(feed,cache,force){
 const stored=cache.custom[feed.id];
 if(!force&&stored&&stored.url===feed.url&&Date.now()-stored.fetched<90*60000)return stored;
 try{
  const req=new Request(feed.url);req.timeoutInterval=15;
  const source=await req.loadString();
  const start=todayPhoenix(),end=addDays(start,105);
  const events=parseICS(source,start,end);
  const item={url:feed.url,fetched:Date.now(),events,healthy:true};
  cache.custom[feed.id]=item;return item;
 }catch(e){
  return stored&&stored.url===feed.url?Object.assign({},stored,{healthy:false}):{fetched:0,events:[],healthy:false,error:String(e).slice(0,120)};
 }
}
async function loadEvents(s,v,force){
 let cache=readJSON(CACHE,{public:null,custom:{}});
 if(!cache||!cache.custom)cache={public:null,custom:{}};
 const feeds=s.feeds.filter(f=>v.feeds.includes(f.id));
 const needPublic=feeds.some(f=>f.kind==="hub");
 const pub=needPublic?await readPublic(cache,force):null;
 let events=[],statuses=[];
 for(const f of feeds){
  let info=null;
  if(f.kind==="hub"){
   const source=pub&&pub.data?pub.data.feeds.find(row=>row.id===f.id):null;
   const outdated=pub?Date.now()-pub.fetched>48*3600000:true;
   statuses.push({id:f.id,healthy:!!(pub&&pub.healthy&&!outdated&&source&&source.status==="healthy")});
   if(source&&Array.isArray(source.upcoming))info=source.upcoming;
  }else{
   const item=await readICS(f,cache,force);
   const outdated=Date.now()-item.fetched>48*3600000;
   statuses.push({id:f.id,healthy:!!(item.healthy&&!outdated)});
   info=item.events;
  }
  if(info)for(const e of info){
   if(f.id==="panchangam"&&!v.dailyPanchangam&&!isNotablePanchangam(e&&e.name))continue;
   if(e&&typeof e.date==="string"&&e.date>=todayPhoenix()&&e.name)
    events.push({id:f.id,date:e.date,name:String(e.name),color:f.color,calendar:f.name});
  }
 }
 const seen=new Set();
 events=events.filter(e=>{const key=e.id+"|"+e.date+"|"+e.name;if(seen.has(key))return false;seen.add(key);return true;});
 events.sort((a,b)=>a.date.localeCompare(b.date)||a.calendar.localeCompare(b.calendar)||a.name.localeCompare(b.name));
 FM.writeString(CACHE,JSON.stringify(cache));
 return {events,statuses,feeds};
}
function isNotablePanchangam(text){
 return /🪔|⚡|🌕|🌑|ekadashi|amavasya|pournami|purnima|festival|sankranti|navaratri|diwali|deepavali|ugadi|dasara|shashti|chavithi|ashtami|shivaratri/i.test(String(text||""));
}
function prettyTitle(s){
 return String(s||"").replace(/^OTT:\s*/i,"").replace(/\s*[—–]\s*/g," — ").trim();
}
function styleText(t,size,hex,bold){
 t.font=bold?Font.boldSystemFont(size):Font.systemFont(size);
 t.textColor=new Color(hex);t.lineLimit=1;t.minimumScaleFactor=0.72;
}
function buildWidget(view,data,family){
 const w=new ListWidget();
 const gradient=new LinearGradient();
 gradient.colors=[new Color("#081631"),new Color("#193765"),new Color("#075C64")];
 gradient.locations=[0,0.55,1];
 w.backgroundGradient=gradient;w.setPadding(13,13,11,13);
 const runUrl=URLScheme.forRunningScript();
 w.url=runUrl+(runUrl.includes("?")?"&":"?")+"view="+encodeURIComponent(view.id);
 w.refreshAfterDate=new Date(Date.now()+60*60000);
 const head=w.addStack();head.centerAlignContent();
 const label=head.addText("✦  "+view.name.toUpperCase());styleText(label,10,"#FFE2A1",true);
 head.addSpacer();
 const healthy=data.statuses.filter(x=>x.healthy).length;
 const badge=head.addText(healthy+"/"+data.statuses.length+" LIVE");
 styleText(badge,9,healthy===data.statuses.length?"#8CEDC9":"#FFB9A1",true);
 w.addSpacer(7);
 const title=w.addText(family==="small"?"NEXT UP":"UPCOMING EVENTS");
 styleText(title,family==="small"?13:15,"#FFFFFF",true);
 w.addSpacer(9);
 const max=family==="large"?6:family==="medium"?3:1;
 const upcoming=data.events.slice(0,max);
 if(!upcoming.length){const msg=w.addText("No future events in selected calendars");styleText(msg,11,"#CBDCEB",false);}
 for(const [i,e] of upcoming.entries()){
  const row=w.addStack();row.centerAlignContent();row.spacing=9;
  const day=row.addStack();day.layoutVertically();day.size=new Size(33,36);
  let mm=MONTH[+e.date.slice(5,7)-1]||"---";
  let mo=day.addText(mm.toUpperCase());styleText(mo,8,"#BDCAE5",true);
  let dd=day.addText(String(+e.date.slice(8,10)));styleText(dd,19,"#FFFFFF",true);
  const detail=row.addStack();detail.layoutVertically();detail.spacing=3;
  const event=detail.addText(prettyTitle(e.name));styleText(event,11,"#FFFFFF",true);
  const sub=detail.addText("●  "+e.calendar);styleText(sub,9,e.color||"#A7D8FF",true);
  if(i<upcoming.length-1)w.addSpacer(family==="large"?8:4);
 }
 if(family!=="small"){w.addSpacer();const foot=w.addText("Tap to view all events and scroll ↗");styleText(foot,9,"#BBD3E6",false);}
 return w;
}
async function showAgenda(s,view){
 const result=await loadEvents(s,view,true);
 const rows=result.events.slice(0,400).map(e=>
  '<div class="item"><div class="date">'+escapeHTML(e.date)+'</div><div class="body"><div class="title">'+escapeHTML(e.name)+'</div><div class="name"><span class="dot" style="background:'+escapeHTML(e.color)+'"></span>'+escapeHTML(e.calendar)+'</div></div></div>').join("");
 const html='<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{background:#0b1730;color:#f3f7ff;font:15px -apple-system,system-ui;margin:0;padding:21px}.top{padding-bottom:16px;border-bottom:1px solid #33405d}.caption{color:#f7ce76;letter-spacing:.08em;font-size:11px;font-weight:800}h1{font-size:24px;margin:8px 0}p{color:#becce4}.item{padding:12px 0;border-bottom:1px solid #273651;display:flex;gap:15px}.date{color:#f7ce76;flex:0 0 91px;font-size:12px;font-weight:700}.body{min-width:0}.title{font-weight:600}.name{color:#afc2db;font-size:12px;margin-top:4px}.dot{display:inline-block;width:9px;height:9px;border-radius:9px;margin-right:6px}</style></head><body><div class="top"><div class="caption">VIHARI CALENDAR HUB</div><h1>'+escapeHTML(view.name)+'</h1><p>'+result.events.length+' upcoming events · '+result.statuses.filter(x=>x.healthy).length+'/'+result.statuses.length+' feeds healthy</p></div>'+(rows||'<p>No future events found.</p>')+'</body></html>';
 const web=new WebView();await web.loadHTML(html);await web.present(true);
}
async function showGuide(s){
 await alert("Using widget views",
  "Add or edit calendars and their colors by running this script in Scriptable.\n\nCreate a widget view and select the calendars for that view.\n\nOn iPhone Home Screen: add a Scriptable widget → Edit Widget → Script: this script → Parameter: a view ID, such as all, culture, entertainment or home.\n\nAdd multiple widgets with different Parameter values. Tap a widget to open its full scrollable event list.");
}
async function menu(s){
 while(true){
  const a=await choose("Vihari Calendar Widget",[
   "View full scrollable agenda","Preview large widget",
   "Manage calendars + colors","Manage widget views","Installation guide"]);
  if(a<0)return;
  if(a===0||a===1){
   const idx=await choose("Select view",s.views.map(v=>v.name+" ("+v.id+")"));
   if(idx<0)continue;const v=s.views[idx];
   if(a===0)await showAgenda(s,v);
   else{const data=await loadEvents(s,v,true);await buildWidget(v,data,"large").presentLarge();}
  }
  if(a===2)await manageFeeds(s);
  if(a===3)await manageViews(s);
  if(a===4)await showGuide(s);
 }
}
async function main(){
 const s=loadSettings();
 if(config.runsInWidget){
  const v=viewFor(s,args.widgetParameter);
  const data=await loadEvents(s,v,false);
  Script.setWidget(buildWidget(v,data,config.widgetFamily||"medium"));
 }else{
  const viewId=args.queryParameters&&args.queryParameters.view;
  if(viewId)await showAgenda(s,viewFor(s,viewId));
  else await menu(s);
 }
 Script.complete();
}
await main();
