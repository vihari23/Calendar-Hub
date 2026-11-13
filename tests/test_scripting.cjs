'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ts=require('/tmp/calendar-hub-ts/node_modules/typescript');
const root='scripting/';
const files=['core.ts','settings.ts','widget.tsx','index.tsx'];
for(const name of files){
 const source=fs.readFileSync(root+name,'utf8');
 const result=ts.transpileModule(source,{fileName:name,reportDiagnostics:true,compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}});
 const errors=(result.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error);
 assert.equal(errors.length,0,name+': '+errors.map(e=>ts.flattenDiagnosticMessageText(e.messageText,' ')).join('; '));
 console.log('TS/TSX syntax valid:',name);
}
const source=fs.readFileSync(root+'core.ts','utf8');
const code=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
const mod={exports:{}};
vm.runInNewContext(code,{module:mod,exports:mod.exports,URL,Date,Set,RegExp,Error,console}, {filename:'core.js'});
const a=mod.exports;
const def=a.defaults();
assert.equal(def.feeds.length,3);assert.equal(def.views.length,4);
assert.equal(a.chosen(def,'entertainment').id,'entertainment');
assert.equal(a.chosen(def,JSON.stringify({view:'home'})).id,'home');
assert.equal(a.chosen(def,'other').id,'all');
assert.equal(a.safeColor('ffddee'),'#FFDDEE');
assert.equal(a.safeColor('red'),null);
assert.equal(a.safeURL('webcal://example.org/all.ics'),'https://example.org/all.ics');
for(const url of ['http://example.org/all.ics','https://localhost/a.ics','https://127.0.0.1/a.ics','https://admin:pass@example.org/a.ics'])assert.equal(a.safeURL(url),null,url);
assert.equal(a.phoenixToday(new Date('2026-11-14T05:30:00Z')),'2026-11-13');
assert.equal(a.icsDate('20261114T003000Z'),'2026-11-13');
assert.equal(a.icsDate('20261114T080000'),'2026-11-14');
assert.equal(a.icsDate('20260231'),null);
assert.equal(a.rowLimit('systemExtraLargePortrait',628),12);
assert.equal(a.rowLimit('systemLarge',390),6);
assert.equal(a.rowLimit('systemMedium',170),3);
const feedData={checked_at_utc:'2026-11-13T19:00:00Z',feeds:[
 {id:'panchangam',status:'healthy',upcoming:[{date:'2026-11-16',name:'Ordinary tithi'},{date:'2026-11-17',name:'🪔 Special puja'}]},
 {id:'india_ott',status:'healthy',upcoming:[{date:'2026-11-18',name:'OTT: Movie name'}]},
 {id:'bulk_trash',status:'healthy',upcoming:[{date:'2026-11-19',name:'Collection'}]}]};
let merged=a.mergeEvents(def,a.chosen(def,'all'),feedData,{},'2026-11-13');
assert.equal(merged.healthy,3);assert.equal(merged.total,3);assert.equal(merged.events.length,3);
assert.equal(merged.events.some(x=>x.title==='Ordinary tithi'),false);
assert.equal(merged.events.find(x=>x.feed==='india_ott').title,'Movie name');
assert.equal(merged.events.find(x=>x.feed==='india_ott').color,'#C6A5FF');
assert.equal(a.mergeEvents(def,a.chosen(def,'culture'),feedData,{},'2026-11-13').events.length,2);
const extra={id:'family',name:'Family',kind:'ics',url:'https://example.org/secure.ics',color:'#00AAFF'};
const customSettings={...def,feeds:[...def.feeds,extra],views:[...def.views,{id:'family',name:'Family view',feeds:['family','india_ott'],showDaily:false}]};
merged=a.mergeEvents(customSettings,a.chosen(customSettings,'family'),feedData,{family:{ok:true,events:[{date:'2026-11-14',title:'Custom family date'}]}},'2026-11-13');
assert.equal(merged.total,2);assert.equal(merged.events.length,2);assert.equal(merged.events[0].color,'#00AAFF');
const sample=['BEGIN:VCALENDAR','VERSION:2.0','BEGIN:VEVENT','UID:x',
 'DTSTART;TZID=America/Phoenix:20261119T080000','SUMMARY:Glendale bulk trash — placement',
 'END:VEVENT','END:VCALENDAR',''].join('\r\n');
assert.equal(a.parseICS(sample,'2026-11-13','2026-11-30').events[0].date,'2026-11-19');
const recur=['BEGIN:VCALENDAR','BEGIN:VEVENT','UID:a','DTSTART;VALUE=DATE:20241115',
'SUMMARY:Anniversary','RRULE:FREQ=YEARLY;INTERVAL=1','END:VEVENT','END:VCALENDAR'].join('\r\n');
assert.deepEqual(Array.from(a.parseICS(recur,'2026-11-01','2026-12-01').events.map(x=>x.date)),['2026-11-15']);
console.log('Calendar widget: configuration, ics, colors, date math, event filtering, layout tests PASSED');
