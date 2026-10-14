// Read-only loopback adapter: runs the SAME Worker handler against existing M4A.
// No Cloudflare connection, R2 credential, upload or audio copy is involved.
import {createServer} from 'node:http';
import {readFile,lstat,stat,realpath} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {createHash,randomBytes} from 'node:crypto';
import {Readable} from 'node:stream';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
import {createService} from './src/service.mjs';
import {validateQuickAudio} from './src/validate-data.mjs';

const here=path.dirname(fileURLToPath(import.meta.url));
const defaultRoot=path.resolve(here,'../..');
const baseline='b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c';
const localCode='public-local-preview-not-production-access';
const desktopOrigins=['http://tauri.localhost','https://tauri.localhost','tauri://localhost'];
const hash=data=>createHash('sha256').update(data).digest('hex');

function validatePrayerAsset(id,asset){
 const slug=id==='watv:vi:prayer:our-wish'?'our-wish':id==='watv:vi:prayer:unison-prayer'?'unison-prayer':null;
 if(!slug || asset?.assetId!==id || Object.keys(asset).sort().join(',')!=='assetId,bytes,localPath,objectKey,sha256' || asset.localPath!==`media/prayer/watv/vi/${slug}/${slug}.m4a` || typeof asset.sha256!=='string' || !/^[a-f0-9]{64}$/.test(asset.sha256) || asset.objectKey!==`audio/v1/watv/vi/prayer/${slug}/${asset.sha256}.m4a` || !Number.isSafeInteger(asset.bytes) || asset.bytes<=0)throw Error('unsafe_prayer_registry');
}

// A missing supplementary projection means no prayer. Existing malformed or
// mismatched files fail closed; they never extend the original manifest roots.
export async function loadQuickAudio(root){
 let quickAudio;
 try{quickAudio=JSON.parse(await readFile(path.join(root,'workers/media-api/generated/quick-audio.json'),'utf8'));}
 catch(error){if(error.code==='ENOENT')return {quickAudio:undefined,assets:{}};throw error;}
 validateQuickAudio(quickAudio,{schemaVersion:1,revision:'local-validation',tracks:[]},{});
 if(!quickAudio.tracks.length)return {quickAudio,assets:{}};
 const manifest=JSON.parse(await readFile(path.join(root,'delivery/prayer-manifest.vi.json'),'utf8'));
 if(manifest.schemaVersion!==quickAudio.schemaVersion || manifest.revision!==quickAudio.revision || !isDeepStrictEqual(manifest.tracks,quickAudio.tracks) || !manifest.assets || Object.keys(manifest.assets).length!==quickAudio.tracks.length)throw Error('unreviewed_prayer_manifest');
 for(const [id,asset] of Object.entries(manifest.assets)){
  validatePrayerAsset(id,asset);
  const {localPath,...projection}=asset;
  if(!isDeepStrictEqual(projection,quickAudio.assets[id]))throw Error('unreviewed_prayer_manifest');
 }
 return {quickAudio,assets:manifest.assets};
}

export class ReadOnlyFileBucket {
 constructor(root,manifest,supplemental={}){
  this.root=path.resolve(root);this.entries=new Map(Object.values(manifest.assets).map(a=>[a.objectKey,a]));this.prayerKeys=new Set();
  for(const [id,asset] of Object.entries(supplemental)){
   validatePrayerAsset(id,asset);
   if(this.entries.has(asset.objectKey) || Object.values(manifest.assets).some(a=>a.assetId===id))throw Error('prayer_registry_collision');
   this.entries.set(asset.objectKey,asset);this.prayerKeys.add(asset.objectKey);
  }
 }
 async lookup(key){
  const asset=this.entries.get(key);if(!asset)return null;
  const namespace=this.prayerKeys.has(key)?'media/prayer/':'media/audio/';
  const pieces=asset.localPath.split('/');
  if(!asset.localPath.startsWith(namespace) || pieces.some(p=>!p || p==='.' || p==='..' || /[\\:%\x00-\x1f]/.test(p)))throw Error('unsafe_media_path');
  let target=this.root;
  for(const piece of pieces){target=path.join(target,piece);if((await lstat(target)).isSymbolicLink())throw Error('redirected_media');}
  const actual=await realpath(target),mediaRoot=await realpath(path.join(this.root,namespace));
  const relative=path.relative(mediaRoot,actual);if(relative.startsWith('..') || path.isAbsolute(relative))throw Error('unsafe_media_path');
  const info=await stat(actual);if(!info.isFile() || info.size!==asset.bytes)throw Error('media_size_mismatch');
  // Windows can retain identical size/mtime/ctime after a rapid rewrite. The
  // local read-only preview therefore verifies bytes for each media lookup.
  const digest=createHash('sha256');for await(const chunk of createReadStream(actual))digest.update(chunk);
  if(digest.digest('hex')!==asset.sha256)throw Error('media_hash_mismatch');
  return {asset,target:actual,meta:{size:asset.bytes,etag:asset.sha256,httpEtag:`"${asset.sha256}"`,customMetadata:{sha256:asset.sha256,'asset-id':asset.assetId},httpMetadata:{contentType:'audio/mp4'}}};
 }
 async head(key){return (await this.lookup(key))?.meta ?? null;}
 async get(key,options={}){
  const entry=await this.lookup(key);if(!entry)return null;
  if(options.onlyIf?.etagMatches && options.onlyIf.etagMatches!==entry.meta.etag)return entry.meta;
  const range=options.range;
  const source=createReadStream(entry.target,range?{start:range.offset,end:range.offset+range.length-1}:{});
  return {...entry.meta,...(range?{range}:{}),body:Readable.toWeb(source)};
 }
}
function localLimiter(limit){const counts=new Map();return {async limit({key}){const minute=Math.floor(Date.now()/60000);if(counts.size>200)counts.clear();const previous=counts.get(key);const count=previous?.minute===minute?previous.count+1:1;counts.set(key,{minute,count});return {success:count<=limit};}};}
export async function createPreviewServer({root=defaultRoot,port=8766,desktop=false}={}){
 const raw=await readFile(path.join(root,'delivery/manifest.vi.json'));
 if(hash(raw)!==baseline)throw Error('unreviewed_manifest');
 const manifest=JSON.parse(raw);
 const {quickAudio,assets:prayerAssets}=await loadQuickAudio(root);
 const client=JSON.parse(await readFile(path.join(root,'workers/media-api/generated/catalog.json'),'utf8'));
 const allowed=JSON.parse(await readFile(path.join(root,'workers/media-api/generated/assets.json'),'utf8'));
 const worker=createService(client,allowed,{quickAudio});
 const web=path.join(root,'apps/windows/web');
 const files=new Set(['index.html','styles.css','app.mjs','catalog.mjs','player.mjs','storage.mjs','ui-core.mjs','api-client.mjs','remember-access.mjs','supplementary.mjs','app-updates.mjs','offline.mjs','catalog.client.json','quick-play.json','favicon.svg']);
 const env={SERVING_ENABLED:'true',LOCAL_PREVIEW:'true',AUTH_EPOCH:'local-only',SIGNING_KEY:randomBytes(32).toString('hex'),GROUP_CODE_SHA256:hash(localCode),SESSION_SECONDS:'43200',MEDIA:new ReadOnlyFileBucket(root,manifest,prayerAssets),LOGIN_LIMITER:localLimiter(30),REQUEST_LIMITER:localLimiter(300)};
 const server=createServer(async(req,res)=>{
  try{
   const actualPort=server.address().port;
   const nativeRequest=desktop && desktopOrigins.includes(req.headers.origin) && req.url.startsWith('/v1/');
   // Browser Use/link navigation can be cross-site. Permit only the HTML entry
   // document, never cross-site API, media, subresource, iframe or POST requests.
   const pageNavigation=['GET','HEAD'].includes(req.method) && req.headers['sec-fetch-mode']==='navigate' && req.headers['sec-fetch-dest']==='document' && ['/', '/index.html'].includes(new URL(req.url,'http://127.0.0.1').pathname);
   if(![`127.0.0.1:${actualPort}`,`localhost:${actualPort}`].includes(req.headers.host) || (req.headers['sec-fetch-site']==='cross-site' && !nativeRequest && !pageNavigation)){res.writeHead(403,{'Cache-Control':'no-store'});res.end();return;}
   const base='http://'+req.headers.host;env.ALLOWED_ORIGINS=[`http://127.0.0.1:${actualPort}`,`http://localhost:${actualPort}`,...(desktop?desktopOrigins:[])].join(',');
   const url=new URL(req.url,base);const method=req.method;
   if(url.pathname==='/connection.json' && ['GET','HEAD'].includes(method)){
    const body=JSON.stringify({mode:'local-files',apiBase:base,version:'1.0.3',buildNumber:'local'});res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store','Content-Length':Buffer.byteLength(body)});res.end(method==='HEAD'?undefined:body);return;
   }
   if(url.pathname.startsWith('/v1/')){
    const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>4096){res.writeHead(413);res.end();return;}chunks.push(chunk);}
    const headers=new Headers();for(const [name,value]of Object.entries(req.headers))if(value)headers.set(name,Array.isArray(value)?value.join(','):value);
    headers.set('CF-Connecting-IP',req.socket.remoteAddress || '127.0.0.1');
    let request=new Request(url,{method,headers,...(!['GET','HEAD'].includes(method)?{body:Buffer.concat(chunks)}:{})});
    if(url.pathname==='/v1/local-session'){
     if(method!=='OPTIONS'){
      if(method!=='POST' || (headers.has('Origin') && !env.ALLOWED_ORIGINS.split(',').includes(headers.get('Origin')))){res.writeHead(403);res.end();return;}
      request=new Request(base+'/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json','CF-Connecting-IP':'127.0.0.1',...(headers.has('Origin')?{Origin:headers.get('Origin')}: {})},body:JSON.stringify({code:localCode})});
     }
    }
    const response=await worker.fetch(request,env);
    if(desktop && desktopOrigins.includes(headers.get('Origin'))){
     const route=['/v1/local-session','/v1/catalog','/v1/play-tickets'].includes(url.pathname)?url.pathname:url.pathname.startsWith('/v1/media/')?'/v1/media/:asset':'other';
     // Fixed route/status only: never log query tickets, headers, bodies or session data.
     console.info(JSON.stringify({event:'desktop_local_api',method,route,status:response.status}));
    }
    res.writeHead(response.status,Object.fromEntries(response.headers));
    if(response.body){const stream=Readable.fromWeb(response.body);res.on('close',()=>stream.destroy());stream.on('error',()=>res.destroy());stream.pipe(res);}else res.end();return;
   }
   if(!['GET','HEAD'].includes(method)){res.writeHead(405);res.end();return;}
   let name;try{name=decodeURIComponent(url.pathname).replace(/^\//,'') || 'index.html';}catch{res.writeHead(403);res.end();return;}
   if(!files.has(name)){res.writeHead(404);res.end();return;}
   const target=path.join(web,name);if((await lstat(target)).isSymbolicLink()){res.writeHead(403);res.end();return;}
   const content=await readFile(target);
   const types={'.html':'text/html; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.svg':'image/svg+xml'};
   res.writeHead(200,{'Content-Type':types[path.extname(name)] || 'application/octet-stream','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Cross-Origin-Resource-Policy':'same-origin',...(name==='index.html'?{'X-Frame-Options':'DENY','Content-Security-Policy':"frame-ancestors 'none'"}:{}),'Content-Length':content.length});res.end(method==='HEAD'?undefined:content);
  }catch{if(!res.headersSent)res.writeHead(503,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end('{"error":"local_preview_unavailable"}');}
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',resolve);});
 return server;
}
if(process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 const input=process.argv.slice(2),desktop=input.includes('--desktop');
 if(input.filter(x=>x==='--desktop').length>1)throw Error('Duplicate --desktop');
 const args=input.filter(x=>x!=='--desktop');if(args.length && !(args.length===2 && args[0]==='--port' && /^\d+$/.test(args[1])))throw Error('Usage: node local-preview.mjs [--desktop] [--port NUMBER]');
 const port=args.length?Number(args[1]):8766;if(port<0 || port>65535)throw Error('Invalid port');
 const server=await createPreviewServer({port,desktop});
 console.log(`AudioTP actual local audio: http://127.0.0.1:${server.address().port} — local file-backed Worker integration; NOT live R2.`);
 process.on('SIGINT',()=>{server.close();server.closeAllConnections();});
}
