import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,mkdir,writeFile,mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {existsSync} from 'node:fs';
import {request as httpRequest} from 'node:http';
import {createPreviewServer,ReadOnlyFileBucket} from '../local-preview.mjs';
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
