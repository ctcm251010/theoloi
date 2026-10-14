import test from 'node:test';
import assert from 'node:assert/strict';
import {createOfflineBrowserHarness} from './offline-browser-harness.mjs';
test('browser offline harness is loopback-only labelled TEST and exposes no production data',async t=>{
 const server=await createOfflineBrowserHarness({port:0});t.after(()=>{server.close();server.closeAllConnections();});const base=`http://127.0.0.1:${server.address().port}`;
 const page=await(await fetch(base+'/?scenario=full')).text();assert.match(page,/TEST ONLY/);assert.match(page,/TEST-bridge.mjs/);assert.doesNotMatch(page,/<script type="module" src="\.\/app.mjs"/);
 const catalog=await(await fetch(base+'/catalog.client.json')).json();assert.ok(catalog.tracks.length>0);assert.ok(catalog.tracks.every(t=>t.title.startsWith('TEST') && t.id.startsWith('test:')));
 assert.equal((await fetch(base+'/../PROJECT.md')).status,404);assert.equal((await fetch(base+'/.env')).status,404);assert.equal((await fetch(base+'/offline.mjs')).status,200);
 assert.equal((await fetch(base+'/v1/health')).status,200);
 const bridge=await(await fetch(base+'/TEST-bridge.mjs')).text();assert.match(bridge,/offline_start/);assert.match(bridge,/offline_remove/);assert.match(bridge,/scenario/);assert.doesNotMatch(bridge,/localStorage|indexedDB/);
 const config=await(await fetch(base+'/updates/connection.json')).json();assert.equal(config.apiBase,base);assert.equal(config.mode,'remote');
 const updateBridge=await(await fetch(base+'/updates/TEST-bridge.mjs')).text();assert.match(updateBridge,/check_release_info/);assert.match(updateBridge,/app-update-progress/);
 const app=await(await fetch(base+'/updates/app.mjs')).text();assert.ok(app.includes(`connection.base==='${base}'`),'isolated served copy points updater presentation to mock loopback, never production');
});
