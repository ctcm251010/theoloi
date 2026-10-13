/** @param {object} value @param {string[]} keys */
function exactKeys(value,keys){return !!value && typeof value==='object' && !Array.isArray(value) && Object.keys(value).length===keys.length && keys.every(k=>Object.hasOwn(value,k));}
/**
 * Validate ignored production inputs at the service boundary, including fields
 * that must never escape through the public catalog. Types alone do not validate JSON.
 * @param {import('./contracts').ClientCatalog} client
 * @param {Record<string,import('./contracts').Asset>} allowlist
 */
export function validateData(client,allowlist){
 if(!exactKeys(client,['schemaVersion','revision','tracks']) || client.schemaVersion!==1 || typeof client.revision!=='string' || !client.revision.trim() || client.revision.length>256 || !Array.isArray(client.tracks) || !client.tracks.length || !allowlist || typeof allowlist!=='object' || Array.isArray(allowlist))throw Error('Invalid catalog');
 const ids=new Set(),keys=new Set();
 for(const t of client.tracks){
  if(!exactKeys(t,['id','logicalId','mode','section','number','title','category','durationSeconds']) || typeof t.id!=='string' || !t.id || ids.has(t.id) || typeof t.logicalId!=='string' || !t.logicalId || !['guide','instrumental','silent'].includes(t.mode) || (t.mode==='silent'?t.section!==null:!['main','appendix'].includes(t.section ?? '')) || !Number.isSafeInteger(t.number) || t.number<1 || typeof t.title!=='string' || !t.title.trim() || typeof t.category!=='string' || !t.category.trim() || !Number.isFinite(t.durationSeconds) || t.durationSeconds<=0)throw Error('Invalid catalog track');
  const a=Object.hasOwn(allowlist,t.id)?allowlist[t.id]:null;
  if(!a || !exactKeys(a,['assetId','objectKey','bytes','sha256']) || a.assetId!==t.id || typeof a.objectKey!=='string' || !/^audio\/v1\/watv\/vi\/[a-zA-Z0-9:._/-]+$/.test(a.objectKey) || a.objectKey.split('/').some(s=>!s || s==='.' || s==='..') || keys.has(a.objectKey) || !Number.isSafeInteger(a.bytes) || a.bytes<=0 || typeof a.sha256!=='string' || !/^[a-f0-9]{64}$/.test(a.sha256))throw Error('Invalid asset allowlist');
  ids.add(t.id);keys.add(a.objectKey);
 }
 if(ids.size!==Object.keys(allowlist).length)throw Error('Invalid asset allowlist');
}

/** @type {import('./contracts').QuickAudio} */
export const EMPTY_QUICK_AUDIO={schemaVersion:1,revision:'sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',tracks:[],assets:{}};

/** @param {import('./contracts').QuickAudio} quick @param {import('./contracts').ClientCatalog} client @param {Record<string,import('./contracts').Asset>} allowlist */
export function validateQuickAudio(quick,client,allowlist){
 if(!exactKeys(quick,['schemaVersion','revision','tracks','assets']) || quick.schemaVersion!==1 || !/^sha256:[a-f0-9]{64}$/.test(quick.revision) || !Array.isArray(quick.tracks) || quick.tracks.length>1 || !quick.assets || typeof quick.assets!=='object' || Array.isArray(quick.assets))throw Error('Invalid quick audio');
 const id='watv:vi:prayer:our-wish';
 if(Object.keys(quick.assets).length!==quick.tracks.length)throw Error('Invalid quick audio assets');
 for(const track of quick.tracks){
  if(!exactKeys(track,['id','logicalId','mode','section','number','title','category','durationSeconds']) || track.id!==id || track.logicalId!==id || track.mode!=='prayer' || track.section!==null || track.number!==null || track.title!=='Cầu nguyện chúng con mong muốn' || track.category!=='Cầu nguyện' || track.durationSeconds!==69.427664 || client.tracks.some(t=>t.id===id || t.logicalId===id) || Object.hasOwn(allowlist,id))throw Error('Invalid quick audio track');
  const asset=Object.hasOwn(quick.assets,id)?quick.assets[id]:null;
  if(!asset || !exactKeys(asset,['assetId','objectKey','bytes','sha256']) || asset.assetId!==id || typeof asset.sha256!=='string' || !/^[a-f0-9]{64}$/.test(asset.sha256) || asset.objectKey!==`audio/v1/watv/vi/prayer/our-wish/${asset.sha256}.m4a` || !Number.isSafeInteger(asset.bytes) || asset.bytes<=0 || Object.values(allowlist).some(a=>a.objectKey===asset.objectKey))throw Error('Invalid quick audio assets');
 }
}

/** @param {string} value @returns {number[] | null} */
export function stableVersion(value){
 if(typeof value!=='string' || !/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.test(value))return null;
 const parts=value.split('.').map(Number);return parts.every(Number.isSafeInteger)?parts:null;
}

/** Canonical base64 only; no URL-safe alphabet or ignored junk. @param {string} value */
function decodeBase64(value){
 if(typeof value!=='string' || value.length===0 || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value))throw Error('Invalid signature');
 const decoded=atob(value);if(btoa(decoded)!==value)throw Error('Invalid signature');return decoded;
}

/** Validate artifact metadata only. Cryptographic verification is performed by the pinned updater public key. @param {import('./contracts').UpdateRelease} update */
export function validateUpdate(update){
 if(!exactKeys(update,['version','pubDate','notes','objectKey','bytes','sha256','signature']) || !stableVersion(update.version) || update.objectKey!==`updates/windows-x86_64/${update.version}/AudioTP_${update.version}_x64-setup.exe` || typeof update.pubDate!=='string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(update.pubDate) || !Number.isFinite(Date.parse(update.pubDate)) || new Date(update.pubDate).toISOString().slice(0,19)!==update.pubDate.slice(0,19) || typeof update.notes!=='string' || !Number.isSafeInteger(update.bytes) || update.bytes<=0 || typeof update.sha256!=='string' || !/^[a-f0-9]{64}$/.test(update.sha256) || typeof update.signature!=='string' || update.signature.length>8192)throw Error('Invalid update release');
 const lines=decodeBase64(update.signature).replace(/\r\n/g,'\n').trimEnd().split('\n');
 if(lines.length!==4 || !lines[0].startsWith('untrusted comment: ') || !lines[2].startsWith('trusted comment: '))throw Error('Invalid signature');
 const packet=decodeBase64(lines[1]);
 if(packet.length!==74 || !['Ed','ED'].includes(packet.slice(0,2)) || decodeBase64(lines[3]).length!==64)throw Error('Invalid signature');
}
