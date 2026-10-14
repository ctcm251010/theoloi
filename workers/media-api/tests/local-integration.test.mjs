import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile,mkdtemp,rm,stat,utimes} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {existsSync} from 'node:fs';
import {request as httpRequest} from 'node:http';
import {createPreviewServer,ReadOnlyFileBucket} from '../local-preview.mjs';
import * as preview from '../local-preview.mjs';
test('preview permits cross-site top-level HTML navigation without exposing API or framed resources',{skip:!existsSync(new URL('../../../delivery/manifest.vi.json',import.meta.url))?'Private manifest/media not available in source-only clone':false},async t=>{
 const server=await createPreviewServer({port:0});t.after(()=>{server.closeAllConnections();return new Promise(resolve=>server.close(resolve));});
 const base='http://127.0.0.1:'+server.address().port;
 const navigation={'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'navigate','Sec-Fetch-Dest':'document'};
 // Node fetch rewrites Sec-Fetch-Mode to cors; raw HTTP preserves the observed browser headers.
 const request=(route,options={})=>new Promise((resolve,reject)=>{
  const req=httpRequest(base+route,{...options,headers:options.headers??navigation},response=>{
   const chunks=[];response.on('data',chunk=>chunks.push(chunk));response.on('error',reject);
   response.on('end',()=>resolve(new Response(Buffer.concat(chunks),{status:response.statusCode,headers:response.headers})));
  });req.on('error',reject);req.end();
 });
 for(const route of ['/','/index.html']){
  const response=await request(route);
  assert.equal(response.status,200,route);assert.match(response.headers.get('Content-Type'),/^text\/html/);
  assert.match(await response.text(),/<title>AudioTP<\/title>/);
  assert.equal(response.headers.get('Cache-Control'),'no-store');
  assert.equal(response.headers.get('X-Frame-Options'),'DENY');
  assert.equal(response.headers.get('Content-Security-Policy'),"frame-ancestors 'none'");
  const head=await request(route,{method:'HEAD'});assert.equal(head.status,200);assert.equal(await head.text(),'');
 }
 for(const route of ['/connection.json','/catalog.client.json','/app.mjs','/v1/catalog','/v1/media/unlisted','/v1/local-session']){
  assert.equal((await request(route)).status,403,route);
 }
 for(const patch of [{'Sec-Fetch-Dest':'iframe'},{'Sec-Fetch-Dest':'empty'},{'Sec-Fetch-Mode':'cors'},{'Sec-Fetch-Mode':'no-cors'},{'Sec-Fetch-Mode':''}]){
  assert.equal((await request('/',{headers:{...navigation,...patch}})).status,403,JSON.stringify(patch));
 }
 assert.equal((await request('/',{method:'POST'})).status,403);
 assert.equal((await request('/v1/local-session',{method:'POST'})).status,403);
 const badHost=await new Promise((resolve,reject)=>{const req=httpRequest(base+'/',{headers:{...navigation,Host:'evil.test'}},response=>{response.resume();resolve(response.statusCode);});req.on('error',reject);req.end();});assert.equal(badHost,403);
 assert.equal((await fetch(base+'/',{headers:{'Sec-Fetch-Site':'none','Sec-Fetch-Mode':'navigate','Sec-Fetch-Dest':'document'}})).status,200);
});
const hash=data=>createHash('sha256').update(data).digest('hex');
test('desktop local access is opt-in and permits only exact native origins with the real 983 catalog',{skip:!existsSync(new URL('../../../delivery/manifest.vi.json',import.meta.url))?'Private manifest/media not available in source-only clone':false},async t=>{
 const servers=[];t.after(async()=>{for(const s of servers){s.closeAllConnections();await new Promise(r=>s.close(r));}});
 for(const desktop of [false,true]){
  const server=await createPreviewServer({port:0,desktop});servers.push(server);
  const base='http://127.0.0.1:'+server.address().port;
  for(const origin of ['http://tauri.localhost','https://tauri.localhost','tauri://localhost']){
   const response=await fetch(base+'/v1/local-session',{method:'POST',headers:{Origin:origin,'Sec-Fetch-Site':'cross-site'}});
   assert.equal(response.status,desktop?200:403);
   if(desktop){
    const bootstrapPreflight=await fetch(base+'/v1/local-session',{method:'OPTIONS',headers:{Origin:origin,'Sec-Fetch-Site':'cross-site','Access-Control-Request-Method':'POST'}});
    assert.equal(bootstrapPreflight.status,204);assert.equal(bootstrapPreflight.headers.get('Access-Control-Allow-Origin'),origin);
    assert.equal(response.headers.get('Access-Control-Allow-Origin'),origin);
    const session=await response.json();
    const headers={Origin:origin,'Sec-Fetch-Site':'cross-site',Authorization:'Bearer '+session.token};
    const preflight=await fetch(base+'/v1/catalog',{method:'OPTIONS',headers:{Origin:origin,'Sec-Fetch-Site':'cross-site','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'}});
    assert.equal(preflight.status,204);
    const catalog=await (await fetch(base+'/v1/catalog',{headers})).json();
    assert.equal(catalog.tracks.length,983);assert.ok(catalog.tracks.every(row=>row.id.startsWith('watv:')));
    const assetId=catalog.tracks.find(row=>row.mode==='silent').id;
    const ticket=await (await fetch(base+'/v1/play-tickets',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({assetId})})).json();
    const media=await fetch(base+ticket.path+'?ticket='+ticket.ticket,{headers:{Origin:origin,'Sec-Fetch-Site':'cross-site',Range:'bytes=0-31'}});
    assert.equal(media.status,206);assert.equal(media.headers.get('Access-Control-Allow-Origin'),origin);assert.equal((await media.arrayBuffer()).byteLength,32);
   }
  }
  for(const origin of ['https://evil.test','http://tauri.localhost.evil','null'])assert.equal((await fetch(base+'/v1/local-session',{method:'POST',headers:{Origin:origin,'Sec-Fetch-Site':'cross-site'}})).status,403);
 }
});
test('real HTTP integration: same Worker handler serves the exact guide/instrumental/silent files',{skip:!existsSync(new URL('../../../delivery/manifest.vi.json',import.meta.url))?'Private manifest/media not available in source-only clone':false},async t=>{
 const server=await createPreviewServer({port:0});t.after(()=>{server.closeAllConnections();return new Promise(resolve=>server.close(resolve));});
 const base='http://127.0.0.1:'+server.address().port;
 const config=await (await fetch(base+'/connection.json')).json();assert.equal(config.mode,'local-files');
 assert.equal((await fetch(base+'/v1/catalog')).status,401);
 const session=await (await fetch(base+'/v1/local-session',{method:'POST'})).json();assert.ok(session.token);
 const headers={Authorization:'Bearer '+session.token};const catalog=await (await fetch(base+'/v1/catalog',{headers})).json();assert.equal(catalog.tracks.length,983);
 assert.deepEqual(['guide','instrumental','silent'].map(mode=>catalog.tracks.filter(t=>t.mode===mode).length),[485,485,13]);
 const manifest=JSON.parse(await readFile(new URL('../../../delivery/manifest.vi.json',import.meta.url),'utf8'));
 for(const id of ['watv:vi:guide:4177','watv:vi:instrumental:17407','watv:vi:silent:19976']){
  const ticket=await (await fetch(base+'/v1/play-tickets',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({assetId:id})})).json();
  const url=base+ticket.path+'?ticket='+ticket.ticket;
  const head=await fetch(url,{method:'HEAD'});assert.equal(head.status,200);assert.equal(Number(head.headers.get('Content-Length')),manifest.assets[id].bytes);
  const range=await fetch(url,{headers:{Range:'bytes=0-1023'}});assert.equal(range.status,206);assert.equal((await range.arrayBuffer()).byteLength,1024);
  const full=await fetch(url);assert.equal(full.status,200);assert.equal(full.headers.get('Content-Type'),'audio/mp4');assert.equal(hash(Buffer.from(await full.arrayBuffer())),manifest.assets[id].sha256);
 }
 for(const route of ['/.secrets/r2.env','/delivery/manifest.vi.json','/fixtures/guide.wav','/../source/private'])assert.equal((await fetch(base+route)).status,404);
 assert.equal((await fetch(base+'/v1/local-session',{method:'POST',headers:{Origin:'https://evil.test'}})).status,403);
 const badHost=await new Promise((resolve,reject)=>{const req=httpRequest(base+'/',{headers:{Host:'evil.test'}},response=>{response.resume();resolve(response.statusCode);});req.on('error',reject);req.end();});assert.equal(badHost,403);
});
test('local file adapter rejects tampered bytes, wrong size and traversal without writing media',async t=>{
 const root=await mkdtemp(path.join(tmpdir(),'audiotp-readonly-'));t.after(()=>{assert.equal(path.dirname(path.resolve(root)),path.resolve(tmpdir()));assert.ok(path.basename(root).startsWith('audiotp-readonly-'));return rm(root,{recursive:true,force:true});});
 const bytes=Buffer.from('permitted-fixture');await mkdir(path.join(root,'media/audio'),{recursive:true});const file=path.join(root,'media/audio/fixture.m4a');await writeFile(file,bytes);
 const asset={assetId:'fixture',objectKey:'key',localPath:'media/audio/fixture.m4a',bytes:bytes.length,sha256:hash(bytes)};
 const bucket=new ReadOnlyFileBucket(root,{assets:{fixture:asset}});assert.equal((await bucket.head('key')).size,bytes.length);assert.equal(await bucket.head('unknown'),null);
 await writeFile(file,Buffer.alloc(bytes.length,1));await assert.rejects(()=>bucket.head('key'),/hash/);
 await writeFile(file,'short');await assert.rejects(()=>bucket.head('key'),/size/);
 const unsafe=new ReadOnlyFileBucket(root,{assets:{fixture:{...asset,localPath:'media/audio/../../secret'}}});await assert.rejects(()=>unsafe.head('key'),/unsafe/);
});

test('local verification never trusts a size/timestamp cache after a same-size rewrite',async t=>{
 const root=await mkdtemp(path.join(tmpdir(),'audiotp-readonly-'));
 t.after(()=>{assert.equal(path.dirname(path.resolve(root)),path.resolve(tmpdir()));assert.ok(path.basename(root).startsWith('audiotp-readonly-'));return rm(root,{recursive:true,force:true});});
 await mkdir(path.join(root,'media/audio'),{recursive:true});
 const file=path.join(root,'media/audio/fixture.m4a'),bytes=Buffer.from('self-authored-cache-fixture');
 await writeFile(file,bytes);
 const bucket=new ReadOnlyFileBucket(root,{assets:{fixture:{assetId:'fixture',objectKey:'key',localPath:'media/audio/fixture.m4a',bytes:bytes.length,sha256:hash(bytes)}}});
 await bucket.head('key');const before=await stat(file);
 await writeFile(file,Buffer.alloc(bytes.length,1));await utimes(file,before.atime,before.mtime);
 // Windows may also preserve ctime at its filesystem timestamp resolution.
 // Even an unchanged metadata fingerprint is not proof that bytes are unchanged.
 if(bucket.verified){const now=await stat(file);bucket.verified.set('key',[now.dev,now.ino,now.size,now.mtimeMs,now.ctimeMs].join(':'));}
 await assert.rejects(()=>bucket.head('key'),/hash/);
});

test('supplementary local prayer bucket requires exact registered path, key and verified bytes',async t=>{
 const root=await mkdtemp(path.join(tmpdir(),'audiotp-readonly-'));t.after(()=>{assert.equal(path.dirname(path.resolve(root)),path.resolve(tmpdir()));assert.ok(path.basename(root).startsWith('audiotp-readonly-'));return rm(root,{recursive:true,force:true});});
 const bytes=Buffer.from('self-authored prayer HTTP bytes'),id='watv:vi:prayer:our-wish';
 const asset={assetId:id,localPath:'media/prayer/watv/vi/our-wish/our-wish.m4a',objectKey:`audio/v1/watv/vi/prayer/our-wish/${hash(bytes)}.m4a`,bytes:bytes.length,sha256:hash(bytes)};
 const file=path.join(root,asset.localPath);await mkdir(path.dirname(file),{recursive:true});await writeFile(file,bytes);
 const bucket=new ReadOnlyFileBucket(root,{assets:{}},{[id]:asset});assert.equal((await bucket.head(asset.objectKey)).size,bytes.length);
 const result=await bucket.get(asset.objectKey,{range:{offset:1,length:3}});assert.deepEqual(Buffer.from(await new Response(result.body).arrayBuffer()),bytes.subarray(1,4));
 assert.equal(await bucket.head('audio/v1/watv/vi/prayer/unlisted'),null);
 for(const patch of [{localPath:'media/prayer/private.m4a'},{localPath:'media/audio/../../secret'},{objectKey:'arbitrary'},{assetId:'other'},{sha256:'bad'}])assert.throws(()=>new ReadOnlyFileBucket(root,{assets:{}},{[id]:{...asset,...patch}}),/unsafe/);
 assert.throws(()=>new ReadOnlyFileBucket(root,{assets:{original:asset}},{[id]:asset}),/collision/);
 const originalOnly=new ReadOnlyFileBucket(root,{assets:{[id]:asset}});await assert.rejects(()=>originalOnly.head(asset.objectKey),/unsafe/);
 await writeFile(file,Buffer.alloc(bytes.length,1));await assert.rejects(()=>bucket.head(asset.objectKey),/hash/);
});

test('optional quick audio loading defaults empty and refuses mismatched local registry',async t=>{
 const root=await mkdtemp(path.join(tmpdir(),'audiotp-readonly-'));t.after(()=>{assert.equal(path.dirname(path.resolve(root)),path.resolve(tmpdir()));assert.ok(path.basename(root).startsWith('audiotp-readonly-'));return rm(root,{recursive:true,force:true});});
 assert.deepEqual(await preview.loadQuickAudio(root),{quickAudio:undefined,assets:{}});
 const id='watv:vi:prayer:our-wish',digest=hash('opaque'),asset={assetId:id,objectKey:`audio/v1/watv/vi/prayer/our-wish/${digest}.m4a`,bytes:6,sha256:digest};
 const track={id,logicalId:id,mode:'prayer',section:null,number:null,title:'Cầu nguyện chúng con mong muốn',category:'Cầu nguyện',durationSeconds:69.427664};
 const quickAudio={schemaVersion:1,revision:'sha256:'+digest,tracks:[track],assets:{[id]:asset}};
 const folder=path.join(root,'workers/media-api/generated');await mkdir(folder,{recursive:true});await writeFile(path.join(folder,'quick-audio.json'),JSON.stringify(quickAudio));
 await assert.rejects(()=>preview.loadQuickAudio(root));
 const assets={[id]:{...asset,localPath:'media/prayer/watv/vi/our-wish/our-wish.m4a'}};
 const manifest={schemaVersion:1,revision:quickAudio.revision,tracks:[track],assets};await mkdir(path.join(root,'delivery'));await writeFile(path.join(root,'delivery/prayer-manifest.vi.json'),JSON.stringify(manifest));
 assert.deepEqual(await preview.loadQuickAudio(root),{quickAudio,assets});
 for(const patch of [{revision:'sha256:'+'0'.repeat(64)},{assets:{[id]:{...assets[id],sha256:'0'.repeat(64)}}},{assets:{[id]:{...assets[id],localPath:'media/prayer/private.m4a'}}},{tracks:[]}]){
  await writeFile(path.join(root,'delivery/prayer-manifest.vi.json'),JSON.stringify({...manifest,...patch}));await assert.rejects(()=>preview.loadQuickAudio(root));
 }
});
