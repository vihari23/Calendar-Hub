import {Button,HStack,List,Navigation,NavigationStack,Script,Section,Text,TextField,Toggle,VStack,Widget,useState} from "scripting";
import {defaults,safeColor,safeURL,type Feed,type Settings,type View} from "./core";
import {loadSettings,saveSettings} from "./settings";
function Manage(){
 const [settings,setSettings]=useState<Settings>(loadSettings());
 const [selected,setSelected]=useState(settings.views[0]?.id||"all");
 const [name,setName]=useState("");
 const [url,setURL]=useState("");
 const [color,setColor]=useState("#8ED2FF");
 const [newView,setNewView]=useState("");
 const [notice,setNotice]=useState("");
 const [editing,setEditing]=useState("");
 function commit(next:Settings){
  saveSettings(next);setSettings({...next,feeds:[...next.feeds],views:[...next.views]});
 }
 function addCalendar(){
  const finalURL=safeURL(url),hex=safeColor(color);
  if(!name.trim()||!finalURL||!hex){setNotice("Provide a name, HTTPS ICS URL, and six-digit color.");return;}
  if(settings.feeds.length>=15){setNotice("Maximum 15 calendars.");return;}
  let id=name.toLowerCase().replace(/[^a-z0-9]+/g,"-").slice(0,25)||"calendar",n=2;
  while(settings.feeds.some(f=>f.id===id)){id=id.replace(/-\d+$/,"")+"-"+n++;}
  const feed:Feed={id,name:name.trim(),kind:"ics",url:finalURL,color:hex};
  const views=settings.views.map(v=>v.id==="all"?{...v,feeds:[...v.feeds,id]}:v);
  commit({...settings,feeds:[...settings.feeds,feed],views});
  setName("");setURL("");setNotice("Calendar added privately on this iPhone.");
 }
 function updateColor(id:string,hex:string){
  const value=safeColor(hex);if(!value){setNotice("Enter a valid six-digit hex color.");return;}
  commit({...settings,feeds:settings.feeds.map(f=>f.id===id?{...f,color:value}:f)});setNotice("Calendar color saved.");
 }
 function addView(){
  const label=newView.trim();if(!label){setNotice("Enter a view name.");return;}
  let id=label.toLowerCase().replace(/[^a-z0-9]+/g,"-").slice(0,30),n=2;
  while(settings.views.some(v=>v.id===id))id=label.toLowerCase().replace(/[^a-z0-9]+/g,"-").slice(0,23)+"-"+n++;
  const v:View={id,name:label,feeds:[],showDaily:false};
  commit({...settings,views:[...settings.views,v]});setSelected(id);setNewView("");
 }
 function toggle(id:string,enabled:boolean){
  commit({...settings,views:settings.views.map(v=>v.id!==selected?v:{...v,feeds:enabled?[...new Set([...v.feeds,id])]:v.feeds.filter(x=>x!==id)})});
 }
 const view=settings.views.find(v=>v.id===selected)||settings.views[0];
 return <NavigationStack>
 <List navigationTitle="Calendar Hub Widgets">
  <Section title="Widget view — select calendars">
   <Text font="caption" foregroundStyle="secondaryLabel">Each Home Screen widget uses its view ID in Edit Widget → Parameter.</Text>
   {settings.views.map(v=><Button key={v.id} title={(v.id===selected?"✓  ":"○  ")+v.name+" · "+v.id}
    action={()=>setSelected(v.id)} />)}
   <TextField title="New view name" value={newView} onChanged={setNewView} prompt="Family dates and OTT" />
   <Button title="Create widget view" action={addView}/>
   {view?<Toggle title="Show daily Panchangam entries" value={view.showDaily}
    onChanged={enabled=>commit({...settings,views:settings.views.map(v=>v.id===view.id?{...v,showDaily:enabled}:v)})}/>:null}
   {view?settings.feeds.map(f=><Toggle key={f.id} title={f.name} value={view.feeds.includes(f.id)}
    onChanged={enabled=>toggle(f.id,enabled)}/>):null}
  </Section>
  <Section title="Add your own ICS feed">
   <TextField title="Calendar name" value={name} onChanged={setName} prompt="Family calendar"/>
   <TextField title="HTTPS ICS URL" value={url} onChanged={setURL} prompt="https://example.com/events.ics"/>
   <TextField title="Calendar hex color" value={color} onChanged={setColor} prompt="#8ED2FF"/>
   <HStack spacing={5}>{["#F8BD72","#C6A5FF","#70DFB7","#FF9D97","#8EC9FF"].map(c=>
    <Button key={c} title="●" action={()=>setColor(c)} foregroundStyle={c}/>)}</HStack>
   <Button title="Add ICS calendar" action={addCalendar}/>
  </Section>
  <Section title="Current calendars & colors">
   {settings.feeds.map(f=><VStack key={f.id} alignment="leading" spacing={4}>
    <Text foregroundStyle={f.color} fontWeight="semibold">{f.name}  ● {f.color}</Text>
    <HStack>
     <Button title="Gold" action={()=>updateColor(f.id,"#F8BD72")}/>
     <Button title="Purple" action={()=>updateColor(f.id,"#C6A5FF")}/>
     <Button title="Teal" action={()=>updateColor(f.id,"#70DFB7")}/>
     <Button title="Custom…" action={()=>{setEditing(f.id);setColor(f.color)}}/>
     {f.kind==="ics"?<Button title="Remove" role="destructive" action={()=>commit({
      ...settings,feeds:settings.feeds.filter(x=>x.id!==f.id),
      views:settings.views.map(v=>({...v,feeds:v.feeds.filter(x=>x!==f.id)}))})}/>:null}
    </HStack>
    {editing===f.id?<HStack>
     <TextField title="Hex" value={color} onChanged={setColor} prompt="#FFFFFF"/>
     <Button title="Save" action={()=>{updateColor(f.id,color);setEditing("")}}/>
    </HStack>:null}
   </VStack>)}
  </Section>
  <Section title="Check full-page layout">
   <Button title="Preview XL portrait widget" action={async()=>{await Widget.preview({family:"systemExtraLargePortrait",
     parameters:{options:{"All":JSON.stringify({view:"all"})},default:"All"}})}} />
   <Text font="caption">iOS 27 or newer. Actual Home Screen layout must also be checked on-device.</Text>
   <Text font="caption">Configuration and private ICS links stay in Scripting's App Group, not GitHub.</Text>
   {notice?<Text foregroundStyle="orange">{notice}</Text>:null}
  </Section>
 </List>
 </NavigationStack>
}
async function main(){
 await Navigation.present({element:<Manage />});
 Script.exit();
}
void main();
