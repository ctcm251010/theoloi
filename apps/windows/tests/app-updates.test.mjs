import test from 'node:test';
import assert from 'node:assert/strict';
import {AppUpdates} from '../web/app-updates.mjs';
test('updates only install following explicit click, check never downloads',async()=>{
 const calls=[];const updates=new AppUpdates(async(cmd,args)=>{calls.push([cmd,args]);return cmd==='check_update'?{version:'1.0.2',currentVersion:'1.0.1'}:null;});
 await updates.check('session');assert.equal(updates.state.status,'available');assert.equal(calls.filter(x=>x[0]==='install_update').length,0);
 await updates.install();assert.equal(calls.filter(x=>x[0]==='install_update').length,1);assert.equal(updates.state.status,'installing');
});
test('logout cancels late notification and install is disallowed',async()=>{
 let finish;const updates=new AppUpdates(cmd=>cmd==='check_update'?new Promise(resolve=>finish=resolve):Promise.resolve());
 const pending=updates.check('session');updates.clear();finish({version:'1.0.2',currentVersion:'1.0.1'});await pending;
 assert.equal(updates.state.status,'idle');await updates.install();assert.equal(updates.state.status,'idle');
});
test('network errors sanitized, retry works and duplicate install prevented',async()=>{
 let fail=true,installs=0,finish;
 const updates=new AppUpdates(async cmd=>{if(cmd==='check_update'){if(fail)throw Error('secret internal URL');return {version:'1.0.2',currentVersion:'1.0.1'};}if(cmd==='install_update'){installs++;await new Promise(resolve=>finish=resolve);}});
 await updates.check('session');assert.equal(updates.state.status,'error');assert.ok(!updates.state.message.includes('secret'));
 fail=false;await updates.check('session');const one=updates.install();await updates.install();assert.equal(installs,1);finish();await one;
});
test('browser cannot check and disconnected sessions only request public metadata',async()=>{
 const browser=new AppUpdates();await browser.check('session');assert.equal(browser.available,false);
 const calls=[];const native=new AppUpdates(async cmd=>{calls.push(cmd);return null;});await native.check('');await native.install();assert.deepEqual(calls,['check_release_info']);
});
