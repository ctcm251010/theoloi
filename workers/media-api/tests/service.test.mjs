import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createService,byteRange} from '../src/service.mjs';
const code='unit-test-access-code-not-a-real-secret';
const sha=data=>createHash('sha256').update(data).digest('hex');
const tracks=[{id:'guide:1',logicalId:'song:1',mode:'guide',durationSeconds:125},{id:'instrumental:1',logicalId:'song:1',mode:'instrumental',durationSeconds:126},{id:'silent:1',logicalId:'silent:1',mode:'silent',durationSeconds:57}].map(t=>({...t,section:t.mode==='silent'?null:'main',number:1,title:'Bài thử tự tạo',category:'Fixture'}));
const bytes=Buffer.from('0123456789abcdefghijklmnopqrstuvwxyz');
const allow=Object.fromEntries(tracks.map(t=>[t.id,{assetId:t.id,objectKey:'audio/v1/watv/vi/'+t.id,bytes:bytes.length,sha256:sha(bytes)}]));
function fixture(options={}){
 let clock=1000;const calls=[];
 const env={SERVING_ENABLED:'true',AUTH_EPOCH:'1',SIGNING_KEY:'unit-test-signing-key-01234567890123456789',GROUP_CODE_SHA256:sha(code),ALLOWED_ORIGINS:'http://tauri.localhost',LOGIN_LIMITER:{async limit(){return {success:true};}},REQUEST_LIMITER:{async limit(){return {success:true};}}};
 const meta=key=>{const update=options.updates;const a=Object.values({...allow,...options.quickAudio?.assets}).find(a=>a.objectKey===key) || (update?.objectKey===key?{...update,assetId:`audiotp:windows:x86_64:${update.version}`}:null);return a?{size:a.bytes,etag:'opaque',httpEtag:'"opaque"',customMetadata:{sha256:a.sha256,'asset-id':a.assetId},httpMetadata:{contentType:key.startsWith('updates/')?'application/octet-stream':'audio/mp4'}}:null;};
 env.MEDIA={async head(key){calls.push(['head',key]);return meta(key);},async get(key,options){calls.push(['get',key,options]);const m=meta(key);if(!m)return null;const r=options?.range;return {...m,...(r?{range:r}:{}),body:new Response(r?bytes.subarray(r.offset,r.offset+r.length):bytes).body};}};
 const service=createService({schemaVersion:1,revision:'reviewed-r1',tracks},allow,{...options,now:()=>clock});
 const request=(path,{method='GET',token,body,headers={}}={})=>service.fetch(new Request('https://media.example'+path,{method,headers:{...(token?{Authorization:'Bearer '+token}:{}),...(body?{'Content-Type':'application/json'}:{}),...headers},...(body?{body:JSON.stringify(body)}:{})}),env);
 const login=async()=>{const r=await request('/v1/auth/login',{method:'POST',body:{code}});assert.equal(r.status,200);return (await r.json()).token;};
 const ticket=async(id='guide:1')=>{const token=await login();const r=await request('/v1/play-tickets',{method:'POST',token,body:{assetId:id}});assert.equal(r.status,200);const data=await r.json();return data.path+'?ticket='+data.ticket;};
 return {env,calls,meta,request,login,ticket,advance:s=>{clock+=s;}};
}
test('unauthenticated requests fail closed before R2; serving and missing config are explicit',async()=>{
 const f=fixture();assert.equal((await f.request('/v1/catalog')).status,401);assert.equal(f.calls.length,0);
 f.env.SERVING_ENABLED='false';assert.equal((await f.request('/v1/auth/login',{method:'POST',body:{code}})).status,403);
 f.env.SERVING_ENABLED='true';delete f.env.SIGNING_KEY;assert.equal((await f.request('/v1/catalog')).status,503);
});
test('login validates code and JSON without reflecting body or secret',async()=>{
 const f=fixture();for(const supplied of ['wrong','wrong-long-access-code-0000000000000',null,{},'x'.repeat(257)]){
  const r=await f.request('/v1/auth/login',{method:'POST',body:{code:supplied}});assert.equal(r.status,401);assert.equal((await r.text()).includes(code),false);
 }
 assert.equal((await f.request('/v1/auth/login',{method:'POST',body:{code:'x'.repeat(5000)}})).status,400);
 assert.equal((await f.request('/v1/auth/login',{method:'POST',headers:{'Content-Type':'text/plain'}})).status,400);
 assert.equal(f.calls.length,0);
});

test('short shared codes authenticate exactly, preserve rate limiting and never read R2',async()=>{
 const f=fixture(),shortCode='4826';f.env.GROUP_CODE_SHA256=sha(shortCode);
 const accepted=await f.request('/v1/auth/login',{method:'POST',body:{code:shortCode}});
 assert.equal(accepted.status,200);const token=(await accepted.json()).token;
 assert.equal((await f.request('/v1/catalog',{token})).status,200);
 for(const supplied of ['', '482', '4827', ' 4826', '4826 ', null, 4826]){
  assert.equal((await f.request('/v1/auth/login',{method:'POST',body:{code:supplied}})).status,401);
 }
 for(const invalid of ['123', 'x'.repeat(257), 'ab\nc']){
  f.env.GROUP_CODE_SHA256=sha(invalid);
  assert.equal((await f.request('/v1/auth/login',{method:'POST',body:{code:invalid}})).status,401);
 }
 f.env.LOGIN_LIMITER.limit=async()=>({success:false});
 assert.equal((await f.request('/v1/auth/login',{method:'POST',body:{code:shortCode}})).status,429);
 assert.equal(f.calls.length,0);
});
test('catalog and logical song API contain metadata only and preserve variants',async()=>{
 const f=fixture(),token=await f.login();const r=await f.request('/v1/catalog',{token});assert.equal(r.status,200);
 const text=await r.text();assert.equal(text.includes('objectKey'),false);assert.equal(text.includes('SIGNING_KEY'),false);
 const song=await (await f.request('/v1/songs/song%3A1',{token})).json();assert.deepEqual(song.tracks.map(t=>t.mode),['guide','instrumental']);
 assert.equal((await f.request('/v1/songs/missing',{token})).status,404);
 assert.equal((await f.request('/v1/catalog',{method:'HEAD',token})).body,null);
});
test('full media and HEAD use manifest key and correct headers without arbitrary key access',async()=>{
 const f=fixture(),path=await f.ticket();const r=await f.request(path);assert.equal(r.status,200);assert.deepEqual(Buffer.from(await r.arrayBuffer()),bytes);
 assert.equal(r.headers.get('Content-Type'),'audio/mp4');assert.equal(r.headers.get('Content-Length'),String(bytes.length));assert.equal(r.headers.get('Cache-Control'),'private, no-store');
 assert.equal(r.headers.get('X-AudioTP-Asset-Id'),'guide:1');assert.equal(r.headers.get('Accept-Ranges'),'bytes');
 const gets=f.calls.filter(c=>c[0]==='get').length;const head=await f.request(path,{method:'HEAD'});assert.equal(head.status,200);assert.equal(head.body,null);assert.equal(f.calls.filter(c=>c[0]==='get').length,gets);
 assert.ok(f.calls.every(c=>c[1]===allow['guide:1'].objectKey));
 const token=await f.login();assert.equal((await f.request('/v1/play-tickets',{method:'POST',token,body:{assetId:'../../secret',objectKey:'arbitrary'}})).status,404);
 assert.equal((await f.request(path,{method:'DELETE'})).status,405);
});
test('single, suffix, open and clamped ranges give exact bytes and lengths',async()=>{
 const f=fixture(),path=await f.ticket();for(const [value,start,end]of [['bytes=2-5',2,5],['bytes=-4',bytes.length-4,bytes.length-1],['bytes=30-',30,bytes.length-1],['bytes=0-999',0,bytes.length-1]]){
  const r=await f.request(path,{headers:{Range:value}});assert.equal(r.status,206);assert.equal(r.headers.get('Content-Range'),`bytes ${start}-${end}/${bytes.length}`);assert.equal(r.headers.get('Content-Length'),String(end-start+1));assert.deepEqual(Buffer.from(await r.arrayBuffer()),bytes.subarray(start,end+1));
 }
 const r=await f.request(path,{method:'HEAD',headers:{Range:'bytes=0-1'}});assert.equal(r.status,200);assert.equal(r.body,null);assert.equal(r.headers.get('Content-Length'),String(bytes.length));
});
test('invalid, multi and unsatisfiable Range returns 416 without GET',async()=>{
 const f=fixture(),path=await f.ticket();for(const value of ['bytes=999-','bytes=4-2','bytes=-0','bytes=-','bytes=1-2,4-5','bytes=1.5-2','bytes=999999999999999999999-','items=0-1']){
  const r=await f.request(path,{headers:{Range:value}});assert.equal(r.status,416,value);assert.equal(r.headers.get('Content-Range'),`bytes */${bytes.length}`);
 }
 assert.equal(f.calls.filter(c=>c[0]==='get').length,0);assert.equal(byteRange('bytes=0-1',0),null);
});
test('If-Range and conditional ETag operate after authorization',async()=>{
 const f=fixture(),path=await f.ticket();let r=await f.request(path,{headers:{Range:'bytes=0-1','If-Range':'"changed"'}});assert.equal(r.status,200);await r.arrayBuffer();
 r=await f.request(path,{headers:{Range:'bytes=0-1','If-Range':'"opaque"'}});assert.equal(r.status,206);await r.arrayBuffer();
 r=await f.request(path,{headers:{'If-None-Match':'W/"opaque"'}});assert.equal(r.status,304);assert.equal(r.body,null);
 assert.equal((await f.request('/v1/media/guide%3A1',{headers:{'If-None-Match':'*'}})).status,401);
});
test('ticket scope, tamper, expiry, session expiry and epoch revocation are enforced',async()=>{
 const f=fixture(),path=await f.ticket();assert.equal((await f.request(path.replace('guide%3A1','instrumental%3A1'))).status,403);
 const u=new URL('https://media.example'+path);u.searchParams.set('ticket','corrupted.'+u.searchParams.get('ticket').split('.')[1]);assert.equal((await f.request(u.pathname+u.search)).status,401);
 const token=await f.login();f.advance(726);assert.equal((await f.request(path)).status,401);
 assert.equal((await f.request('/v1/catalog',{token})).status,200);f.advance(43200);assert.equal((await f.request('/v1/catalog',{token})).status,401);
 const fresh=await f.ticket();f.env.AUTH_EPOCH='2';assert.equal((await f.request(fresh)).status,401);
});
test('metadata mismatch, missing object, changed object and upstream failures are distinct',async()=>{
 for(const patch of [{size:1},{customMetadata:{}},{httpMetadata:{contentType:'text/html'}},{httpEtag:''}]){
  const f=fixture(),path=await f.ticket();f.env.MEDIA.head=async key=>({...f.meta(key),...patch});assert.equal((await f.request(path)).status,409);assert.equal(f.calls.length,0);
 }
 let f=fixture(),path=await f.ticket();f.env.MEDIA.head=async()=>null;assert.equal((await f.request(path)).status,404);
 f=fixture();path=await f.ticket();f.env.MEDIA.get=async key=>f.meta(key);assert.equal((await f.request(path)).status,409);
 f=fixture();path=await f.ticket();f.env.MEDIA.head=async()=>{throw Error('sensitive upstream error');};const r=await f.request(path);assert.equal(r.status,503);assert.equal((await r.text()).includes('sensitive'),false);
});
test('CORS allows exact origins, supports audio Range and never uses cookies',async()=>{
 const f=fixture();assert.equal((await f.request('/v1/catalog',{headers:{Origin:'https://evil.example'}})).status,403);
 const pre=await f.request('/v1/media/guide%3A1',{method:'OPTIONS',headers:{Origin:'http://tauri.localhost','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'range,if-range'}});assert.equal(pre.status,204);assert.equal(pre.headers.get('Access-Control-Allow-Origin'),'http://tauri.localhost');assert.equal(pre.headers.get('Access-Control-Allow-Credentials'),null);
 assert.equal((await f.request('/v1/catalog',{method:'OPTIONS',headers:{Origin:'http://tauri.localhost','Access-Control-Request-Method':'DELETE'}})).status,403);
});
test('rate limits fail closed for login and media without reading R2',async()=>{
 const f=fixture();f.env.LOGIN_LIMITER.limit=async()=>({success:false});assert.equal((await f.request('/v1/auth/login',{method:'POST',body:{code}})).status,429);
 f.env.LOGIN_LIMITER.limit=async()=>({success:true});const path=await f.ticket();f.env.REQUEST_LIMITER.limit=async()=>({success:false});const r=await f.request(path);assert.equal(r.status,429);assert.equal(r.headers.get('Retry-After'),'60');assert.equal(f.calls.length,0);
});
test('unsafe or inconsistent allowlist fails before serving',()=>{
 for(const bad of [{...allow,extra:allow['guide:1']},{...allow,'guide:1':{...allow['guide:1'],objectKey:'private/secret'}},{...allow,'guide:1':{...allow['guide:1'],sha256:'bad'}}])assert.throws(()=>createService({tracks},bad));
});

test('public health is readiness only, no bucket probe or catalog leak',async()=>{
 const f=fixture();const r=await f.request('/v1/health');assert.equal(r.status,200);
 assert.deepEqual(await r.json(),{status:'ready',storage:'not-probed'});assert.equal(f.calls.length,0);
 f.env.SERVING_ENABLED='false';assert.equal((await f.request('/v1/health')).status,503);
 assert.equal((await f.request('/v1/health',{method:'HEAD'})).body,null);
});
test('all responses disable shared caching including auth errors and preflight',async()=>{
 const f=fixture();for(const path of ['/v1/catalog',await f.ticket()]){
  const r=await f.request(path);assert.equal(r.headers.get('CDN-Cache-Control'),'no-store');assert.equal(r.headers.get('Cloudflare-CDN-Cache-Control'),'no-store');await r.arrayBuffer();
 }
 const token=await f.login();await f.request('/v1/catalog',{token});assert.equal(f.calls.filter(c=>c[0]==='get').length,1);
});
test('strict source-free contract rejects secret fields, malformed metadata and unsafe paths',()=>{
 const catalog={schemaVersion:1,revision:'r1',tracks};
 for(const patch of [{sourceUrl:'https://private.invalid'},{revision:''},{tracks:tracks.map(t=>({...t,durationSeconds:NaN}))},{tracks:tracks.map(t=>({...t,objectKey:'hidden'}))},{tracks:tracks.map(t=>({...t,section:'main',mode:'silent'}))}])assert.throws(()=>createService({...catalog,...patch},allow));
 for(const key of ['audio/v1/watv/vi/../secret','audio/v1/watv/vi/a?secret','audio/v1/watv/vi//a'])assert.throws(()=>createService(catalog,{...allow,'guide:1':{...allow['guide:1'],objectKey:key}}));
 assert.throws(()=>createService(catalog,{...allow,'guide:1':{...allow['guide:1'],localPath:'secret'}}));
});
test('R2 range metadata must be exact and discarded bodies are cancelled',async()=>{
 for(const range of [undefined,{offset:1,length:2},{offset:0,length:1}]){
  const f=fixture(),path=await f.ticket();let cancelled=false;
  f.env.MEDIA.get=async key=>({...f.meta(key),range,body:new ReadableStream({cancel(){cancelled=true;}})});
  assert.equal((await f.request(path,{headers:{Range:'bytes=0-1'}})).status,409);assert.equal(cancelled,true);
 }
});
test('request counts remain bounded and limiter/upstream faults do not expose detail',async()=>{
 const f=fixture(),path=await f.ticket();await f.request(path,{method:'HEAD'});assert.deepEqual(f.calls.map(c=>c[0]),['head']);
 await f.request(path,{headers:{'If-None-Match':'*'}});assert.deepEqual(f.calls.map(c=>c[0]),['head','head']);
 const r=await f.request(path,{headers:{Range:'bytes=0-1'}});await r.arrayBuffer();assert.deepEqual(f.calls.map(c=>c[0]),['head','head','head','get']);
 f.env.REQUEST_LIMITER.limit=async()=>{throw Error('private upstream detail');};
 const failed=await f.request(path);assert.equal(failed.status,503);assert.equal(failed.headers.get('Retry-After'),'5');assert.equal((await failed.text()).includes('private upstream detail'),false);assert.equal(f.calls.length,4);
});
test('streaming does not buffer media and consumer cancellation reaches the source',async()=>{
 const f=fixture(),path=await f.ticket();let cancelled=false;
 const body=new ReadableStream({pull(controller){controller.enqueue(bytes.subarray(0,2));},cancel(){cancelled=true;}},{highWaterMark:0});
 f.env.MEDIA.get=async key=>({...f.meta(key),body});
 const response=await f.request(path);assert.equal(response.body,body);const reader=response.body.getReader();assert.deepEqual((await reader.read()).value,bytes.subarray(0,2));await reader.cancel();assert.equal(cancelled,true);
});
test('upstream diagnostics contain only a fixed event and code',async t=>{
 const lines=[];t.mock.method(console,'warn',line=>lines.push(line));const f=fixture(),path=await f.ticket();
 f.env.MEDIA.get=async()=>{throw Error('PRIVATE exception, object key and token must never be logged');};
 const response=await f.request(path);assert.equal(response.status,503);
 assert.deepEqual(lines.map(s=>JSON.parse(s)),[{event:'media_api_failure',code:'upstream_unavailable'}]);
});

const prayerId='watv:vi:prayer:our-wish';
const prayerTrack={id:prayerId,logicalId:prayerId,mode:'prayer',section:null,number:null,title:'Cầu nguyện chúng con mong muốn',category:'Cầu nguyện',durationSeconds:69.427664};
const quickAudio={schemaVersion:1,revision:'sha256:'+sha('supplementary'),tracks:[prayerTrack],assets:{[prayerId]:{assetId:prayerId,objectKey:`audio/v1/watv/vi/prayer/our-wish/${sha(bytes)}.m4a`,bytes:bytes.length,sha256:sha(bytes)}}};
// Structurally valid synthetic minisign envelope; not an executable or trusted release.
const minisign=`untrusted comment: synthetic test signature\n${Buffer.concat([Buffer.from('Ed'),Buffer.alloc(72)]).toString('base64')}\ntrusted comment: synthetic\n${Buffer.alloc(64).toString('base64')}\n`;
const updates={version:'1.0.1',pubDate:'2026-10-13T00:00:00Z',notes:'Synthetic release',objectKey:'updates/windows-x86_64/1.0.1/AudioTP_1.0.1_x64-setup.exe',bytes:bytes.length,sha256:sha(bytes),signature:Buffer.from(minisign).toString('base64')};

test('quick audio is authenticated, metadata only and keeps original catalog unchanged',async()=>{
 const f=fixture({quickAudio}),token=await f.login();
 assert.equal((await f.request('/v1/quick-audio')).status,401);
 const response=await f.request('/v1/quick-audio',{token});assert.equal(response.status,200);
 assert.deepEqual(await response.json(),{schemaVersion:1,revision:quickAudio.revision,tracks:[prayerTrack]});
 assert.deepEqual(await (await f.request('/v1/catalog',{token})).json(),{schemaVersion:1,revision:'reviewed-r1',tracks});
 assert.equal((await f.request('/v1/quick-audio',{method:'HEAD',token})).body,null);
 assert.equal(f.calls.length,0);
 const empty=fixture(),emptyToken=await empty.login();const payload=await (await empty.request('/v1/quick-audio',{token:emptyToken})).json();
 assert.equal(payload.schemaVersion,1);assert.deepEqual(payload.tracks,[]);assert.match(payload.revision,/^sha256:[a-f0-9]{64}$/);
});

test('prayer tickets use supplementary revision and share strict media range and metadata behavior',async()=>{
 const f=fixture({quickAudio}),path=await f.ticket(prayerId);
 const claims=JSON.parse(Buffer.from(new URL('https://media.example'+path).searchParams.get('ticket').split('.')[0],'base64url'));
 assert.equal(claims.revision,quickAudio.revision);
 const oldPath=await f.ticket();const oldClaims=JSON.parse(Buffer.from(new URL('https://media.example'+oldPath).searchParams.get('ticket').split('.')[0],'base64url'));
 assert.equal(oldClaims.revision,'reviewed-r1');assert.equal((await f.request(oldPath,{method:'HEAD'})).status,200);
 let response=await f.request(path,{headers:{Range:'bytes=2-5'}});assert.equal(response.status,206);assert.deepEqual(Buffer.from(await response.arrayBuffer()),bytes.subarray(2,6));
 assert.equal(response.headers.get('X-AudioTP-Asset-Id'),prayerId);
 assert.equal((await f.request(path,{method:'HEAD'})).status,200);
 response=await f.request(path,{headers:{Range:'bytes=999-'}});assert.equal(response.status,416);
 f.env.MEDIA.head=async key=>({...f.meta(key),customMetadata:{sha256:'bad','asset-id':prayerId}});
 assert.equal((await f.request(path)).status,409);
});

test('quick audio validator rejects private fields, shape drift, unsafe keys and original-mode collisions',()=>{
 const catalog={schemaVersion:1,revision:'reviewed-r1',tracks};
 const invalid=[{...quickAudio,sourceUrl:'private'},{...quickAudio,revision:'r1'},{...quickAudio,tracks:[{...prayerTrack,number:1}]},{...quickAudio,tracks:[{...prayerTrack,mode:'guide'}]},{...quickAudio,tracks:[{...prayerTrack,id:'guide:1'}]},{...quickAudio,tracks:[{...prayerTrack,title:'other'}]},{...quickAudio,assets:{...quickAudio.assets,extra:allow['guide:1']}},{...quickAudio,assets:{[prayerId]:{...quickAudio.assets[prayerId],objectKey:'audio/v1/watv/vi/prayer/../secret'}}},{...quickAudio,assets:{[prayerId]:{...quickAudio.assets[prayerId],sha256:'bad'}}}];
 for(const quickAudio of invalid)assert.throws(()=>createService(catalog,allow,{quickAudio}));
 assert.throws(()=>createService({...catalog,tracks:[prayerTrack]},quickAudio.assets));
 assert.throws(()=>createService(catalog,allow,{quickAudio:null}));
});

test('signed update checks require session and only offer strictly newer stable versions',async()=>{
 const f=fixture({updates}),token=await f.login();
 assert.equal((await f.request('/v1/updates/windows-x86_64/1.0.0')).status,401);
 let r=await f.request('/v1/updates/windows-x86_64/1.0.0',{token});assert.equal(r.status,200);
 assert.deepEqual(await r.json(),{version:'1.0.1',pub_date:updates.pubDate,notes:updates.notes,url:'https://media.example/v1/update-files/1.0.1/installer',signature:updates.signature});
 r=await f.request('/v1/updates/windows-x86_64/1.0.0',{method:'HEAD',token});assert.equal(r.status,200);assert.equal(r.body,null);
 for(const version of ['1.0.1','1.0.2','1.1.0','2.0.0','10.0.0'])assert.equal((await f.request('/v1/updates/windows-x86_64/'+version,{token})).status,204);
 for(const version of ['01.0.0','1.0','1.0.0-beta','1.0.0+build','v1.0.0','9007199254740992.0.0','%31.0.0'])assert.equal((await f.request('/v1/updates/windows-x86_64/'+version,{token})).status,400,version);
 const empty=fixture(),emptyToken=await empty.login();assert.equal((await empty.request('/v1/updates/windows-x86_64/1.0.0',{token:emptyToken})).status,204);
 assert.equal(f.calls.length,0);
});

test('installer streams only exact private artifact under bearer auth with cheap HEAD and immutable get',async()=>{
 const f=fixture({updates}),token=await f.login(),path='/v1/update-files/1.0.1/installer';
 assert.equal((await f.request(path)).status,401);
 assert.equal((await f.request(path+'?token='+token)).status,401);
 const head=await f.request(path,{method:'HEAD',token});assert.equal(head.status,200);assert.equal(head.body,null);assert.equal(head.headers.get('Content-Type'),'application/octet-stream');assert.equal(head.headers.get('Content-Length'),String(bytes.length));
 assert.deepEqual(f.calls.map(c=>c[0]),['head']);
 const r=await f.request(path,{token});assert.equal(r.status,200);assert.deepEqual(Buffer.from(await r.arrayBuffer()),bytes);
 assert.deepEqual(f.calls.at(-1),['get',updates.objectKey,{onlyIf:{etagMatches:'opaque'}}]);
 assert.equal(r.headers.get('Location'),null);assert.equal(r.headers.get('sha256'),null);assert.equal(r.headers.get('X-AudioTP-Asset-Id'),null);
 assert.equal((await f.request(path,{token,headers:{'If-None-Match':'"opaque"'}})).status,304);
 for(const bad of ['/v1/update-files/1.0.0/installer','/v1/update-files/1.0.1/other','/v1/update-files/%31.0.1/installer','/v1/update-files/1.0.1/installer/extra','/v1/update-files/1.0.1%2F..%2Fsecret/installer'])assert.equal((await f.request(bad,{token})).status,404,bad);
});

test('installer metadata faults and replacement between HEAD and GET fail closed',async()=>{
 for(const patch of [{size:1},{customMetadata:{}},{httpMetadata:{contentType:'audio/mp4'}},{httpEtag:''}]){
  const f=fixture({updates}),token=await f.login();f.env.MEDIA.head=async key=>({...f.meta(key),...patch});assert.equal((await f.request('/v1/update-files/1.0.1/installer',{token})).status,409);assert.equal(f.calls.length,0);
 }
 const f=fixture({updates}),token=await f.login();let cancelled=false;
 f.env.MEDIA.get=async key=>({...f.meta(key),etag:'changed',body:new ReadableStream({cancel(){cancelled=true;}})});
 assert.equal((await f.request('/v1/update-files/1.0.1/installer',{token})).status,409);assert.equal(cancelled,true);
});

test('updates reject unsafe release metadata and unsigned or invalid minisign envelopes before serving',()=>{
 const catalog={schemaVersion:1,revision:'reviewed-r1',tracks};
 for(const patch of [{version:'1.0.1-beta'},{version:'01.0.1'},{version:'1.0.2'},{pubDate:'tomorrow'},{pubDate:'2026-02-30T00:00:00Z'},{notes:1},{objectKey:'https://evil.invalid/file.exe'},{objectKey:'updates/windows-x86_64/1.0.1/../secret'},{bytes:0},{sha256:'bad'},{signature:''},{signature:'AAAA'},{signature:Buffer.from('not a minisign signature').toString('base64')},{sourceUrl:'private'}])assert.throws(()=>createService(catalog,allow,{updates:{...updates,...patch}}));
 assert.throws(()=>createService(catalog,allow,{updates:null}));
});

test('prayer and update routes preserve serving gates, rate limiting and no-store behavior',async()=>{
 const f=fixture({quickAudio,updates}),token=await f.login();
 for(const path of ['/v1/quick-audio','/v1/updates/windows-x86_64/1.0.0','/v1/update-files/1.0.1/installer']){
  const r=await f.request(path,{token});assert.equal(r.headers.get('Cache-Control'),'private, no-store');await r.arrayBuffer();
  f.env.REQUEST_LIMITER.limit=async()=>({success:false});assert.equal((await f.request(path,{token})).status,429);
  f.env.REQUEST_LIMITER.limit=async()=>({success:true});f.env.SERVING_ENABLED='false';assert.equal((await f.request(path,{token})).status,403);f.env.SERVING_ENABLED='true';
 }
});
