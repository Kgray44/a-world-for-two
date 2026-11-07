import assert from 'node:assert/strict';
import test from 'node:test';
import {VisiblePoller} from '../control_room/static/polling.js';
import {atlasView,currentMeasurement,playerView} from '../control_room/static/atlas-state.js';

const settle=()=>new Promise(resolve=>setImmediate(resolve));
function harness(work){
  const timers=new Map(),events=new EventTarget();let id=0,hidden=false;
  const poller=new VisiblePoller(work,{events,hidden:()=>hidden,schedule:(fn,delay)=>{timers.set(++id,{fn,delay});return id;},cancel:id=>timers.delete(id)});
  return {poller,timers,hide:value=>{hidden=value;events.dispatchEvent(new Event('visibilitychange'));}};
}

test('polls never overlap, and hidden tabs schedule no requests',async()=>{
  let calls=0,finish;const h=harness(()=>{calls++;return new Promise(resolve=>{finish=resolve;});});
  h.poller.start();h.poller.wake();assert.equal(calls,1);assert.equal(h.timers.size,0);
  h.hide(true);finish();await settle();assert.equal(h.timers.size,0);
  h.hide(false);assert.equal(calls,2);h.poller.stop();finish();await settle();assert.equal(h.timers.size,0);
});

test('failures back off, successful reads recover, and stop cancels timers',async()=>{
  let fail=true,calls=0;const h=harness(async()=>{calls++;if(fail)throw new Error('backend offline');});
  h.poller.start();await settle();assert.equal([...h.timers.values()][0].delay,10000);
  h.poller.wake();await settle();assert.equal([...h.timers.values()][0].delay,20000);
  fail=false;h.poller.wake();await settle();assert.equal([...h.timers.values()][0].delay,5000);
  h.poller.stop();assert.equal(h.timers.size,0);h.hide(false);assert.equal(calls,3);
});

test('Atlas live claims and players expire even when the last HTTP response was successful',()=>{
  const now=1800000000000,stamp=new Date(now).toISOString();
  const live={measured_at:stamp,current:true,max_age_seconds:15};
  const data={freshness:{bridge:live,players:live,atlas_claims:{...live,max_age_seconds:45}},
    players:[{name:'Fixture player',online:true,location:{x:1},location_state:'live'}],
    objects:[{name:'Fixture ship',state:'loaded'}],renderer:{queued_chunks:1},claims:{available:true,items:[{}]}};
  assert.equal(atlasView(data,now).players[0].online,true);
  const stale=atlasView(data,now+16000);
  assert.equal(stale.players[0].online,null);assert.equal(stale.players[0].location_state,'last seen');
  assert.equal(stale.objects[0].state,'last seen');assert.equal(stale.renderer,null);assert.equal(stale.claims.available,false);
  assert.equal(data.players[0].online,true);assert.equal(data.objects[0].state,'loaded');
});

test('invalid, future and unsupported measurement times cannot enable a live marker',()=>{
  const now=1800000000000;
  for(const stamp of [null,'bad timestamp',new Date(now+3000).toISOString(),Infinity])
    assert.equal(currentMeasurement({measured_at:stamp,current:true,max_age_seconds:15},now),false);
});

test('cache, independently stopped presence and integration labels expire after backend loss',()=>{
  const now=1800000000000,stamp=new Date(now).toISOString();
  const live={measured_at:stamp,current:true,max_age_seconds:15};
  const data={freshness:{bridge:live,players:live,atlas_claims:{...live,max_age_seconds:45}},
    players_state:'offline',players_measured_at:stamp,players:[{online:false}],
    cache:{measured_at:stamp,current:true},integrations:[{name:'Players, structures and named entities',status:'current'},{name:'Open Parties and Claims',status:'current'}],claims:{available:true,items:[]}};
  const current=atlasView(data,now);
  assert.equal(current.players[0].online,false);assert.equal(current.cache.current,true);
  const stale=atlasView(data,now+61000);
  assert.equal(stale.players[0].online,null);assert.equal(stale.cache.current,false);
  assert.ok(stale.integrations.every(row=>row.status==='unavailable'));
});

test('an open player card expires without becoming an offline report or retaining live capabilities',()=>{
  const now=1800000000000,value={received_at:now,online:true,location_state:'live',location:{at:new Date(now).toISOString(),x:1},capabilities:['safe_teleport']};
  assert.equal(playerView(value,now).online,true);
  const stale=playerView(value,now+16000);
  assert.equal(stale.online,null);assert.equal(stale.location_state,'last seen');assert.deepEqual(stale.capabilities,[]);
  assert.equal(value.online,true);
});
