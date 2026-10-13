export class AppUpdates {
 constructor(invoke){this.invoke=invoke;this.available=typeof invoke==='function';this.state={status:'idle',message:''};this.generation=0;this.listeners=new Set();}
 subscribe(listener){this.listeners.add(listener);listener(this.state);return()=>this.listeners.delete(listener);}
 set(state){this.state=state;for(const listener of this.listeners)listener(state);}
 async check(token){
  if(!this.available || !token || ['checking','installing'].includes(this.state.status))return;
  const generation=++this.generation;this.set({status:'checking',message:'Đang kiểm tra phiên bản…'});
  try{
   const result=await this.invoke('check_update',{token});
   if(generation!==this.generation)return;
   if(result && (!/^\d+\.\d+\.\d+$/.test(result.version) || typeof result.currentVersion!=='string'))throw Error('invalid-update');
   this.set(result?{status:'available',version:result.version,message:`Đã có AudioTP ${result.version}.`}:{status:'current',message:'Bạn đang dùng phiên bản mới nhất.'});
  }catch{if(generation===this.generation)this.set({status:'error',message:'Chưa kiểm tra được cập nhật. Hãy thử lại khi có mạng.'});}
 }
 async install(){
  if(!this.available || this.state.status!=='available')return;
  const generation=++this.generation;this.set({status:'installing',message:'Đang tải và xác minh bản cập nhật. Ứng dụng sẽ đóng để cài đặt…'});
  try{await this.invoke('install_update');}
  catch{if(generation===this.generation)this.set({status:'error',message:'Cập nhật chưa hoàn tất. Hãy kiểm tra phiên bản rồi thử lại; ứng dụng hiện tại vẫn dùng được.'});}
 }
 clear(){++this.generation;this.set({status:'idle',message:''});if(this.available)void this.invoke('clear_update').catch(()=>{});}
}
