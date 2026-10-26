import test from 'node:test';
import assert from 'node:assert/strict';
import {LocalSession} from '../control_room/static/session.js';

const bootstrap=(csrf='old',home='D:/our-world')=>({app_id:'awft-control-room',home,csrf});
const response=(status,data)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});

test('an expired token refreshes once, preserving the exact rejected mutation',async()=>{
  const calls=[];
  const client=new LocalSession(async(path,options)=>{
    calls.push({path,options});
    if(path==='/api/bootstrap')return response(200,bootstrap('new'));
    return options.headers.get('X-AWFT-CSRF')==='old'?response(403,{code:'session_expired'}):response(200,{saved:true});
  });
  client.bind(bootstrap());
  const body=JSON.stringify({setting:'value'});
  const result=await client.request('/api/settings',{method:'POST',body});
  assert.equal(result.status,200);
  assert.equal(calls.length,3);
  assert.equal(calls[0].options.body,body);
  assert.equal(calls[2].options.body,body);
  assert.equal(calls[2].options.headers.get('X-AWFT-CSRF'),'new');
});

test('origin rejections, server errors and network ambiguity never replay a mutation',async()=>{
  for(const failure of ['origin','server','network']){
    let count=0;
    const client=new LocalSession(async()=>{count++;if(failure==='network')throw new Error('Connection lost');return failure==='origin'?response(403,{code:'local_origin_required'}):response(500,{error:'unknown outcome'});});
    client.bind(bootstrap());
    if(failure==='network')await assert.rejects(client.request('/api/backup',{method:'POST',body:'{}'}));
    else assert.equal((await client.request('/api/backup',{method:'POST',body:'{}'})).status,failure==='origin'?403:500);
    assert.equal(count,1);
  }
});

test('a different world at the same address requires fresh human review',async()=>{
  let mutations=0;
  const client=new LocalSession(async path=>path==='/api/bootstrap'?response(200,bootstrap('new','D:/different-world')):(mutations++,response(403,{code:'session_expired'})));
  client.bind(bootstrap());
  await assert.rejects(client.request('/api/server/start',{method:'POST',body:'{}'}),/different world/);
  assert.equal(mutations,1);
});

test('image uploads recover the session without changing the original bytes',async()=>{
  const payload=new Uint8Array([137,80,78,71,0,255]);let uploads=0;
  const client=new LocalSession(async(path,options)=>{
    if(path==='/api/bootstrap')return response(200,bootstrap('new'));
    uploads++;assert.equal(options.body,payload);assert.equal(options.headers.get('Content-Type'),'image/png');
    return uploads===1?response(403,{code:'session_expired'}):response(200,{saved:true});
  });
  client.bind(bootstrap());
  assert.equal((await client.request('/api/cinematics/background',{method:'POST',headers:{'Content-Type':'image/png'},body:payload})).status,200);
  assert.equal(uploads,2);
});
