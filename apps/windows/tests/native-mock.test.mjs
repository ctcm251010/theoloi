import test from 'node:test';
import assert from 'node:assert/strict';
import {createMockServer,fixtureCatalog,fixtureQuick,TEST_CODE} from '../native-mock.mjs';
import {MediaAPI} from '../web/api-client.mjs';

test('native mock serves only labelled self-authored fixtures with session, ticket and real WAV Range',async t=>{
 const server=await createMockServer({port:0});t.after(()=>{server.close();server.closeAllConnections();});
 const base=`http://127.0.0.1:${server.address().port}`;const api=new MediaAPI(base);t.after(()=>api.logout());
 assert.equal((await fetch(base+'/v1/catalog')).status,401);
 await assert.rejects(()=>api.login('wrong'));
 await api.login(TEST_CODE);assert.deepEqual(await api.catalog(),fixtureCatalog);
 assert.equal(fixtureCatalog.tracks.length,4);assert.ok(fixtureCatalog.tracks.every(x=>x.id.startsWith('test:') && x.title.startsWith('TEST')));
 assert.equal(fixtureQuick[0].assetIds[0],'test:silent:1');
 const url=await api.resolve(fixtureCatalog.tracks[0]);const r=await fetch(url,{headers:{Range:'bytes=0-11'}});
 assert.equal(r.status,206);assert.equal(r.headers.get('Content-Type'),'audio/wav');assert.equal(r.headers.get('Cache-Control'),'no-store');
 const bytes=Buffer.from(await r.arrayBuffer());assert.equal(bytes.toString('ascii',0,4),'RIFF');assert.equal(bytes.toString('ascii',8,12),'WAVE');
 assert.equal((await fetch(url,{method:'HEAD'})).status,200);
 assert.equal((await fetch(url,{headers:{Range:'bytes=0-1,2-3'}})).status,416);
 assert.equal((await fetch(url.replace(/ticket=.*/, 'ticket=bad.bad'))).status,401);
 assert.equal((await fetch(base+'/v1/catalog',{headers:{Origin:'https://untrusted.invalid'}})).status,403);
 assert.equal((await fetch(base+'/media/audio/anything.m4a')).status,404);
 assert.equal((await fetch(base+'/v1/media/'+encodeURIComponent('watv:vi:guide:1'))).status,401);
 await assert.rejects(()=>api.resolve({id:'watv:vi:guide:1'}));
});

test('mock rejects invalid bind ports before listening',async()=>{
 for(const port of [-1,65536,1.5])await assert.rejects(()=>createMockServer({port}));
});
