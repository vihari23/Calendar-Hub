import {HStack,Link,Script,Spacer,Text,VStack,Widget} from "scripting";
import {HUB_URL,WIDGET_URL,addDays,chosen,mergeEvents,parseICS,phoenixToday,rowLimit,selection,type Event} from "./core";
import {loadCache,loadSettings,saveCache} from "./settings";
const settings=loadSettings();
const view=chosen(settings,Widget.parameter);
const now=new Date(),today=phoenixToday(now);
const cache=loadCache();let publicData=cache.public,custom=cache.custom||{};
try{
 const res=await fetch(WIDGET_URL,{timeout:12});
 if(!res.ok)throw Error("Hub HTTP "+res.status);
 const data=await res.json();
 if(data.schema_version!==1||!Array.isArray(data.feeds))throw Error("Hub format changed");
 publicData=data;cache.public=data;cache.at=Date.now();
}catch(err){console.warn("Hub data fallback:",String(err));}
for(const f of selection(settings,view).filter(f=>f.kind==="ics")){
 try {
  if(!f.url)continue;
  const res=await fetch(f.url,{timeout:13});
  if(!res.ok)throw Error("ICS HTTP "+res.status);
  const text=await res.text();
  const parsed=parseICS(text,today,addDays(today,90));
  custom[f.id]={ok:parsed.unsupported===0,events:parsed.events.map(e=>({...e,name:e.title})),unsupported:parsed.unsupported};
  if(parsed.unsupported)console.warn("Unsupported recurrence rules in "+f.name);
 }catch(err){console.warn(f.name+" fallback: "+String(err));if(custom[f.id])custom[f.id].ok=false;}
}
cache.custom=custom;
try{saveCache(cache)}catch(err){console.warn("Cache unavailable:",String(err))}
const data=mergeEvents(settings,view,publicData,custom,today);
if(!publicData||Date.now()-Date.parse(publicData.checked_at_utc||"")>48*3600000)data.offline=true;
const family=Widget.family;
const height=Widget.displaySize?.height||628;
const limit=rowLimit(family,height);
const visible=data.events.slice(0,limit);
const months=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function Row({item}:{item:Event}){
 const month=months[Number(item.date.slice(5,7))-1]||"—";
 return <HStack spacing={10}>
  <VStack alignment="leading" spacing={0} frame={{width:37}}>
   <Text font={10} fontWeight="bold" foregroundStyle="#ACCBE1">{month.toUpperCase()}</Text>
   <Text font={19} fontWeight="bold" foregroundStyle="white">{String(Number(item.date.slice(8,10)))}</Text>
  </VStack>
  <VStack alignment="leading" spacing={2}>
   <Text font={11} fontWeight="semibold" lineLimit={1} foregroundStyle="white">{item.title}</Text>
   <Text font={9} fontWeight="semibold" lineLimit={1} foregroundStyle={item.color}>●  {item.calendar}</Text>
  </VStack>
  <Spacer />
 </HStack>
}
const isPortrait=family==="systemExtraLargePortrait";
const title=isPortrait?"CALENDAR HUB · FULL PAGE":family==="systemSmall"?"CALENDAR HUB":"CALENDAR HUB · AGENDA";
Widget.present(
 <VStack alignment="leading" spacing={isPortrait?10:6} padding={isPortrait?19:14}
  widgetBackground="#0A1C3A">
  <HStack>
   <Text font={isPortrait?13:11} fontWeight="bold" foregroundStyle="#FBD28B">✦ {title}</Text>
   <Spacer />
   <Text font={10} foregroundStyle={data.offline?"#FFBBA9":"#99E9C0"}>{data.healthy}/{data.total} OK</Text>
  </HStack>
  <Text font={isPortrait?24:17} fontWeight="bold" lineLimit={1} foregroundStyle="white">{view.name}</Text>
  {data.offline?<Text font={10} foregroundStyle="#FFD09E">Some sources could not be verified. Dates may be stale.</Text>:null}
  {visible.length?visible.map((item,i)=><Row key={item.feed+"-"+item.date+"-"+i} item={item}/>)
   :<Text font="caption" foregroundStyle="#C0D6E8">No upcoming events in these calendars.</Text>}
  <Spacer />
  <Link url={HUB_URL}><Text font={10} foregroundStyle="#B8DBF7">Open scrollable Calendar Hub ↗</Text></Link>
 </VStack>,
 {policy:"after",date:new Date(Date.now()+60*60*1000)}
);
Script.exit();
