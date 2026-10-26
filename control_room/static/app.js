'use strict';
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = {csrf:'', page:'overview', overview:null, jobs:[], history:[], tab:'installed', raw:null, seenJobs:new Set(), busy:false};
const labels = {overview:'Overview', performance:'Performance', storage:'Storage', mods:'Mod Manager', settings:'World settings', players:'Players & access', console:'Console & logs', backups:'Backups', connectivity:'Connectivity', graphics:'Graphics & distance', compatibility:'Compatibility', setup:'Setup & repair'};
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

async function api(path, body) {
  const response = await fetch(path, body === undefined ? {cache:'no-store'} : {method:'POST', headers:{'Content-Type':'application/json','X-AWFT-CSRF':state.csrf}, body:JSON.stringify(body)});
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
  const d=state.overview,m=d.metrics||{},s=d.server,online=s.state==='online';
  const controls=online?button('stop','Ⅱ Stop world')+button('restart','↻ Restart','ghost'):button('start','▷ Start world','primary');
  const warnings=(m.alerts||[]).map(a=>notice(a.message,a.severity==='critical'?'error':'warn')).join('')+(s.warning?notice(s.warning,'warn'):'');
  $('#main').innerHTML=header('Welcome home.', 'A little world, beautifully looked after.',button('prism','◇ Open Prism Launcher'))+warnings+
    `<section class="hero"><div class="hero-copy">${pill(`< ${s.state.toUpperCase()} >`,online?'good':'')}<h2>${online?'Your next adventure is waiting.':'A place to call ours.'}</h2><p>${online?'The world is awake. Find a quiet meadow, follow the river, or take the long way home.':'Mountains to wander. A cottage to come home to. Start your shared world when you’re ready.'}</p><div class="button-row">${controls}${button('goto-console','View console','ghost')}</div></div>${landscape}</section>`+
    `<div class="metric-grid">${metric('SERVER TICK RATE',number(m.tps),m.tps==null?'':'TPS',m.tps==null?'Unavailable until NeoForge reports':`Measured MSPT · ${number(m.mspt)} ms`)}${metric('JAVA PROCESS MEMORY',bytes(m.server_rss),'',`Host available · ${bytes(m.host_memory_available)}`,'▱')}${metric('PLAYERS ONLINE',number(s.status?.players?.online,0),'',`Maximum · ${s.status?.players?.max??2}`,'♧')}${metric('WORLD STORAGE',bytes(d.storage.breakdown.categories.find(x=>x.key==='world')?.bytes||0),'','Measured from world files · live','◇')}</div>`+
    `<div class="grid-two">${card('A healthy little world',`<canvas id="overview-chart" class="chart" role="img" aria-label="Measured server TPS over time"></canvas><div class="chart-legend"><span>Server TPS · actual NeoForge readings</span></div>`,pill('LIVE'))}${card('At a glance',row('Minecraft',esc(d.pack.minecraft))+row('NeoForge',esc(d.pack.neoforge))+row('Pack release',`<span class="mono">${esc(d.pack.version)}</span>`)+row('Uptime',duration(s.uptime_seconds))+row('View / simulation',`${esc(d.world.view_distance)} / ${esc(d.world.simulation_distance)} chunks`)+row('Latest backup',when(d.last_backup?.created)))}</div>`+
    `<div class="grid-equal">${card('Just the two of you',Object.entries(d.sync.players).map(([name,p])=>`<div class="player-card"><div class="player-avatar">${name==='KG'?'KG':'S'}</div><div class="player-main"><strong>${name}</strong><small>${esc(p.message)}</small></div>${pill(p.state,p.state==='reported match'?'good':'')}</div>`).join(''),button('goto-players','Manage access →','ghost small'))}${card('Room to grow',row('Project files',bytes(d.storage.project_bytes))+row('Project budget',bytes(d.storage.project_budget))+d.storage.drives.map(x=>row(`${x.drive} free`,`${bytes(x.free)} ${x.low?pill('LOW','error'):''}`)).join('')+`<p class="subtle">Both drives keep a separate 30 GiB reserve.</p>`,button('goto-storage','View storage →','ghost small'))}</div>`+
    `<div class="section-label">LITTLE THINGS THAT KEEP IT RUNNING</div><div class="quick-actions">${[['backup','↶','Create a backup','Save a safe little snapshot'],['health','✓','Check world health','See what needs attention'],['diagnostics','⌁','Performance report','Export real measurements'],['goto-mods','◇','Find a new mod','Stage, review, then deploy']].map(([a,i,t,n])=>`<button class="quick-action" data-action="${a}"><span class="action-icon">${i}</span><span><b>${t}</b><small>${n}</small></span></button>`).join('')}</div>`;
  chart('overview-chart',state.history,'tps');
}

function storagePage(data) {
  const b=data.breakdown;
  $('#main').innerHTML=header('A little room to grow.','Every world, cache, backup and temporary file, measured from disk.',button('refresh-storage','↻ Refresh now'))+
    (!b.complete?notice('Some files changed during the scan or could not be read. The next sample will refresh them. See measurement details below.','warn'):'')+
    `<div class="grid-two">${card('The whole project',`<div class="storage-summary"><div><div class="storage-number">${bytes(b.bytes)}</div><p class="subtle">File contents · ${number(b.files,0)} files</p></div><div class="storage-detail">${bytes(b.allocated_bytes)} allocated on disk<br>${bytes(data.project_budget)} project budget<br>Scanned ${when(b.measured_at)} · ${number(b.scan_ms)} ms</div></div><progress value="${b.bytes}" max="${data.project_budget}" aria-label="Project storage used"></progress><div class="storage-rows">${b.categories.map(x=>`<div class="info-row"><div>${esc(x.label)}<small>${number(x.files,0)} files · ${esc(x.key)}</small></div><progress value="${x.bytes}" max="${Math.max(1,b.bytes)}" aria-label="${esc(x.label)} share of project"></progress><div>${bytes(x.bytes)}<small>${bytes(x.allocated_bytes)} allocated</small></div></div>`).join('')}</div>`)}${card('Your drives',data.drives.map(d=>`<div class="drive"><div class="drive-head"><strong>${esc(d.drive)}</strong>${pill(d.low?'RESERVE AT RISK':'RESERVE PROTECTED',d.low?'error':'good')}</div><div class="storage-number">${bytes(d.free)} <small>free</small></div><progress value="${d.used}" max="${d.total}" aria-label="Drive ${esc(d.drive)} used"></progress><small>${bytes(d.used)} used of ${bytes(d.total)} · 30 GiB reserve</small></div>`).join('')+`<p class="subtle">${esc(data.coverage)}</p>`)}</div>`+
    card('Measured, not estimated',`<p class="subtle">${esc(b.note)} Refreshed every ${b.refresh_seconds} seconds. Downloads and managed generation also run the host reserve guard before writing.</p>${b.issues.length?`<pre>${esc(b.issues.join('\n'))}</pre>`:''}`);
}

function performance() {
  const m=state.overview.metrics||{};
  $('#main').innerHTML=header('Keep the world feeling effortless.','Live host and Java-process measurements. Stored history uses one point per minute.',`<a class="button" href="/api/export/metrics.csv">↓ Export CSV</a>${button('profile','Sample with spark','primary')}`)+
    `<div class="metric-grid">${metric('MEASURED TPS',number(m.tps),'TPS',m.tick_at?when(m.tick_at):'Waiting for NeoForge')}${metric('MEAN TICK TIME',number(m.mspt),'ms','50 ms is the 20 TPS tick budget')}${metric('SERVER CPU',number(m.server_cpu),'%','Normalized to total host CPU capacity')}${metric('HOST AVAILABLE RAM',bytes(m.host_memory_available),'',`${number(m.host_memory_percent)}% of host RAM in use`)}</div>`+
    `<div class="grid-equal">${card('Server tick rate','<canvas id="tps-chart" class="chart" role="img" aria-label="Server TPS history"></canvas>')}${card('Host & server CPU','<canvas id="cpu-chart" class="chart" role="img" aria-label="Host and server CPU history"></canvas><div class="chart-legend"><span>Host</span><span>Server</span></div>')}</div>`+
    `<div class="grid-equal">${card('Java & world telemetry',row('Java RSS',bytes(m.server_rss))+row('JVM heap usage','Unavailable · RSS is separate')+row('Latest GC pause',m.gc_pause_ms==null?'Unavailable':`${number(m.gc_pause_ms)} ms`)+row('Loaded chunks','Unavailable without a diagnostic bridge')+row('Entity counts','Unavailable without a diagnostic bridge')+row('Dimension activity','Available in an in-game spark report'))}${card('A useful next step',`<p class="details">A one-minute spark sample helps explain expensive ticks, entity simulation and chunk generation. The console will show spark’s report link. Review it before sharing.</p>${button('profile','Start 60-second sample','primary')}<p class="subtle">FPS, frametimes and GPU load require a real client benchmark. They are never inferred from server TPS.</p>`)}</div>`;
  chart('tps-chart',state.history,'tps');chart('cpu-chart',state.history,'host_cpu','server_cpu');
}

async function modsPage() {
  const d=await api('/api/mods');
  $('#main').innerHTML=header('Make this world your own.','One manifest. Exact versions. Every change gets a safe place to land.',pill(`${d.mods.length} PINNED FILES`))+
    `<div class="tabs"><button data-mod-tab="installed" class="${state.tab==='installed'?'active':''}">Installed inventory</button><button data-mod-tab="search" class="${state.tab==='search'?'active':''}">Find a mod</button><button data-mod-tab="proposals" class="${state.tab==='proposals'?'active':''}">Staged changes</button></div><div id="mod-content"></div>`;
  if(state.tab==='installed') {
    $('#mod-content').innerHTML=`<div class="toolbar"><input id="inventory-filter" placeholder="Filter mods, versions or feature groups…" aria-label="Filter inventory">${pill(esc(d.version))}</div><div class="card table-wrap"><table><thead><tr><th>MOD</th><th>EXACT VERSION</th><th>INSTALLATION</th><th>VALIDATION</th><th></th></tr></thead><tbody>${d.mods.map(m=>`<tr data-inventory-name="${esc((m.name+' '+m.version+' '+(m.request||'')).toLowerCase())}"><td class="name">${esc(m.name)}<small>${esc(m.request||'Required dependency')}${m.optional?' · Optional':''}</small></td><td class="mono version">${esc(m.version)}</td><td>${pill(m.side)}</td><td>${pill(m.validation?.runtime==='pass'?'Runtime tested':'Runtime pending',m.validation?.runtime==='pass'?'good':'warn')}</td><td><div class="button-row">${button('mod-versions','Versions','small',`data-project="${esc(m.slug)}"`)}${button('mod-remove','Remove','ghost small',`data-project="${esc(m.slug)}" data-name="${esc(m.name)}"`)}</div></td></tr>`).join('')}</tbody></table></div>`;
  } else if(state.tab==='search') {
    $('#mod-content').innerHTML=`<form id="mod-search" class="toolbar"><input name="q" placeholder="Search Modrinth or paste a project URL…" aria-label="Find a mod" required><button class="button primary">Search mods</button></form><div id="search-results" class="card">${empty('Find something lovely. We’ll check the loader, version, dependencies and installation side.')}</div><details class="card"><summary>CurseForge lookup</summary><p class="subtle">Uses an authorized host API key. Restricted downloads and distribution rules are respected.</p><form id="curseforge-search" class="toolbar"><input name="id" placeholder="Numeric CurseForge project ID" required><button class="button">Look up</button></form><div id="curseforge-result"></div></details>`;
  } else {
    const proposals=await api('/api/proposals');
    $('#mod-content').innerHTML=notice('A staged change downloads and checks files in isolation. Production deployment requires review, exact-candidate runtime acceptance, a verified backup and a matching published client release.')+card('A safe place for new ideas',proposals.length?proposals.map(p=>`<div class="result-card"><div class="result-head"><div><h3>${esc(p.version)}</h3><span class="subtle">${when(p.created)} · ${p.changes.length} changes</span></div>${pill(p.status,p.static_errors.length?'error':'warn')}</div><p>${p.changes.map(c=>`${esc(c.name)} · ${esc(c.from||'new')} → ${esc(c.to||'removed')}`).join('<br>')}</p><div class="button-row">${button('proposal-review','Review change','small',`data-id="${p.id}"`)}${button('proposal-rollback','Roll back','ghost small',`data-id="${p.id}" data-version="${esc(p.version)}"`)}</div></div>`).join(''):empty('No changes waiting. Your active manifest has stayed exactly where you left it.'));
  }
}

async function settingsPage() {
  const d=await api('/api/settings');
  function settingsForm(scope,title) {return card(title,`<form class="settings-form" data-scope="${scope}"><div class="field-grid">${d.fields.filter(f=>f.scope===scope).map(f=>`<div class="field"><label for="setting-${f.key}">${esc(f.label)} ${pill(f.change,f.change.startsWith('Dangerous')?'warn':'')}</label>${f.type==='boolean'?`<label class="check-label"><input id="setting-${f.key}" name="${f.key}" type="checkbox" ${f.current?'checked':''}>Enabled</label>`:f.type==='enum'?`<select id="setting-${f.key}" name="${f.key}">${f.values.map(v=>`<option ${v===f.current?'selected':''}>${esc(v)}</option>`).join('')}</select>`:`<input id="setting-${f.key}" name="${f.key}" type="${f.type==='integer'?'number':f.key==='level-seed'?'password':'text'}" ${f.min!=null?`min="${f.min}" max="${f.max}"`:''} value="${esc(f.current)}">`}<small>${esc(f.description)}<br>Recommended: ${esc(String(f.recommended??'default'))}</small></div>`).join('')}</div><button class="button primary">Save ${scope==='server'?'world':'Control Room'} settings</button></form>`);}
  $('#main').innerHTML=header('A world that feels just right.','Clear settings, thoughtful defaults and a way back to your previous values.')+
    notice('Stop the world before changing restart-required settings. Client-only weather, shaders and LOD rendering are managed through graphics profiles on each player’s computer.')+
    settingsForm('server','World & simulation')+`<div class="section-label">CONTROL ROOM</div>`+settingsForm('app','Memory, backups & monitoring')+
    `<div class="section-label">MOD INTEGRATION</div>`+card('Weather, seasons, Create & distant terrain',d.mods.length?d.mods.map(m=>row(m.label,m.available?esc(m.current):esc(m.reason))).join(''):`<p class="subtle">Generated settings will appear after the first successful mod load. No guessed configuration keys are written.</p>`)+
    `<div class="section-label">ADVANCED SETTINGS</div>`+card('Configuration editor',`<form id="raw-open" class="toolbar"><select name="path" id="config-files" aria-label="Configuration file"><option value="server.properties">server.properties</option></select><button class="button">Open file</button></form><div id="raw-editor"></div><p class="subtle">Syntax checks, a reviewable diff, optimistic concurrency and a prior-value snapshot protect every save. Mod-specific values still need their upstream schema.</p>`)+
    card('Previous configurations',`<div id="config-history">Loading history…</div><p class="subtle">${esc(d.gc)}</p>`);
  const files=await api('/api/config/files');$('#config-files').insertAdjacentHTML('beforeend',files.map(f=>`<option>${esc(f)}</option>`).join(''));
  const history=await api('/api/config/history');$('#config-history').innerHTML=history.length?history.slice(0,12).map(h=>row(esc(h.path),button('config-restore',`Restore ${when(h.created)}`,'small',`data-id="${esc(h.id)}"`))).join(''):empty('Previous values will be saved here whenever you change a configuration.');
}

async function playersPage() {
  const d=await api('/api/players');
  $('#main').innerHTML=header('Good company only.','An editable whitelist, verified Java profiles and clear player permissions.',pill('ONLINE AUTHENTICATION ON','good'))+
    `<div class="grid-two">${card('Who’s welcome here',`<div id="whitelist-list">${whitelistHtml(d)}</div><form id="whitelist-add" class="toolbar"><input name="name" placeholder="Minecraft Java username" pattern="[A-Za-z0-9_]{1,16}" aria-label="Player to add to whitelist" required><button class="button primary">＋ Add to whitelist</button></form><p class="subtle">Names are verified with Mojang. Changes work while the server is online or offline; existing access is backed up.</p>`)}${card('Who’s here right now',d.online?row('Players online',`${d.online.online} / ${d.online.max}`)+(d.online.sample||[]).map(p=>row(p.name,button('player-kick','Kick','small',`data-name="${esc(p.name)}"`))).join(''):empty('The world is resting, or the server has not returned a player list.'))}</div>`+
    card('Little arrivals & goodbyes',d.events.length?d.events.slice().reverse().map(e=>row(`${e.name} ${e.event}`,when(e.at))).join(''):empty('Join and leave events will appear once players visit.'));
}
function whitelistHtml(d) {return d.whitelist.length?d.whitelist.map(p=>{const op=d.operators.some(o=>o.uuid===p.uuid);return `<div class="player-card"><div class="player-avatar">${esc(p.name.slice(0,2).toUpperCase())}</div><div class="player-main"><strong>${esc(p.name)}</strong><small>${op?'Operator · level '+d.operators.find(o=>o.uuid===p.uuid).level:'Whitelisted player'}</small></div><div class="button-row">${button(op?'player-deop':'player-op',op?'Remove op':'Make operator','small',`data-name="${esc(p.name)}"`)}${button('player-whitelist-remove','Remove','ghost small',`data-name="${esc(p.name)}"`)}</div></div>`;}).join(''):empty('No players on the whitelist yet. Add KG and Sera below.');}

async function consolePage() {
  $('#main').innerHTML=header('Listen to the world.','Live server output, useful diagnostics and a safe command console.',`<a class="button" href="/api/export/diagnostics.zip">↓ Diagnostic bundle</a>`)+
    `<div class="toolbar"><input id="log-query" placeholder="Search console output…" aria-label="Search logs"><select id="log-level" aria-label="Log severity"><option value="all">All messages</option><option value="warning">Warnings</option><option value="error">Errors</option></select></div><div id="console-log" class="log" role="log" aria-label="Server console">Waiting for server output…</div><form id="console-command" class="command-form"><input name="command" placeholder="Try list, neoforge tps, or say Welcome home" aria-label="Server command" required><button class="button primary">Send command</button></form><p class="subtle">Player-access and world-setting commands require confirmation. Commands outside the safe allowlist stay in the local server console.</p><div class="section-label">IF SOMETHING GOES WRONG</div>${card('Crash reports','<div id="crash-list">Loading…</div>')}`;
  await refreshConsole();const crashes=await api('/api/crashes');$('#crash-list').innerHTML=crashes.length?crashes.map(c=>row(esc(c.name),button('crash-read','Read report','small',`data-name="${esc(c.name)}"`))).join(''):empty('No crash reports found. A quiet console is a good thing.');
}
async function refreshConsole() {const node=$('#console-log');if(!node)return;const follow=node.scrollHeight-node.scrollTop-node.clientHeight<60;const logs=await api(`/api/console?query=${encodeURIComponent($('#log-query').value)}&level=${$('#log-level').value}`);node.innerHTML=logs.length?logs.map(l=>`<span class="${l.level}">${esc(new Date(l.at).toLocaleTimeString())} ${esc(l.text)}</span>`).join('\n'):'No matching console messages yet.';if(follow)node.scrollTop=node.scrollHeight;}

async function backupsPage() {
  const d=await api('/api/backups');
  $('#main').innerHTML=header('Keep the memories safe.','Verified snapshots, clear history and careful restores.',button('backup','＋ Create backup','primary'))+
    notice('Backups use a controlled stop so Minecraft can flush the world, then resume after verification. Restore requires the server to be offline and preserves the current world in a separate safety directory.')+
    card('Your world, through time',d.length?`<div class="table-wrap"><table><thead><tr><th>CREATED</th><th>ARCHIVE SIZE</th><th>WORLD & CONFIG FILES</th><th>INTEGRITY</th><th></th></tr></thead><tbody>${d.map(b=>`<tr><td class="name">${when(b.created)}<small class="mono">${esc(b.id)}</small></td><td>${bytes(b.bytes)}</td><td>${number(b.files,0)} files · ${bytes(b.source_bytes)}</td><td>${pill(b.integrity,b.integrity==='verified'?'good':'warn')}</td><td><div class="button-row">${button('backup-verify','Verify','small',`data-id="${b.id}"`)}${button('backup-restore','Restore','danger small',`data-id="${b.id}"`)}</div></td></tr>`).join('')}</tbody></table></div>`:empty('Your first backup will appear after Minecraft has created and saved a world.'));
}

async function connectivityPage() {
  const d=await api('/api/connectivity');
  $('#main').innerHTML=header('The long distance, made shorter.','A private world for you, wherever the two of you happen to be.')+
    `<div class="grid-equal">${card('On this laptop',row('Minecraft address',`<code>${esc(d.local_address)}</code>`)+row('Control Room',`<code>${esc(d.dashboard)}</code>`)+row('Authentication',pill('ONLINE MODE','good'))+row('Whitelist',pill('ENFORCED','good')))}${card('Sera’s way home',row('Playit agent',esc(d.playit.state))+row('External connection',esc(d.external_connection))+`<form id="tunnel-address"><div class="field"><label for="join-address">Playit join address</label><input id="join-address" name="address" placeholder="your-tunnel.joinmc.link" value="${esc(d.playit.address||'')}"><small>Owner-supplied address. A configured address is not proof of a working remote connection.</small></div><button class="button primary">Save join address</button></form>`)}</div>`+
    card('Set up once, then just join',`<ol class="details">${d.instructions.map(i=>`<li>${esc(i)}</li>`).join('')}</ol><p class="subtle">The public Minecraft tunnel must point only at the game port. The dashboard, RCON and monitoring ports stay private.</p>`);
}

async function graphicsPage() {
  const data=await api('/api/graphics');
  $('#main').innerHTML=header('A world beyond the horizon.','Distant Horizons + SeedGen. Shared content, personal graphics.')+
    notice('These are local client settings. Control Room does not remotely edit Sera’s computer. Both profiles use the same gameplay manifest; shader choices never change the dedicated server’s mod set.')+
    `<div class="grid-equal">${data.profiles.map(p=>`<section class="profile-card"><div class="eyebrow">${esc(p.audience)}</div><h3>${esc(p.name)}</h3><p class="subtle">${esc(p.description)}</p>${Object.entries(p.settings).map(([k,v])=>row(k,esc(v))).join('')}<p class="subtle">${esc(p.validation)}</p></section>`).join('')}</div>`+
    card('Distant terrain, without the long walk',`<p class="details">SeedGen builds visual terrain representations from compatible world-generation information. These LODs are not full saved Minecraft chunks. The server and clients carry the same terrain mods so their biome and height information can agree.</p><p class="subtle">Dense fog, storms, shaders and moving Sable contraptions have separate acceptance tests. C2ME, Fog and Better Fog are outside the default profile.</p>`);
}

async function compatibilityPage() {
  const d=await api('/api/compatibility');
  $('#main').innerHTML=header('Every detail, accounted for.','Requested mods, exact identities, selected versions and the evidence behind each decision.')+
    `<div class="toolbar"><input id="compat-filter" placeholder="Filter requested mods, evidence or status…" aria-label="Filter compatibility report"><span class="subtle">${d.requests.length} requests tracked</span></div>`+
    card('Compatibility inventory',`<div class="table-wrap"><table><thead><tr><th>REQUEST</th><th>DECISION</th><th>VERSION</th><th>EVIDENCE / LIMITATION</th></tr></thead><tbody>${d.requests.map(r=>`<tr data-compat-text="${esc(JSON.stringify(r).toLowerCase())}"><td class="name">${esc(r.name)}<small>${esc(r.group)}</small></td><td>${pill(r.status,r.status.startsWith('Integrated and tested')?'good':r.status.startsWith('Incompatible')?'error':'warn')}</td><td class="mono version">${esc(r.version||'—')}</td><td>${esc(r.reason)}${r.source?`<small><a href="${esc(r.source)}" target="_blank" rel="noopener noreferrer">Upstream evidence ↗</a></small>`:''}</td></tr>`).join('')}</tbody></table></div>`);
}

async function setupPage() {
  const d=await api('/api/setup');
  $('#main').innerHTML=header('A good beginning.','A few things to set up once. Then it’s just Start World.')+
    card('Your installation',row('Data directory',`<code>${esc(d.home)}</code>`)+row('Java',`${esc(d.java_version||'Not found')} ${pill(d.java_21?'JAVA 21 READY':'JAVA 21 REQUIRED',d.java_21?'good':'warn')}`)+row('Pack installed',d.installed?esc(d.installed.pack_version):'Not yet')+row('Minecraft EULA',pill(d.eula_accepted?'ACCEPTED BY OWNER':'AWAITING OWNER',d.eula_accepted?'good':'warn')))+
    card('Let’s get you home',`<div class="setup-step"><span class="step-number">1</span><div><h3>Install the dedicated server</h3><p>Downloads the pinned NeoForge and mod files, verifies their hashes and separates client-only mods. Existing worlds and settings are preserved.</p>${button('install','Install server','primary')}${button('repair','Repair installation','ghost')}</div></div><div class="setup-step"><span class="step-number">2</span><div><h3>Read Minecraft’s EULA</h3><p><a href="https://www.minecraft.net/en-us/eula" target="_blank" rel="noopener noreferrer">Read the official agreement ↗</a>. Acceptance is the owner’s choice.</p>${d.eula_accepted?pill('OWNER ACCEPTANCE RECORDED','good'):`<label class="check-label"><input id="accept-eula" type="checkbox"> I have read and accept Minecraft’s EULA.</label>${button('accept-eula','Record my acceptance','small')}`}</div></div><div class="setup-step"><span class="step-number">3</span><div><h3>Welcome KG & Sera</h3><p>Whitelist: ${esc(d.players.KG||'KG not configured')} · ${esc(d.players.Sera||'Sera not configured')}. Change access any time from Players & access.</p>${button('goto-players','Edit whitelist','small')}</div></div><div class="setup-step"><span class="step-number">4</span><div><h3>Open Prism, import your instance, and play</h3><p>Use the generated KG and Sera Prism packages. Their Packwiz pre-launch step checks the same release before Minecraft starts. Sign in with your own licensed Microsoft account.</p><div class="button-row">${button('prism','Open Prism Launcher','primary')}${button('start','Start world')}</div></div></div>`);
}

async function render() {
  const page=state.page;$('#page-label').textContent=labels[page];$$('nav a').forEach(a=>a.classList.toggle('active',a.dataset.page===page));
  try {
    if(page==='overview')overview();else if(page==='performance')performance();else if(page==='storage')storagePage(await api('/api/storage'));
    else if(page==='mods')await modsPage();else if(page==='settings')await settingsPage();else if(page==='players')await playersPage();
    else if(page==='console')await consolePage();else if(page==='backups')await backupsPage();else if(page==='connectivity')await connectivityPage();
    else if(page==='graphics')await graphicsPage();else if(page==='compatibility')await compatibilityPage();else if(page==='setup')await setupPage();
    showJobs();
  } catch(error) {$('#main').innerHTML=header(labels[page],'This view needs a little attention.')+notice(error.message,'error');}
}
function showJobs() {
  $('#job-strip')?.remove();const jobs=state.jobs.filter(j=>['running','queued'].includes(j.status));
  if(jobs.length){const node=document.createElement('div');node.id='job-strip';node.className='job-strip';node.innerHTML=`<span class="spinner"></span><div>${jobs.map(j=>`${esc(j.title)}${j.messages.length?` · ${esc(j.messages.at(-1))}`:''}`).join('<br>')}</div>`;$('#main').prepend(node);}
}
async function refresh() {
  if(state.busy)return;state.busy=true;
  try {
    [state.overview,state.jobs]=await Promise.all([api('/api/overview'),api('/api/jobs')]);
    $('#connection').className='connection';$('#connection').innerHTML='<i></i> Connected locally';
    $('#last-update').textContent='Live sample · '+new Date().toLocaleTimeString();
    if(!state.history.length || Date.now()-(state.historyAt||0)>15000){state.history=await api('/api/history?hours=1');state.historyAt=Date.now();}
    for(const j of state.jobs){if(['failed','complete'].includes(j.status)&&!state.seenJobs.has(j.id)){state.seenJobs.add(j.id);toast(j.status==='failed'?`${j.title}: ${j.error}`:`${j.title} finished.`,j.status==='failed');}}
    if(['overview','performance'].includes(state.page))await render();else if(state.page==='storage')storagePage(await api('/api/storage'));else if(state.page==='console')await refreshConsole();
    showJobs();
  }catch(error){$('#connection').className='connection error';$('#connection').innerHTML='<i></i> Connection lost';$('#last-update').textContent='Waiting to reconnect · live data is stale';}
  finally{state.busy=false;}
}

async function versionsDialog(project) {
  const d=await api('/api/mods/versions?project='+encodeURIComponent(project));
  const installed=(await api('/api/mods')).mods.some(m=>m.project_id===d.project.id);
  modal(d.project.title,`<p>${esc(d.project.description)}</p>${row('Client / server',`${esc(d.project.client_side)} / ${esc(d.project.server_side)}`)}<div class="field"><label for="mod-version">Exact NeoForge 1.21.1 version</label><select id="mod-version">${d.versions.map(v=>`<option value="${v.id}">${esc(v.version_number)} · ${v.version_type} · ${v.dependencies.filter(x=>x.dependency_type==='required').length} required dependencies</option>`).join('')}</select></div><label class="check-label"><input id="allow-beta" type="checkbox">Allow a reviewed prerelease for this candidate.</label><p>Staging verifies dependencies and JARs without changing the active server.</p>`,[{label:'Stage for review',run:async()=>{await run('/api/mods/propose',{action:installed?'update':'add',project:d.project.id,version:$('#mod-version').value,allow_prerelease:$('#allow-beta').checked});state.tab='proposals';await modsPage();}}]);
}

document.addEventListener('click',async event=>{
  const tab=event.target.closest('[data-mod-tab]');if(tab){state.tab=tab.dataset.modTab;await modsPage();return;}
  const target=event.target.closest('[data-action]');if(!target)return;const action=target.dataset.action;
  try {
    if(action.startsWith('goto-')){location.hash=action.slice(5);return;}
    if(action==='start')await run('/api/server/start');else if(action==='stop')confirmAction('Let the world rest?','Minecraft will save and flush the world before stopping.',()=>run('/api/server/stop'),'Save & stop');
    else if(action==='restart')confirmAction('Restart the world?','Both players will disconnect while Minecraft saves and restarts.',()=>run('/api/server/restart'),'Restart');
    else if(action==='prism')await run('/api/open',{target:'prism'});
    else if(action==='backup')confirmAction('Keep a safe snapshot?','If the server is online, it will stop to flush its world, create and verify a backup, then resume.',()=>run('/api/backups/create'),'Create backup');
    else if(action==='health'){const d=await run('/api/health');modal('Health check started','<p>The result will appear in the task history. You can export a diagnostic bundle from Console & logs.</p>');}
    else if(action==='diagnostics')location.href='/api/export/metrics.csv';
    else if(action==='profile')await run('/api/diagnostics/start');
    else if(action==='refresh-storage')storagePage(await api('/api/storage'));
    else if(action==='mod-versions')await versionsDialog(target.dataset.project);
    else if(action==='mod-remove')confirmAction('Remove '+target.dataset.name+'?','A proposal will check dependent mods and flag saved-world content risks. This does not remove anything from the running server.',async()=>{await run('/api/mods/propose',{action:'remove',project:target.dataset.project});state.tab='proposals';await modsPage();},'Stage removal');
    else if(action==='proposal-review') {const p=(await api('/api/proposals')).find(x=>x.id===target.dataset.id);modal('Review '+p.version,`<p>${esc(p.warning)}</p><pre>${esc(JSON.stringify(p.changes,null,2))}</pre>${p.static_errors.length?notice(p.static_errors.join('; '),'error'):notice('Static checks passed. Runtime acceptance is still required.','warn')}<div class="field"><label>Published immutable client pack URL</label><input id="release-url" value="https://kgray44.github.io/a-world-for-two/releases/${esc(p.version)}/pack.toml"></div><div class="field"><label>Type DEPLOY ${esc(p.version)}</label><input id="deploy-confirm"></div>`,[{label:'Approve & deploy',run:()=>run('/api/mods/deploy',{id:p.id,confirmation:$('#deploy-confirm').value,publication_url:$('#release-url').value})}]);}
    else if(action==='proposal-rollback') {modal('Roll back this release?',`<p>Stop the server first. A world backup is made before the previous manifest and server mods are restored. Publish the matching prior client pointer before players relaunch.</p><div class="field"><label>Type ROLLBACK ${esc(target.dataset.version)}</label><input id="rollback-confirm"></div>`,[{label:'Roll back',kind:'danger',run:()=>run('/api/mods/rollback',{id:target.dataset.id,confirmation:$('#rollback-confirm').value})}]);}
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
    else if(form.classList.contains('settings-form')){const schema=await api('/api/settings'),scope=form.dataset.scope,changes={};for(const f of schema.fields.filter(x=>x.scope===scope)){const input=form.elements.namedItem(f.key);const value=f.type==='boolean'?input.checked:f.type==='integer'?Number(input.value):input.value;if(value!==f.current)changes[f.key]=value;}if(!Object.keys(changes).length){toast('Everything is already saved.');return;}await run('/api/settings',{scope,changes});}
    else if(form.id==='raw-open'){state.raw=await api('/api/config/raw?path='+encodeURIComponent(fd.get('path')));$('#raw-editor').innerHTML=`<textarea id="raw-content" aria-label="Raw configuration contents" spellcheck="false">${esc(state.raw.content)}</textarea><div class="button-row">${button('raw-diff','Review diff','primary')}</div>`;}
    else if(form.id==='console-command'){const command=fd.get('command');const dangerous=/^(op |deop |kick |whitelist remove |gamerule |difficulty |chunky cancel)/.test(command.replace(/^\//,''));if(dangerous)confirmAction('Send this command?',command,()=>run('/api/console',{command,confirmed:true}),'Send command');else await run('/api/console',{command});form.reset();}
    else if(form.id==='tunnel-address')await run('/api/connectivity',{address:fd.get('address')});
  }catch(error){toast(error.message,true);}
});
document.addEventListener('input',event=>{const e=event.target;if(e.id==='inventory-filter')$$('[data-inventory-name]').forEach(r=>r.classList.toggle('hidden',!r.dataset.inventoryName.includes(e.value.toLowerCase())));if(e.id==='compat-filter')$$('[data-compat-text]').forEach(r=>r.classList.toggle('hidden',!r.dataset.compatText.includes(e.value.toLowerCase())));if(e.id==='log-query')refreshConsole().catch(e=>toast(e.message,true));});
document.addEventListener('change',event=>{if(event.target.id==='log-level')refreshConsole().catch(e=>toast(e.message,true));});
window.addEventListener('hashchange',()=>{state.page=labels[location.hash.slice(1)]?location.hash.slice(1):'overview';document.body.classList.remove('menu-open');render();});
window.addEventListener('resize',()=>{if(state.page==='overview')chart('overview-chart',state.history,'tps');if(state.page==='performance'){chart('tps-chart',state.history,'tps');chart('cpu-chart',state.history,'host_cpu','server_cpu');}});
$('#modal-close').onclick=()=>$('#modal').close();$('#menu').onclick=()=>document.body.classList.toggle('menu-open');
(async()=>{try{const bootstrap=await api('/api/bootstrap');state.csrf=bootstrap.csrf;state.page=labels[location.hash.slice(1)]?location.hash.slice(1):'overview';await refresh();await render();setInterval(refresh,3000);}catch(error){$('#main').innerHTML=header('Your world is taking a moment.','Open Control Room with the local launch script.')+notice(error.message,'error');}})();
