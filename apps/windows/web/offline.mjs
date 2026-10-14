import {validateCatalog} from './catalog.mjs';
import {quickPlaybackPlan} from './ui-core.mjs';

export const offlineSource=id=>`http://offline.localhost/${encodeURIComponent(id)}`;
export function formatBytes(bytes){const value=Math.max(0,Number(bytes)||0);if(value<1024)return `${value} B`;const power=Math.min(3,Math.floor(Math.log(value)/Math.log(1024)));return `${(value/1024**power).toLocaleString('vi',{maximumFractionDigits:1})} ${['B','KB','MB','GB'][power]}`;}
export const isNetworkFailure=error=>error?.network===true || error?.name==='AbortError' || error instanceof TypeError || [502,503,504].includes(error?.status);
export function offlineQuickPlan(card,tracks,offline){const plan=quickPlaybackPlan(card,tracks);if(!plan)return null;const queue=offline.filter(plan.queue);return queue.length?{...plan,queue,first:queue[0]}:null;}

// Native owns bytes, hashes, atomic writes and entitlements. The webview stores
// no credentials or download records and trusts only validated native snapshots.
export class OfflineLibrary {
 constructor(invoke){this.invoke=typeof invoke==='function'?invoke:null;this.available=!!this.invoke;this.offline=false;this.sessionGeneration=0;this.listeners=new Set();this.state={manifest:null,completed:[],items:[],job:{status:'idle',total:0,completed:0,failed:0,bytes:0,totalBytes:0},freeBytes:0};}
 get tracks(){return this.state.manifest?.tracks || [];}
 get completed(){const known=new Set(this.tracks.map(t=>t.id));return this.state.completed.filter(id=>known.has(id));}
 get stale(){return !!this.expectedCatalog && !this.refreshedManifest && this.expectedCatalog.revision!==this.state.manifest?.revision;}
 get complete(){return !this.stale && this.tracks.length>0 && this.tracks.every(t=>this.has(t.id));}
 setCatalog(catalog){validateCatalog(catalog);this.expectedCatalog=catalog;if(this.automaticStartup && this.startupOnline && !this.complete)this.offline=false;this.emit();}
 get busy(){return ['initializing','running','downloading','verifying','queued'].includes(this.state.job.status);}
 subscribe(listener){this.listeners.add(listener);listener(this.state);return()=>this.listeners.delete(listener);}
 emit(){for(const listener of this.listeners)listener(this.state);}
 accept(snapshot){
  if(!snapshot || !Array.isArray(snapshot.completed) || !Array.isArray(snapshot.items) || !snapshot.job || typeof snapshot.job.status!=='string')throw Error('Trạng thái offline không hợp lệ.');
  if(snapshot.manifest){
   const tracks=validateCatalog(snapshot.manifest),assets=snapshot.manifest.assets;
   if(!Array.isArray(assets) || assets.length!==tracks.length)throw Error('Danh mục offline không hợp lệ.');
   const ids=new Set(tracks.map(t=>t.id)),seen=new Set();
   for(const a of assets){if(!a || !ids.has(a.assetId) || seen.has(a.assetId) || !Number.isSafeInteger(a.bytes) || a.bytes<=0 || !/^[a-fA-F0-9]{64}$/.test(a.sha256) || typeof a.contentType!=='string' || !a.contentType.startsWith('audio/'))throw Error('Danh mục offline không hợp lệ.');seen.add(a.assetId);}
  }
  this.state=snapshot;
  if(this.startupPending && !['initializing','verifying'].includes(snapshot.job.status)){this.startupPending=false;this.offline=!this.startupOnline || this.complete;}
  this.emit();return snapshot;
 }
 async command(command,args){
  if(!this.available)throw Error('Tải offline chỉ hỗ trợ trong ứng dụng Windows.');
  // Serialize status and mutations so a delayed poll cannot roll back a start,
  // remove or manifest refresh. A failed command must not poison later actions.
  const generation=this.sessionGeneration,authenticated=['offline_start','offline_sync'].includes(command) || command==='offline_control' && ['resume','retry'].includes(args?.action);
  const operation=(this.pending || Promise.resolve()).then(async()=>{
   if(authenticated && generation!==this.sessionGeneration)throw Error('Đã hủy tác vụ do phiên kết nối thay đổi.');
   const snapshot=await this.invoke(command,args);if(authenticated && generation!==this.sessionGeneration)return this.state;
   const previous=this.refreshedManifest;if(command==='offline_sync')this.refreshedManifest=true;
   try{return this.accept(snapshot);}catch(error){this.refreshedManifest=previous;throw error;}
  });
  this.pending=operation.catch(()=>{});return operation;
 }
 async refresh(){if(!this.available)return this.state;return this.command('offline_status');}
 async initialize({online=true}={}){this.startupOnline=online;this.automaticStartup=true;this.startupPending=true;await this.refresh();this.offline=!online || this.complete;this.emit();return this.state;}
 sync(session){return this.command('offline_sync',session);}
 has(id){return !!this.state.manifest?.tracks.some(t=>t.id===id) && this.state.completed.includes(id);}
 source(id){return this.has(id)?offlineSource(id):null;}
 async resolve(track,onlineResolver,onNetworkFailure=()=>{}){
  const local=this.source(track.id);if(local)return local;
  if(this.offline)throw Error('Bài này chưa được tải để nghe offline.');
  try{return await onlineResolver(track);}catch(error){if(isNetworkFailure(error)){this.setOffline(true);onNetworkFailure(error);}throw error;}
 }
 item(id){return this.has(id)?{assetId:id,status:'completed'}:this.state.items.find(item=>item.assetId===id) || {assetId:id,status:'missing',bytes:0};}
 setOffline(value){this.startupPending=false;this.automaticStartup=false;this.offline=!!value;this.emit();}
 async clearSession(){
  ++this.sessionGeneration;if(!this.available)return this.state;
  // Cancellation bypasses pending network operations. Native also checks its
  // generation before publishing a manifest or promoting downloaded bytes.
  return this.accept(await this.invoke('offline_control',{action:'cancel'}));
 }
 filter(tracks){return this.offline?tracks.filter(t=>this.has(t.id)):tracks;}
 plan(tracks=this.tracks){const known=new Map((this.state.manifest?.assets || []).map(a=>[a.assetId,a]));const ids=[...new Set(tracks.map(t=>t.id))].filter(id=>known.has(id) && !this.has(id));return {ids,count:ids.length,bytes:ids.reduce((sum,id)=>sum+known.get(id).bytes,0)};}
 async start(ids,session){if(!this.available)return this.command('offline_start');this.assertKnown(ids);const plan=this.plan(ids.map(id=>({id})));if(!plan.count)return this.state;return this.command('offline_start',{...session,ids:plan.ids});}
 control(action,session={}){if(!['pause','resume','cancel','retry'].includes(action))throw Error('Thao tác tải không hợp lệ.');return this.command('offline_control',{action,...session});}
 assertKnown(ids){const known=new Set(this.tracks.map(t=>t.id));if(!Array.isArray(ids) || ids.some(id=>!known.has(id)))throw Error('Bài không thuộc danh mục offline hiện hành.');}
 async remove(ids){this.assertKnown(ids);return this.command('offline_remove',{ids:[...new Set(ids)]});}
}
