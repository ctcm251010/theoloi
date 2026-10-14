const idle=()=>({status:'idle',message:'',notification:false});
function validRelease(result){
 if(!result || !/^\d+\.\d+\.\d+$/.test(result.version) || !/^\d+\.\d+\.\d+$/.test(result.currentVersion))return false;
 const current=result.currentVersion.split('.').map(BigInt),version=result.version.split('.').map(BigInt);
 for(let i=0;i<3;i++){if(version[i]!==current[i])return version[i]>current[i];}return false;
}
export class AppUpdates {
 constructor(invoke,{listen,timeoutMs=6000}={}){this.invoke=invoke;this.listen=listen;this.timeoutMs=timeoutMs;this.available=typeof invoke==='function';this.state=idle();this.generation=0;this.listeners=new Set();this.deferred=new Set();this.token='';}
 subscribe(listener){this.listeners.add(listener);listener(this.state);return()=>this.listeners.delete(listener);}
 set(state){this.state=state;for(const listener of this.listeners)listener(state);}
 async startup(){return this.checkPublic(true);}
 async checkPublic(silent){
  if(!this.available || ['checking','installing'].includes(this.state.status))return;
  const generation=++this.generation,previous=this.state;let timer;
  if(!silent)this.set({status:'checking',message:'Đang kiểm tra phiên bản…',notification:false});
  try{
   const result=await Promise.race([this.invoke('check_release_info'),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('timeout')),this.timeoutMs);})]);
   if(generation!==this.generation)return;
   if(result && !validRelease(result))throw Error('invalid-update');
   if(result)this.set({status:'available',...result,notification:!silent || !this.deferred.has(result.version),message:`Đã có AudioTP ${result.version}.`});
   else if(!silent)this.set({status:'current',message:'Bạn đang dùng phiên bản mới nhất.',notification:false});
  }catch{if(generation===this.generation)this.set(silent?previous:{status:'error',notification:false,message:'Chưa kiểm tra được cập nhật. Hãy thử lại khi có mạng.'});}
  finally{clearTimeout(timer);}
 }
 async check(token,{automatic=false}={}){
  if(!token)return this.checkPublic(automatic);
  if(!this.available || ['checking','installing'].includes(this.state.status))return;
  this.token=token;const generation=++this.generation;this.set({status:'checking',message:'Đang kiểm tra phiên bản…',notification:false});
  try{
   const result=await this.invoke('check_update',{token});
   if(generation!==this.generation)return;
   if(result && !validRelease(result))throw Error('invalid-update');
   this.set(result?{status:'available',...result,notification:!automatic || !this.deferred.has(result.version),message:`Đã có AudioTP ${result.version}.`}:{status:'current',notification:false,message:'Bạn đang dùng phiên bản mới nhất.'});
  }catch{if(generation===this.generation)this.set({status:'error',notification:false,message:'Chưa kiểm tra được cập nhật. Hãy thử lại khi có mạng.'});}
 }
 defer(){
  if(this.state.version)this.deferred.add(this.state.version);
  const preparing=this.state.status==='checking' && !!this.state.version;
  if(preparing){++this.generation;if(this.available)void this.invoke('clear_update').catch(()=>{});}
  this.set({...this.state,...(preparing?{status:'available'}:{}),notification:false});
 }
 async install(token=this.token){
  if(!this.available || this.state.status!=='available')return;
  if(!token){this.set({...this.state,requiresAuth:true,message:'Hãy kết nối bằng mật khẩu chung để tải bản cập nhật.'});return;}
  this.token=token;const generation=++this.generation;let unlisten;
  this.set({...this.state,status:'checking',requiresAuth:false,notification:true,message:'Đang xác minh phiên bản cập nhật…'});
  try{
   // Public metadata only notifies. A fresh authenticated official check must precede install.
   const result=await this.invoke('check_update',{token});
   if(generation!==this.generation)return;
   if(!result){this.set({status:'current',notification:false,message:'Bạn đang dùng phiên bản mới nhất.'});return;}
   if(!validRelease(result))throw Error('invalid-update');
   this.set({status:'installing',...result,notification:true,progress:{phase:'downloading',downloaded:0,total:null,percent:null},message:'Đang tải và xác minh bản cập nhật. Ứng dụng sẽ đóng để cài đặt…'});
   if(typeof this.listen==='function')unlisten=await this.listen('app-update-progress',event=>{
    if(generation!==this.generation || this.state.status!=='installing')return;
    const progress=event?.payload;
    if(!progress || !['downloading','verifying','installing'].includes(progress.phase) || !Number.isFinite(progress.downloaded) || progress.downloaded<0)return;
    this.set({...this.state,progress});
   });
   if(generation!==this.generation)return;
   await this.invoke('install_update');
  }catch{if(generation===this.generation)this.set({status:'error',notification:true,message:'Cập nhật chưa hoàn tất. Hãy kiểm tra phiên bản rồi thử lại; ứng dụng hiện tại vẫn dùng được.'});}
  finally{if(typeof unlisten==='function')unlisten();}
 }
 clear(){++this.generation;this.token='';this.set(idle());if(this.available)void this.invoke('clear_update').catch(()=>{});}
}
