// No browser/localStorage fallback. Native Windows DPAPI owns persistence.
export class RememberedAccess {
 constructor(invoke){this.invoke=invoke;this.available=typeof invoke==='function';this.epoch=0;this.tail=Promise.resolve();}
 enqueue(operation){const result=this.tail.then(operation);this.tail=result.catch(()=>{});return result;}
 async read(base){
  if(!this.available)return null;
  const epoch=this.epoch;
  const code=await this.enqueue(()=>epoch===this.epoch?this.invoke('read_access_code',{base}):null);
  return epoch===this.epoch && typeof code==='string'?code:null;
 }
 save(base,code){
  if(!this.available)return Promise.reject(Error('Chỉ lưu đăng nhập an toàn trong ứng dụng Windows.'));
  const epoch=this.epoch;
  return this.enqueue(()=>epoch===this.epoch?this.invoke('save_access_code',{base,code}):undefined);
 }
 clear(){++this.epoch;return this.available?this.enqueue(()=>this.invoke('forget_access_code')):Promise.resolve();}
}
