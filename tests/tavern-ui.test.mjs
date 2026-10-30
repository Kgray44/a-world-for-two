import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

// Exercise the actual card without booting the browser application or any API.
const source=readFileSync(new URL('../control_room/static/app.js',import.meta.url),'utf8');
const code=source.slice(source.indexOf('function tavernCurrent('),source.indexOf('function mountTavernCard('));
const context=vm.createContext({
  esc:value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
  number:value=>String(value),when:value=>value||'Not yet',
  currentMeasurement:value=>{const age=(Date.now()-Date.parse(value.measured_at))/1000;return value.current===true&&Number.isFinite(age)&&age>=-2&&age<=value.max_age_seconds;},
  notice:(value,kind)=>`<div class="notice ${kind}">${value}</div>`,
  row:(label,value)=>`<div>${label}: ${value}</div>`,
  pill:value=>`<span>${value}</span>`,card:(title,body,side)=>`<section>${title}${side}${body}</section>`,
});
vm.runInContext(code,context);
const fixture=()=>({current:true,at:new Date().toISOString(),max_age_seconds:15,
  counts:{registered:30,loaded:0,roster:30},life_admission:{registered_total:309,at:'2026-10-30T01:23:56Z'},
  paused:false,suspended:true,music:true,runtime_accepted:false,residents:[],
  qualification:'Awaiting visual, behavior and audio qualification'});

test('card keeps tavern registrations separate from LIFE and makes no presence claim',()=>{
  const data=fixture(),html=context.tavernCardHTML(data);
  assert.match(html,/Registered · Easy NPC: 30/);
  assert.match(html,/Loaded at this report: 0/);
  assert.match(html,/Native LIFE · last completed admission: 309/);
  assert.doesNotMatch(html,/339/);
  assert.match(html,/Awaiting visual, behavior and audio qualification/);
  assert.equal(data.life_admission.registered_total,309);
});

test('client freshness expiry disables both controls even before the next poll',()=>{
  const data=fixture();data.at=new Date(Date.now()-60000).toISOString();
  const html=context.tavernCardHTML(data);
  assert.equal(context.tavernCurrent(data),false);
  assert.equal((html.match(/data-tavern-control=/g)||[]).length,2);
  assert.equal((html.match(/ disabled>/g)||[]).length,2);
  assert.match(html,/Last reported registrations/);
});
