import test from 'node:test';
import assert from 'node:assert/strict';
import {getValue,setValue,linesFromText,characterMatches,characterIsNearby,locationLabel,atlasCharacterLink,newCharacter,mountCharacters,modelPolicy,effectiveReasoning,samplingSupported,providerIsVerified,takeCredential,measuredCount,estimatedUSD} from '../control_room/static/characters.js';

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

test('provider presets preserve named models and only expose supported sampling',()=>{
  assert.equal(modelPolicy('gpt-6-luna').input_usd_per_million,.1);
  assert.equal(effectiveReasoning('gpt-6-luna','global',{reasoning_effort:'none'}),'none');
  assert.equal(effectiveReasoning('gpt-6.1-sol','global',{reasoning_effort:'none'}),'low');
  assert.equal(samplingSupported('gpt-6-luna','none'),true);
  assert.equal(samplingSupported('gpt-6-luna','high'),false);
  assert.equal(samplingSupported('gpt-6.1-sol','low'),false);
  assert.equal(samplingSupported('custom-unverified','none'),false);
});
test('connection enablement requires the tested model, endpoint and reasoning policy',()=>{
  const settings={credential_configured:true,connection_verified:true,model:'gpt-6-luna',endpoint:'https://api.openai.com/v1/chat/completions',reasoning_effort:'none'};
  const verified={verified:true,model:settings.model,endpoint:settings.endpoint,reasoning_effort:'none'};
  assert.equal(providerIsVerified(settings,verified),true);
  assert.equal(providerIsVerified({...settings,model:'gpt-6.1-sol'},verified),false);
  assert.equal(providerIsVerified({...settings,endpoint:'https://example.invalid'},verified),false);
  assert.equal(providerIsVerified({...settings,credential_configured:false},verified),false);
  assert.equal(providerIsVerified({...settings,response_tokens:512},verified,settings),false);
  assert.equal(providerIsVerified({...settings,input_usd_per_million:7},verified,settings),false);
});
test('one-time credential input clears synchronously before returning its value',()=>{
  const input={value:'local-test-placeholder'};
  assert.equal(takeCredential(input),'local-test-placeholder');
  assert.equal(input.value,'');assert.equal(takeCredential(input),'');
});
test('unknown request counts and estimated cost never become measured zero',async()=>{
  assert.equal(measuredCount(null),'Unavailable');assert.equal(measuredCount(undefined),'Unavailable');
  assert.equal(measuredCount(0),'0');assert.equal(estimatedUSD(null),'Unavailable');
  assert.equal(estimatedUSD(0),'$0.0000');
  const root=new StudioRoot(),snapshot={revision:'r1',characters:[],districts:[],templates:[],provider_status:{usage:{available:false,requests_today:null,requests_last_minute:null,requests_last_hour:null,reserved_cost_today_usd:null,measured_counts:null,estimated_token_cost_usd:null}}};
  const cleanup=await mountCharacters({root,api:async()=>snapshot});
  assert.match(root.innerHTML,/Requests today: Unavailable/);assert.match(root.innerHTML,/Reserved estimate: Unavailable/);
  assert.match(root.innerHTML,/missing measurements are not zero/);cleanup();
});

const providerSnapshot=()=>({revision:'r1',characters:[],districts:[],templates:[],settings:{provider:'openai',model:'gpt-6-luna',endpoint:'https://api.openai.com/v1/chat/completions',reasoning_effort:'none',credential_configured:true,credential_source:'windows_user_store',external_enabled:false,response_tokens:120,timeout_seconds:15,max_concurrent:2,requests_per_minute:6,requests_per_hour:24,requests_per_day:100,daily_budget_usd:.5,input_usd_per_million:.1,output_usd_per_million:.5}});
class ProviderRoot extends StudioRoot {
  constructor(){super();this.key={value:''};this.consent={checked:false};}
  querySelector(selector){if(selector==='[data-provider-key]')return this.key;if(selector==='[data-provider-consent]'||selector==='[data-npc-model-consent]')return this.consent;return null;}
}
test('credential submission is direct and clears the field even when saving fails',async()=>{
  const root=new ProviderRoot(),calls=[],messages=[];root.key.value='local-test-placeholder';
  const api=async(path,body)=>{calls.push(path);if(path.endsWith('/credential')){assert.equal(root.key.value,'');assert.equal(body.api_key,'local-test-placeholder');assert.equal(body.expected,'r1');throw new Error('Credential store unavailable');}return providerSnapshot();};
  const cleanup=await mountCharacters({root,api,toast:value=>messages.push(value)});
  await root.click('provider-credential');
  assert.deepEqual(calls,['/api/characters','/api/characters/credential']);
  assert.equal(root.key.value,'');assert.equal(root.innerHTML.includes('local-test-placeholder'),false);
  assert.equal(messages.some(message=>message.includes('local-test-placeholder')),false);
  assert.doesNotMatch(root.innerHTML,/data-provider-key[^>]*\bvalue=/);
  cleanup();
});
test('connection tests require explicit consent and never run on directory display',async()=>{
  const root=new ProviderRoot(),calls=[];
  const cleanup=await mountCharacters({root,api:async(path)=>{calls.push(path);return providerSnapshot();}});
  await root.click('provider-test');
  assert.deepEqual(calls,['/api/characters']);
  cleanup();
});
test('connection test sends no credential or character context and unmount cancels job polling',async()=>{
  const root=new ProviderRoot(),calls=[];root.consent.checked=true;
  let started;const submitted=new Promise(resolve=>started=resolve);
  const api=async(path,body)=>{calls.push(path);if(path.endsWith('/connection-test')){assert.deepEqual(body,{expected:'r1',external_opt_in:true});started();return {job:'provider-test'};}return providerSnapshot();};
  const cleanup=await mountCharacters({root,api});
  const clicking=root.click('provider-test');await submitted;await Promise.resolve();cleanup();await clicking;
  assert.equal(calls.includes('/api/jobs'),false);
  assert.equal(root.key.value,'');
});

test('provider form saves only configuration fields and never submits the masked credential',async()=>{
  const root=new ProviderRoot();root.key.value='not-a-real-key';
  const controls=[{dataset:{setting:'model'},type:'text',value:'gpt-6-luna'},
    {dataset:{setting:'response_tokens'},type:'number',value:'120'},
    {dataset:{setting:'external_enabled'},type:'checkbox',checked:false}];
  const baseAll=root.querySelectorAll.bind(root);root.querySelectorAll=selector=>selector==='[data-setting]'?controls:baseAll(selector);
  let submitted;
  const api=async(path,body)=>{if(path.endsWith('/settings')){submitted=body;return {revision:'r2',note:'Saved'};}return providerSnapshot();};
  const cleanup=await mountCharacters({root,api});await root.click('settings');
  assert.deepEqual(submitted,{expected:'r1',changes:{provider:'openai',model:'gpt-6-luna',response_tokens:120,external_enabled:false}});
  assert.equal(JSON.stringify(submitted).includes('not-a-real-key'),false);
  cleanup();
});
test('a selected character model can be tested without changing the global default',async()=>{
  const root=new ProviderRoot();root.consent.checked=true;
  const character={...newCharacter(),id:'bill',name:'Barnacle Bill'};
  let tested;
  const api=async(path,body)=>{if(path.includes('/detail'))return {revision:'r1',character,history:[],memories:[]};if(path.endsWith('/connection-test')){tested=body;return {verified:true,model:'gpt-6.1-sol',reasoning_effort:'low',usage:{counts:{input:8,output:1,total:9}}};}return providerSnapshot();};
  const cleanup=await mountCharacters({root,api});await root.click('open',{id:'bill'});
  root.inputs=[{dataset:{field:'ai.model'},type:'text',value:'gpt-6.1-sol'}];
  await root.click('provider-test-model');
  assert.deepEqual(tested,{expected:'r1',external_opt_in:true,model:'gpt-6.1-sol'});
  assert.equal(character.ai.model,'');
  cleanup();
});
test('recognized global and character model IDs remain editable without credentials or adapter',async()=>{
  const root=new StudioRoot(),character={...newCharacter(),id:'bill',name:'Barnacle Bill'};
  character.ai.model='gpt-6.1-sol';
  const snapshot=providerSnapshot();snapshot.settings.model='gpt-6-luna';snapshot.settings.credential_configured=false;
  const api=async path=>path.includes('/detail')?{revision:'r1',character,history:[],memories:[],capabilities:{runtime:{per_npc_model:false}}}:snapshot;
  const cleanup=await mountCharacters({root,api});
  const globalInput=root.innerHTML.match(/<input[^>]*data-setting="model"[^>]*>/)?.[0];
  assert.ok(globalInput);assert.doesNotMatch(globalInput,/\breadonly\b|\bdisabled\b/);
  await root.click('open',{id:'bill'});await root.click('tab',{tab:'ai'});
  const characterInput=root.innerHTML.match(/<input[^>]*data-field="ai.model"[^>]*>/)?.[0];
  assert.ok(characterInput);assert.doesNotMatch(characterInput,/\breadonly\b|\bdisabled\b/);
  assert.match(root.innerHTML,/Character AI model/);assert.match(root.innerHTML,/Use global default \(gpt-6-luna\)/);
  assert.match(root.innerHTML,/Luna · gpt-6-luna/);assert.match(root.innerHTML,/Sol · gpt-6.1-sol/);
  cleanup();
});
test('typing and leaving a character model field preserves the editor DOM and subsequent save',async()=>{
  const root=new StudioRoot(),character={...newCharacter(),id:'bill',name:'Barnacle Bill'};
  let submitted;
  const api=async(path,body)=>{if(path.endsWith('/save')){submitted=body.profile;return {revision:'r2',character:body.profile};}return path.includes('/detail')?{revision:'r1',character,history:[],memories:[]}:providerSnapshot();};
  const cleanup=await mountCharacters({root,api});await root.click('open',{id:'bill'});await root.click('tab',{tab:'ai'});
  const html=root.innerHTML,input={dataset:{field:'ai.model'},type:'text',value:'custom-model',hasAttribute:()=>false};root.inputs=[input];
  root.listeners.input({target:input});assert.equal(root.innerHTML,html);
  await root.listeners.change({target:input});assert.equal(root.innerHTML,html);
  await root.click('save');assert.equal(submitted.ai.model,'custom-model');cleanup();
});
