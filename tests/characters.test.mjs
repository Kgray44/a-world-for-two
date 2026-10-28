import test from 'node:test';
import assert from 'node:assert/strict';
import {getValue,setValue,linesFromText,characterMatches,characterIsNearby,locationLabel,atlasCharacterLink,newCharacter,mountCharacters} from '../control_room/static/characters.js';

test('character search covers identity and district without changing profiles',()=>{
  const bill={name:'Barnacle Bill',profession:'Tavern keeper',district:'tortuga',kind:'villager'};
  assert.equal(characterMatches(bill,'BARNACLE'),true);
  assert.equal(characterMatches(bill,'tavern','tortuga','villager'),true);
  assert.equal(characterMatches(bill,'','rosewater'),false);
  assert.equal(characterMatches(bill,'','','animal'),false);
  assert.equal(bill.name,'Barnacle Bill');
});
test('blank or stale positions never claim live telemetry',()=>{
  assert.equal(locationLabel(null),'Position unavailable');
  assert.match(locationLabel({x:1,y:2,z:3,status:'live',measured_at:'2020-01-01T00:00:00Z'}),/^Last known/);
  assert.match(locationLabel({x:1,y:2,z:3,status:'live',measured_at:new Date().toISOString()}),/^Live position/);
  assert.match(locationLabel({x:1,y:null,z:3,status:'assigned'}),/^Assigned home/);
});
test('atlas links carry stable profile identity and only finite positions',()=>{
  const link=atlasCharacterLink({id:'bill',location:{dimension:'minecraft:overworld',x:12,z:-4}});
  assert.equal(new URLSearchParams(link.split('?')[1]).get('character'),'bill');
  assert.equal(new URLSearchParams(link.split('?')[1]).get('z'),'-4');
  assert.equal(atlasCharacterLink({id:'unbound',location:{x:null,z:null}}).includes('&x='),false);
});
test('nearby search excludes unknown positions and other dimensions',()=>{
  const character={location:{x:10,z:20,dimension:'minecraft:overworld'}};
  assert.equal(characterIsNearby(character,{x:10,z:25,radius:10,dimension:'minecraft:overworld'}),true);
  assert.equal(characterIsNearby(character,{x:10,z:25,radius:10,dimension:'minecraft:the_nether'}),false);
  assert.equal(characterIsNearby({location:{x:null,z:null}},{x:0,z:0,radius:128}),false);
});
test('new characters are scripted, unbound and independent with bounded defaults',()=>{
  const a=newCharacter(),b=newCharacter();a.personality.traits.push('salty');
  assert.equal(b.personality.traits.length,0);
  assert.equal(a.ai.enabled,false);assert.equal(a.ai.provider,'scripted');
  assert.equal(a.voice.enabled,false);assert.equal(a.voice.bubbles,true);
  assert.equal(a.entity_uuid,null);assert.equal(a.location.x,null);
});
test('friendly fields preserve nested profile semantics and multiline dialogue',()=>{
  const profile=newCharacter();setValue(profile,'personality.speaking_style','Dry, nautical wit.');
  assert.equal(getValue(profile,'personality.speaking_style'),'Dry, nautical wit.');
  assert.deepEqual(linesFromText(' Ahoy!\r\n\n The kettle mutinied. '),['Ahoy!','The kettle mutinied.']);
});

class StudioRoot {
  constructor(){this.innerHTML='';this.listeners={};this.classList={add(){},remove(){}};this.inputs=[];}
  querySelector(){return null;}
  querySelectorAll(selector){return selector==='[data-field]'?this.inputs:[];}
  addEventListener(type,listener,options){this.listeners[type]=listener;options.signal.addEventListener('abort',()=>delete this.listeners[type]);}
  contains(){return true;}
  async click(command,extra={}){const button={dataset:{command,...extra},disabled:false,isConnected:true};await this.listeners.click({target:{closest:()=>button}});}
}
test('opening the directory loads only summaries and selected details without an AI request',async()=>{
  const root=new StudioRoot(),calls=[],profile={...newCharacter(),id:'bill',name:'Barnacle Bill'};
  const api=async path=>{calls.push(path);return path.includes('/detail')?{revision:'r1',character:profile,history:[],memories:[]}:{revision:'r1',characters:[profile],districts:['tortuga'],templates:[],settings:{}};};
  const cleanup=await mountCharacters({root,api});
  assert.deepEqual(calls,['/api/characters']);
  assert.match(root.innerHTML,/Barnacle Bill/);
  await root.click('open',{id:'bill'});
  assert.deepEqual(calls,['/api/characters','/api/characters/detail?id=bill']);
  assert.match(root.innerHTML,/Test conversation/);
  cleanup();assert.equal(root.listeners.click,undefined);
});
test('editing a friendly field saves the draft with its original compare-and-swap revision',async()=>{
  const root=new StudioRoot(),calls=[],profile={...newCharacter(),id:'bill',name:'Barnacle Bill'};
  let revision='r1';
  const api=async(path,body)=>{calls.push({path,body});if(path.endsWith('/save')){assert.equal(body.expected,'r1');assert.equal(body.profile.personality.speaking_style,'A very dry pirate.');Object.assign(profile,body.profile);revision='r2';return {revision,character:profile};}return path.includes('/detail')?{revision,character:profile,history:[],memories:[]}:{revision,characters:[profile],districts:['tortuga'],templates:[],settings:{}};};
  const cleanup=await mountCharacters({root,api});await root.click('open',{id:'bill'});
  root.inputs=[{dataset:{field:'personality.speaking_style'},type:'text',value:'A very dry pirate.'}];
  await root.click('save');
  assert.equal(calls.filter(c=>c.path.endsWith('/save')).length,1);
  assert.equal(calls.some(c=>c.path.endsWith('/apply')),false);
  cleanup();
});
test('unsafe profile text is escaped in directory cards',async()=>{
  const root=new StudioRoot(),profile={...newCharacter(),id:'unsafe',name:'<img src=x onerror=alert(1)>',description:'<script>bad</script>'};
  const cleanup=await mountCharacters({root,api:async()=>({revision:'r1',characters:[profile],templates:[],districts:[]})});
  assert.equal(root.innerHTML.includes('<img src=x'),false);
  assert.match(root.innerHTML,/&lt;script&gt;bad&lt;\/script&gt;/);
  cleanup();
});
