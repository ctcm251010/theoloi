import test from 'node:test';
import assert from 'node:assert/strict';
import {AppUpdates} from '../web/app-updates.mjs';
const release={version:'1.0.4',currentVersion:'1.0.3'};
test('startup public metadata never downloads and defer only suppresses automatic notices',async()=>{
 const calls=[];const updates=new AppUpdates(async cmd=>{calls.push(cmd);return release;});
 await updates.startup();assert.equal(updates.state.notification,true);assert.equal(updates.state.currentVersion,'1.0.3');
 assert.deepEqual(calls,['check_release_info']);updates.defer();assert.equal(updates.state.notification,false);
 await updates.startup();assert.equal(updates.state.notification,false);
 await updates.check('session',{automatic:true});assert.equal(updates.state.notification,false);
 await updates.check();assert.equal(updates.state.notification,true);
});
test('startup offline, malformed, latest and bounded timeout stay silent',async()=>{
 for(const result of [null,{version:'1.0.3',currentVersion:'1.0.3'},{version:'bad',currentVersion:'1.0.3'}]){
  const updates=new AppUpdates(async()=>result);await updates.startup();assert.equal(updates.state.status,'idle');assert.equal(updates.state.notification,false);
 }
 const offline=new AppUpdates(async()=>{throw Error('internal');});await offline.startup();assert.equal(offline.state.status,'idle');
 let finish;const updates=new AppUpdates(()=>new Promise(resolve=>finish=resolve),{timeoutMs:5});
 await updates.startup();assert.equal(updates.state.status,'idle');finish(release);await new Promise(resolve=>setTimeout(resolve,0));assert.equal(updates.state.status,'idle');
});
test('public notification cannot install without authentication and fresh signed check',async()=>{
 const calls=[];const updates=new AppUpdates(async cmd=>{calls.push(cmd);return cmd.includes('check')?release:null;});
 await updates.startup();await updates.install();assert.equal(updates.state.status,'available');assert.equal(updates.state.requiresAuth,true);
 await updates.install('session');assert.deepEqual(calls,['check_release_info','check_update','install_update']);
});
test('logout during signed recheck prevents install',async()=>{
 let finish;let installs=0;const updates=new AppUpdates(cmd=>cmd==='check_release_info'?Promise.resolve(release):cmd==='check_update'?new Promise(resolve=>finish=resolve):Promise.resolve(installs+=cmd==='install_update'?1:0));
 await updates.startup();const installing=updates.install('session');updates.clear();finish(release);await installing;assert.equal(installs,0);assert.equal(updates.state.status,'idle');
});
test('defer during the authenticated pre-install check cancels the explicit install attempt',async()=>{
 let finish;const calls=[];const updates=new AppUpdates(cmd=>{calls.push(cmd);return cmd==='check_update'?new Promise(resolve=>finish=resolve):Promise.resolve(cmd==='check_release_info'?release:null);});
 await updates.startup();const installing=updates.install('session');updates.defer();finish(release);await installing;
 assert.equal(calls.includes('install_update'),false);assert.equal(calls.includes('clear_update'),true);assert.equal(updates.state.notification,false);assert.equal(updates.state.status,'available');
});
test('progress is scoped to installation and disposed after failure',async()=>{
 let progress,disposed=0;const updates=new AppUpdates(async cmd=>{if(cmd.includes('check'))return release;if(cmd==='install_update'){progress({payload:{phase:'downloading',downloaded:5,total:10,percent:50}});assert.equal(updates.state.progress.percent,50);throw Error('signature failure');}}, {listen:async(name,callback)=>{assert.equal(name,'app-update-progress');progress=callback;return()=>disposed++;}});
 await updates.startup();await updates.install('session');assert.equal(updates.state.status,'error');assert.equal(disposed,1);progress({payload:{phase:'installing',downloaded:10,total:10,percent:100}});assert.equal(updates.state.status,'error');
});
