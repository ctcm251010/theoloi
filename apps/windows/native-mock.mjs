// Acceptance only. No production catalog/media, Cloudflare, credential or R2 access.
import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {randomBytes,createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import {byteRange} from '../../workers/media-api/src/service.mjs';

const fixture=JSON.parse(await readFile(new URL('./test-fixtures.json',import.meta.url),'utf8'));
export const fixtureCatalog=fixture.catalog,fixtureQuick=fixture.quick;
export const TEST_CODE='public-self-authored-native-test-code';
const origins=new Set(['http://tauri.localhost','https://tauri.localhost','tauri://localhost','http://127.0.0.1:8871']);
const opaque=()=>randomBytes(24).toString('base64url');
export async function createMockServer({port=8870}={}){
 if(!Number.isInteger(port) || port<0 || port>65535)throw Error('Invalid loopback port');
 const audio=new Map();
 for(const track of fixtureCatalog.tracks){
  const bytes=await readFile(new URL(`./web/fixtures/${track.mode}.wav`,import.meta.url));
  if(bytes.toString('ascii',0,4)!=='RIFF' || bytes.toString('ascii',8,12)!=='WAVE')throw Error('Invalid self-authored WAV');
  audio.set(track.id,bytes);
 }
 const sessions=new Map(),tickets=new Map();
 const server=createServer(async(req,res)=>{
  const base=`http://127.0.0.1:${server.address().port}`,origin=req.headers.origin;
  const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Vary':'Origin'};
  const reply=(status,body,extra={})=>{res.writeHead(status,{...headers,...extra});res.end(req.method==='HEAD'?undefined:body);};
  const json=(status,data)=>reply(status,JSON.stringify(data),{'Content-Type':'application/json'});
  try{
   if(req.headers.host!==new URL(base).host || (origin && !origins.has(origin) && origin!==base))return json(403,{error:'forbidden'});
   if(origin)headers['Access-Control-Allow-Origin']=origin;
   if(req.method==='OPTIONS')return reply(204,null,{'Access-Control-Allow-Methods':'GET, HEAD, POST, OPTIONS','Access-Control-Allow-Headers':'Authorization, Content-Type, Range'});
   const url=new URL(req.url,base),now=Date.now()/1000;
   for(const [key,value]of sessions)if(value<=now)sessions.delete(key);
   for(const [key,value]of tickets)if(value.expiresAt<=now)tickets.delete(key);
   let body={};
   if(req.method==='POST'){
    const chunks=[];let size=0;for await(const chunk of req){size+=chunk.length;if(size>4096)return json(413,{error:'too_large'});chunks.push(chunk);}
    try{body=JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');}catch{return json(400,{error:'invalid_json'});}
   }
   if(url.pathname==='/v1/auth/login' && req.method==='POST'){
    if(body.code!==TEST_CODE)return json(401,{error:'invalid_code'});
    if(sessions.size>=64)return json(429,{error:'test_limit'});
    const token=opaque(),expiresAt=now+3600;sessions.set(token,expiresAt);return json(200,{token,expiresAt});
   }
   if(url.pathname.startsWith('/v1/media/') && ['GET','HEAD'].includes(req.method)){
    const id=decodeURIComponent(url.pathname.slice('/v1/media/'.length)),ticket=tickets.get(url.searchParams.get('ticket'));
    if(!ticket || ticket.id!==id || ticket.expiresAt<=now)return json(401,{error:'invalid_ticket'});
    const bytes=audio.get(id);if(!bytes)return json(404,{error:'missing_fixture'});
    const range=req.method==='GET' && req.headers.range?byteRange(req.headers.range,bytes.length):null;
    if(req.method==='GET' && req.headers.range && !range)return reply(416,null,{'Content-Range':`bytes */${bytes.length}`});
    const output=range?bytes.subarray(range.offset,range.offset+range.length):bytes;
    return reply(range?206:200,output,{'Content-Type':'audio/wav','Accept-Ranges':'bytes','ETag':'"'+createHash('sha256').update(bytes).digest('hex')+'"','X-AudioTP-Asset-Id':id,'Content-Length':output.length,...(range?{'Content-Range':`bytes ${range.offset}-${range.offset+range.length-1}/${bytes.length}`}:{})});
   }
   if(!url.pathname.startsWith('/v1/'))return json(404,{error:'not_found'});
   const expiry=sessions.get(String(req.headers.authorization || '').replace(/^Bearer /,''));
   if(!expiry || expiry<=now)return json(401,{error:'session_required'});
   if(url.pathname==='/v1/catalog' && req.method==='GET')return json(200,fixtureCatalog);
   if(url.pathname==='/v1/offline-manifest' && req.method==='GET')return json(200,{schemaVersion:1,revision:fixtureCatalog.revision,tracks:fixtureCatalog.tracks,assets:fixtureCatalog.tracks.map(t=>({assetId:t.id,bytes:audio.get(t.id).length,sha256:createHash('sha256').update(audio.get(t.id)).digest('hex'),contentType:'audio/wav'}))});
   if(url.pathname==='/v1/play-tickets' && req.method==='POST'){
    if(!audio.has(body.assetId))return json(404,{error:'unknown_test_asset'});
    if(tickets.size>=256)return json(429,{error:'test_limit'});
    const ticket=opaque()+'.'+opaque(),expiresAt=Math.min(expiry,now+600);tickets.set(ticket,{id:body.assetId,expiresAt});
    return json(200,{assetId:body.assetId,path:'/v1/media/'+encodeURIComponent(body.assetId),ticket,expiresAt});
   }
   return json(404,{error:'not_found'});
  }catch{if(!res.headersSent)json(500,{error:'test_server_error'});else res.destroy();}
 });
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(port,'127.0.0.1',resolve);});
 return server;
}
if(process.argv[1] && import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 const args=process.argv.slice(2);if(args.length && !(args.length===2 && args[0]==='--port' && /^\d+$/.test(args[1])))throw Error('Usage: node native-mock.mjs [--port NUMBER]');
 const server=await createMockServer({port:args.length?Number(args[1]):8870});
 console.log(`TEST ONLY mock: http://127.0.0.1:${server.address().port}; public fixture code: ${TEST_CODE}; no real audio/R2.`);
 process.on('SIGINT',()=>{server.close();server.closeAllConnections();});
}
