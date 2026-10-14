// Opaque self-authored bytes exercise HTTP/R2, not audio quality. No private input,
// network Cloudflare API, persistent R2, credentials or generated JSON required.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash,randomBytes} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {Miniflare,convertV4MiniflareOptions} from 'miniflare';
import {MediaAPI} from '../../../apps/windows/web/api-client.mjs';

test('source-only workerd: online client, private R2 simulation, exact ranges and safe errors',async t=>{
 const root=fileURLToPath(new URL('../src/',import.meta.url));
 const bytes=Buffer.from('self-authored opaque HTTP streaming fixture '.repeat(128));
 const asset={assetId:'fixture:guide:1',objectKey:'audio/v1/watv/vi/fixture/guide1.m4a',bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')};
 const track={id:asset.assetId,logicalId:'fixture:song:1',mode:'guide',section:'main',number:1,title:'Fixture tự tạo',category:'Fixture',durationSeconds:120};
 const client={schemaVersion:1,revision:'synthetic-runtime-v1',tracks:[track]};
 const prayerId='watv:vi:prayer:our-wish';
 const prayer={id:prayerId,logicalId:prayerId,mode:'prayer',section:null,number:null,title:'Cầu nguyện chúng con mong muốn',category:'Cầu nguyện',durationSeconds:69.427664};
 const prayerAsset={...asset,assetId:prayerId,objectKey:`audio/v1/watv/vi/prayer/our-wish/${asset.sha256}.m4a`};
 const quickAudio={schemaVersion:1,revision:'sha256:'+asset.sha256,tracks:[prayer],assets:{[prayerId]:prayerAsset}};
 const minisign=`untrusted comment: synthetic\n${Buffer.concat([Buffer.from('Ed'),Buffer.alloc(72)]).toString('base64')}\ntrusted comment: synthetic\n${Buffer.alloc(64).toString('base64')}\n`;
 const updates={version:'1.0.1',pubDate:'2026-10-13T00:00:00Z',notes:'Synthetic',objectKey:'updates/windows-x86_64/1.0.1/AudioTP_1.0.1_x64-setup.exe',bytes:bytes.length,sha256:asset.sha256,signature:Buffer.from(minisign).toString('base64')};
 const code='synthetic-runtime-code-never-a-production-secret';
 const modules=[{type:'ESModule',path:root+'source-test-entry.mjs',contents:`import {createService} from './service.mjs'; export default createService(${JSON.stringify(client)},${JSON.stringify({[asset.assetId]:asset})},${JSON.stringify({quickAudio,updates})});`}];
 for(const name of ['service.mjs','validate-data.mjs'])modules.push({type:'ESModule',path:root+name,contents:await readFile(root+name,'utf8')});
 const mf=new Miniflare(convertV4MiniflareOptions({rootPath:root,modules,modulesRoot:root,compatibilityDate:'2026-10-12',compatibilityFlags:['nodejs_compat'],cf:false,host:'127.0.0.1',port:0,r2Buckets:['MEDIA'],r2Persist:false,bindings:{SERVING_ENABLED:'true',AUTH_EPOCH:'synthetic',SIGNING_KEY:randomBytes(32).toString('hex'),GROUP_CODE_SHA256:createHash('sha256').update(code).digest('hex'),ALLOWED_ORIGINS:'http://tauri.localhost',SESSION_SECONDS:'43200'},ratelimits:{LOGIN_LIMITER:{namespace_id:'1',simple:{limit:100,period:60}},REQUEST_LIMITER:{namespace_id:'2',simple:{limit:100,period:60}}}}));
 t.after(()=>mf.dispose());
 const bucket=await mf.getR2Bucket('MEDIA');
 await bucket.put(asset.objectKey,bytes,{httpMetadata:{contentType:'audio/mp4'},customMetadata:{sha256:asset.sha256,'asset-id':asset.assetId}});
 await bucket.put(prayerAsset.objectKey,bytes,{httpMetadata:{contentType:'audio/mp4'},customMetadata:{sha256:prayerAsset.sha256,'asset-id':prayerId}});
 await bucket.put(updates.objectKey,bytes,{httpMetadata:{contentType:'application/octet-stream'},customMetadata:{sha256:updates.sha256,'asset-id':'audiotp:windows:x86_64:1.0.1'}});
 const api=new MediaAPI('https://runtime.test',{fetcher:(url,init)=>mf.dispatchFetch(url,init)});
 t.after(()=>api.logout());await api.login(code);assert.deepEqual(await api.catalog(),client);
 const offline=await api.request('/v1/offline-manifest');assert.deepEqual(offline,{schemaVersion:1,revision:client.revision,tracks:client.tracks,assets:[{assetId:asset.assetId,bytes:bytes.length,sha256:asset.sha256,contentType:'audio/mp4'}]});
 assert.equal((await mf.dispatchFetch('https://runtime.test/v1/offline-manifest')).status,401);
 const releaseInfo=await mf.dispatchFetch('https://runtime.test/v1/release-info/windows-x86_64/1.0.0');assert.deepEqual(await releaseInfo.json(),{version:'1.0.1',currentVersion:'1.0.0'});
 assert.deepEqual(await api.request('/v1/quick-audio'),{schemaVersion:1,revision:quickAudio.revision,tracks:[prayer]});
 const prayerURL=await api.resolve(prayer);
 const prayerResponse=await mf.dispatchFetch(prayerURL,{headers:{Range:'bytes=1-4'}});assert.equal(prayerResponse.status,206);assert.deepEqual(Buffer.from(await prayerResponse.arrayBuffer()),bytes.subarray(1,5));
 assert.equal((await mf.dispatchFetch('https://runtime.test/v1/quick-audio')).status,401);
 const update=await api.request('/v1/updates/windows-x86_64/1.0.0');
 assert.deepEqual(update,{version:updates.version,pub_date:updates.pubDate,notes:updates.notes,url:'https://runtime.test/v1/update-files/1.0.1/installer',signature:updates.signature});
 const auth={Authorization:'Bearer '+api.token};
 assert.equal((await mf.dispatchFetch('https://runtime.test/v1/updates/windows-x86_64/1.0.1',{headers:auth})).status,204);
 assert.equal((await mf.dispatchFetch(update.url)).status,401);
 const installerHead=await mf.dispatchFetch(update.url,{method:'HEAD',headers:auth});assert.equal(installerHead.status,200);assert.equal(installerHead.headers.get('Content-Type'),'application/octet-stream');assert.equal(await installerHead.text(),'');
 const installer=await mf.dispatchFetch(update.url,{headers:auth});assert.equal(installer.status,200);assert.deepEqual(Buffer.from(await installer.arrayBuffer()),bytes);
 const partialInstaller=await mf.dispatchFetch(update.url,{headers:{...auth,Range:'bytes=2-5'}});assert.equal(partialInstaller.status,206);assert.deepEqual(Buffer.from(await partialInstaller.arrayBuffer()),bytes.subarray(2,6));
 await bucket.put(updates.objectKey,bytes,{httpMetadata:{contentType:'application/octet-stream'},customMetadata:{sha256:'bad','asset-id':'audiotp:windows:x86_64:1.0.1'}});
 assert.equal((await mf.dispatchFetch(update.url,{headers:auth})).status,409);
 const url=await api.resolve(track);assert.equal(await api.resolve(track),url);
 for(const [range,start,end]of [['bytes=0-7',0,7],['bytes=16-',16,bytes.length-1],['bytes=-6',bytes.length-6,bytes.length-1],['bytes=0-99999',0,bytes.length-1]]){
  const r=await mf.dispatchFetch(url,{headers:{Range:range}});assert.equal(r.status,206);
  assert.equal(r.headers.get('Content-Range'),`bytes ${start}-${end}/${bytes.length}`);assert.equal(Number(r.headers.get('Content-Length')),end-start+1);
  assert.deepEqual(Buffer.from(await r.arrayBuffer()),bytes.subarray(start,end+1));
 }
 const full=await mf.dispatchFetch(url);assert.equal(full.status,200);const etag=full.headers.get('ETag');assert.deepEqual(Buffer.from(await full.arrayBuffer()),bytes);
 const head=await mf.dispatchFetch(url,{method:'HEAD',headers:{Range:'bytes=0-1'}});assert.equal(head.status,200);assert.equal(Number(head.headers.get('Content-Length')),bytes.length);assert.equal(await head.text(),'');
 assert.equal((await mf.dispatchFetch(url,{headers:{'If-None-Match':etag}})).status,304);
 const fallback=await mf.dispatchFetch(url,{headers:{Range:'bytes=0-1','If-Range':'"wrong"'}});assert.equal(fallback.status,200);await fallback.arrayBuffer();
 for(const range of ['bytes=999999-','bytes=1-2,4-5','bytes=-0'])assert.equal((await mf.dispatchFetch(url,{headers:{Range:range}})).status,416);
 assert.equal((await mf.dispatchFetch(url.split('?')[0])).status,401);
 const health=await mf.dispatchFetch('https://runtime.test/v1/health');assert.deepEqual(await health.json(),{status:'ready',storage:'not-probed'});
 // Mutation is ONLY in this disposable emulator, to prove mismatched metadata fails closed.
 await bucket.put(asset.objectKey,bytes,{httpMetadata:{contentType:'text/html'}});
 assert.equal((await mf.dispatchFetch(url)).status,409);
 await bucket.delete(asset.objectKey);assert.equal((await mf.dispatchFetch(url)).status,404);
 api.logout();await assert.rejects(()=>api.resolve(track));
});
