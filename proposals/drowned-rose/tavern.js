// Proposed module for Control Room's existing card/table design system.
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export async function mountTavern({root,api,toast}) {
  let closed=false,timer;
  async function render(){
    try {
      const data=await api('/api/tavern');if(closed)return;
      root.innerHTML=`<div class="page-head"><div><div class="eyebrow">TORTUGA</div><h1>The Drowned Rose</h1><p class="subtle">Residents, conversations and the tavern ensemble.</p></div></div>`+
        (!data.current?`<div class="notice warn">${esc(data.reason)}. Controls are unavailable.</div>`:'')+
        `<section class="card"><div class="card-head"><h2>Tavern company</h2><span class="pill">${data.residents.filter(r=>r.loaded).length} present · ${data.residents.filter(r=>r.registered).length} registered</span></div>`+
        `<p class="subtle">${esc(data.fault||'')} ${data.suspended?'Resting while the tavern is inactive.':''}</p>`+
        `<button class="button" data-music="${!data.music}" ${data.current?'':'disabled'}>${data.music?'Pause performances':'Enable performances'}</button>`+
        `<div class="table-wrap"><table><thead><tr><th>Resident</th><th>Activity</th><th>Destination</th><th>Identity</th><th>Controls</th></tr></thead><tbody>`+
        data.residents.map(r=>`<tr><td>${esc(r.name)}</td><td>${esc(r.activity)}</td><td>${esc(r.destination)}</td><td><small>${esc(r.uuid)}</small><br>${r.loaded?'Present':'Unloaded'} · ${r.registered?'Registered':'Unregistered'}</td><td><button class="button small" data-id="${esc(r.id)}" data-enabled="${r.disabled}" ${data.current?'':'disabled'}>${r.disabled?'Enable':'Rest'}</button> <button class="button small ghost" data-recover="${esc(r.id)}" ${data.current?'':'disabled'}>Recover if stuck</button></td></tr>`).join('')+
        `</tbody></table></div></section><section class="card"><div class="card-head"><h2>Activity measurements</h2></div><p>${esc(data.decisions??'—')} decisions · ${esc(data.path_requests??'—')} path requests · ${esc(data.path_refusals??'—')} refused paths · ${esc(data.recovery_teleports??'—')} recoveries</p><p class="subtle">These counters describe the scheduler. Overall tick cost and two-player music acceptance require separate game measurements.</p></section>`;
    } catch(e){if(!closed)root.innerHTML=`<div class="notice warn">${esc(e.message)}</div>`;}
    if(!closed)timer=setTimeout(render,5000);
  }
  async function click(event){
    const button=event.target.closest('button');if(!button||button.disabled)return;
    let body;
    if(button.dataset.music!==undefined)body={action:'music',enabled:button.dataset.music==='true'};
    else if(button.dataset.enabled!==undefined)body={action:'enabled',id:button.dataset.id,enabled:button.dataset.enabled==='true'};
    else if(button.dataset.recover)body={action:'recover',id:button.dataset.recover};
    else return;
    button.disabled=true;
    try{await api('/api/tavern/control',body);toast('Request sent; the next live reading shows the result.');}
    catch(e){toast(e.message,'error');button.disabled=false;}
  }
  root.addEventListener('click',click);await render();
  return ()=>{closed=true;clearTimeout(timer);root.removeEventListener('click',click);};
}
