/* Response timestamps keep old coordinates from becoming a current location. */
export function currentMeasurement(info, now=Date.now()) {
  const stamp=typeof info?.measured_at==='number'?info.measured_at*1000:Date.parse(info?.measured_at);
  const age=(now-stamp)/1000;
  return info?.current===true&&Number.isFinite(age)&&age>=-2&&age<=info.max_age_seconds;
}
export function atlasView(data,now=Date.now()) {
  const bridge=currentMeasurement(data.freshness?.bridge,now);
  const players=bridge&&currentMeasurement(data.freshness?.players,now);
  const stopped=data.players_state==='offline'&&currentMeasurement({measured_at:data.players_measured_at,current:true,max_age_seconds:15},now);
  const claims=bridge&&currentMeasurement(data.freshness?.atlas_claims,now);
  return {...data,
    players:(data.players||[]).map(p=>({...p,online:players?p.online:stopped?false:null,
      location_state:players?p.location_state:p.location?'last seen':'not available'})),
    objects:(data.objects||[]).map(p=>({...p,state:bridge?p.state:'last seen'})),
    renderer:bridge?data.renderer:null,
    claims:claims?data.claims:{available:false,items:[],unavailable:'Current claim boundaries are unavailable. Refreshing server observations…'},
    bridgeCurrent:bridge,
  };
}
