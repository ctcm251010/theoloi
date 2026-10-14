// TEST ONLY: isolated browser presentation harness. No production data, disk
// download, persistent offline records, credentials, or external API access.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import {fixtureCatalog,fixtureQuick,TEST_CODE} from '../native-mock.mjs';

const web=new URL('../web/',import.meta.url);
const allow=new Set(['app.mjs','offline.mjs','api-client.mjs','app-updates.mjs','catalog.mjs','player.mjs','storage.mjs','remember-access.mjs','supplementary.mjs','ui-core.mjs','styles.css','favicon.svg']);
const banner=`<aside style="padding:12px;background:#fae7a0;color:#231e0b;font:13px system-ui"><strong>TEST ONLY — self-authored fixtures; in-memory mock IPC; no real downloads, installers or offline playback.</strong><div>Scenarios: <a href="/?scenario=empty">Empty</a> · <a href="/?scenario=partial">Partial</a> · <a href="/?scenario=full">Full</a> · <a href="/?scenario=failed">Failed</a> · <a href="/?scenario=partial&amp;verify=1">Startup verification</a> · <a href="/updates/?scenario=update-available">Update available</a> · <a href="/updates/?scenario=update-error">Update failure</a> · <a href="/updates/?scenario=update-current">No update</a> · <a href="/updates/?scenario=update-offline">Update offline</a></div><div>Public TEST password: <code>${TEST_CODE}</code></div><button id="TEST-offline">TEST: lose connectivity</button> <button id="TEST-online">TEST: connectivity returns</button> <button id="TEST-fail">TEST: fail next queued download</button></aside>`;

function bridgeScript(base){return `
const catalog=${JSON.stringify(fixtureCatalog)};
const params=new URLSearchParams(location.search),scenario=params.get('scenario') || 'empty';
const manifest={...catalog,assets:catalog.tracks.map(t=>({assetId:t.id,bytes:1024*1024,sha256:'a'.repeat(64),contentType:'audio/wav'}))};
let saved=new Set(scenario==='full'?catalog.tracks.map(t=>t.id):['partial','failed'].includes(scenario)?[catalog.tracks[0].id]:[]),queue=[],failed=new Set(scenario==='failed'?[catalog.tracks[1].id]:[]),failNext=false,phase=params.has('verify')?'verifying':'idle',done=0,bytes=0,total=0;
const items=new Map(),updateListeners=new Set();let timer;
function snapshot(){return structuredClone({manifest,completed:[...saved],items:catalog.tracks.map(t=>({assetId:t.id,status:saved.has(t.id)?'completed':failed.has(t.id)?'failed':items.get(t.id)||'missing',bytes:saved.has(t.id)?1024*1024:0,...(failed.has(t.id)?{error:'TEST simulated transfer failure'}:{})})),job:{status:phase,total,completed:done,failed:failed.size,bytes,totalBytes:total*1024*1024},freeBytes:1024**3});}
function begin(){clearInterval(timer);phase='running';timer=setInterval(()=>{if(!queue.length){phase=failed.size?'failed':'completed';clearInterval(timer);return;}const id=queue[0];items.set(id,'downloading');bytes=Math.min(total*1024*1024,bytes+128*1024);if(bytes>= (done+1)*1024*1024){queue.shift();if(failNext){failNext=false;failed.add(id);items.set(id,'failed');}else{saved.add(id);items.set(id,'completed');}done++;}},400);}
if(params.has('verify'))setTimeout(()=>{phase='idle';},2500);
window.__TAURI__={core:{invoke:async(command,args={})=>{
 if(command==='check_release_info' || command==='check_update'){if(scenario==='update-offline')throw Error('TEST no Internet');return scenario==='update-current'?null:{currentVersion:'0.0.0',version:'9.0.0'};}
 if(command==='install_update'){for(let percent=0;percent<=100;percent+=10){await new Promise(resolve=>setTimeout(resolve,300));for(const listener of updateListeners)listener({payload:{phase:percent===100?'installing':'downloading',downloaded:percent*1024,total:100*1024,percent}});}if(scenario==='update-error')throw Error('TEST invalid update package');return null;}
 if(command==='offline_status' || command==='offline_sync')return snapshot();
 if(command==='offline_start'){queue=[...new Set(args.ids)].filter(id=>!saved.has(id));total=queue.length;done=0;bytes=0;failed.clear();for(const id of queue)items.set(id,'queued');begin();return snapshot();}
 if(command==='offline_control'){
  if(args.action==='pause'){clearInterval(timer);phase='paused';for(const id of queue)items.set(id,'paused');}
  if(args.action==='resume')begin();
  if(args.action==='cancel'){clearInterval(timer);phase='cancelled';for(const id of queue)items.set(id,'cancelled');queue=[];}
  if(args.action==='retry'){queue=[...failed];failed.clear();total=queue.length;done=0;bytes=0;for(const id of queue)items.set(id,'queued');begin();}
  return snapshot();
 }
 if(command==='offline_remove'){clearInterval(timer);phase='idle';queue=[];for(const id of args.ids){saved.delete(id);failed.delete(id);items.delete(id);}return snapshot();}
 if(command==='clear_update')return null;
 throw Error('TEST unsupported command '+command);
}},event:{listen:async(name,listener)=>{if(name==='app-update-progress')updateListeners.add(listener);return ()=>updateListeners.delete(listener);}}};
document.getElementById('TEST-offline').onclick=async()=>{await fetch('/TEST/network',{method:'POST',body:'offline'});window.dispatchEvent(new Event('offline'));};
document.getElementById('TEST-online').onclick=async()=>{await fetch('/TEST/network',{method:'POST',body:'online'});window.dispatchEvent(new Event('online'));};
document.getElementById('TEST-fail').onclick=()=>{failNext=true;document.getElementById('TEST-fail').textContent='TEST: next download will fail';};
await import('./app.mjs');
`;}

export async function createOfflineBrowserHarness({port=0}={}){
 if(!Number.isInteger(port) || port<0 || port>65535)throw Error('Invalid loopback port');
 let online=true;
 const server=createServer(async(req,res)=>{
  const base=`http://127.0.0.1:${server.address().port}`,url=new URL(req.url,base),updaterTest=url.pathname.startsWith('/updates/');
  if(updaterTest)url.pathname=url.pathname.slice('/updates'.length);
  const send=(status,body,type='text/plain')=>{res.writeHead(status,{'Content-Type':type,'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(body);};
  const json=(status,body)=>send(status,JSON.stringify(body),'application/json');
  if(req.headers.host!==new URL(base).host || req.headers.origin && req.headers.origin!==base)return send(403,'TEST loopback only');
  try{
   if(url.pathname==='/TEST/network' && req.method==='POST'){let body='';for await(const chunk of req){body+=chunk;if(body.length>64)return send(413,'Too large');}online=body==='online';return json(200,{online});}
   if(url.pathname.startsWith('/v1/')){
    if(!online)return json(503,{error:'TEST offline'});
    if(url.pathname==='/v1/health')return json(200,{status:'TEST ready'});
    if(url.pathname==='/v1/auth/login')return json(200,{token:'TEST-browser-memory-only',expiresAt:Date.now()/1000+3600});
    if(url.pathname==='/v1/catalog')return json(200,fixtureCatalog);
    if(url.pathname==='/v1/quick-audio')return json(200,{schemaVersion:1,tracks:[]});
    return json(404,{error:'TEST unsupported route'});
   }
   if(url.pathname==='/' || url.pathname==='/index.html'){const html=await readFile(new URL('index.html',web),'utf8');return send(200,html.replace('<body>','<body>'+banner).replace('<script type="module" src="./app.mjs"></script>','<script type="module" src="./TEST-bridge.mjs"></script>'),'text/html; charset=utf-8');}
   if(url.pathname==='/TEST-bridge.mjs')return send(200,bridgeScript(base),'text/javascript; charset=utf-8');
   if(url.pathname==='/catalog.client.json')return json(200,fixtureCatalog);
   if(url.pathname==='/quick-play.json')return json(200,fixtureQuick);
   if(url.pathname==='/connection.json')return json(200,{mode:updaterTest?'remote':'test-fixtures',apiBase:base,version:'0.0.0',buildNumber:'TEST-browser-offline'});
   const name=url.pathname.slice(1);if(!allow.has(name))return send(404,'TEST file not allowed');
   let source=await readFile(new URL(name,web));
   // Only this TEST served copy enables the updater presentation for loopback.
   // Production source/CSP/connection config are never changed by the harness.
   if(updaterTest && name==='app.mjs')source=source.toString('utf8').replace("connection.base==='https://audiotp-media-api.ctcm251010.workers.dev'",`connection.base==='${base}'`);
   return send(200,source,name.endsWith('.mjs')?'text/javascript; charset=utf-8':name.endsWith('.css')?'text/css; charset=utf-8':'image/svg+xml');
  }catch{return send(500,'TEST harness error');}
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',resolve);});return server;
}
if(process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 const args=process.argv.slice(2);if(args.length && !(args.length===2 && args[0]==='--port' && /^\d+$/.test(args[1])))throw Error('Usage: node tests/offline-browser-harness.mjs [--port NUMBER]');
 const server=await createOfflineBrowserHarness({port:args.length?Number(args[1]):0});console.log(`TEST ONLY offline UI: http://127.0.0.1:${server.address().port}/?scenario=partial`);
 process.on('SIGINT',()=>{server.close();server.closeAllConnections();});
}
