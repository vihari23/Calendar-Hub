import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";
const script=readFileSync("scriptable/CalendarHubWidget.js","utf8");
assert.match(script,/^\/\/ Calendar Hub Widget/);
const stripped=script.replace(/\nawait main\(\);\s*$/,"");
assert.notEqual(stripped,script,"Script entry point was unexpectedly changed");
const stub={FileManager:{local:()=>({
 libraryDirectory:()=>"/tmp",
 joinPath:(x,y)=>x+"/"+y,
 fileExists:()=>false,
 readString:()=>null,
 writeString:()=>null
})}};
const functions=vm.runInNewContext(stripped+
 "\n({safeURL,cleanHex,defaults,viewFor,parseICS,rruleAllowed,dayFromICS,isNotablePanchangam})",stub);
assert.equal(functions.safeURL("webcal://example.org/events.ics"),"https://example.org/events.ics");
assert.equal(functions.safeURL("http://example.org/events.ics"),null);
assert.equal(functions.safeURL("https://localhost/foo.ics"),null);
assert.equal(functions.safeURL("https://example.org/events.ics"),"https://example.org/events.ics");
assert.equal(functions.cleanHex("e5a3be"),"#E5A3BE");
assert.equal(functions.cleanHex("nonsense"),null);
const config=functions.defaults();
assert.equal(config.feeds.length,3);
assert.equal(functions.viewFor(config,"entertainment").feeds[0],"india_ott");
assert.equal(functions.viewFor(config,"home").feeds[0],"bulk_trash");
assert.equal(functions.viewFor(config,"unknown").id,"all");
assert.equal(config.views.find(v=>v.id==="all").dailyPanchangam,false);
assert.equal(config.views.find(v=>v.id==="culture").dailyPanchangam,true);
assert.equal(functions.isNotablePanchangam("🪔 Diwali — Shukla"),true);
assert.equal(functions.isNotablePanchangam("Shukla Panchami · Rohini"),false);
const ics=["BEGIN:VCALENDAR","VERSION:2.0",
"BEGIN:VEVENT","UID:test-1","DTSTART;TZID=America/Phoenix:20261114T080000",
"SUMMARY:Crazy Kalyanam","END:VEVENT",
"BEGIN:VEVENT","UID:repeat-1","DTSTART;VALUE=DATE:20241120",
"SUMMARY:Annual reminder","RRULE:FREQ=YEARLY;INTERVAL=1","EXDATE;VALUE=DATE:20261120","END:VEVENT",
"END:VCALENDAR",""].join("\r\n");
const events=functions.parseICS(ics,"2026-11-13","2027-02-01");
assert.equal(events.length,1);
assert.equal(events[0].name,"Crazy Kalyanam");
const noEx=ics.replace("EXDATE;VALUE=DATE:20261120\r\n","");
assert.equal(functions.parseICS(noEx,"2026-11-13","2027-02-01").length,2);
const rdate=["BEGIN:VCALENDAR","BEGIN:VEVENT","UID:rdate","DTSTART;VALUE=DATE:20260101",
"SUMMARY:Special","RDATE;VALUE=DATE:20261118","END:VEVENT","END:VCALENDAR"].join("\r\n");
assert.equal(functions.parseICS(rdate,"2026-11-13","2026-11-30").length,1);
assert.equal(functions.dayFromICS("20261114T003000Z"),"2026-11-13");
assert.equal(functions.dayFromICS("20261114T080000"),"2026-11-14");
console.log("Scriptable widget: 20 functional assertions passed");
