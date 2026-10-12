// The resolver is the sole source boundary. This module never constructs live URLs.
export class Player {
  constructor(media,resolver,{timeoutMs=15000,random=Math.random,shouldRefresh=()=>false}={}) {
    this.media=media;this.resolver=resolver;this.timeoutMs=timeoutMs;this.random=random;this.shouldRefresh=shouldRefresh;this.resumeAt=0;this.bufferTimer=null;
    this.listeners=new Set();this.generation=0;this.intent=false;this.ready=false;this.queue=[];
    this.state={track:null,status:'idle',error:'',position:0,duration:0,volume:media.volume,muted:media.muted,continuous:false,repeat:false,shuffle:false};
    for(const type of ['timeupdate','durationchange','loadedmetadata'])media.addEventListener(type,()=>this.syncTime());
    media.addEventListener('error',()=>{if(this.state.track && this.ready && media.error)this.fail('Không tải được âm thanh. Kiểm tra kết nối rồi thử lại.');});
    for(const type of ['waiting','stalled'])media.addEventListener(type,()=>{
      if(!this.ready || !this.intent || this.state.status==='error')return;
      this.clearBuffering();const token=this.generation;this.update({status:'buffering'});
      this.bufferTimer=setTimeout(()=>{if(token===this.generation && this.intent && this.state.status==='buffering')this.fail('Kết nối âm thanh bị gián đoạn. Hãy thử lại.');},this.timeoutMs);
    });
    media.addEventListener('playing',()=>{if(this.ready && this.intent && this.state.status!=='error'){this.clearBuffering();this.update({status:'playing',error:''});}});
    media.addEventListener('ended',()=>{if(!this.ready || !this.intent)return;if(this.state.repeat){void this.select(this.state.track,this.queue);}else if(this.state.continuous){void this.next();}else{this.intent=false;this.update({status:'ended',position:this.state.duration});}});
  }
  subscribe(listener){this.listeners.add(listener);listener(this.state);return()=>this.listeners.delete(listener);}
  update(patch){Object.assign(this.state,patch);for(const listener of this.listeners)listener(this.state);}
  async bounded(operation){let timer;try{return await Promise.race([operation,new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Âm thanh phản hồi quá lâu. Hãy thử lại.')),this.timeoutMs);})]);}finally{clearTimeout(timer);}}
  clearBuffering(){clearTimeout(this.bufferTimer);this.bufferTimer=null;}
  async select(track,queue=[track],{position=0,autoplay=true}={}) {
    this.clearBuffering();this.resumeAt=Number.isFinite(position)?Math.max(0,position):0;
    const token=++this.generation;this.intent=!!autoplay;this.ready=false;this.media.pause();this.media.src='';this.media.load();
    this.queue=queue.slice();if(!this.queue.some(t=>t.id===track.id))this.queue.unshift(track);
    this.update({track,status:'loading',error:'',position:0,duration:0});
    try {
      const src=await this.bounded(Promise.resolve().then(()=>this.resolver(track)));
      if(token!==this.generation)return;
      if(typeof src!=='string' || !src)throw Error('Chưa có nguồn âm thanh được cấp quyền.');
      this.media.src=src;this.media.load();this.ready=true;this.syncTime();
      if(!this.intent){this.update({status:'paused'});return;}
      await this.start(token);
    } catch(error){if(token===this.generation)this.fail(error.message || 'Không thể phát âm thanh.');}
  }
  async start(token=this.generation) {
    try {
      const completion=Promise.resolve(this.media.play()).then(()=>{if(!this.intent)this.media.pause();});
      await this.bounded(completion);
      if(token!==this.generation){if(!this.intent)this.media.pause();return;}
      if(!this.intent){this.media.pause();this.update({status:'paused'});return;}
      this.clearBuffering();this.update({status:'playing',error:''});
    }catch(error){if(token===this.generation)this.fail(error.message || 'Trình duyệt chưa cho phép phát. Hãy thử lại.');}
  }
  fail(error){this.clearBuffering();++this.generation;this.intent=false;this.media.pause();this.update({status:'error',error});}
  pause(){this.clearBuffering();this.intent=false;this.media.pause();if(this.state.track)this.update({status:'paused'});}
  async resume(){if(!this.state.track)return;if(this.state.status==='error' || !this.ready || this.shouldRefresh(this.state.track))return this.retry();this.intent=true;if(this.state.status==='ended')this.seek(0);this.update({status:'loading'});return this.start();}
  async toggle(){return this.intent?this.pause():this.resume();}
  stop(){this.clearBuffering();++this.generation;this.intent=false;this.ready=false;this.resumeAt=0;this.media.pause();this.media.src='';this.media.load();this.queue=[];this.update({track:null,status:'idle',position:0,duration:0,error:''});}
  retry(){if(this.state.track)return this.select(this.state.track,this.queue,{position:this.state.status==='ended'?0:this.state.position});}
  syncTime(){if(!this.ready)return;const duration=Number.isFinite(this.media.duration)?Math.max(0,this.media.duration):0;if(this.resumeAt && duration){this.media.currentTime=Math.min(this.resumeAt,duration);this.resumeAt=0;}const position=Math.max(0,Number.isFinite(this.media.currentTime)?this.media.currentTime:0);if(position>this.state.position && this.state.status==='buffering' && this.intent){this.clearBuffering();this.update({status:'playing'});}this.update({duration,position});}
  seek(seconds){if(!this.ready || !Number.isFinite(seconds) || !this.state.duration)return;const position=Math.min(this.state.duration,Math.max(0,seconds));if(this.shouldRefresh(this.state.track))return this.select(this.state.track,this.queue,{position,autoplay:this.intent});this.media.currentTime=position;this.syncTime();}
  setVolume(volume){if(!Number.isFinite(volume))return;this.media.volume=Math.max(0,Math.min(1,volume));this.update({volume:this.media.volume});}
  toggleMute(){this.media.muted=!this.media.muted;this.update({muted:this.media.muted});}
  setModes(patch){for(const key of ['continuous','repeat','shuffle'])if(key in patch)this.state[key]=!!patch[key];this.update({});}
  next(){
    this.clearBuffering();
    const index=this.queue.findIndex(t=>t.id===this.state.track?.id);
    if(this.state.shuffle && this.queue.length>1){const choices=this.queue.filter(t=>t.id!==this.state.track.id);return this.select(choices[Math.min(choices.length-1,Math.floor(this.random()*choices.length))],this.queue);}
    if(index>=0 && index<this.queue.length-1)return this.select(this.queue[index+1],this.queue);
    this.intent=false;this.media.pause();if(this.state.track)this.update({status:'ended'});
  }
  previous(){const index=this.queue.findIndex(t=>t.id===this.state.track?.id);if(this.state.position>3 || index<=0){this.seek(0);return;}return this.select(this.queue[index-1],this.queue);}
}
