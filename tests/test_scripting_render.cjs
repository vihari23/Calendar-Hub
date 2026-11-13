'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),ts=require('/tmp/calendar-hub-ts/node_modules/typescript');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
const jsx=(type,props,key)=>({type,props:props||{},key});
const transpile=(p)=>ts.transpileModule(fs.readFileSync(p,'utf8'),{fileName:p,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
async function runScenario(family,parameter,fixture){
 const files=new Map();const paths={};
 const mockSDK={
 FileManager:{appGroupDocumentsDirectory:'/privategroup',existsSync:p=>files.has(p),readAsStringSync:p=>files.get(p),writeAsStringSync:(p,v)=>files.set(p,v)},
 Widget:{family,displaySize:{width:300,height:628},parameter,present:(element,policy)=>{paths.rendered=element;paths.policy=policy;},reloadAll:()=>{}},
 Script:{exit:()=>{paths.exited=true}},
 HStack:'HStack',VStack:'VStack',Text:'Text',Spacer:'Spacer',Link:'Link'
 };
 const publicData={checked_at_utc:new Date().toISOString(),feeds:[{id:'panchangam',status:'healthy',upcoming:[]},
 {id:'india_ott',status:'healthy',upcoming:Array.from({length:18},(_,i)=>({date:new Date(Date.now()+i*86400000).toISOString().slice(0,10),name:'OTT: Movie '+i}))},
 {id:'bulk_trash',status:'healthy',upcoming:[]}]};
 if(fixture)files.set('/privategroup/vihari-hub-xl-settings-v1.json',JSON.stringify(fixture));
 const api={...(mockSDK)};
 async function evalSource(path,req){const exports={};const module={exports};const code=transpile(path);await new AsyncFunction('module','exports','require','fetch','console','Date',code)(module,exports,req,async(url)=>{
   if(url.includes('widget.json'))return {ok:true,json:async()=>publicData};
   return {ok:true,text:async()=>['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:x','DTSTART;VALUE=DATE:20261119','SUMMARY:Private event','END:VEVENT','END:VCALENDAR'].join('\r\n')};
 },console,Date);return module.exports;}
 const core=await evalSource('scripting/core.ts',()=>{throw Error('unexpected import')});
 const settings=await evalSource('scripting/settings.ts',id=>id==='scripting'?api:id==='./core'?core:null);
 await evalSource('scripting/widget.tsx',id=>id==='scripting'?api:id==='./core'?core:id==='./settings'?settings:id==='react/jsx-runtime'?{jsx,jsxs:jsx,Fragment:'Fragment'}:null);
 assert.ok(paths.rendered,'Widget.present was not called');assert.ok(paths.exited,'Script.exit was not called');
 const rows=[];
 function walk(node){if(!node||typeof node!=='object')return;
  if(Array.isArray(node)){for(const n of node)walk(n);return;}
  if(typeof node.type==='function'&&node.type.name==='Row')rows.push(node.props.item);
  walk(node.props?.children);
 }
 walk(paths.rendered);
 return {rows,paths};
}
(async()=>{
 const xl=await runScenario('systemExtraLargePortrait','entertainment');
 assert.equal(xl.rows.length,12);assert.ok(xl.rows.every(x=>x.feed==='india_ott'));
 assert.equal(xl.paths.rendered.props.widgetBackground,'#0A1C3A');
 assert.equal(xl.paths.policy.policy,'after');
 const med=await runScenario('systemMedium','entertainment');assert.equal(med.rows.length,3);
 const small=await runScenario('systemSmall','entertainment');assert.equal(small.rows.length,1);
 const large=await runScenario('systemLarge','entertainment');assert.equal(large.rows.length,6);
 const custom={version:1,feeds:[{id:'family',name:'Family Calendar',kind:'ics',color:'#55AAFF',url:'https://example.org/f.ics'}],views:[{id:'family',name:'Family',feeds:['family'],showDaily:false}]};
 const family=await runScenario('systemExtraLargePortrait','family',custom);
 assert.ok(family.rows.some(x=>x.calendar==='Family Calendar'&&x.color==='#55AAFF'));
 console.log('Scripting UI simulated render: XL=12, large=6, medium=3, small=1; per-widget private feed color passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
