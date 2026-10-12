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
