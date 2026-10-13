import {timingSafeEqual} from 'node:crypto';
import {validateData} from './validate-data.mjs';
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
 */
function metadataMatches(object,asset){
 return !!object && object.size===asset.bytes && object.customMetadata?.sha256===asset.sha256 && object.customMetadata?.['asset-id']===asset.assetId && object.httpMetadata?.contentType==='audio/mp4' && typeof object.etag==='string' && object.etag.length>0 && typeof object.httpEtag==='string' && /^"[^"\r\n]+"$/.test(object.httpEtag);
}

/**
 * @param {ClientCatalog} client
 * @param {Record<string,Asset>} allowlist
 */
export function createService(client,allowlist,{now=epochSeconds}={}){
 validateData(client,allowlist);
 const tracks=new Map(client.tracks.map(t=>[t.id,t]));
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
    if(claims.id!==id || claims.revision!==client.revision)return finish(error(403,'ticket_scope_mismatch'));
    const asset=allowlist[id];if(!asset)return finish(error(404,'asset_not_found'));
    const head=await env.MEDIA.head(asset.objectKey);if(!head)return finish(error(404,'asset_missing'));
    if(!metadataMatches(head,asset))return finish(error(409,'asset_integrity_mismatch'));
    const h=new Headers({'Content-Type':'audio/mp4','Accept-Ranges':'bytes','ETag':head.httpEtag,'X-AudioTP-Asset-Id':id});
    const none=request.headers.get('If-None-Match');
    if(none?.split(',').some(t=>['*',head.httpEtag].includes(t.trim().replace(/^W\//,''))))return finish(new Response(null,{status:304,headers:h}));
    // Range is defined for GET; HEAD describes the full selected representation.
    const rawRange=request.method==='GET'?request.headers.get('Range'):null;
    const ifRange=request.headers.get('If-Range');
    let range=null;
    if(rawRange && (!ifRange || ifRange===head.httpEtag)){
     range=byteRange(rawRange,asset.bytes);
     if(!range){h.set('Content-Range',`bytes */${asset.bytes}`);return finish(error(416,'invalid_range',h));}
    }
    const length=range?.length ?? asset.bytes;h.set('Content-Length',String(length));
    if(range)h.set('Content-Range',`bytes ${range.offset}-${range.offset+range.length-1}/${asset.bytes}`);
    const status=range?206:200;
    if(request.method==='HEAD')return finish(new Response(null,{status,headers:h}));
    const object=await env.MEDIA.get(asset.objectKey,{...(range?{range}:{}),onlyIf:{etagMatches:head.etag}});
    if(!object)return finish(error(404,'asset_missing'));
    if(!('body' in object))return finish(error(409,'asset_changed'));
    if(!metadataMatches(object,asset) || object.etag!==head.etag || (range && (!object.range || !('offset' in object.range) || !('length' in object.range) || object.range.offset!==range.offset || object.range.length!==range.length))){await object.body.cancel();return finish(error(409,'asset_changed'));}
    return finish(new Response(object.body,{status,headers:h}));
   }
   const authorization=request.headers.get('Authorization');
   const session=await verify(authorization?.startsWith('Bearer ')?authorization.slice(7):null,env.SIGNING_KEY,'session',env.AUTH_EPOCH,now());
   if(!session)return finish(error(401,'invalid_or_expired_session'));
   if(url.pathname==='/v1/catalog' && ['GET','HEAD'].includes(request.method))return finish(Response.json(client));
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
    const claims={v:1,type:'media',sub:session.sub,id:track.id,revision:client.revision,epoch:env.AUTH_EPOCH,iat:issued,exp:Math.min(session.exp,issued+seconds)};
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
