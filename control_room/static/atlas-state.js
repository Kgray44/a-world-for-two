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
    cache:{...data.cache,current:currentMeasurement({measured_at:data.cache?.measured_at,current:data.cache?.current,max_age_seconds:60},now)},
    integrations:(data.integrations||[]).map(row=>({...row,status:row.status==='current'&&!(row.name==='Open Parties and Claims'?claims&&data.claims?.available:bridge)?'unavailable':row.status})),
    claims:claims?data.claims:{available:false,items:[],unavailable:'Current claim boundaries are unavailable. Refreshing server observations…'},
    bridgeCurrent:bridge,
  };
}

export function playerView(value,now=Date.now()) {
  const responseCurrent=Number.isFinite(value?.received_at)&&now-value.received_at>=-2000&&now-value.received_at<=15000;
  const locationCurrent=currentMeasurement({measured_at:value?.location?.at,current:value?.location_state==='live',max_age_seconds:15},now);
  if(responseCurrent&&(value.online!==true||!value.location||locationCurrent))return value;
  return {...value,online:null,online_state:'unknown',location_state:value?.location?'last seen':'not available',capabilities:[]};
}
