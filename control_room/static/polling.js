/* One request at a time. Hidden tabs sleep; failures back off without replaying actions. */
export class VisiblePoller {
  constructor(work,{delay=()=>5000,hidden=()=>document.hidden,events=document,schedule=(fn,ms)=>setTimeout(fn,ms),cancel=id=>clearTimeout(id),onError=()=>{}}={}) {
    Object.assign(this,{work,delay,hidden,events,schedule,cancel,onError});
    this.active=false;this.running=false;this.timer=null;this.failures=0;
    this.visibility=()=>{this.clear();if(!this.hidden())this.wake();};
  }
  clear(){if(this.timer!==null)this.cancel(this.timer);this.timer=null;}
  start(){if(this.active)return;this.active=true;this.events.addEventListener('visibilitychange',this.visibility);this.wake();}
  stop(){this.active=false;this.clear();this.events.removeEventListener('visibilitychange',this.visibility);}
  wake(){this.clear();if(this.active&&!this.running&&!this.hidden())void this.tick();}
  async tick(){
    if(!this.active||this.running||this.hidden())return;
    this.running=true;
    try{await this.work();this.failures=0;}
    catch(error){this.failures=Math.min(4,this.failures+1);this.onError(error);}
    finally{this.running=false;if(this.active&&!this.hidden())this.timer=this.schedule(()=>{this.timer=null;void this.tick();},Math.min(30000,this.delay()*2**this.failures));}
  }
}
