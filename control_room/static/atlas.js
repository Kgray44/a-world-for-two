/* Loaded only when World Atlas is opened. Leaflet renders existing squaremap tiles. */
let ctx, map, tiles, marks, claimMarks, timer, data, dimension='minecraft:overworld', picked, loaded;
const symbols={home:'⌂',heart:'♥',anchor:'⚓',tree:'♠',treasure:'◆',train:'▣',star:'★',danger:'!',grave:'†',pin:'●',player:'➤',pet:'♧',vehicle:'⚓',structure:'◇',death:'†'};
const titles={'minecraft:overworld':'Overworld','minecraft:the_nether':'Nether','minecraft:the_end':'The End'};
const el=id=>document.getElementById(id);
const latLng=p=>[-p.z/8,p.x/8];
function coordinates(p){return `${Math.round(p.x)}, ${p.y==null?'surface':Math.round(p.y)}, ${Math.round(p.z)}`;}
function collection(){return el('atlas-collection')?.value||'all';}
async function leaflet(){
  if(window.L)return;
  if(!loaded)loaded=new Promise((resolve,reject)=>{
    const css=document.createElement('link');css.rel='stylesheet';css.href='/vendor/leaflet.css';document.head.append(css);
    const script=document.createElement('script');script.src='/vendor/leaflet.js';script.onload=resolve;script.onerror=()=>reject(new Error('The local map library could not load'));document.head.append(script);
  });
  await loaded;
}
export function unmount(){clearTimeout(timer);timer=null;if(map){map.remove();map=null;}ctx=null;}
export async function mount(helpers){
  unmount();ctx=helpers;const {esc,header,button}=ctx;
  data=await ctx.api('/api/atlas');await leaflet();
  if(!ctx)return;
  el('main').innerHTML=header('World Atlas','Your travels, little landmarks, and the way home.')+
    `<div class="atlas-toolbar"><label>Dimension<select id="atlas-dimension">${Object.entries(titles).map(([id,name])=>`<option value="${id}">${name}</option>`).join('')}</select></label><label>Collection<select id="atlas-collection"><option value="all">All collections</option><option value="shared">Shared</option><option value="KG">KG’s personal</option><option value="Sera">Sera’s personal</option></select></label><label class="atlas-search">Find a place<input id="atlas-search" placeholder="Name, temple, civilization, notes, or X, Z" type="search"></label><label>Category<select id="atlas-category"><option value="">All categories</option></select></label><label>Exploration<select id="atlas-exploration"><option value="">Any status</option><option>unknown</option><option>unexplored</option><option>explored</option></select></label><button class="button" id="atlas-go">Find coordinates</button><button class="button primary" id="atlas-new">Add waypoint</button><button class="button" id="atlas-return">Return from teleport…</button></div>`+
    `<div class="atlas-layout"><section class="card atlas-map-card"><div class="atlas-legend"><span>Rendered terrain · blank areas have no tiles</span><span id="atlas-coordinates">Move over the map for coordinates</span></div><div id="world-map" aria-label="Interactive world map"></div><div class="atlas-pick" id="atlas-picked">Click the map to choose a waypoint or a safe teleport destination.</div><div class="atlas-layer-options"><label><input type="checkbox" id="atlas-structures" checked> Known structures</label><label><input type="checkbox" id="atlas-objects" checked> Loaded pets & vehicles</label><label><input type="checkbox" id="atlas-deaths" checked> Deaths</label><label><input type="checkbox" id="atlas-claims" checked> Protected claims</label><span class="subtle" id="atlas-claim-status"></span></div></section><aside class="card atlas-places"><div class="card-head"><h2>People & places</h2><span class="pill" id="atlas-count"></span></div><div id="atlas-results"></div></aside></div>`+
    `<section class="card"><div class="card-head"><h2>A gentle footprint</h2><button class="button small" id="atlas-pause"></button></div><div id="atlas-measurements" class="atlas-measurements"></div><details><summary>Rendering & collections</summary><p class="subtle">${esc(data.boundary)}</p><p class="subtle">${esc(data.xaero_sync)}</p><p class="subtle">${esc(data.interval_note)}</p><div class="atlas-toolbar"><label>Refresh (seconds)<input id="atlas-refresh" type="number" min="2" max="5"></label><label>Cache limit (MiB)<input id="atlas-cache" type="number" min="64" max="2048"></label><label>Chunks per interval<input id="atlas-chunks" type="number" min="1" max="64"></label><label>Interval (seconds)<input id="atlas-interval" type="number" min="15" max="120"></label><button class="button" id="atlas-settings">Save limits</button></div><div class="button-row"><button class="button" id="atlas-export">Export selected collection</button><button class="button" id="atlas-import">Import collection</button><button class="button danger" id="atlas-clear">Clear rendered cache</button></div><p class="subtle">Cache cleanup requires the server to be stopped. It removes rendered PNG tiles; explored world data is preserved.</p></details></section>`;
  el('atlas-dimension').value=dimension;
  map=L.map('world-map',{crs:L.CRS.Simple,minZoom:0,maxZoom:5,attributionControl:true,preferCanvas:true});
  map.attributionControl.setPrefix('Leaflet');
  claimMarks=L.layerGroup().addTo(map);marks=L.layerGroup().addTo(map);switchDimension(false);
  map.on('mousemove',event=>el('atlas-coordinates').textContent=`X ${Math.round(event.latlng.lng*8)} · Z ${Math.round(-event.latlng.lat*8)}`);
  map.on('click',event=>{picked={dimension,x:Math.round(event.latlng.lng*8),y:null,z:Math.round(-event.latlng.lat*8)};el('atlas-picked').replaceChildren();const text=document.createElement('span');text.textContent=`Selected ${titles[dimension]} · ${coordinates(picked)} `;el('atlas-picked').append(text);for(const [label,action]of [['Save waypoint',()=>edit(picked)],['Teleport…',()=>teleport(picked)]]){const b=document.createElement('button');b.className='button small';b.textContent=label;b.onclick=action;el('atlas-picked').append(b);}});
  el('atlas-dimension').onchange=()=>{dimension=el('atlas-dimension').value;switchDimension(true);renderPlaces();};
  for(const id of ['atlas-collection','atlas-search','atlas-structures','atlas-objects','atlas-deaths','atlas-claims','atlas-category','atlas-exploration'])el(id).addEventListener(id==='atlas-search'?'input':'change',renderPlaces);
  el('atlas-go').onclick=()=>{const match=el('atlas-search').value.match(/^\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*$/);if(!match||Math.abs(+match[1])>29999984||Math.abs(+match[2])>29999984){ctx.toast('Enter X, Z, such as 128, -64.',true);return;}map.setView([-Number(match[2])/8,Number(match[1])/8],3);};
  el('atlas-new').onclick=()=>edit(picked||{dimension,x:Math.round(map.getCenter().lng*8),y:null,z:Math.round(-map.getCenter().lat*8)});
  el('atlas-return').onclick=()=>teleport({name:'Previous position',return:true});
  el('atlas-pause').onclick=async()=>{await mutate('/api/atlas/settings',{changes:{paused:!data.options.paused}});};
  el('atlas-settings').onclick=async()=>{try{await mutate('/api/atlas/settings',{changes:{refresh_seconds:Number(el('atlas-refresh').value),cache_limit_mib:Number(el('atlas-cache').value),chunks_per_interval:Number(el('atlas-chunks').value),interval_seconds:Number(el('atlas-interval').value)}});}catch(e){ctx.toast(e.message,true);}};
  el('atlas-export').onclick=()=>{const c=collection()==='all'?'shared':collection();window.location.href='/api/atlas/export?collection='+encodeURIComponent(c);};
  el('atlas-import').onclick=()=>ctx.modal('Import waypoint collection','<p>Paste a collection exported from World Atlas. Up to 500 waypoints can be added at once.</p><label>Collection JSON<textarea id="atlas-import-json" rows="10"></textarea></label>',[{label:'Import waypoints',run:async()=>{const value=JSON.parse(el('atlas-import-json').value);await mutate('/api/atlas/import',{data:value,expected:data.revision});}}]);
  el('atlas-clear').onclick=()=>ctx.confirmAction('Clear rendered map cache?','Stop the server first. The atlas will become blank until squaremap renders the explored areas again.',()=>mutate('/api/atlas/clear-cache',{confirmed:true}),'Clear cached tiles');
  for(const [id,key]of [['atlas-refresh','refresh_seconds'],['atlas-cache','cache_limit_mib'],['atlas-chunks','chunks_per_interval'],['atlas-interval','interval_seconds']])el(id).value=data.options[key];
  renderPlaces();measurements();schedule();
}
function switchDimension(center){
  if(tiles)map.removeLayer(tiles);
  const world=data.worlds.find(w=>w.id===dimension);
  const stamp=Math.floor((data.cache.last_update||0)/30);
  tiles=L.tileLayer(`/atlas/tiles/${world.slug}/{z}/{x}_{y}.png?v=${stamp}`,{tileSize:512,minZoom:0,maxZoom:5,maxNativeZoom:3,noWrap:true,keepBuffer:1,errorTileUrl:'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',attribution:'squaremap · existing world chunks'}).addTo(map);
  if(center||!map._loaded){const spawn=world.spawn||{x:0,z:0};map.setView(latLng(spawn),2);}
}
function allPlaces(){
  const c=collection(),q=el('atlas-search').value.trim().toLowerCase();
  const players=data.players.filter(p=>p.location).map(p=>({...p.location,id:'player:'+p.uuid,name:p.name,kind:'player',online:p.online,player:p.name,state:p.location_state}));
  const waypoints=data.waypoints.filter(w=>c==='all'||w.collection===c).map(w=>({...w,kind:'waypoint'}));
  const category=el('atlas-category').value,status=el('atlas-exploration').value;
  const claimGroups=new Map();if(el('atlas-claims')?.checked)for(const claim of data.claims?.items||[]){const key=`${claim.dimension}:${claim.owner}:${claim.name}`;if(!claimGroups.has(key))claimGroups.set(key,{id:'claim:'+key,dimension:claim.dimension,name:claim.name||claim.owner,kind:'claim',category:'Protected territory',x:claim.chunk_x*16+8,z:claim.chunk_z*16+8,y:null,color:claim.color,state:'server claim record'});}
  return [...players,...waypoints,...claimGroups.values(),...(el('atlas-structures').checked?data.locations.filter(p=>p.kind==='structure'):[]),...(el('atlas-deaths').checked?data.locations.filter(p=>p.kind==='death'):[]),...(el('atlas-objects').checked?[...data.objects,...data.locations.filter(p=>p.kind==='known object'&&!data.objects.some(o=>o.id===p.id))]:[])].filter(p=>p.dimension===dimension&&(!category||p.category===category)&&(!status||(p.exploration||'unknown')===status)&&(!q||`${p.name} ${p.type||''} ${p.category||''} ${p.civilization||''} ${p.notes||''} ${p.kind}`.toLowerCase().includes(q)));
}
function renderClaims(){
  claimMarks.clearLayers();if(!el('atlas-claims')?.checked||!data.claims?.available)return;
  const query=el('atlas-search').value.trim().toLowerCase();
  for(const claim of data.claims.items){
    if(claim.dimension!==dimension||query&&!`${claim.name} ${claim.owner}`.toLowerCase().includes(query))continue;
    const popup=document.createElement('div'),title=document.createElement('strong'),detail=document.createElement('p');title.textContent=claim.name||'Protected territory';detail.textContent=`Claimed chunk ${claim.chunk_x}, ${claim.chunk_z} · ${claim.owner}${claim.forceloadable?' · marked as eligible for force loading':''}. A claim boundary does not mean this chunk is loaded.`;popup.append(title,detail);
    L.rectangle([latLng({x:claim.chunk_x*16,z:claim.chunk_z*16}),latLng({x:claim.chunk_x*16+16,z:claim.chunk_z*16+16})],{color:claim.color,weight:1,fillOpacity:.13}).addTo(claimMarks).bindPopup(popup);
  }
}
function renderPlaces(){
  if(!map)return;
  renderClaims();
  const categories=el('atlas-category'),current=categories.value;
  categories.replaceChildren(new Option('All categories',''),...[...new Set([...data.waypoints,...data.locations].map(p=>p.category).filter(Boolean))].sort().map(v=>new Option(v,v)));
  categories.value=current;
  marks.clearLayers();const places=allPlaces(),list=el('atlas-results');list.replaceChildren();el('atlas-count').textContent=places.length;
  for(const place of places){
    const icon=document.createElement('span');icon.className='atlas-marker '+(place.kind==='player'?'atlas-player':'');icon.textContent=symbols[place.icon||place.kind]||'●';icon.title=place.name;icon.style.color=place.color||'#335e4b';if(place.kind==='player')icon.style.transform=`rotate(${Number(place.yaw||0)+90}deg)`;
    const marker=L.marker(latLng(place),{icon:L.divIcon({html:icon,iconSize:[28,28],iconAnchor:[14,14],className:'atlas-icon'}),title:place.name}).addTo(marks);
    const popup=document.createElement('div');const title=document.createElement('strong');title.textContent=place.name;popup.append(title,document.createElement('br'));const detail=document.createElement('span');detail.textContent=`${place.kind} · ${coordinates(place)}${place.state?' · '+place.state:''}`;popup.append(detail);
    const actions=document.createElement('div');actions.className='button-row';
    if(place.kind==='structure'||place.kind==='waypoint'||place.kind==='death'){
      const journal=document.createElement('p');journal.className='subtle';journal.textContent=`${place.provenance||'manual waypoint'} · ${place.category||'Places'}${place.civilization?' · '+place.civilization:''} · ${place.exploration||'unknown'}${place.at?' · first recorded '+new Date(place.at).toLocaleString():''}${place.notes?'\n'+place.notes:''}`;popup.append(journal);
    }
    const choices=[[place.kind==='waypoint'?'Edit':'Save waypoint',()=>edit(place)],['Teleport…',()=>teleport(place)]];
    if(data.locations.some(p=>p.id===place.id))choices.unshift(['Notes & status',()=>annotate(place)]);
    choices.push(['Cinematic trigger…',()=>cinematicTrigger(place)]);
    for(const [label,action]of choices){const b=document.createElement('button');b.className='button small';b.textContent=label;b.onclick=action;actions.append(b);}popup.append(actions);marker.bindPopup(popup);
    if(list.childElementCount<100){const b=document.createElement('button');b.className='atlas-result';const strong=document.createElement('strong');strong.textContent=place.name;const small=document.createElement('small');small.textContent=`${place.kind} · ${coordinates(place)}${place.state?' · '+place.state:''}`;b.append(strong,small);b.onclick=()=>{map.setView(latLng(place),3);marker.openPopup();};list.append(b);}
  }
  if(!places.length){const p=document.createElement('p');p.className='subtle';p.textContent='No matching places in this dimension. Add a waypoint, or explore with the server running.';list.append(p);}
  if(places.length>100){const p=document.createElement('p');p.className='subtle';p.textContent='Showing the first 100 results. Narrow your search to find a place.';list.append(p);}
}
function edit(place){
  const {esc,modal}=ctx;const existing=place.kind==='waypoint'||data.waypoints.some(w=>w.id===place.id);
  const select=(id,values,current)=>`<select id="${id}">${values.map(v=>`<option value="${esc(v)}"${v===current?' selected':''}>${esc(v)}</option>`).join('')}</select>`;
  modal(existing?'Edit waypoint':'A new little landmark',`<div class="form-grid"><label>Name<input id="wp-name" maxlength="80" value="${esc(place.name||'')}"></label><label>Category<input id="wp-category" maxlength="40" value="${esc(place.category||'Places')}"></label><label>Collection${select('wp-collection',['shared','KG','Sera'],place.collection||'shared')}</label><label>Dimension${select('wp-dimension',Object.keys(titles),place.dimension)}</label><label>X<input id="wp-x" type="number" value="${Number(place.x)}"></label><label>Y (blank uses surface)<input id="wp-y" type="number" value="${place.y==null?'':Number(place.y)}"></label><label>Z<input id="wp-z" type="number" value="${Number(place.z)}"></label><label>Icon${select('wp-icon',data.icons,place.icon||'pin')}</label><label>Color<input id="wp-color" type="color" value="${esc(place.color||'#bc985b')}"></label>${journalForm(place)}</div><p class="subtle">Saved coordinates are manual waypoints. Verified structure records keep their server evidence separately.</p>`,[
    ...(existing?[{label:'Delete',kind:'danger',run:async()=>{await mutate('/api/atlas/remove',{id:place.id,expected:data.revision,confirmed:true});}}]:[]),
    {label:'Save waypoint',run:async()=>{const waypoint={id:existing?place.id:undefined,name:el('wp-name').value,category:el('wp-category').value,collection:el('wp-collection').value,dimension:el('wp-dimension').value,x:Number(el('wp-x').value),y:el('wp-y').value===''?null:Number(el('wp-y').value),z:Number(el('wp-z').value),icon:el('wp-icon').value,color:el('wp-color').value,...journalValue()};await mutate('/api/atlas/waypoint',{waypoint,expected:data.revision});}}
  ]);
}
function journalForm(place){return `<label>Civilization or theme<input id="landmark-civilization" maxlength="60" value="${ctx.esc(place.civilization||'')}"></label><label>Exploration<select id="landmark-exploration">${['unknown','unexplored','explored'].map(v=>`<option${v===(place.exploration||'unknown')?' selected':''}>${v}</option>`).join('')}</select></label><label class="wide">Your notes<textarea id="landmark-notes" rows="4" maxlength="2000">${ctx.esc(place.notes||'')}</textarea></label>`;}
function journalValue(){return {civilization:el('landmark-civilization').value,exploration:el('landmark-exploration').value,notes:el('landmark-notes').value};}
function annotate(place){ctx.modal('Landmark journal',`<p><strong>${ctx.esc(place.name)}</strong><br>${coordinates(place)} · ${ctx.esc(place.evidence||'Server-observed location')}</p><div class="form-grid"><label>Category<input id="landmark-category" maxlength="40" value="${ctx.esc(place.category||'Structures')}"></label>${journalForm(place)}</div><p class="subtle">Unknown means nobody has recorded an exploration status. Notes preserve the verified coordinates and first observation date.</p>`,[{label:'Save notes',run:()=>mutate('/api/atlas/annotation',{id:place.id,annotation:{category:el('landmark-category').value,...journalValue()},expected:data.annotations_revision})}]);}
async function cinematicTrigger(place){
  try{const c=await ctx.api('/api/cinematics'),scenes=c.runtime?.scenes||[];if(!scenes.length){ctx.toast('Start the updated server to discover its available cinematic scenes.',true);return;}
    ctx.modal('Cinematic at this landmark',`<p>${ctx.esc(place.name||'Selected point')} · ${coordinates(place)}</p><label>Scene<select id="landmark-scene">${scenes.map(s=>`<option value="${ctx.esc(s.id)}">${ctx.esc(s.id)}</option>`).join('')}</select></label><p class="subtle">Creates a disabled arrival trigger with a ten-minute cooldown. Review and enable it on Cinematics.</p>`,[{label:'Create trigger',run:()=>ctx.api('/api/cinematics/trigger',{location:{dimension:place.dimension,x:place.x,y:place.y,z:place.z},scene:el('landmark-scene').value,enabled:false,expected:c.revision}).then(()=>ctx.toast('Trigger saved. Review it on Cinematics.'))}]);
  }catch(e){ctx.toast(e.message,true);}
}
function teleport(place){
  const online=data.players.filter(p=>p.online),{esc,modal}=ctx;
  if(!online.length){ctx.toast('Safe teleport needs an online player and current bridge telemetry.',true);return;}
  const surface=(data.teleport_modes||[]).includes('surface')&&place.dimension!=='minecraft:the_nether';
  const modes=place.return?'':`<label>Landing<select id="atlas-landing">${surface?'<option value="surface">Find safe dry surface nearby</option>':''}<option value="near-y">Near a known Y coordinate</option></select></label><label>Y coordinate (used for known-height landing)<input id="atlas-landing-y" type="number" min="-2047" max="2047" value="${place.y==null?'':Number(place.y)}" placeholder="Required for Nether or indoor locations"></label>`;
  modal('Confirm a safe teleport',`<p>Destination: <strong>${esc(place.name||'Selected map point')}</strong><br>${place.return?'The saved position before your last administrator teleport.':esc(titles[place.dimension])+' · '+coordinates(place)}</p><label>Move this online player<select id="atlas-teleport-player">${online.map(p=>`<option>${esc(p.name)}</option>`).join('')}</select></label>${modes}<p class="subtle">The server checks solid dry ground, headroom, nearby hazards and the world border. A safe landing may be up to eight blocks from the selected point, inside one destination chunk. Your previous position is saved.${place.dimension==='minecraft:the_nether'?' Enter a known safe Y in the Nether; the roof is refused.':''}${!surface&&!place.return&&place.dimension!=='minecraft:the_nether'?' Surface search becomes available after the server bridge update.':''}</p>`,[{label:'Confirm safe teleport',run:async()=>{const mode=el('atlas-landing')?.value,raw=el('atlas-landing-y')?.value;await mutate('/api/atlas/teleport',{name:el('atlas-teleport-player').value,destination:place.return?{return:true}:{dimension:place.dimension,x:place.x,y:mode==='surface'||raw===''?null:Number(raw),z:place.z,landing:mode},confirmed:true});}}]);
}
function measurements(){
  const r=data.renderer||{},fmt=ctx.bytes;el('atlas-measurements').textContent=`Tiles ${data.cache.tiles.toLocaleString()} · Cache ${fmt(data.cache.bytes)} / ${data.options.cache_limit_mib} MiB · Index ${fmt(data.index_bytes)} · Queue ${r.queued_chunks??'unavailable'} · Renderer CPU ${r.cpu_percent_one_core==null?'unavailable':r.cpu_percent_one_core.toFixed(1)+'% of one core'} · ${r.unavailable|| (r.paused?'Rendering paused':r.source?'Rendering available':'Renderer telemetry appears after startup')}`;
  el('atlas-pause').textContent=data.options.paused?'Resume rendering':'Pause rendering';
  const claims=el('atlas-claim-status');if(claims){const c=data.claims;claims.textContent=c?.available?`${c.items.length} claimed chunks${c.truncated?' · partial bounded snapshot':''} · updated ${new Date(c.at).toLocaleTimeString()} · ${c.measurement_ms.toFixed(2)} ms query`:(c?.unavailable||'Claim boundaries need the updated server bridge.');}
}
async function mutate(path,body){const result=await ctx.api(path,body);ctx.toast(result.job?'Task queued; check Task history.':'Atlas saved.');data=await ctx.api('/api/atlas');renderPlaces();measurements();return result;}
function schedule(){clearTimeout(timer);timer=setTimeout(async()=>{if(!ctx||!el('world-map'))return;try{const before=data.cache.last_update;data=await ctx.api('/api/atlas');if(data.cache.last_update!==before)tiles.setUrl(`/atlas/tiles/${data.worlds.find(w=>w.id===dimension).slug}/{z}/{x}_{y}.png?v=${Math.floor((data.cache.last_update||0)/30)}`);renderPlaces();measurements();}catch(error){ctx.toast(error.message,true);}schedule();},(data.options.refresh_seconds||5)*1000);}
