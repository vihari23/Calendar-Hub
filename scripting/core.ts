/* Pure Calendar Hub logic. Scripting iOS 27+ widget; no private URLs published. */
export type Feed={id:string,name:string,color:string,kind:"hub"|"ics",url?:string};
export type View={id:string,name:string,feeds:string[],showDaily:boolean};
export type Settings={version:1,feeds:Feed[],views:View[]};
export type Event={date:string,title:string,feed:string,calendar:string,color:string};
export type Result={events:Event[],healthy:number,total:number,updated:string,offline:boolean};
export const HUB_URL="https://vihari23.github.io/Calendar-Hub/";
export const WIDGET_URL=HUB_URL+"widget.json";
export const SETTINGS_FILE="vihari-hub-xl-settings-v1.json";
export const CACHE_FILE="vihari-hub-xl-cache-v1.json";
export function defaults():Settings{return {version:1,feeds:[
 {id:"panchangam",name:"Phoenix Panchangam",color:"#F8BD72",kind:"hub"},
 {id:"india_ott",name:"India OTT",color:"#C6A5FF",kind:"hub"},
 {id:"bulk_trash",name:"Arizona Bulk Trash",color:"#70DFB7",kind:"hub"}],
 views:[{id:"all",name:"All Subscriptions",feeds:["panchangam","india_ott","bulk_trash"],showDaily:false},
 {id:"culture",name:"Panchangam",feeds:["panchangam"],showDaily:true},
 {id:"entertainment",name:"India OTT",feeds:["india_ott"],showDaily:false},
 {id:"home",name:"Home & Trash",feeds:["bulk_trash"],showDaily:false}]};}
export function safeColor(input:string):string|null {
 const s=String(input||"").trim().toUpperCase();
 return /^#[0-9A-F]{6}$/.test(s)?s:/^[0-9A-F]{6}$/.test(s)?"#"+s:null;
}
export function safeURL(input:string):string|null {
 let s=String(input||"").trim().replace(/^webcal:\/\//i,"https://");
 try {const u=new URL(s);
   if(u.protocol!=="https:"||u.username||u.password||u.port)return null;
   const host=u.hostname.toLowerCase();
   if(host==="localhost"||host.endsWith(".local")||host==="::1"||
      /^(\d{1,3}\.){3}\d{1,3}$/.test(host)||host.includes(":"))return null;
   return u.href;
 } catch {return null;}
}
export function validSettings(raw:unknown):Settings {
 if(!raw||typeof raw!=="object")return defaults();
 const s=raw as Partial<Settings>;
 if(s.version!==1||!Array.isArray(s.feeds)||!Array.isArray(s.views))return defaults();
 const feeds=s.feeds.filter(f=>!!f&&typeof f.id==="string"&&typeof f.name==="string"&&
  (f.kind==="hub"||f.kind==="ics")&&!!safeColor(f.color)&&
  (f.kind==="hub"||!!safeURL(f.url||""))).slice(0,15);
 if(!feeds.length)return defaults();
 const ids=new Set(feeds.map(f=>f.id));
 const views=s.views.filter(v=>!!v&&typeof v.id==="string"&&typeof v.name==="string"&&Array.isArray(v.feeds))
 .map(v=>({...v,feeds:v.feeds.filter(id=>ids.has(id)),showDaily:!!v.showDaily})).slice(0,15);
 return {version:1,feeds,views:views.length?views:defaults().views};
}
export function chosen(settings:Settings,parameter:string):View {
 let id=String(parameter||"all").trim();
 try{const v=JSON.parse(id);if(v&&typeof v.view==="string")id=v.view;}catch{}
 return settings.views.find(v=>v.id===id)||settings.views.find(v=>v.id==="all")||settings.views[0];
}
export function phoenixToday(now:Date=new Date()):string {
 return new Date(now.getTime()-7*3600000).toISOString().slice(0,10);
}
export function addDays(day:string,n:number):string {
 return new Date(Date.parse(day+"T12:00:00Z")+n*86400000).toISOString().slice(0,10);
}
export function icsDate(value:string):string|null {
 const m=/^(\d{4})(\d\d)(\d\d)(?:T(\d\d)(\d\d)(\d\d)?(Z)?)?$/.exec(value);
 if(!m)return null;
 const [_,y,mon,day,h="00",min="00",sec="00",z]=m;
 const d=new Date(Date.UTC(+y,+mon-1,+day,+h,+min,+sec));
 if(d.getUTCFullYear()!==+y||d.getUTCMonth()!==+mon-1||d.getUTCDate()!==+day)return null;
 return z?phoenixToday(d):y+"-"+mon+"-"+day;
}
export function isNotable(title:string):boolean {
 return /🪔|⚡|🌕|🌑|ekadashi|amavasya|pournami|purnima|festival|sankranti|navaratri|diwali|deepavali|ugadi|dasara|shashti|chavithi|ashtami|shivaratri/i.test(title);
}
function unescapeICS(s:string):string {
 return s.replace(/\\[nN]/g," ").replace(/\\([\\;,])/g,"$1").trim();
}
export function parseICS(text:string,start:string,end:string):{events:{date:string,title:string}[],unsupported:number} {
 if(text.length>3000000||!text.includes("BEGIN:VCALENDAR")||!text.includes("END:VCALENDAR"))throw Error("Invalid/oversized ICS");
 const lines=text.replace(/\r\n?/g,"\n").split("\n");
 const folded:string[]=[];
 for(const line of lines){if(/^[ \t]/.test(line)&&folded.length)folded[folded.length-1]+=line.slice(1);else folded.push(line);}
 const output:{date:string,title:string}[]=[],seen=new Set<string>();let unsupported=0;
 let entry:Record<string,string>|null=null;
 const add=(d:string,title:string)=>{
  if(d>=start&&d<=end){const key=d+"|"+title;if(!seen.has(key)){seen.add(key);output.push({date:d,title});}}
 };
 let count=0;
 for(const line of folded) {
  if(line==="BEGIN:VEVENT"){entry={};if(++count>6500)throw Error("Too many ICS events");continue;}
  if(line==="END:VEVENT"){
   if(entry&&entry.DTSTART&&entry.SUMMARY&&entry.STATUS!=="CANCELLED"){
    const title=unescapeICS(entry.SUMMARY),day=icsDate(entry.DTSTART);
    // Don't guess event dates for unknown time zones.
    const unknownZone=!!entry.TZID && entry.TZID!=="America/Phoenix";
    if(unknownZone){unsupported++;}
    else if(day) {
     add(day,title);
     // Expand only simple date-anchored yearly/monthly recurrences.
     // Complex exceptions/COUNT/BY* patterns must be handled in Apple Calendar.
     if(entry.RRULE){
      const r=entry.RRULE.toUpperCase(),freq=/FREQ=(YEARLY|MONTHLY)(?:;|$)/.exec(r)?.[1];
      const m=/(?:^|;)INTERVAL=(\d+)(?:;|$)/.exec(r),intv=m?Number(m[1]):1;
      const untilRaw=/(?:^|;)UNTIL=([^;]+)/.exec(r)?.[1];
      const until=untilRaw?icsDate(untilRaw):null;
      if(freq&&intv>0&&intv<=12&&!entry.COMPLEX&&!/BYDAY|BYSETPOS|COUNT|BYMONTHDAY|BYMONTH|WKST/.test(r)){
       for(let n=1;n<=120;n++){
        const base=new Date(day+"T12:00:00Z");
        if(freq==="YEARLY")base.setUTCFullYear(base.getUTCFullYear()+n*intv);
        else base.setUTCMonth(base.getUTCMonth()+n*intv);
        // Jan 31 + one month must not become an invented March date.
        if(base.getUTCDate()!==Number(day.slice(8,10)))continue;
        const next=base.toISOString().slice(0,10);
        if(next>end||(until&&next>until))break;
        if(next>day)add(next,title);
       }
      }else unsupported++;
     }
    }
   }
   entry=null;continue;
  }
  if(entry){const p=line.indexOf(":");if(p>0){
   const meta=line.slice(0,p),key=meta.split(";")[0].toUpperCase();
   if(["EXDATE","RDATE","RECURRENCE-ID"].includes(key))entry.COMPLEX="1";
   if(key==="DTSTART")entry.TZID=/TZID=([^;:]+)/.exec(meta)?.[1]||"";
   if(["DTSTART","SUMMARY","STATUS","RRULE"].includes(key))entry[key]=line.slice(p+1);
  }}
 }
 output.sort((a,b)=>a.date.localeCompare(b.date)||a.title.localeCompare(b.title));
 return {events:output.slice(0,400),unsupported};
}
export function selection(settings:Settings,view:View):Feed[] {
 return settings.feeds.filter(f=>view.feeds.includes(f.id));
}
export function mergeEvents(settings:Settings,view:View,publicData:any,custom:Record<string,any>,today:string):Result {
 const active=selection(settings,view),events:Event[]=[];let healthy=0,offline=false;
 for(const feed of active){
  let entries:any[]=[],ok=false;
  if(feed.kind==="hub"){
   const item=publicData?.feeds?.find((r:any)=>r.id===feed.id);
   entries=Array.isArray(item?.upcoming)?item.upcoming:[];
   ok=item?.status==="healthy"&&!!publicData?.checked_at_utc;
  }else {
   const item=custom[feed.id];
   entries=Array.isArray(item?.events)?item.events:[];
   ok=!!item?.ok;
  }
  if(ok)healthy++;else offline=true;
  for(const e of entries){
   if(e?.date>=today&&typeof e?.name==="string"||e?.date>=today&&typeof e?.title==="string"){
    const name=String(e.name??e.title);
    if(feed.id==="panchangam"&&!view.showDaily&&!isNotable(name))continue;
    events.push({date:e.date,title:name.replace(/^OTT:\s*/i,""),feed:feed.id,calendar:feed.name,color:safeColor(feed.color)||"#A8D4FA"});
   }
  }
 }
 events.sort((a,b)=>a.date.localeCompare(b.date)||a.calendar.localeCompare(b.calendar)||a.title.localeCompare(b.title));
 return {events,healthy,total:active.length,updated:publicData?.checked_at_utc||"",offline};
}
export function rowLimit(family:string,height:number):number {
 if(family==="systemExtraLargePortrait")return Math.min(14,Math.max(9,Math.floor((height-100)/43)));
 if(family==="systemLarge")return 6;
 if(family==="systemMedium")return 3;
 return 1;
}
