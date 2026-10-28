import test from 'node:test';
import assert from 'node:assert/strict';
import {characterProfileLink,characterPlaces,characterFocus} from '../control_room/static/atlas.js';

const at='2026-10-28T21:40:00Z',now=Date.parse(at);
const bill={id:'character:barnacle-bill',character_id:'barnacle-bill',kind:'character',character_type:'villager',name:'Barnacle Bill',dimension:'minecraft:overworld',x:123,y:68,z:-456,state:'live',at};
test('character Atlas marker freshness expires separately from map or bridge freshness',()=>{
  assert.equal(characterPlaces([bill],now+14000)[0].state,'live');
  assert.equal(characterPlaces([bill],now+16000)[0].state,'last known');
  assert.equal(characterPlaces([{...bill,at:null}],now)[0].state,'last known');
  assert.equal(bill.state,'live');
});
test('assigned homes stay assigned and unknown positions are excluded',()=>{
  assert.equal(characterPlaces([{...bill,state:'assigned home',at:null}],now)[0].state,'assigned home');
  assert.deepEqual(characterPlaces([{...bill,x:null},{...bill,z:Infinity},{...bill,dimension:'__proto__'}],now),[]);
});
test('character popup link uses the stable profile identifier',()=>{
  assert.equal(characterProfileLink(bill),'#characters?id=barnacle-bill');
});
test('camera character focus uses known registry coordinates instead of query coordinate claims',()=>{
  const result=characterFocus([bill],'#atlas?character=barnacle-bill&dimension=minecraft:the_end&x=999&z=999');
  assert.equal(result.x,123);assert.equal(result.z,-456);assert.equal(result.dimension,'minecraft:overworld');
  assert.equal(characterFocus([bill],'#atlas?character=unknown&x=999&z=999'),null);
});
