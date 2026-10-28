/* A rejected request may recover once; ambiguous failures are never replayed. */
export class LocalSession {
  constructor(fetcher=globalThis.fetch.bind(globalThis),changed=()=>{}){this.fetcher=fetcher;this.changed=changed;this.home=null;this.token='';this.refreshing=null;}
  bind(bootstrap){
    if(bootstrap.app_id!=='awft-control-room'||typeof bootstrap.home!=='string'||typeof bootstrap.csrf!=='string')throw new Error('Control Room session could not be verified. Reload this page.');
    if(this.home!==null&&bootstrap.home!==this.home)throw new Error('This address now manages a different world. Reload the page and review it before making changes.');
    this.home=bootstrap.home;this.token=bootstrap.csrf;this.changed(this.token);
  }
  async refresh(){
    if(!this.refreshing)this.refreshing=(async()=>{const response=await this.fetcher('/api/bootstrap',{cache:'no-store',signal:AbortSignal.timeout(15000)});if(!response.ok)throw new Error('Control Room restarted. Reload this page to reconnect.');this.bind(await response.json());})().finally(()=>{this.refreshing=null;});
    return this.refreshing;
  }
  async request(path,options={}){
    if(typeof path!=='string'||!path.startsWith('/api/'))throw new Error('Control Room requests must use its local API.');
    const mutate=(options.method||'GET').toUpperCase()==='POST';
    const send=()=>{const headers=new Headers(options.headers||{});if(mutate)headers.set('X-AWFT-CSRF',this.token);return this.fetcher(path,{cache:'no-store',...options,headers,signal:options.signal||AbortSignal.timeout(15000)});};
    const sentToken=this.token;
    let response=await send();
    if(response.status===403&&mutate){
      const error=await response.clone().json().catch(()=>({}));
      // This response is emitted before any mutation. No timeout, 5xx, accepted
      // operation or origin rejection is automatically retried.
      if(error.code==='session_expired'||(!error.code&&error.error==='Local origin and current session token required')){
        if(this.token===sentToken)await this.refresh();
        if(this.token!==sentToken)response=await send();
      }
    }
    return response;
  }
}
