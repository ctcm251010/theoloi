import test from 'node:test';
import assert from 'node:assert/strict';
import {ConnectionGate} from '../web/api-client.mjs';

test('disconnect cancels pending client and prevents its late publication',async()=>{
 const gate=new ConnectionGate();let cancelled=0,finish;
 const client={logout(){cancelled++;}};const attempt=gate.begin(client);
 const result=new Promise(resolve=>{finish=resolve;}).then(()=>attempt.current()?'publish':'discard');
 gate.cancel();finish();assert.equal(await result,'discard');assert.equal(cancelled,1);
});
test('new connection owns UI updates; stale failure/finally cannot overwrite it',()=>{
 const gate=new ConnectionGate();let oldCancelled=0;const first=gate.begin({logout(){oldCancelled++;}});
 const second=gate.begin({logout(){}});assert.equal(first.current(),false);assert.equal(second.current(),true);assert.equal(oldCancelled,1);
 first.complete();gate.cancel();assert.equal(second.current(),false);
});
test('completed connection relinquishes only its pending client; generation stays valid until disconnect',()=>{
 const gate=new ConnectionGate();let calls=0;const current=gate.begin({logout(){calls++;}});current.complete();assert.equal(current.current(),true);gate.cancel();assert.equal(calls,0);assert.equal(current.current(),false);
});
