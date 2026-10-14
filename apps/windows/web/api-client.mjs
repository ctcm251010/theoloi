export function validateAPIBase(value){
 const url=new URL(value);
 if(url.username || url.password || url.search || url.hash || !['','/'].includes(url.pathname))throw Error('Địa chỉ máy chủ không hợp lệ.');
 if(url.protocol!=='https:' && !(url.protocol==='http:' && ['127.0.0.1','localhost'].includes(url.hostname)))throw Error('Máy chủ cần dùng HTTPS.');
 return url.origin;
}
// Own pending connection separately from active playback. Every UI continuation
// checks current() so cancellation cannot be undone by a late login/catalog.
export class ConnectionGate {
 constructor(){this.generation=0;this.pending=null;}
 cancel(){++this.generation;this.pending?.logout();this.pending=null;}
 begin(client){
  this.cancel();this.pending=client;const generation=this.generation;
  return {current:()=>generation===this.generation,complete:()=>{if(generation===this.generation && this.pending===client)this.pending=null;}};
 }
}
export class MediaAPI {
 constructor(base,{fetcher=(...args)=>fetch(...args),now=()=>Date.now()/1000,onUnauthorized=()=>{},timeoutMs=10000}={}){this.base=validateAPIBase(base);this.fetcher=fetcher;this.now=now;this.onUnauthorized=onUnauthorized;this.timeoutMs=timeoutMs;this.token='';this.expiresAt=0;this.tickets=new Map();this.urls=new Map();this.pending=new Map();this.controllers=new Set();this.generation=0;this.cancellation=0;this.localPreview=false;}
 async request(path,{method='GET',body,authenticated=true,retried=false,accept=data=>data}={}){
  const cancellation=this.cancellation;
  if(authenticated && (!this.token || this.expiresAt<=this.now())){
   if(this.localPreview && !retried)await this.localSession();
   else{this.logout();this.onUnauthorized();throw Error('Phiên truy cập đã hết hạn. Hãy kết nối lại.');}
  }
  if(cancellation!==this.cancellation)throw Error('Yêu cầu kết nối đã hủy.');
  const generation=this.generation,controller=new AbortController(),timer=setTimeout(()=>controller.abort(),this.timeoutMs);this.controllers.add(controller);
  try{
   const response=await this.fetcher(this.base+path,{method,headers:{...(authenticated?{Authorization:'Bearer '+this.token}:{}),...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{}),credentials:'omit',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer',signal:controller.signal});
   if(generation!==this.generation)throw Error('Yêu cầu đã hủy do phiên kết nối thay đổi.');
   if(!response.ok){
    if(response.status===401 && authenticated){
     if(this.localPreview && !retried){await this.localSession();if(cancellation!==this.cancellation)throw Error('Yêu cầu kết nối đã hủy.');const data=await this.request(path,{method,body,authenticated,retried:true,accept});if(cancellation!==this.cancellation)throw Error('Yêu cầu kết nối đã hủy.');return data;}
     this.logout();this.onUnauthorized();
    }
    const messages={401:'Mật khẩu chung hoặc phiên kết nối không hợp lệ.',403:'Chưa được cấp quyền phát từ máy chủ này.',404:'Chưa tìm thấy bài trên máy chủ.',409:'File audio không khớp dữ liệu đã xác minh.',429:'Đang có nhiều yêu cầu. Hãy chờ một phút rồi thử lại.',503:'Máy chủ tạm chưa sẵn sàng.'};const failure=Error(messages[response.status] || `Không kết nối được (${response.status}).`);failure.status=response.status;failure.network=[502,503,504].includes(response.status);throw failure;
   }
   const data=await response.json();
   if(generation!==this.generation)throw Error('Yêu cầu đã hủy do phiên kết nối thay đổi.');
   // Accept synchronously under the validated request generation. This also
   // permits a legitimate preview re-bootstrap without accepting stale login data.
   return accept(data);
  }catch(error){if(generation!==this.generation)throw Error('Yêu cầu đã hủy do phiên kết nối thay đổi.');if(error.name==='AbortError')throw Object.assign(Error('Máy chủ phản hồi quá lâu. Hãy thử lại.'),{network:true});if(error instanceof SyntaxError)throw Error('Dữ liệu máy chủ trả về không hợp lệ.');if(error instanceof TypeError)throw Object.assign(Error('Không kết nối được thư viện. Kiểm tra địa chỉ và kết nối mạng.'),{network:true});throw error;}
  finally{clearTimeout(timer);this.controllers.delete(controller);}
 }
 adoptSession(data){if(typeof data?.token!=='string' || !data.token || !Number.isFinite(data.expiresAt) || data.expiresAt<=this.now())throw Error('Phiên máy chủ trả về không hợp lệ.');++this.generation;this.tickets.clear();this.urls.clear();this.pending.clear();this.token=data.token;this.expiresAt=data.expiresAt;}
 async login(code){this.logout();const generation=this.generation;const data=await this.request('/v1/auth/login',{method:'POST',body:{code},authenticated:false});if(generation!==this.generation)throw Error('Yêu cầu kết nối đã hủy.');this.adoptSession(data);}
 async localSession(){if(!['127.0.0.1','localhost'].includes(new URL(this.base).hostname))throw Error('Chỉ dùng cho bản nghe local.');const generation=this.generation;const data=await this.request('/v1/local-session',{method:'POST',authenticated:false});if(generation!==this.generation)throw Error('Yêu cầu kết nối đã hủy.');this.adoptSession(data);this.localPreview=true;}
 catalog(){return this.request('/v1/catalog');}
 async quickAudio(){try{return await this.request('/v1/quick-audio');}catch(error){if(error.status===404)return null;throw error;}}
 async resolve(track){
  const cancellation=this.cancellation;
  if(this.token && this.expiresAt>this.now() && !this.needsRefresh(track) && this.urls.has(track.id))return this.urls.get(track.id);
  if(this.pending.has(track.id)){const url=await this.pending.get(track.id);if(cancellation!==this.cancellation)throw Error('Yêu cầu phát đã hủy.');return url;}
  const operation=this.request('/v1/play-tickets',{method:'POST',body:{assetId:track.id},accept:data=>{
   const expected=`/v1/media/${encodeURIComponent(track.id)}`;
   if(data?.assetId!==track.id || data.path!==expected || typeof data.ticket!=='string' || data.ticket.length>2048 || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(data.ticket) || !Number.isFinite(data.expiresAt) || data.expiresAt<=this.now() || data.expiresAt>this.expiresAt)throw Error('Nguồn phát không khớp bài đã chọn.');
   // No further await: a logout cannot interleave cache insertion with validation.
   if(!this.token)throw Error('Yêu cầu phát đã hủy.');
   this.tickets.set(track.id,data.expiresAt);const url=new URL(expected,this.base);url.searchParams.set('ticket',data.ticket);this.urls.set(track.id,url.href);
   if(this.urls.size>16){const oldest=this.urls.keys().next().value;this.urls.delete(oldest);this.tickets.delete(oldest);}
   return url.href;
  }});
  this.pending.set(track.id,operation);
  try{const url=await operation;if(cancellation!==this.cancellation)throw Error('Yêu cầu phát đã hủy.');return url;}finally{if(this.pending.get(track.id)===operation)this.pending.delete(track.id);}
 }
 needsRefresh(track){return (this.tickets.get(track?.id) || 0)<=this.now()+30;}
 logout(){++this.generation;++this.cancellation;for(const controller of this.controllers)controller.abort();this.controllers.clear();this.token='';this.expiresAt=0;this.tickets.clear();this.urls.clear();this.pending.clear();this.localPreview=false;}
}
