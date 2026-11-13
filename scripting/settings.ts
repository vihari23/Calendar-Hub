import {FileManager,Widget} from "scripting";
import {CACHE_FILE,SETTINGS_FILE,defaults,validSettings,type Settings} from "./core";
const ROOT=FileManager.appGroupDocumentsDirectory;
const FILE=ROOT+"/"+SETTINGS_FILE, CACHE=ROOT+"/"+CACHE_FILE;
export function loadSettings():Settings {
 try {return FileManager.existsSync(FILE)?validSettings(JSON.parse(FileManager.readAsStringSync(FILE))):defaults();}
 catch {return defaults();}
}
export function saveSettings(settings:Settings):void {
 FileManager.writeAsStringSync(FILE,JSON.stringify(validSettings(settings),null,2));
 Widget.reloadAll();
}
export type Saved={at:number,public:any,custom:Record<string,any>};
export function loadCache():Saved {
 try{if(FileManager.existsSync(CACHE))return JSON.parse(FileManager.readAsStringSync(CACHE));}catch{}
 return {at:0,public:null,custom:{}};
}
export function saveCache(cache:Saved):void{FileManager.writeAsStringSync(CACHE,JSON.stringify(cache));}
