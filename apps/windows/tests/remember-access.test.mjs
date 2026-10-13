import test from 'node:test';
import assert from 'node:assert/strict';
import {RememberedAccess} from '../web/remember-access.mjs';
import {MediaAPI} from '../web/api-client.mjs';
import {readFile} from 'node:fs/promises';

test('connection form accepts a four-character shared code without embedding one',async()=>{
 const html=await readFile(new URL('../web/index.html',import.meta.url),'utf8');
 const input=html.match(/<input\b[^>]*id="access-code"[^>]*>/)?.[0];
 assert.ok(input);assert.match(input,/minlength="4"/);assert.match(input,/maxlength="256"/);
 assert.doesNotMatch(input,/\bvalue=/);
});

test('login rejection carries only HTTP status for clearing revoked saved access',async()=>{
 const api=new MediaAPI('https://library.test',{fetcher:async()=>({ok:false,status:401})});
 await assert.rejects(api.login('synthetic-code'),error=>error.status===401 && !error.message.includes('synthetic-code'));
});

test('browser has no persistent credential fallback',async()=>{
 const store=new RememberedAccess();assert.equal(store.available,false);
 assert.equal(await store.read('https://library.test'),null);
 await assert.rejects(store.save('https://library.test','synthetic-code'),/Windows/);
});
test('native commands bind saved code to the exact API origin',async()=>{
 const calls=[];const store=new RememberedAccess(async(name,args)=>{calls.push([name,args]);return name==='read_access_code'?'synthetic-code':undefined;});
 await store.save('https://library.test','synthetic-code');
 assert.equal(await store.read('https://library.test'),'synthetic-code');await store.clear();
 assert.deepEqual(calls,[['save_access_code',{base:'https://library.test',code:'synthetic-code'}],['read_access_code',{base:'https://library.test'}],['forget_access_code',undefined]]);
});
test('logout waits for pending save then deletes it, invalidating a pending read',async()=>{
 let release;const calls=[];
 const store=new RememberedAccess(async name=>{calls.push(name);if(name==='save_access_code')await new Promise(r=>release=r);return 'synthetic-code';});
 const saved=store.save('https://library.test','synthetic-code');await new Promise(r=>setImmediate(r));
 const read=store.read('https://library.test');const clear=store.clear();release();
 await saved;assert.equal(await read,null);await clear;
 assert.equal(calls.at(-1),'forget_access_code');
});
test('a failed storage operation does not poison later logout',async()=>{
 let count=0;const store=new RememberedAccess(async()=>{if(!count++)throw Error('synthetic storage failure');});
 await assert.rejects(store.save('https://library.test','synthetic-code'));await store.clear();assert.equal(count,2);
});
