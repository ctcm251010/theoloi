import {timingSafeEqual} from 'node:crypto';
import {validateData,validateQuickAudio,validateUpdate,stableVersion,EMPTY_QUICK_AUDIO} from './validate-data.mjs';
/** @typedef {{[K in keyof Env]: Env[K] extends string ? string : Env[K]} & {LOCAL_PREVIEW?:string}} WorkerEnv */
/** @typedef {import('./contracts').Asset} Asset */
/** @typedef {import('./contracts').ClientCatalog} ClientCatalog */
/** @typedef {{v:1,type:'session'|'media',sub:string,epoch:string,iat:number,exp:number,id?:string,revision?:string}} Claims */

const encoder=new TextEncoder();
/** @param {ArrayBuffer | Uint8Array} bytes */
const b64=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
/** @param {string} text */
const unb64=text=>Uint8Array.from(atob(text.replace(/-/g,'+').replace(/_/g,'/')),c=>c.charCodeAt(0));
const epochSeconds=()=>Math.floor(Date.now()/1000);
/**
 * @param {number} status
 * @param {string} code
 * @param {HeadersInit} headers
 */
const error=(status,code,headers={})=>{const h=new Headers(headers);h.set('Content-Type','application/json');h.delete('Content-Length');return Response.json({error:code},{status,headers:h});};

/** @param {string} secret */
async function signingKey(secret){return crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);}
/**
 * @param {Claims} claims
 * @param {string} key
 */
async function sign(claims,key){const payload=b64(encoder.encode(JSON.stringify(claims)));return `${payload}.${b64(await crypto.subtle.sign('HMAC',await signingKey(key),encoder.encode(payload)))}`;}
/**
 * @param {string | null} token
 * @param {string} key
 * @param {'session'|'media'} type
 * @param {string} epoch
 * @param {number} now
 * @returns {Promise<Claims | null>}
 */
async function verify(token,key,type,epoch,now){
 try{
  if(typeof token!=='string' || token.length>2048)return null;
  const parts=token.split('.');if(parts.length!==2 || !parts.every(p=>/^[A-Za-z0-9_-]+$/.test(p)))return null;
  if(!await crypto.subtle.verify('HMAC',await signingKey(key),unb64(parts[1]),encoder.encode(parts[0])))return null;
  /** @type {Record<string,unknown>} */
  const c=JSON.parse(new TextDecoder().decode(unb64(parts[0])));
  if(!c || c.v!==1 || c.type!==type || c.epoch!==epoch || typeof c.sub!=='string' || typeof c.exp!=='number' || typeof c.iat!=='number' || !Number.isSafeInteger(c.exp) || !Number.isSafeInteger(c.iat) || c.iat>now+30 || c.exp<=now || c.exp-c.iat>(type==='session'?43200:3600))return null;
  return {v:1,type,epoch,sub:c.sub,iat:c.iat,exp:c.exp,...(typeof c.id==='string'?{id:c.id}:{}),...(typeof c.revision==='string'?{revision:c.revision}:{})};
 }catch{return null;}
}
/**
 * @param {Request} request
 * @returns {Promise<Record<string,unknown>>}
 */
async function boundedJSON(request){
 if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json'))throw Error('body');
 if(Number(request.headers.get('content-length') || 0)>4096)throw Error('body');
 const reader=request.body?.getReader();if(!reader)throw Error('body');
 let size=0;/** @type {Uint8Array[]} */const chunks=[];
 try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size>4096){await reader.cancel();throw Error('body');}chunks.push(part.value);}}
 finally{reader.releaseLock();}
 const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}
 const data=JSON.parse(new TextDecoder().decode(bytes));if(!data || typeof data!=='object' || Array.isArray(data))throw Error('body');return data;
}
/**
 * @param {string} value
 * @param {number} size
 */
export function byteRange(value,size){
 const match=/^bytes=(\d*)-(\d*)$/i.exec(value.trim());if(!match || !size || (!match[1] && !match[2]))return null;
 const a=match[1]?Number(match[1]):null,b=match[2]?Number(match[2]):null;
 if((a!==null && !Number.isSafeInteger(a)) || (b!==null && !Number.isSafeInteger(b)))return null;
 if(a===null){if(!b)return null;return {offset:Math.max(0,size-b),length:Math.min(size,b)};}
 const end=b===null?size-1:Math.min(size-1,b);if(a>=size || end<a)return null;
 return {offset:a,length:end-a+1};
}
/**
 * @param {R2Object | null} object
 * @param {Asset} asset
 * @param {string} contentType
 */
function metadataMatches(object,asset,contentType){
 return !!object && object.size===asset.bytes && object.customMetadata?.sha256===asset.sha256 && object.customMetadata?.['asset-id']===asset.assetId && object.httpMetadata?.contentType===contentType && typeof object.etag==='string' && object.etag.length>0 && typeof object.httpEtag==='string' && /^"[^"\r\n]+"$/.test(object.httpEtag);
}

/** @param {Request} request @param {R2Bucket} bucket @param {Asset} asset @param {string} contentType @param {boolean} exposeId */
async function streamAsset(request,bucket,asset,contentType,exposeId){
 const head=await bucket.head(asset.objectKey);if(!head)return error(404,'asset_missing');
 if(!metadataMatches(head,asset,contentType))return error(409,'asset_integrity_mismatch');
 const h=new Headers({'Content-Type':contentType,'Accept-Ranges':'bytes','ETag':head.httpEtag});
 if(exposeId)h.set('X-AudioTP-Asset-Id',asset.assetId);
 const none=request.headers.get('If-None-Match');
 if(none?.split(',').some(t=>['*',head.httpEtag].includes(t.trim().replace(/^W\//,''))))return new Response(null,{status:304,headers:h});
 // Range is defined for GET; HEAD describes the full selected representation.
 const rawRange=request.method==='GET'?request.headers.get('Range'):null;
 const ifRange=request.headers.get('If-Range');
 let range=null;
 if(rawRange && (!ifRange || ifRange===head.httpEtag)){
  range=byteRange(rawRange,asset.bytes);
  if(!range){h.set('Content-Range',`bytes */${asset.bytes}`);return error(416,'invalid_range',h);}
 }
 const length=range?.length ?? asset.bytes;h.set('Content-Length',String(length));
 if(range)h.set('Content-Range',`bytes ${range.offset}-${range.offset+range.length-1}/${asset.bytes}`);
 const status=range?206:200;
 if(request.method==='HEAD')return new Response(null,{status,headers:h});
 const object=await bucket.get(asset.objectKey,{...(range?{range}:{}),onlyIf:{etagMatches:head.etag}});
 if(!object)return error(404,'asset_missing');
 if(!('body' in object))return error(409,'asset_changed');
 if(!metadataMatches(object,asset,contentType) || object.etag!==head.etag || (range && (!object.range || !('offset' in object.range) || !('length' in object.range) || object.range.offset!==range.offset || object.range.length!==range.length))){await object.body.cancel();return error(409,'asset_changed');}
 return new Response(object.body,{status,headers:h});
}

/**
 * @param {ClientCatalog} client
 * @param {Record<string,Asset>} allowlist
 * @param {{now?:()=>number,quickAudio?:import('./contracts').QuickAudio,updates?:import('./contracts').UpdateRelease}} options
 */
export function createService(client,allowlist,{now=epochSeconds,quickAudio=EMPTY_QUICK_AUDIO,updates}={}){
 validateData(client,allowlist);
 validateQuickAudio(quickAudio,client,allowlist);
 if(updates!==undefined)validateUpdate(updates);
 /** @type {Map<string,import('./contracts').ClientTrack | import('./contracts').PrayerTrack>} */
 const tracks=new Map([...client.tracks,...quickAudio.tracks].map(t=>[t.id,t]));
 const publicQuick={schemaVersion:quickAudio.schemaVersion,revision:quickAudio.revision,tracks:quickAudio.tracks};
 /** @param {string} id */
 const revisionFor=id=>Object.hasOwn(quickAudio.assets,id)?quickAudio.revision:client.revision;
 return {
 /**
  * @param {Request} request
  * @param {WorkerEnv} env
  */
 async fetch(request,env){
  let origin=request.headers.get('Origin'),allowed=false;
  const headers=new Headers({'Cache-Control':'private, no-store','CDN-Cache-Control':'no-store','Cloudflare-CDN-Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Vary':'Origin'});
  try{
   const origins=String(env.ALLOWED_ORIGINS || '').split(',').map(s=>s.trim()).filter(Boolean);
   allowed=!!origin && origins.includes(origin);
   if(origin && !allowed)return finish(error(403,'origin_forbidden'));
   if(origin && allowed){headers.set('Access-Control-Allow-Origin',origin);headers.set('Access-Control-Expose-Headers','Content-Length, Content-Range, Accept-Ranges, ETag, X-AudioTP-Asset-Id, Retry-After');}
   const url=new URL(request.url);
   if(url.protocol!=='https:' && !(env.LOCAL_PREVIEW==='true' && ['127.0.0.1','localhost'].includes(url.hostname)))return finish(error(403,'https_required'));
   if(request.method==='OPTIONS'){
    if(!allowed)return finish(error(403,'origin_forbidden'));
    const method=request.headers.get('Access-Control-Request-Method');
    const requested=(request.headers.get('Access-Control-Request-Headers') || '').toLowerCase().split(',').map(s=>s.trim()).filter(Boolean);
    if(!method || !['GET','HEAD','POST'].includes(method) || requested.some(h=>!['authorization','content-type','range','if-range','if-none-match'].includes(h)))return finish(error(403,'preflight_forbidden'));
    headers.set('Access-Control-Allow-Methods','GET, HEAD, POST, OPTIONS');headers.set('Access-Control-Allow-Headers','Authorization, Content-Type, Range, If-Range, If-None-Match');headers.set('Access-Control-Max-Age','600');return finish(new Response(null,{status:204}));
   }
   if(!['GET','HEAD','POST'].includes(request.method))return finish(error(405,'method_not_allowed',{Allow:'GET, HEAD, POST, OPTIONS'}));
   if(env.SERVING_ENABLED!=='true')return finish(error(url.pathname==='/v1/health'?503:403,'serving_disabled'));
   if(typeof env.SIGNING_KEY!=='string' || env.SIGNING_KEY.length<32 || !/^[a-f0-9]{64}$/.test(env.GROUP_CODE_SHA256 || '') || !env.AUTH_EPOCH || !env.MEDIA || !env.LOGIN_LIMITER || !env.REQUEST_LIMITER)return finish(error(503,'service_not_configured'));
   const ip=request.headers.get('CF-Connecting-IP') || 'unattributed';
   const login=url.pathname==='/v1/auth/login';
   const limiter=login?env.LOGIN_LIMITER:env.REQUEST_LIMITER;
   if(!(await limiter.limit({key:`${login?'login':'requests'}:${ip}`})).success)return finish(error(429,'rate_limited',{'Retry-After':'60'}));
   if(url.pathname==='/v1/health')return finish(['GET','HEAD'].includes(request.method)?Response.json({status:'ready',storage:'not-probed'}):error(405,'method_not_allowed',{Allow:'GET, HEAD'}));
   // Public version notification only. Installer, catalog and audio still require
   // their existing authorization; this route performs no storage operations.
   const releaseInfo=/^\/v1\/release-info\/windows-x86_64\/([^/]+)$/.exec(url.pathname);
   if(releaseInfo){
    if(!['GET','HEAD'].includes(request.method))return finish(error(405,'method_not_allowed',{Allow:'GET, HEAD'}));
    const current=stableVersion(releaseInfo[1]);if(!current)return finish(error(400,'invalid_version'));
    const available=updates?stableVersion(updates.version):null;
    const differing=available?current.findIndex((part,index)=>part!==available[index]):-1;
    if(!updates || !available || differing===-1 || current[differing]>available[differing])return finish(new Response(null,{status:204}));
    return finish(Response.json({version:updates.version,currentVersion:releaseInfo[1]}));
   }
   if(login){
    if(request.method!=='POST')return finish(error(405,'method_not_allowed',{Allow:'POST'}));
    let data;try{data=await boundedJSON(request);}catch{return finish(error(400,'invalid_body'));}
    if(typeof data?.code!=='string' || data.code.length<4 || data.code.length>256 || /[\u0000-\u001f\u007f-\u009f]/.test(data.code))return finish(error(401,'invalid_access_code'));
    const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',encoder.encode(data.code)));
    const expected=Uint8Array.from(env.GROUP_CODE_SHA256.match(/../g) || [],h=>parseInt(h,16));
    if(!timingSafeEqual(digest,expected))return finish(error(401,'invalid_access_code'));
    const seconds=Math.min(43200,Math.max(300,Number(env.SESSION_SECONDS)||43200));
    const issued=now();
    /** @type {Claims} */
    const claims={v:1,type:'session',sub:crypto.randomUUID(),epoch:env.AUTH_EPOCH,iat:issued,exp:issued+Math.floor(seconds)};
    return finish(Response.json({token:await sign(claims,env.SIGNING_KEY),expiresAt:claims.exp}));
   }
   const mediaMatch=/^\/v1\/media\/([^/]+)$/.exec(url.pathname);
   if(mediaMatch){
    if(!['GET','HEAD'].includes(request.method))return finish(error(405,'method_not_allowed',{Allow:'GET, HEAD'}));
    const claims=await verify(url.searchParams.get('ticket'),env.SIGNING_KEY,'media',env.AUTH_EPOCH,now());
    if(!claims)return finish(error(401,'invalid_or_expired_ticket'));
    let id;try{id=decodeURIComponent(mediaMatch[1]);}catch{return finish(error(404,'asset_not_found'));}
    if(claims.id!==id || claims.revision!==revisionFor(id))return finish(error(403,'ticket_scope_mismatch'));
    const asset=Object.hasOwn(quickAudio.assets,id)?quickAudio.assets[id]:Object.hasOwn(allowlist,id)?allowlist[id]:null;if(!asset)return finish(error(404,'asset_not_found'));
    return finish(await streamAsset(request,env.MEDIA,asset,'audio/mp4',true));
   }
   const authorization=request.headers.get('Authorization');
   const session=await verify(authorization?.startsWith('Bearer ')?authorization.slice(7):null,env.SIGNING_KEY,'session',env.AUTH_EPOCH,now());
   if(!session)return finish(error(401,'invalid_or_expired_session'));
   if(url.pathname==='/v1/quick-audio' && ['GET','HEAD'].includes(request.method))return finish(Response.json(publicQuick));
   const updateCheck=/^\/v1\/updates\/windows-x86_64\/([^/]+)$/.exec(url.pathname);
   if(updateCheck && ['GET','HEAD'].includes(request.method)){
    const current=stableVersion(updateCheck[1]);if(!current)return finish(error(400,'invalid_version'));
    const available=updates?stableVersion(updates.version):null;
    const differing=available?current.findIndex((part,index)=>part!==available[index]):-1;
    if(!updates || !available || differing===-1 || current[differing]>available[differing])return finish(new Response(null,{status:204}));
    return finish(Response.json({version:updates.version,pub_date:updates.pubDate,notes:updates.notes,url:`${url.origin}/v1/update-files/${updates.version}/installer`,signature:updates.signature}));
   }
   const updateFile=/^\/v1\/update-files\/([^/]+)\/installer$/.exec(url.pathname);
   if(updateFile && ['GET','HEAD'].includes(request.method)){
    if(!updates || updateFile[1]!==updates.version)return finish(error(404,'asset_not_found'));
    const asset={assetId:`audiotp:windows:x86_64:${updates.version}`,objectKey:updates.objectKey,bytes:updates.bytes,sha256:updates.sha256};
    return finish(await streamAsset(request,env.MEDIA,asset,'application/octet-stream',false));
   }
   if(url.pathname==='/v1/catalog' && ['GET','HEAD'].includes(request.method))return finish(Response.json(client));
   if(url.pathname==='/v1/offline-manifest' && ['GET','HEAD'].includes(request.method))return finish(Response.json({schemaVersion:1,revision:client.revision,tracks:client.tracks,assets:client.tracks.map(track=>({assetId:track.id,bytes:allowlist[track.id].bytes,sha256:allowlist[track.id].sha256,contentType:'audio/mp4'}))}));
   const song=/^\/v1\/songs\/([^/]+)$/.exec(url.pathname);
   if(song && ['GET','HEAD'].includes(request.method)){
    let logicalId;try{logicalId=decodeURIComponent(song[1]);}catch{return finish(error(404,'song_not_found'));}
    const matches=client.tracks.filter(t=>t.logicalId===logicalId);
    return finish(matches.length?Response.json({logicalId,tracks:matches}):error(404,'song_not_found'));
   }
   if(url.pathname==='/v1/play-tickets' && request.method==='POST'){
    let data;try{data=await boundedJSON(request);}catch{return finish(error(400,'invalid_body'));}
    const track=typeof data?.assetId==='string'?tracks.get(data.assetId):null;if(!track)return finish(error(404,'asset_not_found'));
    const issued=now(),seconds=Math.min(3600,Math.max(300,Math.ceil(track.durationSeconds)+600));
    /** @type {Claims} */
    const claims={v:1,type:'media',sub:session.sub,id:track.id,revision:revisionFor(track.id),epoch:env.AUTH_EPOCH,iat:issued,exp:Math.min(session.exp,issued+seconds)};
    return finish(Response.json({assetId:track.id,path:`/v1/media/${encodeURIComponent(track.id)}`,ticket:await sign(claims,env.SIGNING_KEY),expiresAt:claims.exp}));
   }
   return finish(error(404,'route_not_found'));
  }catch{
   // Static diagnostic only. Never log the request URL (bearer ticket), env or error.
   console.warn(JSON.stringify({event:'media_api_failure',code:'upstream_unavailable'}));
   return finish(error(503,'upstream_unavailable',{'Retry-After':'5'}));
  }
  /** @param {Response} response */
  function finish(response){for(const [k,v]of headers)response.headers.set(k,v);if(request.method==='HEAD')return new Response(null,{status:response.status,headers:response.headers});return response;}
 }};
}
