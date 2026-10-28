'use strict';
import {LocalSession} from './session.js';
import {VisiblePoller} from './polling.js';
import {playerView} from './atlas-state.js';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = {csrf:'', page:'overview', overview:null, jobs:[], history:[], tab:'installed', raw:null, seenJobs:new Set(), busy:false, connected:false, renderGeneration:0};
const localSession=new LocalSession(globalThis.fetch.bind(globalThis),token=>{state.csrf=token;});
const labels = {overview:'Overview', performance:'Performance', storage:'Storage', mods:'Mod Manager', settings:'World settings', players:'Players & access', atlas:'World Atlas', cinematics:'Cinematics', console:'Console & logs', backups:'Backups', connectivity:'Connectivity', graphics:'Graphics & distance', compatibility:'Compatibility', setup:'Setup & repair'};
const bytes = value => {if(value == null) return '—'; if(value === 0) return '0 B'; const i = Math.min(4,Math.floor(Math.log(value)/Math.log(1024))); return `${(value/1024**i).toLocaleString(undefined,{maximumFractionDigits:i>1?2:0})} ${['B','KiB','MiB','GiB','TiB'][i]}`;};
const number = (value, digits=1) => value == null ? '—' : Number(value).toLocaleString(undefined,{maximumFractionDigits:digits});
const when = value => value ? new Date(value).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}) : 'Not yet';
const duration = seconds => seconds == null ? '—' : seconds < 3600 ? `${Math.floor(seconds/60)}m ${Math.floor(seconds%60)}s` : `${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m`;
const pill = (text, kind='') => `<span class="pill ${kind}">${esc(text)}</span>`;
const button = (action, label, classes='', attrs='') => `<button class="button ${classes}" data-action="${action}" ${attrs}>${label}</button>`;
const notice = (text, kind='') => `<div class="notice ${kind}">${esc(text)}</div>`;
const empty = (text, symbol='❧') => `<div class="empty"><span class="symbol">${symbol}</span>${esc(text)}</div>`;
const row = (label, value) => `<div class="info-row"><span class="label">${esc(label)}</span><strong>${value}</strong></div>`;
const header = (title, subtitle, actions='') => `<div class="page-head"><div><div class="eyebrow">A WORLD FOR TWO</div><h1>${title}</h1><p class="subtle">${subtitle}</p></div><div class="button-row">${actions}</div></div>`;
const card = (title, body, side='') => `<section class="card"><div class="card-head"><h2>${title}</h2>${side}</div>${body}</section>`;
const metric = (label,value,unit='',foot='',icon='⌁') => `<div class="metric"><div class="metric-label">${label}<span class="metric-icon">${icon}</span></div><div class="metric-value">${value}${unit?`<small>${unit}</small>`:''}</div><div class="metric-foot">${foot}</div></div>`;
const measurementMillis = value => typeof value==='number' ? value*1000 : typeof value==='string' ? Date.parse(value) : NaN;
function currentMeasurement(info) {const age=(Date.now()-measurementMillis(info?.measured_at))/1000;return info?.current===true&&Number.isFinite(age)&&age>=-2&&age<=info.max_age_seconds;}
function measurementLabel(info) {
  const stamp=measurementMillis(info?.measured_at),age=(Date.now()-stamp)/1000;
  if(!Number.isFinite(stamp)||!Number.isFinite(new Date(stamp).getTime()))return 'Measurement unavailable';
  const ageText=Number.isFinite(age)&&age>=-2?`${age>604800?'≥ ':''}${number(Math.min(604800,Math.max(0,age)),0)} s old`:'clock differs';
  return `${currentMeasurement(info)?'Measured':'Unavailable now; last measured'} ${when(new Date(stamp).toISOString())} · ${ageText}`;
}
const liveMetric = (measurement,key,group='snapshot') => currentMeasurement(measurement.freshness?.[group]) ? measurement[key] : null;
function freshnessNotice(measurement) {
  const delayed=['snapshot','tick','bridge'].filter(key=>measurement.freshness?.[key]&&!currentMeasurement(measurement.freshness[key]));
  return delayed.length?notice(`Telemetry delayed or unavailable (${delayed.join(', ')}). Current readings show — until fresh measurements arrive. Server process state and last-known player positions are separate.`,'warn'):'';
}

export function idleSimulationRows(value,current,dimension) {
  const stamp=measurementMillis(value?.at),age=(Date.now()-stamp)/1000;
  if(current!==true||!value||value.dimension!==dimension||!Number.isFinite(age)||age< -2||age>15)
    return '<p class="subtle">Native idle eligibility unavailable for this dimension. A current bridge sample is required.</p>';
  const counter=Number.isInteger(value.empty_time_ticks)&&value.empty_time_ticks>=-2147483648&&value.empty_time_ticks<=2147483647?value.empty_time_ticks:null;
  const players=Number.isInteger(value.dimension_players)&&value.dimension_players>=0?value.dimension_players:null;
  const branch={eligible:'Eligible',suspended:'Suspended (idle)',unknown:'Unknown'}[value.next_entity_and_block_entity_idle_branch]||'Unknown';
  const forced=value.native_saved_forced_chunk_branch===true?'Present':value.native_saved_forced_chunk_branch===false?'None':'Unknown';
  return `<div class="idle-simulation">${row('Native idle branch · next tick',pill(branch))}`+
    row('Native empty-world counter',counter===null?'Unavailable':`${number(counter,0)} ticks · cutoff 300`)+
    row('Saved forced-chunk wake status',forced)+row('Native dimension players',players===null?'Unavailable':number(players,0))+
    `<p class="subtle">Idle state sampled ${esc(when(value.at))}. Eligibility applies to the next normal dimension tick if native inputs stay unchanged; holder counts do not measure actual entity or block-entity tick executions.${value.counter_unavailable?' Counter access unavailable: '+esc(String(value.counter_unavailable).slice(0,240))+'.':''}</p></div>`;
}

async function api(path, body) {
  let response;
  try {response = await localSession.request(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});}
  catch(error){if(['TimeoutError','AbortError'].includes(error.name))throw new Error('Control Room did not respond in time. An action may still be running; check Task history and server state before retrying.');throw error;}
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
let toastTimer;
function toast(message, error=false) {
  const node = $('#toast'); node.textContent=message; node.className=`visible${error?' error':''}`;
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>node.className='', error?10000:5000);
}
async function run(path,body={}) {
  try {const result=await api(path,body); toast(result.job ? 'Working on it. You can keep using Control Room.' : result.note || 'Done.'); await refresh(); return result;} catch(error) {toast(error.message,true); throw error;}
}
function modal(title, html, actions=[]) {
  $('#modal-title').textContent=title; $('#modal-body').innerHTML=html; $('#modal-actions').replaceChildren();
  const cancel=document.createElement('button');cancel.className='button';cancel.textContent='Cancel';cancel.onclick=()=>$('#modal').close();$('#modal-actions').append(cancel);
  for(const action of actions) {const b=document.createElement('button');b.className=`button ${action.kind||'primary'}`;b.textContent=action.label;b.onclick=async()=>{b.disabled=true;try{await action.run();$('#modal').close();}catch(error){toast(error.message,true);}finally{b.disabled=false;}};$('#modal-actions').append(b);}
  if(!$('#modal').open) $('#modal').showModal();
}
function confirmAction(title,message,action,label='Confirm') {modal(title,`<p>${esc(message)}</p>`,[{label,run:action}]);}

const landscape = `<svg class="hero-art" viewBox="0 0 620 250" preserveAspectRatio="xMidYMax slice" aria-hidden="true"><defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#f4efcf"/><stop offset="1" stop-color="#e3e8d3"/></linearGradient><linearGradient id="hill" x2="0" y2="1"><stop stop-color="#91aa85"/><stop offset="1" stop-color="#6e8c6a"/></linearGradient></defs><rect width="620" height="250" fill="url(#sky)"/><circle cx="474" cy="65" r="30" fill="#fff5d5"/><path d="M20 202 172 47l57 65 47-40 84 90 65-74 158 116" fill="#c5d0b7"/><path d="m106 125 66-78 57 65-37-15-20-23-30 38Z" fill="#f3f1df"/><path d="M0 216 91 140l99 64 111-89 132 94 89-56 98 53v44H0" fill="#a8b99a"/><path d="M0 224c106-57 184 2 278-19 118-28 221-47 342-5v50H0" fill="url(#hill)"/><path d="M0 249c126-38 245-11 331-19 92-8 187-3 289-13v33H0" fill="#597c60"/><path d="M405 199c-34 10 48 15 13 24s-24 15-12 27h71c-73-17-33-22-37-31s-53-9-25-20" fill="#ccdbcf"/><path d="m277 181 38-29 39 29v39h-77Z" fill="#eee6c8"/><path d="m267 183 47-38 50 38-12 3-37-28-37 29Z" fill="#7f7962"/><path d="M294 153v-13h10v21" fill="#a58d6d"/><path d="M289 220v-26h15v26" fill="#84957a"/><path d="M321 189h18v15h-18Z" fill="#d9b973"/><path d="M330 189v15m-9-7h18" stroke="#998e67" fill="none"/><path d="M298 135c-11-8-7-13 0-15s10-8 1-13" stroke="#c9d0b5" fill="none" stroke-width="4" stroke-linecap="round"/><g fill="#52745a"><path d="m507 194 17-45 18 45h-12l14 18h-42l14-18Z"/><path d="m555 199 14-38 15 38h-9l11 15h-34l11-15Z"/><path d="m221 208 13-34 14 34h-9l10 15h-31l10-15Z"/></g><g fill="#365f4b"><path d="m82 231 20-58 22 58h-14l15 19H79l16-19Z"/><path d="m158 234 15-43 16 43h-11l12 16h-35l12-16Z"/><path d="m576 237 23-66 24 66h-16l15 18h-46l16-18Z"/></g><g stroke="#b9caa5" fill="none" opacity=".4"><path d="M15 236c75-16 131-15 196 0m-184-7c65-15 130-12 164-3m287-11c27-4 59-3 84 2"/></g><path d="m349 75 4-2 4 2m-18-11 3-2 3 2" fill="none" stroke="#a5b194"/></svg>`;

function chart(id,values,key,secondary=null) {
  const canvas=$('#'+id);if(!canvas)return;
  const rect=canvas.getBoundingClientRect(),ratio=window.devicePixelRatio||1;
  canvas.width=rect.width*ratio;canvas.height=rect.height*ratio;
  const c=canvas.getContext('2d');c.scale(ratio,ratio);const w=rect.width,h=rect.height;
  c.font='9px Segoe UI';c.fillStyle='#a4ae9a';c.strokeStyle='#e9ede1';c.lineWidth=1;
  const actual=values.filter(x=>x[key]!=null);const max=key==='tps'?20:key.includes('cpu')?100:Math.max(1,...actual.map(x=>x[key]))*1.2;
  for(let i=0;i<4;i++){const y=12+i*(h-37)/3;c.beginPath();c.moveTo(30,y);c.lineTo(w-5,y);c.stroke();c.fillText(number(max*(1-i/3),0),0,y+3);}
  if(!actual.length){c.fillStyle='#9aa78e';c.textAlign='center';c.fillText(key==='tps'?'Tick samples appear after the server starts.':'Waiting for measured samples.',w/2,h/2);return;}
  function line(field,color,scaleMax){let begun=false;c.strokeStyle=color;c.lineWidth=1.8;c.beginPath();values.forEach((v,i)=>{if(v[field]==null){begun=false;return;}const x=31+i*(w-38)/Math.max(1,values.length-1),y=12+(1-Math.min(1,v[field]/scaleMax))*(h-37);if(begun)c.lineTo(x,y);else c.moveTo(x,y);begun=true;});c.stroke();}
  line(key,'#7c9669',max);if(secondary)line(secondary,'#b99a63',max);
  c.textAlign='left';c.fillStyle='#a4ae9a';c.fillText('Earlier',30,h-4);c.textAlign='right';c.fillText('Now',w-5,h-4);
}

function overview() {
  const d=state.overview,m=d.metrics||{},s=d.server,serverCurrent=state.connected&&currentMeasurement({measured_at:d.at,current:true,max_age_seconds:15}),online=serverCurrent&&s.state==='online';
  const tps=liveMetric(m,'tps','tick'),mspt=liveMetric(m,'mspt','tick'),playerCount=serverCurrent?(currentMeasurement(m.freshness?.bridge)?m.players_online:s.state==='offline'?0:null):null;
  const integrity=d.sync.server_integrity;
  const integrityNote=integrity?`${esc(integrity.status)}${integrity.last_verified_at?`<small>Last full check ${when(integrity.last_verified_at)} · ${number(integrity.age_seconds,0)} s ago</small>`:'<small>Waiting for a full background check</small>'}`:'Unavailable';
  const controls=!serverCurrent?button('start','Server status unavailable','','disabled'):d.active_test?`<a class="button primary" href="${esc(d.active_test.url)}">Open live playtest →</a>`:online?button('stop','Ⅱ Stop world')+button('restart','↻ Restart','ghost'):button('start','▷ Start world','primary');
  const warnings=(m.alerts||[]).map(a=>notice(a.message,a.severity==='critical'?'error':'warn')).join('')+(s.warning?notice(s.warning,'warn'):'')+freshnessNotice(m);
  $('#main').innerHTML=header('Welcome home.', 'A little world, beautifully looked after.',button('prism','◇ Open Prism Launcher'))+warnings+
    `<section class="hero"><div class="hero-copy">${pill(`< ${serverCurrent?s.state.toUpperCase():'UNAVAILABLE'} >`,online?'good':'')}<h2>${online?'Your next adventure is waiting.':'A place to call ours.'}</h2><p>${online?'The world is awake. Find a quiet meadow, follow the river, or take the long way home.':'Mountains to wander. A cottage to come home to. Start your shared world when you’re ready.'}</p><div class="button-row">${controls}${button('goto-console','View console','ghost')}</div></div>${landscape}</section>`+
    `<div class="metric-grid">${metric('SERVER TICK RATE',number(tps),tps==null?'':'TPS',`${tps==null?'Unavailable':`Measured MSPT · ${number(mspt)} ms`} · ${esc(measurementLabel(m.freshness?.tick))}`)}${metric('JAVA PROCESS MEMORY',bytes(liveMetric(m,'server_rss')),'',esc(measurementLabel(m.freshness?.snapshot)),'▱')}${metric('PLAYERS ONLINE',number(playerCount,0),'',playerCount==null?'Presence unknown · fresh bridge telemetry required':`Maximum · ${s.status?.players?.max??2}`,'♧')}${metric('WORLD STORAGE',bytes(d.storage.breakdown.categories.find(x=>x.key==='world')?.bytes??null),'',d.storage.breakdown.measured_at?`Measured ${when(d.storage.breakdown.measured_at)}`:'Collecting first measurement…','◇')}</div>`+
    `<div class="grid-two">${card('A healthy little world',`<canvas id="overview-chart" class="chart" role="img" aria-label="Measured server TPS over time"></canvas><div class="chart-legend"><span>Server TPS · actual NeoForge readings</span></div>`,pill('HISTORY'))}${card('At a glance',row('Minecraft',esc(d.pack.minecraft))+row('NeoForge',esc(d.pack.neoforge))+row('Pack release',`<span class="mono">${esc(d.pack.version)}</span>`)+row('Mod file check',integrityNote)+row('Uptime',duration(s.uptime_seconds))+row('View / simulation',`${esc(d.world.view_distance)} / ${esc(d.world.simulation_distance)} chunks`)+row('Latest backup',when(d.last_backup?.created)))}</div>`+
    `<div class="grid-equal">${card('Just the two of you',Object.entries(d.sync.players).map(([name,p])=>`<div class="player-card"><div class="player-avatar">${name==='KG'?'KG':'S'}</div><div class="player-main"><strong>${name}</strong><small>${esc(p.message)}</small></div>${pill(p.state,p.state==='reported match'?'good':'')}</div>`).join(''),button('goto-players','Manage access →','ghost small'))}${card('Room to grow',row('Project files',bytes(d.storage.project_bytes))+row('Project budget',bytes(d.storage.project_budget))+d.storage.drives.map(x=>row(`${x.drive} free`,`${bytes(x.free)} ${x.low?pill('LOW','error'):''}`)).join('')+`<p class="subtle">Both drives keep a separate 30 GiB reserve.</p>`,button('goto-storage','View storage →','ghost small'))}</div>`+
    `<div class="section-label">LITTLE THINGS THAT KEEP IT RUNNING</div><div class="quick-actions">${[['backup','↶','Create a backup','Save a safe little snapshot'],['health','✓','Check world health','See what needs attention'],['diagnostics','⌁','Performance report','Export real measurements'],['goto-mods','◇','Find a new mod','Stage, review, then deploy']].map(([a,i,t,n])=>`<button class="quick-action" data-action="${a}"><span class="action-icon">${i}</span><span><b>${t}</b><small>${n}</small></span></button>`).join('')}</div>`;
  chart('overview-chart',state.history,'tps');scheduleLiveExpiry();
}

function storagePage(data) {
  const b=data.breakdown;
  if(!b.measured_at){
    $('#main').innerHTML=header('A little room to grow.','Measuring the world, caches, backups and temporary files.')+notice(b.scan_error||'The first inventory is running in the background. Measured sizes will appear here automatically.',b.scan_error?'warn':'')+card('Your drives',data.drives.map(d=>row(`${d.drive} free`,bytes(d.free))).join(''));
    return;
  }
  $('#main').innerHTML=header('A little room to grow.','Every world, cache, backup and temporary file, measured from disk.',button('refresh-storage','↻ Refresh now'))+
    (b.scan_error?notice('The latest scan could not finish: '+b.scan_error+'. The measurements below retain their original timestamp.','warn'):'')+
    (!b.complete?notice('Some files changed during the scan or could not be read. The next sample will refresh them. See measurement details below.','warn'):'')+
    `<div class="grid-two">${card('The whole project',`<div class="storage-summary"><div><div class="storage-number">${bytes(b.bytes)}</div><p class="subtle">File contents · ${number(b.files,0)} files</p></div><div class="storage-detail">${bytes(b.allocated_bytes)} allocated on disk<br>${bytes(data.project_budget)} project budget<br>Scanned ${when(b.measured_at)} · ${number(b.scan_ms)} ms</div></div><progress value="${b.bytes}" max="${data.project_budget}" aria-label="Project storage used"></progress><div class="storage-rows">${b.categories.map(x=>`<div class="info-row"><div>${esc(x.label)}<small>${number(x.files,0)} files · ${esc(x.key)}</small></div><progress value="${x.bytes}" max="${Math.max(1,b.bytes)}" aria-label="${esc(x.label)} share of project"></progress><div>${bytes(x.bytes)}<small>${bytes(x.allocated_bytes)} allocated</small></div></div>`).join('')}</div>`)}${card('Your drives',data.drives.map(d=>`<div class="drive"><div class="drive-head"><strong>${esc(d.drive)}</strong>${pill(d.low?'RESERVE AT RISK':'RESERVE PROTECTED',d.low?'error':'good')}</div><div class="storage-number">${bytes(d.free)} <small>free</small></div><progress value="${d.used}" max="${d.total}" aria-label="Drive ${esc(d.drive)} used"></progress><small>${bytes(d.used)} used of ${bytes(d.total)} · 30 GiB reserve</small></div>`).join('')+`<p class="subtle">${esc(data.coverage)}</p>`)}</div>`+
    (data.associated?card('Source & shared launcher storage',`<div class="storage-rows">${data.associated.rows.map(x=>`<div class="info-row"><div>${esc(x.label)}<small>${esc(x.path)}${x.shared?' · shared with other packs':''}</small></div><strong>${bytes(x.bytes)}<small>${number(x.files,0)} files${x.complete?'':' · partial scan'}</small></strong></div>`).join('')}</div><p class="subtle">${esc(data.associated.note)} Scanned ${when(data.associated.measured_at)} · refreshed every ${data.associated.refresh_seconds} seconds.</p>`):'')+
    card('Measured, not estimated',`<p class="subtle">${esc(b.note)} Refreshed every ${b.refresh_seconds} seconds. Downloads and managed generation also run the host reserve guard before writing.</p>${b.issues.length?`<pre>${esc(b.issues.join('\n'))}</pre>`:''}`);
}

function chunkDiagnostics(measurement) {
  const data=measurement.chunk_diagnostics;
  if(!data)return card('Chunks & background simulation',empty('Start the server with the current Control Bridge to inspect loaded chunks and their ticket sources.'));
  if(data.unavailable)return card('Chunks & background simulation',notice(data.unavailable,'warn'));
  if(!currentMeasurement(measurement.freshness?.bridge)||!currentMeasurement(measurement.freshness?.chunk_diagnostics))return card('Chunks & background simulation',notice('Current chunk diagnostics are unavailable. '+measurementLabel(measurement.freshness?.chunk_diagnostics),'warn'));
  const age=Math.max(0,Math.round((Date.now()-Date.parse(data.at))/1000));
  const dimensions=Object.entries(data.dimensions||{});
  const tables=dimensions.map(([name,value])=>{
    const details=value.details||{},partial=details.truncated?'≥ ':'';
    return `<details class="chunk-dimension" open><summary><strong>${esc(name)}</strong> · ${number(value.visible_holders,0)} holders</summary>`+
      `<div class="table-scroll"><table><thead><tr><th>Full chunks</th><th>Block-ready holders</th><th>Entity-ready holders</th><th>Pending unloads</th><th>Saved vanilla forced chunks</th></tr></thead><tbody><tr>`+
      `<td>${partial}${number(value.full_chunks,0)}</td><td>${partial}${number(value.block_ticking,0)}</td><td>${partial}${number(value.entity_ticking,0)}</td><td>${number(value.pending_unloads,0)}</td><td>${number(value.vanilla_forced_chunks,0)}</td></tr></tbody></table></div>`+
      `<p class="subtle">${number(value.ticket_positions,0)} direct ticket positions · ${number(value.holders_examined,0)} holders examined · ${number(details.measurement_ms,2)} ms diagnostic cost${details.truncated?' · Bounded sample: ticking totals and ticket details may be partial.':''}</p>`+
      idleSimulationRows(measurement.dimensions?.[name]?.idle_simulation,currentMeasurement(measurement.freshness?.bridge),name)+
      ((details.sources||[]).length?`<div class="table-scroll"><table><thead><tr><th>Ticket source</th><th>Direct tickets</th><th>Example chunk positions</th></tr></thead><tbody>${details.sources.map(source=>`<tr><td><code>${esc(source.type)}</code></td><td>${number(source.tickets,0)}</td><td>${source.examples.map(example=>`<span title="${esc(example.description)}">${number(example.chunk_x,0)}, ${number(example.chunk_z,0)} · level ${number(example.level,0)}</span>`).join('<br>')}</td></tr>`).join('')}</tbody></table></div>`:'<p class="subtle">No direct tickets in this dimension.</p>')+
      `<details><summary>NeoForge mod-owned forced chunks</summary>${details.mod_owners?.unavailable?notice(details.mod_owners.unavailable,'warn'):(details.mod_owners?.owners||[]).length?`<div class="table-scroll"><table><thead><tr><th>Controller</th><th>Owner</th><th>Requested chunks</th></tr></thead><tbody>${details.mod_owners.owners.map(owner=>`<tr><td>${esc(owner.controller)}</td><td>${esc(owner.kind)} · ${esc(owner.owner)}</td><td>${number(owner.chunks,0)} · ${owner.ticking?'ticking':'loaded'}</td></tr>`).join('')}</tbody></table></div>`:'<p class="subtle">No persistent NeoForge mod tickets recorded.</p>'}${details.mod_owners?.truncated?'<p class="subtle">Owner details are partial because the diagnostic budget was reached.</p>':''}</details>`+
      `<details><summary>Holder ticket levels</summary><p class="subtle">${Object.entries(details.ticket_levels||{}).map(([level,count])=>`Level ${esc(level)}: ${number(count,0)}`).join(' · ')}</p></details></details>`;
  }).join('');
  return card('Chunks & background simulation',`<p class="subtle">Measured ${esc(new Date(data.at).toLocaleTimeString())} · ${age} seconds ago · refreshed every 30 seconds · spawn radius ${number(data.spawn_chunk_radius,0)}. Visible holders include chunks preparing to load or unload; they are not all simulating.</p>`+tables+`<p class="subtle">${esc(data.source)} These diagnostics only inspect existing server state.</p>`,`<a class="button small" href="/api/diagnostics/chunks" target="_blank" rel="noopener">View diagnostics JSON</a>`);
}

function performance() {
  const m=state.overview.metrics||{};
  const tick=key=>liveMetric(m,key,'tick'),bridge=key=>liveMetric(m,key,'bridge');
  $('#main').innerHTML=header('Keep the world feeling effortless.','Measured host and Java-process data. Stored history uses one point per minute.',`<a class="button" href="/api/export/metrics.csv">↓ Export CSV</a>${button('profile','Sample with spark','primary')}`)+freshnessNotice(m)+
    `<div class="metric-grid">${metric('MEASURED TPS',number(tick('tps')),'TPS',esc(measurementLabel(m.freshness?.tick)))}${metric('MEAN TICK TIME',number(tick('mspt')),'ms','50 ms is the 20 TPS tick budget')}${metric('SERVER CPU',number(liveMetric(m,'server_cpu')),'%','Normalized to total host CPU capacity')}${metric('HOST AVAILABLE RAM',bytes(liveMetric(m,'host_memory_available')),'',esc(measurementLabel(m.freshness?.snapshot)))}</div>`+
    `<div class="grid-equal">${card('Server tick rate','<canvas id="tps-chart" class="chart" role="img" aria-label="Server TPS history"></canvas>')}${card('Host & server CPU','<canvas id="cpu-chart" class="chart" role="img" aria-label="Host and server CPU history"></canvas><div class="chart-legend"><span>Host</span><span>Server</span></div>')}</div>`+
    ((m.clients||[]).length?`<div class="grid-equal">${m.clients.map(client=>{const current=currentMeasurement(client.freshness),processCurrent=currentMeasurement(client.process_freshness);return card(`${esc(client.player||'Local')} · Minecraft client`,row('Context',current?esc(client.in_world?'In world':client.screen):'Unavailable; client presence is unconfirmed')+row('Client FPS',number(current?client.fps:null,0))+row('Java RSS',bytes(processCurrent?client.rss:null))+row('JVM heap',current?`${bytes(client.heap_used)} / ${bytes(client.heap_max)}`:'Unavailable')+row('Client CPU',`${number(processCurrent?client.cpu_percent_host:null)}% of host`)+row('Frame intervals',current&&client.frame_interval_ms?`${number(client.frame_interval_ms.mean,2)} ms mean · ${number(client.frame_interval_ms.p95,2)} ms p95`:'Unavailable')+row('Camera / focus',current?`${esc(client.camera)} · ${client.focused?'focused':'background'}`:'Unconfirmed')+`<p class="subtle">${esc(measurementLabel(client.freshness))}. Frame intervals include frame pacing; they are not GPU execution times.${client.integration_error?' '+esc(client.integration_error):''}</p>`);}).join('')}</div>`:'')+
    `<div class="grid-equal">${card('Java & world telemetry',row('Java RSS',bytes(liveMetric(m,'server_rss')))+row('JVM heap usage',bridge('heap_used')==null?'Unavailable':`${bytes(bridge('heap_used'))} / ${bytes(bridge('heap_max'))}`)+row('Latest GC pause',liveMetric(m,'gc_pause_ms')==null?'Unavailable':`${number(liveMetric(m,'gc_pause_ms'))} ms`)+row('Visible chunk holders',number(bridge('loaded_chunks'),0))+row('Entity counts',number(bridge('entities'),0))+row('Dimensions',bridge('dimensions')?Object.entries(bridge('dimensions')).map(([name,v])=>`${esc(name)}: ${number(v.loaded_chunks,0)} holders · ${number(v.entities,0)} entities`).join('<br>'):'Unavailable')+`<p class="subtle">${esc(measurementLabel(m.freshness?.bridge))}${m.bridge_error?' · '+esc(m.bridge_error):''}</p>`)}${card('A useful next step',`<p class="details">A one-minute spark sample helps explain expensive ticks, entity simulation and chunk generation. The console will show spark’s report link. Review it before sharing.</p>${button('profile','Start 60-second sample','primary')}<p class="subtle">FPS, frametimes and GPU load require a real client benchmark. They are never inferred from server TPS.</p>`)}</div>`+chunkDiagnostics(m);
  chart('tps-chart',state.history,'tps');chart('cpu-chart',state.history,'host_cpu','server_cpu');scheduleLiveExpiry();
}

async function modsPage() {
  const view=state.renderGeneration,tab=state.tab;
  let d=await api('/api/mods');
  if(!viewCurrent('mods',view)||state.tab!==tab)return;
  const candidate=state.tab==='candidate';
  if(candidate)d={...d,...d.candidate};
  $('#main').innerHTML=header('Make this world your own.','One manifest. Exact versions. Every change gets a safe place to land.',pill(`${d.mods.length} PINNED FILES`))+
    `<div class="tabs"><button data-mod-tab="installed" class="${state.tab==='installed'?'active':''}">Installed inventory</button><button data-mod-tab="candidate" class="${state.tab==='candidate'?'active':''}">Build candidate</button><button data-mod-tab="search" class="${state.tab==='search'?'active':''}">Find a mod</button><button data-mod-tab="proposals" class="${state.tab==='proposals'?'active':''}">Staged changes</button></div><div id="mod-content"></div>`;
  if(state.tab==='installed'||candidate) {
    $('#mod-content').innerHTML=(candidate?notice('This is the current complete build candidate. The installed release is shown separately; gameplay acceptance is pending.','warn'):'')+`<div class="toolbar"><input id="inventory-filter" placeholder="Filter mods, versions or feature groups…" aria-label="Filter inventory">${pill(esc(d.version))}</div><div class="card table-wrap"><table><thead><tr><th>MOD</th><th>EXACT VERSION</th><th>INSTALLATION</th><th>VALIDATION</th><th></th></tr></thead><tbody>${d.mods.map(m=>`<tr data-inventory-name="${esc((m.name+' '+m.version+' '+(m.request||'')).toLowerCase())}"><td class="name">${esc(m.name)}<small>${esc(m.request||'Required dependency')}${m.optional?' · Optional':''}</small></td><td class="mono version">${esc(m.version)}</td><td>${pill(m.side)}</td><td>${pill(m.validation?.runtime==='pass'?'Runtime tested':'Runtime pending',m.validation?.runtime==='pass'?'good':'warn')}</td><td><div class="button-row">${m.provider&&m.provider!=='modrinth'?`<a class="button small" href="${esc(m.source)}" target="_blank" rel="noopener">Author source</a>`:button('mod-versions','Versions','small',`data-project="${esc(m.slug)}"`)}${candidate?'':button('mod-remove','Remove','ghost small',`data-project="${esc(m.slug)}" data-name="${esc(m.name)}"`)}</div></td></tr>`).join('')}</tbody></table></div>`;
  } else if(state.tab==='search') {
    $('#mod-content').innerHTML=`<form id="mod-search" class="toolbar"><input name="q" placeholder="Search Modrinth or paste a project URL…" aria-label="Find a mod" required><button class="button primary">Search mods</button></form><div id="search-results" class="card">${empty('Find something lovely. We’ll check the loader, version, dependencies and installation side.')}</div><details class="card"><summary>CurseForge lookup</summary><p class="subtle">Uses an authorized host API key. Restricted downloads and distribution rules are respected.</p><form id="curseforge-search" class="toolbar"><input name="id" placeholder="Numeric CurseForge project ID" required><button class="button">Look up</button></form><div id="curseforge-result"></div></details>`;
    const manual=await api('/api/mods/manual');if(!viewCurrent('mods',view)||state.tab!==tab)return;
    if(manual.length)$('#mod-content').insertAdjacentHTML('beforeend',card('Author downloads',`<p class="subtle">Download the exact file to your Downloads folder, then import it here. Every import checks its pinned size and hash. This prepares the candidate cache.</p>${manual.map(m=>`<div class="result-card"><h3>${esc(m.name)} · ${esc(m.version)}</h3><p class="mono">${esc(m.filename)}</p><p class="subtle">${esc(m.license.id)} · ${bytes(m.size)}</p><div class="button-row"><a class="button" href="${esc(m.source)}" target="_blank" rel="noopener">Open author file</a>${button('manual-import',m.cached?'Recheck download':'Import downloaded file','primary',`data-slug="${esc(m.slug)}"`)}${pill(m.cached?'Cached':'Download needed',m.cached?'good':'warn')}</div></div>`).join('')}`));
  } else {
    const proposals=await api('/api/proposals');if(!viewCurrent('mods',view)||state.tab!==tab)return;
    $('#mod-content').innerHTML=notice('A staged change downloads and checks files in isolation. Production deployment requires review, exact-candidate runtime acceptance, a verified backup and a matching published client release.')+card('A safe place for new ideas',proposals.length?proposals.map(p=>`<div class="result-card"><div class="result-head"><div><h3>${esc(p.version)}</h3><span class="subtle">${when(p.created)} · ${p.changes.length} changes</span></div>${pill(p.status,p.static_errors.length?'error':'warn')}</div><p>${p.changes.map(c=>`${esc(c.name)} · ${esc(c.from||'new')} → ${esc(c.to||'removed')}`).join('<br>')}</p><div class="button-row">${button('proposal-review','Review change','small',`data-id="${p.id}"`)}${button('proposal-rollback','Roll back','ghost small',`data-id="${p.id}" data-version="${esc(p.version)}"`)}</div></div>`).join(''):empty('No changes waiting. Your active manifest has stayed exactly where you left it.'));
  }
}

async function settingsPage() {
  const view=state.renderGeneration;
  const d=await api('/api/settings');
  if(!viewCurrent('settings',view))return;
  function settingsForm(scope,title) {return card(title,`<form class="settings-form" data-scope="${scope}"><div class="field-grid">${d.fields.filter(f=>f.scope===scope).map(f=>`<div class="field"><label for="setting-${f.key}">${esc(f.label)} ${pill(f.change,f.change.startsWith('Dangerous')?'warn':'')}</label>${f.type==='boolean'?`<label class="check-label"><input id="setting-${f.key}" name="${f.key}" type="checkbox" ${f.current?'checked':''}>Enabled</label>`:f.type==='enum'?`<select id="setting-${f.key}" name="${f.key}">${f.values.map(v=>`<option ${v===f.current?'selected':''}>${esc(v)}</option>`).join('')}</select>`:`<input id="setting-${f.key}" name="${f.key}" type="${f.type==='integer'?'number':f.key==='level-seed'?'password':'text'}" ${f.min!=null?`min="${f.min}" max="${f.max}"`:''} value="${esc(f.current)}">`}<small>${esc(f.description)}<br>Recommended: ${esc(String(f.recommended??'default'))}</small></div>`).join('')}</div><button class="button primary">Save ${scope==='server'?'world':'Control Room'} settings</button></form>`);}
  $('#main').innerHTML=header('A world that feels just right.','Clear settings, thoughtful defaults and a way back to your previous values.')+
    notice('Stop the world before changing restart-required settings. Client-only weather, shaders and LOD rendering are managed through graphics profiles on each player’s computer.')+
    settingsForm('server','World & simulation')+`<div class="section-label">CONTROL ROOM</div>`+settingsForm('app','Memory, backups & monitoring')+
    `<div class="section-label">MOD INTEGRATION</div>`+card('Weather, seasons, Create & distant terrain',d.mods.length?`<div class="field-grid">${d.mods.map(m=>`<form class="mod-setting-form field" data-id="${esc(m.id)}" data-expected="${esc(m.expected||'')}" data-type="${m.type}"><label for="mod-setting-${esc(m.id)}">${esc(m.label)}</label>${m.available?(m.type==='boolean'?`<label class="check-label"><input id="mod-setting-${esc(m.id)}" name="value" type="checkbox" ${m.current?'checked':''}>Enabled</label>`:`<input id="mod-setting-${esc(m.id)}" name="value" type="number" step="${m.type==='integer'?'1':'any'}" min="${m.min}" max="${m.max}" value="${esc(m.current)}">`)+`<small>${esc(m.description||'')} · Requires restart</small><button class="button small">Save setting</button>`:`<small>${esc(m.reason)}</small>`}</form>`).join('')}</div>`:`<p class="subtle">Generated settings will appear after the first successful mod load. No guessed configuration keys are written.</p>`)+
    `<div class="section-label">ADVANCED SETTINGS</div>`+card('Configuration editor',`<form id="raw-open" class="toolbar"><select name="path" id="config-files" aria-label="Configuration file"><option value="server.properties">server.properties</option></select><button class="button">Open file</button></form><div id="raw-editor"></div><p class="subtle">Syntax checks, a reviewable diff, optimistic concurrency and a prior-value snapshot protect every save. Mod-specific values still need their upstream schema.</p>`)+
    card('Previous configurations',`<div id="config-history">Loading history…</div><p class="subtle">${esc(d.gc)}</p>`);
  const files=await api('/api/config/files');if(!viewCurrent('settings',view))return;$('#config-files').insertAdjacentHTML('beforeend',files.map(f=>`<option>${esc(f)}</option>`).join(''));
  const history=await api('/api/config/history');if(!viewCurrent('settings',view))return;$('#config-history').innerHTML=history.length?history.slice(0,12).map(h=>row(esc(h.path),button('config-restore',`Restore ${when(h.created)}`,'small',`data-id="${esc(h.id)}"`))).join(''):empty('Previous values will be saved here whenever you change a configuration.');
}

async function playersPage() {
  const view=state.renderGeneration;
  const d=await api('/api/players');
  if(!viewCurrent('players',view))return;
  $('#main').innerHTML=header('Good company only.','An editable whitelist, verified Java profiles and clear player permissions.',pill('ONLINE AUTHENTICATION ON','good'))+
    `<div class="grid-two">${card('Who’s welcome here',`<div id="whitelist-list">${whitelistHtml(d)}</div><form id="whitelist-add" class="toolbar"><input name="name" placeholder="Minecraft Java username" pattern="[A-Za-z0-9_]{1,16}" aria-label="Player to add to whitelist" required><button class="button primary">＋ Add to whitelist</button></form><p class="subtle">Names are verified with Mojang. Changes work while the server is online or offline; existing access is backed up.</p>`)}${card('Who’s here right now',d.online?row('Players online',`${d.online.online} / ${d.online.max}`)+(d.online.sample||[]).map(p=>row(p.name,button('player-kick','Kick','small',`data-name="${esc(p.name)}"`))).join(''):empty('Player presence is unknown until fresh server telemetry arrives. Last-known positions do not imply a disconnect.'))}</div>`+
    card('Little arrivals & goodbyes',d.events.length?d.events.slice().reverse().map(e=>row(`${e.name} ${e.event}`,when(e.at))).join(''):empty('Join and leave events will appear once players visit.'));
}
function whitelistHtml(d) {const members=d.members||d.whitelist;return members.length?members.map(p=>`<button class="player-card player-open" data-action="player-details" data-name="${esc(p.name)}"><span class="player-avatar">${esc(p.name.slice(0,2).toUpperCase())}</span><span class="player-main"><strong>${esc(p.name)}</strong><small>${p.operator_level?'Operator · level '+p.operator_level:'Member'} · ${p.whitelisted?'Whitelisted':'Not whitelisted'} · ${p.online===true?'Online':p.online===false?'Offline':'Presence unknown'}</small></span><span class="player-chevron" aria-hidden="true">›</span></button>`).join(''):empty('No players on the whitelist yet. Add KG and Sera below.');}

function playerLiveHtml(p) {
  const l=p.location;
  return `<div class="profile-status">${pill(p.online===true?'ONLINE':p.online===false?'OFFLINE':'PRESENCE UNKNOWN',p.online===true?'good':p.online===false?'':'warn')}${pill(p.location_state==='live'?'LIVE':l?'LAST KNOWN':'UNAVAILABLE',p.location_state==='live'?'good':'')}</div>`+
    (l?row('Dimension',`<code>${esc(l.dimension)}</code>`)+`<div class="coordinate-grid">${['x','y','z'].map(k=>`<div><small>${k.toUpperCase()}</small><strong>${number(l[k],1)}</strong></div>`).join('')}</div>`+row(p.location_state==='live'?'Measured':'Last measured',when(l.at))+row('Health / food',`${number(l.health,1)} / ${number(l.food,0)}`)+row('XP / game mode',`${number(l.xp_level,0)} · ${esc(l.game_mode)}`)+(l.map?`<canvas id="player-map" width="320" height="320" aria-label="Actual loaded surface terrain around ${esc(p.name)}, north is up"></canvas><p class="subtle">${p.location_state==='live'?'Surface map':'Last-known surface map'} · 128 × 128 blocks · north ↑<br>${esc(l.map.source)} Measured ${when(l.map.at)}. Checkerboard areas are unavailable. Caves and the Nether roof can hide terrain at the player’s height.</p>`:notice('Waiting for a surface sample of loaded chunks. Coordinates update independently.')):empty('A fresh Control Bridge sample is needed for current coordinates. Missing telemetry does not confirm that this player disconnected.'));
}
function drawPlayerMap(p) {
  const canvas=$('#player-map'),l=p.location,t=l?.map;if(!canvas||!t)return;
  const ctx=canvas.getContext('2d'),scale=10;ctx.imageSmoothingEnabled=false;
  for(let i=0;i<t.pixels.length;i++){const color=t.pixels[i];ctx.fillStyle=color<0?((i%32+Math.floor(i/32))%2?'#e4e8de':'#f1f2ec'):'#'+color.toString(16).padStart(6,'0');ctx.fillRect(i%32*scale,Math.floor(i/32)*scale,scale,scale);}
  ctx.strokeStyle='#ffffff33';ctx.lineWidth=1;for(let c=0;c<=32;c+=4){ctx.beginPath();ctx.moveTo(c*scale,0);ctx.lineTo(c*scale,320);ctx.moveTo(0,c*scale);ctx.lineTo(320,c*scale);ctx.stroke();}
  const x=(l.x-t.origin_x)/t.blocks_per_pixel*scale,z=(l.z-t.origin_z)/t.blocks_per_pixel*scale;
  if(l.dimension===t.dimension&&x>=0&&z>=0&&x<=320&&z<=320){ctx.save();ctx.translate(x,z);ctx.rotate((l.yaw+180)*Math.PI/180);ctx.beginPath();ctx.moveTo(0,-10);ctx.lineTo(7,8);ctx.lineTo(0,4);ctx.lineTo(-7,8);ctx.closePath();ctx.fillStyle='#183d32';ctx.strokeStyle='#fff9e9';ctx.lineWidth=2;ctx.fill();ctx.stroke();ctx.restore();}
  ctx.fillStyle='#fff9e9';ctx.fillRect(7,5,21,24);ctx.fillStyle='#183d32';ctx.font='bold 14px Segoe UI';ctx.fillText('N',12,23);
}
async function playerDetails(name) {
  const response=await api('/api/player/details?name='+encodeURIComponent(name)),p={...response,received_at:Date.now()};state.playerDetails=name;state.playerSnapshot=p;
  modal(p.name,`<p class="subtle mono">${esc(p.uuid)}</p><div class="player-detail-grid"><section><h3>Access & permissions</h3><form id="player-permissions" data-name="${esc(p.name)}"><div class="field"><label for="player-permission-level">User / operator level</label><select id="player-permission-level" name="level">${[[0,'Member · no operator permissions'],[1,'Operator 1 · bypass spawn protection'],[2,'Operator 2 · gameplay commands'],[3,'Operator 3 · player administration'],[4,'Operator 4 · full server control']].map(([v,label])=>`<option value="${v}" ${p.operator_level===v?'selected':''}>${label}</option>`).join('')}</select></div><label class="check-label"><input type="checkbox" name="bypass" ${p.bypass_player_limit?'checked':''}>Bypass the player limit (operators only)</label><p class="subtle">Permission changes are saved to the real operator list. Level 4 includes server stop commands. Prior values are backed up.</p><button class="button primary">Review permission change</button></form><div class="button-row profile-actions">${button(p.whitelisted?'player-whitelist-remove':'player-whitelist-add',p.whitelisted?'Remove from whitelist':'Add to whitelist','small',`data-name="${esc(p.name)}"`)}${p.online?button('player-kick','Kick player','danger small',`data-name="${esc(p.name)}"`):''}</div><h3 class="profile-subheading">Player settings</h3><form id="player-game-settings" data-name="${esc(p.name)}"><div class="field"><label for="player-game-mode">Game mode</label><select id="player-game-mode" name="mode" ${p.online?'':'disabled'}>${['survival','creative','adventure','spectator'].map(v=>`<option ${p.location?.game_mode===v?'selected':''}>${v}</option>`).join('')}</select></div><button class="button small" ${p.online?'':'disabled'}>Review game mode change</button></form><form id="player-xp-settings" data-name="${esc(p.name)}"><div class="field"><label for="player-xp-level">Experience level</label><input id="player-xp-level" name="level" type="number" min="0" max="1000" value="${p.location?.xp_level??0}" ${p.online?'':'disabled'}></div><button class="button small" ${p.online?'':'disabled'}>Review XP change</button></form><p class="subtle">Game settings require the player to be online. Native Java permission levels are used; visitor/build restrictions need a claim system or spectator mode.</p></section><section><h3>Where they are</h3><div id="player-live">${playerLiveHtml(p)}</div></section></div>`);
  renderPlayerSnapshot();
}
let playerExpiry;
function renderPlayerSnapshot(){
  clearTimeout(playerExpiry);if(!$('#modal').open||!$('#player-live')||!state.playerSnapshot)return;
  const p=playerView(state.playerSnapshot);$('#player-live').innerHTML=playerLiveHtml(p);drawPlayerMap(p);
  $$('#player-game-settings input,#player-game-settings select,#player-game-settings button,#player-xp-settings input,#player-xp-settings button').forEach(input=>input.disabled=p.online!==true);
  const end=Math.min(state.playerSnapshot.received_at+15000,state.playerSnapshot.location_state==='live'?measurementMillis(state.playerSnapshot.location?.at)+15000:Infinity);
  if(Number.isFinite(end)&&end>=Date.now())playerExpiry=setTimeout(renderPlayerSnapshot,end-Date.now()+100);
}
async function refreshPlayerDetails(){if(!state.playerDetails||!$('#modal').open||!$('#player-live'))return;const name=state.playerDetails,p=await api('/api/player/details?name='+encodeURIComponent(name));if(!$('#modal').open||!$('#player-live')||state.playerDetails!==name)return;state.playerSnapshot={...p,received_at:Date.now()};renderPlayerSnapshot();}

async function consolePage() {
  $('#main').innerHTML=header('Listen to the world.','Live server output, useful diagnostics and a safe command console.',`<a class="button" href="/api/export/diagnostics.zip">↓ Diagnostic bundle</a>`)+
    `<div class="toolbar"><input id="log-query" placeholder="Search console output…" aria-label="Search logs"><select id="log-level" aria-label="Log severity"><option value="all">All messages</option><option value="warning">Warnings</option><option value="error">Errors</option></select></div><div id="console-log" class="log" role="log" aria-label="Server console">Waiting for server output…</div><form id="console-command" class="command-form"><input name="command" placeholder="Try list, neoforge tps, or say Welcome home" aria-label="Server command" required><button class="button primary">Send command</button></form><p class="subtle">Player-access and world-setting commands require confirmation. Commands outside the safe allowlist stay in the local server console.</p><div class="section-label">IF SOMETHING GOES WRONG</div>${card('Crash reports','<div id="crash-list">Loading…</div>')}`;
  await refreshConsole();const crashes=await api('/api/crashes');if(state.page!=='console'||!$('#crash-list'))return;$('#crash-list').innerHTML=crashes.length?crashes.map(c=>row(esc(c.name),button('crash-read','Read report','small',`data-name="${esc(c.name)}"`))).join(''):empty('No crash reports found. A quiet console is a good thing.');
}
async function refreshConsole() {const node=$('#console-log');if(!node)return;const follow=node.scrollHeight-node.scrollTop-node.clientHeight<60;const logs=await api(`/api/console?query=${encodeURIComponent($('#log-query').value)}&level=${$('#log-level').value}`);node.innerHTML=logs.length?logs.map(l=>`<span class="${l.level}">${esc(new Date(l.at).toLocaleTimeString())} ${esc(l.text)}</span>`).join('\n'):'No matching console messages yet.';if(follow)node.scrollTop=node.scrollHeight;}

async function backupsPage() {
  const view=state.renderGeneration;
  const d=await api('/api/backups');
  if(!viewCurrent('backups',view))return;
  state.backupsDirty=false;
  $('#main').innerHTML=header('Keep the memories safe.','Verified snapshots, clear history and careful restores.',button('backup','＋ Create backup','primary'))+
    notice('Backups use a controlled stop so Minecraft can flush the world, then resume after verification. Restore requires the server to be offline and preserves the current world in a separate safety directory.')+
    card('Your world, through time',d.length?`<div class="table-wrap"><table><thead><tr><th>CREATED</th><th>ARCHIVE SIZE</th><th>WORLD & CONFIG FILES</th><th>INTEGRITY</th><th></th></tr></thead><tbody>${d.map(b=>`<tr><td class="name">${when(b.created)}<small class="mono">${esc(b.id)}</small></td><td>${bytes(b.bytes)}</td><td>${number(b.files,0)} files · ${bytes(b.source_bytes)}</td><td>${pill(b.integrity,b.integrity==='verified'?'good':'warn')}<small>${b.checked_at?'Last check':'At creation'} ${when(b.checked_at||b.created)}</small></td><td><div class="button-row">${button('backup-verify','Verify','small',`data-id="${b.id}"`)}${button('backup-restore','Restore','danger small',`data-id="${b.id}"`)}</div></td></tr>`).join('')}</tbody></table></div>`:empty('Your first backup will appear after Minecraft has created and saved a world.'));
}

async function connectivityPage() {
  const view=state.renderGeneration;
  const d=await api('/api/connectivity');
  if(!viewCurrent('connectivity',view))return;
  $('#main').innerHTML=header('The long distance, made shorter.','A private world for you, wherever the two of you happen to be.')+
    `<div class="grid-equal">${card('On this laptop',row('Minecraft address',`<code>${esc(d.local_address)}</code>`)+row('Control Room',`<code>${esc(d.dashboard)}</code>`)+row('Authentication',pill('ONLINE MODE','good'))+row('Whitelist',pill('ENFORCED','good')))}${card('Sera’s way home',row('Playit agent',esc(d.playit.state))+row('External connection',esc(d.external_connection))+`<form id="tunnel-address"><div class="field"><label for="join-address">Playit join address</label><input id="join-address" name="address" placeholder="your-tunnel.joinmc.link" value="${esc(d.playit.address||'')}"><small>Owner-supplied address. A configured address is not proof of a working remote connection.</small></div><button class="button primary">Save join address</button></form>`)}</div>`+
    card('Playit, right here',`${row('Windows service',esc(d.playit.service_status||'Unknown'))}${row('Agent version',esc(d.playit.version||'Unknown'))}${row('Linked account',pill(d.playit.linked?'LINKED':'NOT CONFIRMED',d.playit.linked?'good':'warn'))}${row('Active connections',number(d.playit.stats?.active_tcp??0,0)+' TCP · '+number(d.playit.stats?.active_udp??0,0)+' UDP')}${row('Traffic',bytes(d.playit.stats?.bytes_in??0)+' received · '+bytes(d.playit.stats?.bytes_out??0)+' sent')}<div class="button-row">${button('playit-start','Start Playit','primary')}${button('playit-stop','Stop Playit','danger')}${button('playit-refresh','Refresh','')}</div><p class="subtle">${esc(d.playit.management||'')} ${esc(d.playit.ipc_error||d.playit.error||'')}</p>${(d.playit.tunnels||[]).map(t=>`<div class="result-card">${row('Public join address',`<code>${esc(t.display_address)}</code>`)}${row('Local destination',`<code>${esc(t.destination)}</code>`)}${row('Tunnel',pill(t.is_disabled?'DISABLED':'ENABLED',t.is_disabled?'warn':'good'))}${t.destination!==d.local_address?'<p class="subtle">This tunnel targets a different local game port from this dashboard. Check the intended server before sharing it.</p>':''}</div>`).join('')}${(d.playit.notices||[]).map(n=>notice(n,'warn')).join('')}<p class="subtle">Last local agent update: ${when(d.playit.at)}. ${esc(d.playit.remote_join||'')}</p><h3>Recent activity</h3><pre id="playit-logs">${esc((d.playit.logs||[]).map(l=>`${l.at} [${l.level}] ${l.message}`).join('\n')||'Waiting for live Playit activity…')}</pre>`)+
    card('Set up once, then just join',`<ol class="details">${d.instructions.map(i=>`<li>${esc(i)}</li>`).join('')}</ol><p class="subtle">The public Minecraft tunnel must point only at the game port. The dashboard, RCON and monitoring ports stay private.</p>`);
}

async function graphicsPage() {
  const view=state.renderGeneration;
  const data=await api('/api/graphics');
  if(!viewCurrent('graphics',view))return;
  $('#main').innerHTML=header('A world beyond the horizon.','Distant Horizons + SeedGen. Shared content, personal graphics.')+
    notice('These are local client settings. Control Room does not remotely edit Sera’s computer. Both profiles use the same gameplay manifest; shader choices never change the dedicated server’s mod set.')+
    `<div class="grid-equal">${data.profiles.map(p=>`<section class="profile-card"><div class="eyebrow">${esc(p.audience)}</div><h3>${esc(p.name)}</h3><p class="subtle">${esc(p.description)}</p>${Object.entries(p.settings).map(([k,v])=>row(k,esc(v))).join('')}<p class="subtle">${esc(p.validation)}</p></section>`).join('')}</div>`+
    card('Choose your light',`<p class="subtle">Choose a shader in Minecraft → Video Settings → Shader Packs, or select it below for a closed local client. Cost labels describe intended settings; they are not FPS measurements.</p><div class="grid-equal">${(data.shaders||[]).map(s=>`<section class="profile-card"><div class="eyebrow">${esc(s.style)} · ${esc(s.cost)}</div><h3>${esc(s.name)}</h3><p>${esc(s.description)}</p>${row('Pinned version',esc(s.version||'Pending'))}${row('Distant Horizons',pill(s.dh_status==='programs-present'?'PROGRAMS PRESENT':'LIMITED / UNVERIFIED',s.dh_status==='programs-present'?'good':'warn'))}<p class="subtle">${esc(s.dh_note)} ${esc(s.validation)}</p><a href="${esc(s.source)}" target="_blank" rel="noopener noreferrer">Author page ↗</a></section>`).join('')}</div>${data.clients?.length?`<form id="shader-select"><div class="field"><label for="shader-client">Local client</label><select id="shader-client" name="client">${data.clients.map(c=>`<option value="${esc(c.id)}" data-revision="${esc(c.revision||'')}">${esc(c.player)} · ${esc(c.id)} · ${c.enabled?esc(c.shader):'Shaders off'}</option>`).join('')}</select></div><div class="field"><label for="shader-choice">Shader for next launch</label><select id="shader-choice" name="shader"><option value="off">Shaders off</option>${data.shaders.filter(s=>s.pinned&&s.cached).map(s=>`<option value="${esc(s.id)}">${esc(s.name)} ${esc(s.version)}${s.dh_status==='programs-present'?'':' · limited DH support'}</option>`).join('')}</select></div><label class="check"><input type="checkbox" name="allow_lod_limited"> Allow a shader with limited or unverified distant-terrain support</label><button class="button primary">Select for closed client</button></form>`:'<p class="subtle">Imported clients on other computers select shaders in Minecraft. Control Room only edits explicitly owned local test instances.</p>'}`)+
    card('Distant terrain, without the long walk',`<p class="details">SeedGen builds visual terrain representations from compatible world-generation information. These LODs are not full saved Minecraft chunks. The server and clients must carry matching terrain mods and generation settings. The earlier playtest revealed a vanilla fallback; the corrected installation still needs a fresh runtime check.</p><p class="subtle">Dense fog, storms, shaders and moving Sable contraptions have separate acceptance tests. C2ME, Fog and Better Fog are outside the default profile.</p>`);
}

async function compatibilityPage() {
  const view=state.renderGeneration;
  const d=await api('/api/compatibility');
  if(!viewCurrent('compatibility',view))return;
  $('#main').innerHTML=header('Every detail, accounted for.','Requested mods, exact identities, selected versions and the evidence behind each decision.')+
    `<div class="toolbar"><input id="compat-filter" placeholder="Filter requested mods, evidence or status…" aria-label="Filter compatibility report"><span class="subtle">${d.requests.length} requests tracked</span></div>`+
    card('Compatibility inventory',`<div class="table-wrap"><table><thead><tr><th>REQUEST</th><th>DECISION</th><th>VERSION</th><th>EVIDENCE / LIMITATION</th></tr></thead><tbody>${d.requests.map(r=>`<tr data-compat-text="${esc(JSON.stringify(r).toLowerCase())}"><td class="name">${esc(r.name)}<small>${esc(r.group)}</small></td><td>${pill(r.status,r.status.startsWith('Integrated and tested')?'good':r.status.startsWith('Incompatible')?'error':'warn')}</td><td class="mono version">${esc(r.version||'—')}</td><td>${esc(r.reason)}${r.source?`<small><a href="${esc(r.source)}" target="_blank" rel="noopener noreferrer">Upstream evidence ↗</a></small>`:''}</td></tr>`).join('')}</tbody></table></div>`);
}

async function setupPage() {
  const view=state.renderGeneration;
  const d=await api('/api/setup');
  if(!viewCurrent('setup',view))return;
  $('#main').innerHTML=header('A good beginning.','A few things to set up once. Then it’s just Start World.')+
    card('Your installation',row('Data directory',`<code>${esc(d.home)}</code>`)+row('Java',`${esc(d.java_version||'Not found')} ${pill(d.java_21?'JAVA 21 READY':'JAVA 21 REQUIRED',d.java_21?'good':'warn')}`)+row('Pack installed',d.installed?esc(d.installed.pack_version):'Not yet')+row('Minecraft EULA',pill(d.eula_accepted?'ACCEPTED BY OWNER':'AWAITING OWNER',d.eula_accepted?'good':'warn')))+
    card('Let’s get you home',`<div class="setup-step"><span class="step-number">1</span><div><h3>Install the dedicated server</h3><p>Downloads the pinned NeoForge and mod files, verifies their hashes and separates client-only mods. Existing worlds and settings are preserved.</p>${button('install','Install server','primary')}${button('repair','Repair installation','ghost')}</div></div><div class="setup-step"><span class="step-number">2</span><div><h3>Read Minecraft’s EULA</h3><p><a href="https://www.minecraft.net/en-us/eula" target="_blank" rel="noopener noreferrer">Read the official agreement ↗</a>. Acceptance is the owner’s choice.</p>${d.eula_accepted?pill('OWNER ACCEPTANCE RECORDED','good'):`<label class="check-label"><input id="accept-eula" type="checkbox"> I have read and accept Minecraft’s EULA.</label>${button('accept-eula','Record my acceptance','small')}`}</div></div><div class="setup-step"><span class="step-number">3</span><div><h3>Welcome KG & Sera</h3><p>Whitelist: ${esc(d.players.KG||'KG not configured')} · ${esc(d.players.Sera||'Sera not configured')}. Change access any time from Players & access.</p>${button('goto-players','Edit whitelist','small')}</div></div><div class="setup-step"><span class="step-number">4</span><div><h3>Open Prism, import your instance, and play</h3><p>Use the generated KG and Sera Prism packages. Their Packwiz pre-launch step checks the same release before Minecraft starts. Sign in with your own licensed Microsoft account.</p><div class="button-row">${button('prism','Open Prism Launcher','primary')}${button('start','Start world')}</div></div></div>`);
}

const viewCurrent=(page,generation)=>state.page===page&&state.renderGeneration===generation;
async function render() {
  const view=++state.renderGeneration,page=state.page;$('#page-label').textContent=labels[page];$$('nav a').forEach(a=>a.classList.toggle('active',a.dataset.page===page));
  if(page!=='atlas'&&state.atlas){state.atlas.unmount();state.atlas=null;}
  try {
    if(!['overview','performance'].includes(page))$('#main').innerHTML='<div class="loading"><span class="spinner"></span>Opening '+esc(labels[page])+'…</div>';
    if(page==='overview')overview();else if(page==='performance')performance();else if(page==='storage'){const response=await api('/api/storage');if(viewCurrent(page,view))storagePage(response);}
    else if(page==='mods')await modsPage();else if(page==='settings')await settingsPage();else if(page==='players')await playersPage();
    else if(page==='console')await consolePage();else if(page==='backups')await backupsPage();else if(page==='connectivity')await connectivityPage();
    else if(page==='graphics')await graphicsPage();else if(page==='compatibility')await compatibilityPage();else if(page==='setup')await setupPage();
    else if(page==='atlas'){const module=await import('/atlas.js');if(!viewCurrent(page,view))return;state.atlas=module;await state.atlas.mount({api,esc,header,button,bytes,toast,modal,confirmAction});}
    else if(page==='cinematics'){const module=await import('/cinematics.js');if(!viewCurrent(page,view))return;await module.mount({api,esc,header,card,bytes,toast,modal,confirmAction,request:(path,options)=>localSession.request(path,options),csrf:()=>state.csrf});}
    showJobs();
    if(state.page==='players'&&$('#whitelist-list')){const d=await api('/api/players');if(state.page==='players'&&$('#whitelist-list'))$('#whitelist-list').innerHTML=whitelistHtml(d);}
    await refreshPlayerDetails();
  } catch(error) {if(!viewCurrent(page,view))return;$('#main').innerHTML=header(labels[page],'This view needs a little attention.')+notice(error.message,'error');}
}
function showJobs() {
  $('#job-strip')?.remove();const jobs=state.jobs.filter(j=>['running','queued'].includes(j.status));
  if(jobs.length){const node=document.createElement('div');node.id='job-strip';node.className='job-strip';node.innerHTML=`<span class="spinner"></span><div>${jobs.map(j=>`${esc(j.title)}${j.messages.length?` · ${esc(j.messages.at(-1))}`:''}`).join('<br>')}</div>`;$('#main').prepend(node);}
}
async function refresh() {
  if(state.busy)return;state.busy=true;
  try {
    [state.overview,state.jobs]=await Promise.all([api('/api/overview'),api('/api/jobs')]);
    const context=$('#playtest-context'),activeTest=state.overview.active_test;
    if(context){context.hidden=!activeTest;context.replaceChildren();if(activeTest){context.append(document.createTextNode('Your playtest world is running. This page manages the main installation. '));const link=document.createElement('a');link.href=activeTest.url;link.textContent='Open the live playtest Control Room →';context.append(link);}}
    state.connected=true;$('#connection').className='connection';$('#connection').innerHTML='<i></i> Connected locally';
    $('#last-update').textContent=measurementLabel(state.overview.metrics?.freshness?.snapshot);
    if(['overview','performance'].includes(state.page)&&(!state.historyAt || Date.now()-state.historyAt>60000)){state.history=await api('/api/history?hours=1');state.historyAt=Date.now();}
    for(const j of state.jobs){if(['failed','complete','interrupted'].includes(j.status)&&!state.seenJobs.has(j.id)){state.seenJobs.add(j.id);if(state.jobsLoaded){state.backupsDirty=true;toast(j.status!=='complete'?`${j.title}: ${j.error}`:`${j.title} finished.`,j.status!=='complete');}}}
    state.jobsLoaded=true;
    if(['overview','performance'].includes(state.page))await render();else if(state.page==='storage')storagePage(await api('/api/storage'));else if(state.page==='console')await refreshConsole();else if(state.page==='connectivity'&&!$('#modal').open&&!document.activeElement?.closest('form'))await connectivityPage();
    else if(state.page==='backups'&&state.backupsDirty&&!$('#modal').open)await backupsPage();
    showJobs();
    if(state.page==='players'&&$('#whitelist-list')){const d=await api('/api/players');if(state.page==='players'&&$('#whitelist-list'))$('#whitelist-list').innerHTML=whitelistHtml(d);}
    await refreshPlayerDetails();
    return true;
  }catch(error){state.connected=false;if(state.overview&&['overview','performance'].includes(state.page)){if(state.page==='overview')overview();else performance();}$('#connection').className='connection error';$('#connection').innerHTML='<i></i> Connection lost';$('#last-update').textContent='Waiting to reconnect · live data is stale';return false;}
  finally{state.busy=false;}
}

let liveExpiry;
function scheduleLiveExpiry(){
  clearTimeout(liveExpiry);
  if(document.hidden||!['overview','performance'].includes(state.page)||!state.overview)return;
  const m=state.overview.metrics||{},fresh=[...Object.values(m.freshness||{}),...(m.clients||[]).flatMap(c=>[c.freshness,c.process_freshness]),{measured_at:state.overview.at,current:state.connected,max_age_seconds:15}];
  const waits=fresh.filter(currentMeasurement).map(info=>measurementMillis(info.measured_at)+info.max_age_seconds*1000-Date.now()+100);
  if(waits.length)liveExpiry=setTimeout(()=>{if(!document.hidden&&['overview','performance'].includes(state.page)){if(state.page==='overview')overview();else performance();}},Math.max(100,Math.min(...waits)));
}
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.overview){if(state.page==='overview')overview();else if(state.page==='performance')performance();}});

async function versionsDialog(project) {
  const d=await api('/api/mods/versions?project='+encodeURIComponent(project));
  const installed=(await api('/api/mods')).mods.some(m=>m.project_id===d.project.id);
  modal(d.project.title,`<p>${esc(d.project.description)}</p>${row('Client / server',`${esc(d.project.client_side)} / ${esc(d.project.server_side)}`)}<div class="field"><label for="mod-version">Exact NeoForge 1.21.1 version</label><select id="mod-version">${d.versions.map(v=>`<option value="${v.id}">${esc(v.version_number)} · ${v.version_type} · ${v.dependencies.filter(x=>x.dependency_type==='required').length} required dependencies</option>`).join('')}</select></div><label class="check-label"><input id="allow-beta" type="checkbox">Allow a reviewed prerelease for this candidate.</label><p>Staging verifies dependencies and JARs without changing the active server.</p>`,[{label:'Stage for review',run:async()=>{await run('/api/mods/propose',{action:installed?'update':'add',project:d.project.id,version:$('#mod-version').value,allow_prerelease:$('#allow-beta').checked});state.tab='proposals';await modsPage();}}]);
}

document.addEventListener('click',async event=>{
  if(document.body.classList.contains('menu-open')&&!event.target.closest('#menu')) {
    document.body.classList.remove('menu-open');
    $('#menu').setAttribute('aria-expanded','false');
  }
  const tab=event.target.closest('[data-mod-tab]');if(tab){state.tab=tab.dataset.modTab;await modsPage();return;}
  const target=event.target.closest('[data-action]');if(!target)return;const action=target.dataset.action;
  try {
    if(action.startsWith('goto-')){location.hash=action.slice(5);return;}
    if(action==='start')await run('/api/server/start');else if(action==='stop')confirmAction('Let the world rest?','Minecraft will save and flush the world before stopping.',()=>run('/api/server/stop'),'Save & stop');
    else if(action==='playit-start')await run('/api/playit/action',{action:'start',confirmed:true});
    else if(action==='playit-stop')confirmAction('Stop Playit?','This stops the installed tunnel service and disconnects remote players using any of its tunnels. Minecraft continues running locally.',()=>run('/api/playit/action',{action:'stop',confirmed:true}),'Stop Playit');
    else if(action==='playit-refresh')await connectivityPage();
    else if(action==='restart')confirmAction('Restart the world?','Both players will disconnect while Minecraft saves and restarts.',()=>run('/api/server/restart'),'Restart');
    else if(action==='prism')await run('/api/open',{target:'prism'});
    else if(action==='backup')confirmAction('Keep a safe snapshot?','If the server is online, it will stop to flush its world, create and verify a backup, then resume.',()=>run('/api/backups/create'),'Create backup');
    else if(action==='health'){const d=await run('/api/health');modal('Health check started','<p>The result will appear in the task history. You can export a diagnostic bundle from Console & logs.</p>');}
    else if(action==='diagnostics')location.href='/api/export/metrics.csv';
    else if(action==='profile')await run('/api/diagnostics/start');
    else if(action==='refresh-storage')storagePage(await api('/api/storage?refresh=1'));
    else if(action==='jobs'){const jobs=await api('/api/jobs');modal('Task history',jobs.length?jobs.map(j=>`<details class="result-card"><summary>${esc(j.title)} · ${esc(j.status)} · ${when(j.created)}</summary>${j.error?notice(j.error,'error'):''}${j.history_warning?notice(j.history_warning,'warn'):''}${j.result?.history_warning?notice(j.result.history_warning,'warn'):''}<pre>${esc(j.messages.join('\n'))}</pre>${j.result?`<pre>${esc(JSON.stringify(j.result,null,2))}</pre>`:''}</details>`).join(''):empty('No tasks have run in this Control Room session.'));}
    else if(action==='manual-import')await run('/api/mods/import-manual',{slug:target.dataset.slug});
    else if(action==='mod-versions')await versionsDialog(target.dataset.project);
    else if(action==='mod-remove')confirmAction('Remove '+target.dataset.name+'?','A proposal will check dependent mods and flag saved-world content risks. This does not remove anything from the running server.',async()=>{await run('/api/mods/propose',{action:'remove',project:target.dataset.project});state.tab='proposals';await modsPage();},'Stage removal');
    else if(action==='proposal-review') {const p=(await api('/api/proposals')).find(x=>x.id===target.dataset.id);modal('Review '+p.version,`<p>${esc(p.warning)}</p><pre>${esc(JSON.stringify(p.changes,null,2))}</pre>${p.static_errors.length?notice(p.static_errors.join('; '),'error'):notice('Static checks passed. Runtime acceptance is still required.','warn')}<div class="field"><label>Published immutable client pack URL</label><input id="release-url" value="https://kgray44.github.io/a-world-for-two/releases/${esc(p.version)}/pack.toml"></div><div class="field"><label>Type DEPLOY ${esc(p.version)}</label><input id="deploy-confirm"></div>`,[{label:'Approve & deploy',run:()=>run('/api/mods/deploy',{id:p.id,confirmation:$('#deploy-confirm').value,publication_url:$('#release-url').value})}]);}
    else if(action==='proposal-rollback') {modal('Roll back this release?',`<p>Stop the server first. A world backup is made before the previous manifest and server mods are restored. Publish the matching prior client pointer before players relaunch.</p><div class="field"><label>Type ROLLBACK ${esc(target.dataset.version)}</label><input id="rollback-confirm"></div>`,[{label:'Roll back',kind:'danger',run:()=>run('/api/mods/rollback',{id:target.dataset.id,confirmation:$('#rollback-confirm').value})}]);}
    else if(action==='player-details')await playerDetails(target.dataset.name);
    else if(action.startsWith('player-')) {const cmd=action.slice(7);confirmAction('Change '+target.dataset.name+' access?',`Action: ${cmd}. This change applies to the real server whitelist or player permissions.`,async()=>{await run('/api/player',{action:cmd,name:target.dataset.name,confirmed:true});await playersPage();},'Confirm change');}
    else if(action==='backup-verify')await run('/api/backups/verify',{id:target.dataset.id});
    else if(action==='backup-restore') {const id=target.dataset.id;modal('Restore this world snapshot?',`<p>The server must be offline. The current world is preserved in a separate safety directory. Review the backup’s pack version before starting the restored world.</p><div class="field"><label>Type RESTORE ${id}</label><input id="restore-confirm"></div>`,[{label:'Restore world',kind:'danger',run:()=>run('/api/backups/restore',{id,confirmation:$('#restore-confirm').value})}]);}
    else if(action==='config-restore')confirmAction('Restore previous settings?','The server must be offline. Current values are saved before restoring this snapshot.',()=>run('/api/config/restore',{id:target.dataset.id}),'Restore settings');
    else if(action==='raw-diff'){const p=await api('/api/config/propose',{path:state.raw.path,expected:state.raw.sha256,content:$('#raw-content').value});modal('Review configuration changes',`<p>${esc(p.warning)}</p><pre>${esc(p.diff||'No changes.')}</pre>`,[{label:'Save with backup',run:async()=>{await run('/api/config/save',p);state.raw=await api('/api/config/raw?path='+encodeURIComponent(p.path));}}]);}
    else if(action==='crash-read'){const d=await api('/api/crash?name='+encodeURIComponent(target.dataset.name));modal(d.name,`<pre>${esc(d.content)}</pre>`);}
    else if(action==='install')await run('/api/setup/install');else if(action==='repair')await run('/api/setup/repair');
    else if(action==='accept-eula'){if(!$('#accept-eula').checked)throw new Error('Read the EULA and explicitly check the acceptance box first.');await run('/api/setup/eula',{accepted:true});await setupPage();}
  }catch(error){toast(error.message,true);}
});

document.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.target,fd=new FormData(form);
  try {
    if(form.id==='mod-search'){const d=await api('/api/mods/search?q='+encodeURIComponent(fd.get('q')));$('#search-results').innerHTML=d.hits.length?d.hits.map(m=>`<div class="result-card"><div class="result-head"><h3>${esc(m.title)}</h3>${button('mod-versions','Choose version','small',`data-project="${esc(m.project_id)}"`)}</div><p>${esc(m.description)}</p><span class="subtle">NeoForge · Minecraft 1.21.1</span></div>`).join(''):empty('No compatible projects found. Try the exact project name or URL.');}
    else if(form.id==='curseforge-search'){$('#curseforge-result').textContent=JSON.stringify(await api('/api/mods/curseforge',{project_id:fd.get('id')}),null,2);}
    else if(form.id==='whitelist-add'){const who=await api('/api/player/lookup?name='+encodeURIComponent(fd.get('name')));confirmAction('Welcome '+who.name+'?',`This verified Java profile will be allowed to join. UUID: ${who.uuid}`,async()=>{await run('/api/player',{action:'whitelist-add',name:who.name});form.reset();await playersPage();},'Add player');}
    else if(form.id==='player-permissions'){const name=form.dataset.name,level=Number(fd.get('level')),bypass=fd.get('bypass')==='on';if(level===0&&bypass)throw new Error('Player-limit bypass requires operator level 1–4.');confirmAction('Save '+name+' permissions?',`Set level ${level}${bypass?' and player-limit bypass':''}. ${level===4?'This grants full server control, including stop and permission commands.':'The current operator values will be backed up.'}`,()=>run('/api/player/permissions',{name,level,bypass,confirmed:true}),'Save permissions');}
    else if(form.id==='player-game-settings'){const name=form.dataset.name,value=fd.get('mode');confirmAction('Change '+name+' game mode?',`Set this online player to ${value}.`,()=>run('/api/player/action',{name,action:'game-mode',value,confirmed:true}),'Save game mode');}
    else if(form.id==='player-xp-settings'){const name=form.dataset.name,value=Number(fd.get('level'));confirmAction('Change '+name+' experience?',`Replace this player's current experience level with ${value}.`,()=>run('/api/player/action',{name,action:'xp-level',value,confirmed:true}),'Set experience');}
    else if(form.classList.contains('settings-form')){const schema=await api('/api/settings'),scope=form.dataset.scope,changes={};for(const f of schema.fields.filter(x=>x.scope===scope)){const input=form.elements.namedItem(f.key);const value=f.type==='boolean'?input.checked:f.type==='integer'?Number(input.value):input.value;if(value!==f.current)changes[f.key]=value;}if(!Object.keys(changes).length){toast('Everything is already saved.');return;}await run('/api/settings',{scope,changes});}
    else if(form.classList.contains('mod-setting-form')){const input=form.elements.namedItem('value');await run('/api/settings/mod',{id:form.dataset.id,expected:form.dataset.expected,value:form.dataset.type==='boolean'?input.checked:Number(input.value)});await settingsPage();}
    else if(form.id==='raw-open'){state.raw=await api('/api/config/raw?path='+encodeURIComponent(fd.get('path')));$('#raw-editor').innerHTML=`<textarea id="raw-content" aria-label="Raw configuration contents" spellcheck="false">${esc(state.raw.content)}</textarea><div class="button-row">${button('raw-diff','Review diff','primary')}</div>`;}
    else if(form.id==='console-command'){const command=fd.get('command');const dangerous=/^(op |deop |kick |whitelist remove |gamerule |difficulty |chunky cancel)/.test(command.replace(/^\//,''));if(dangerous)confirmAction('Send this command?',command,()=>run('/api/console',{command,confirmed:true}),'Send command');else await run('/api/console',{command});form.reset();}
    else if(form.id==='tunnel-address')await run('/api/connectivity',{address:fd.get('address')});
    else if(form.id==='shader-select')await run('/api/graphics/select',{client:fd.get('client'),shader:fd.get('shader'),expected:$('#shader-client').selectedOptions[0].dataset.revision||null,allow_lod_limited:fd.has('allow_lod_limited')});
  }catch(error){toast(error.message,true);}
});
document.addEventListener('input',event=>{const e=event.target;if(e.id==='inventory-filter')$$('[data-inventory-name]').forEach(r=>r.classList.toggle('hidden',!r.dataset.inventoryName.includes(e.value.toLowerCase())));if(e.id==='compat-filter')$$('[data-compat-text]').forEach(r=>r.classList.toggle('hidden',!r.dataset.compatText.includes(e.value.toLowerCase())));if(e.id==='log-query')refreshConsole().catch(e=>toast(e.message,true));});
document.addEventListener('change',event=>{if(event.target.id==='log-level')refreshConsole().catch(e=>toast(e.message,true));});
window.addEventListener('hashchange',()=>{
  state.page=labels[location.hash.slice(1)]?location.hash.slice(1):'overview';
  document.body.classList.remove('menu-open');
  // Begin a newly selected page at the top; polling preserves the reading position.
  window.scrollTo(0,0);
  render();
  poller.wake();
});
window.addEventListener('resize',()=>{if(state.page==='overview')chart('overview-chart',state.history,'tps');if(state.page==='performance'){chart('tps-chart',state.history,'tps');chart('cpu-chart',state.history,'host_cpu','server_cpu');}});
$('#modal-close').onclick=()=>$('#modal').close();$('#menu').onclick=()=>{const open=document.body.classList.toggle('menu-open');$('#menu').setAttribute('aria-expanded',String(open));};
document.addEventListener('keydown',event=>{if(event.key==='Escape'){document.body.classList.remove('menu-open');$('#menu').setAttribute('aria-expanded','false');}});
const poller=new VisiblePoller(async()=>{if(!await refresh())throw new Error('Dashboard unavailable');},{delay:()=>state.jobs.some(j=>['queued','running'].includes(j.status))?3000:['overview','performance','players','console','connectivity'].includes(state.page)?5000:15000});
(async()=>{try{const bootstrap=await api('/api/bootstrap');localSession.bind(bootstrap);if(bootstrap.test_context){$('.local-tag').textContent='DISPOSABLE TEST';document.title='A World for Two · Disposable playtest';}state.page=labels[location.hash.slice(1)]?location.hash.slice(1):'overview';await refresh();await render();}catch(error){$('#main').innerHTML=header('Your world is taking a moment.','Open Control Room with the local launch script.')+notice(error.message,'error');}finally{poller.start();}})();
