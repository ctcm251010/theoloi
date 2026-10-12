import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {MediaAPI,validateAPIBase} from '../web/api-client.mjs';
const session={token:'synthetic-session',expiresAt:10000};
test('default browser fetch is invoked without the MediaAPI receiver',async()=>{
 const original=globalThis.fetch;
 try{globalThis.fetch=function(){assert.equal(this,undefined);return Promise.resolve(Response.json(session));};const api=new MediaAPI('https://api.test',{now:()=>100});await api.login('synthetic-user-access-code');assert.equal(api.token,session.token);}
 finally{globalThis.fetch=original;}
});
test('API base accepts HTTPS/loopback and rejects credentials and non-origin URLs',()=>{
 assert.equal(validateAPIBase('https://example.test/'),'https://example.test');assert.equal(validateAPIBase('http://127.0.0.1:8766'),'http://127.0.0.1:8766');
 for(const url of ['http://evil.test','https://secret@example.test','https://example.test/?token=x','https://example.test/#x','https://example.test/path','file:///a'])assert.throws(()=>validateAPIBase(url));
});
test('each asset receives its own scoped URL; media never falls back to mode tones',async()=>{
 const calls=[];const api=new MediaAPI('https://api.test',{now:()=>100,fetcher:async(url,init)=>{
  calls.push({url,init});if(url.endsWith('/auth/login'))return Response.json(session);
  const id=JSON.parse(init.body).assetId;return Response.json({assetId:id,path:'/v1/media/'+encodeURIComponent(id),ticket:'payload.signature',expiresAt:500});
 }});
 await api.login('synthetic-user-access-code');
 const first=await api.resolve({id:'guide:1',mode:'guide'}),second=await api.resolve({id:'guide:2',mode:'guide'});
 assert.notEqual(first,second);assert.ok(first.startsWith('https://api.test/v1/media/guide%3A1?ticket='));
 assert.equal(calls[1].init.headers.Authorization,'Bearer synthetic-session');assert.equal(calls[1].init.credentials,'omit');assert.equal(first.includes('Bearer'),false);
 api.logout();assert.equal(api.token,'');assert.equal(api.tickets.size,0);
 const source=await readFile(new URL('../web/app.mjs',import.meta.url),'utf8');assert.equal(source.includes('demoSource'),false);assert.equal(source.includes('fixtures/'),false);
});
test('wrong asset/path/expiry from server is rejected',async()=>{
 const valid={assetId:'a',path:'/v1/media/a',ticket:'p.s',expiresAt:500};
 for(const patch of [{assetId:'b'},{path:'https://evil.test/audio'},{path:'/v1/media/b'},{expiresAt:1},{ticket:'not-a-token'}]){
  const api=new MediaAPI('https://api.test',{now:()=>100,fetcher:async()=>Response.json({...valid,...patch})});api.adoptSession(session);await assert.rejects(()=>api.resolve({id:'a'}));
 }
});
test('401/expiry clear in-memory session; refresh threshold and local bootstrap are constrained',async()=>{
 let unauthorized=0;const api=new MediaAPI('https://api.test',{now:()=>100,fetcher:async()=>new Response(null,{status:401}),onUnauthorized:()=>unauthorized++});api.adoptSession(session);
 await assert.rejects(()=>api.catalog());assert.equal(api.token,'');assert.equal(unauthorized,1);await assert.rejects(()=>api.localSession());
 api.tickets.set('a',120);assert.equal(api.needsRefresh({id:'a'}),true);api.tickets.set('a',500);assert.equal(api.needsRefresh({id:'a'}),false);
});
test('network errors and bounded timeout are recoverable without returning fake URL',async()=>{
 let broken=true;const api=new MediaAPI('https://api.test',{now:()=>100,fetcher:async()=>{if(broken)throw Error('offline');return Response.json({schemaVersion:1,tracks:[]});}});api.adoptSession(session);await assert.rejects(()=>api.catalog());broken=false;assert.equal((await api.catalog()).schemaVersion,1);
 const slow=new MediaAPI('https://api.test',{now:()=>100,timeoutMs:5,fetcher:(_url,{signal})=>new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('Timeout','AbortError'))))});slow.adoptSession(session);await assert.rejects(()=>slow.catalog(),/quá lâu/);
});
test('only explicit loopback preview can re-bootstrap once after its local server restarts',async()=>{
 let logins=0,catalogs=0;const api=new MediaAPI('http://127.0.0.1:8766',{now:()=>100,fetcher:async url=>{
  if(url.endsWith('/local-session'))return Response.json({token:'local-'+(++logins),expiresAt:10000});
  catalogs++;return catalogs===1?new Response(null,{status:401}):Response.json({tracks:[]});
 }});
 await api.localSession();assert.deepEqual(await api.catalog(),{tracks:[]});assert.equal(logins,2);assert.equal(catalogs,2);
 const remote=new MediaAPI('https://library.test',{now:()=>100});await assert.rejects(()=>remote.localSession());assert.equal(remote.localPreview,false);
});
