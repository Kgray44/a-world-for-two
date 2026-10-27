import assert from 'node:assert/strict';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';

// Execute the real app module with inert DOM and failed fixture HTTP. No browser,
// network, Control Room or runtime process is started. Startup failure is handled
// by the app's existing catch; the exported pure formatter is exercised directly.
const nodes=new Map();
globalThis.document={
  querySelector(selector){if(!nodes.has(selector))nodes.set(selector,{setAttribute(){},close(){},classList:{remove(){},toggle(){return false;}}});return nodes.get(selector);},
  querySelectorAll(){return [];},addEventListener(){},body:{classList:{remove(){},toggle(){return false;}}}
};
globalThis.window={addEventListener(){},scrollTo(){}};
globalThis.location={hash:''};
globalThis.fetch=async()=>{throw new Error('Fixture HTTP is disabled');};
const app=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../../control_room/static/app.js');
const {idleSimulationRows}=await import(pathToFileURL(app));
let checks=0;
const check=(condition,message)=>{checks++;assert.ok(condition,message);};
const dimension='minecraft:overworld';
const fresh=()=>({at:new Date().toISOString(),dimension,dimension_players:0,empty_time_ticks:0,native_saved_forced_chunk_branch:false,next_entity_and_block_entity_idle_branch:'eligible'});
let html=idleSimulationRows(fresh(),true,dimension);
check(html.includes('0 ticks'),'A real zero counter must remain visible');
check(html.includes('>None<'),'Native false saved-forcing status must remain None');
check(html.includes('>Eligible<'),'Known native eligibility is shown');
check(html.includes('do not measure actual entity or block-entity tick executions'),'Eligibility is not represented as actual ticking');
html=idleSimulationRows({...fresh(),empty_time_ticks:300,next_entity_and_block_entity_idle_branch:'suspended'},true,dimension);
check(html.includes('Suspended (idle)')&&html.includes('300 ticks'),'Threshold state stays distinct from loaded holders');
html=idleSimulationRows({...fresh(),empty_time_ticks:undefined,counter_unavailable:'java.lang.IllegalAccessException',next_entity_and_block_entity_idle_branch:'unknown'},true,dimension);
check(html.includes('>Unknown<')&&html.includes('>Unavailable<')&&!html.includes('0 ticks'),'Unavailable getter is never a zero counter');
html=idleSimulationRows({...fresh(),empty_time_ticks:undefined,dimension_players:1,next_entity_and_block_entity_idle_branch:'eligible'},true,dimension);
check(html.includes('>Eligible<')&&html.includes('>Unavailable<'),'Known players can establish eligibility independently of the unavailable counter');
check(!idleSimulationRows(fresh(),false,dimension).includes('>Eligible<'),'Stale outer bridge freshness cannot show current eligibility');
check(!idleSimulationRows({...fresh(),at:new Date(Date.now()-30000).toISOString()},true,dimension).includes('>Eligible<'),'Stale nested sample cannot borrow fresh bridge age');
check(!idleSimulationRows({...fresh(),dimension:'minecraft:the_nether'},true,dimension).includes('>Eligible<'),'Another dimension cannot borrow this row');
html=idleSimulationRows({...fresh(),empty_time_ticks:'0',native_saved_forced_chunk_branch:'false',next_entity_and_block_entity_idle_branch:'unknown'},true,dimension);
check(html.includes('>Unknown<')&&html.includes('>Unavailable<')&&!html.includes('0 ticks'),'String values do not impersonate native booleans/counters');
html=idleSimulationRows({...fresh(),counter_unavailable:'<img src=x onerror=alert(1)>'},true,dimension);
check(html.includes('&lt;img')&&!html.includes('<img'),'Native diagnostic strings are escaped');
console.log(`IDLE_SIMULATION_UI_CHECKS=${checks} PASS; real formatter, no browser/server`);
