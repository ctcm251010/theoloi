import test from 'node:test';
import assert from 'node:assert/strict';
import {OfflineLibrary,offlineSource,formatBytes,isNetworkFailure} from '../web/offline.mjs';

const track=(id,mode='guide')=>({id,logicalId:id,mode,section:'main',number:1,title:`TEST ${id}`,category:'TEST',durationSeconds:1});
const manifest={schemaVersion:1,revision:'TEST-1',tracks:[track('TEST-a'),track('TEST-b','silent')],assets:[{assetId:'TEST-a',bytes:10,sha256:'a'.repeat(64),contentType:'audio/wav'},{assetId:'TEST-b',bytes:20,sha256:'b'.repeat(64),contentType:'audio/wav'}]};
const status=(completed=[],job={status:'idle',total:0,completed:0,failed:0,bytes:0,totalBytes:0})=>({manifest,completed,items:[],job,freeBytes:100});

test('browser does not pretend native storage is available',async()=>{
 const offline=new OfflineLibrary();await offline.refresh();assert.equal(offline.available,false);assert.equal(offline.has('TEST-a'),false);
 await assert.rejects(offline.start(['TEST-a'],{}),/Windows/);
});
test('verified snapshot permits restart without any online credentials',async()=>{
 const calls=[];const offline=new OfflineLibrary(async(command)=>{calls.push(command);return status(['TEST-a','TEST-b']);});
 await offline.initialize({online:true});assert.equal(offline.offline,true);assert.equal(offline.complete,true);assert.equal(offline.tracks.length,2);assert.deepEqual(calls,['offline_status']);
 assert.equal(offline.source('TEST-a'),'http://offline.localhost/TEST-a');
});
test('partial libraries default online, lost network filters every supplied queue',async()=>{
 const offline=new OfflineLibrary(async()=>status(['TEST-a']));await offline.initialize({online:true});assert.equal(offline.offline,false);
 offline.setOffline(true);assert.deepEqual(offline.filter(manifest.tracks).map(t=>t.id),['TEST-a']);
 offline.setOffline(false);assert.equal(offline.filter(manifest.tracks).length,2);
 await offline.initialize({online:false});assert.equal(offline.offline,true);
});
test('background startup verification selects offline after the last current file validates',async()=>{
 let snapshot=status([],{status:'verifying'});const offline=new OfflineLibrary(async()=>snapshot);
 await offline.initialize({online:true});assert.equal(offline.busy,true);assert.equal(offline.offline,false);
 snapshot=status(['TEST-a','TEST-b']);await offline.refresh();assert.equal(offline.offline,true);
 snapshot=status([],{status:'initializing'});await offline.initialize({online:true});assert.equal(offline.busy,true);
 offline.setOffline(false);snapshot=status(['TEST-a','TEST-b']);await offline.refresh();assert.equal(offline.offline,false,'manual choice wins over late verification');
});
test('download plans skip verified files and calculate current group/all bytes',async()=>{
 const calls=[];const offline=new OfflineLibrary(async(command,args)=>{calls.push([command,args]);return status(['TEST-a']);});await offline.refresh();
 assert.deepEqual(offline.plan(manifest.tracks),{ids:['TEST-b'],count:1,bytes:20});assert.equal(offline.plan(manifest.tracks.filter(t=>t.mode==='guide')).count,0);
 await offline.start(['TEST-a','TEST-b','TEST-b'],{base:'https://test.invalid',token:'TEST'});
 assert.deepEqual(calls.at(-1),['offline_start',{base:'https://test.invalid',token:'TEST',ids:['TEST-b']}]);
});
test('pause resume cancel retry and local deletion use only scoped native commands',async()=>{
 const calls=[];let saved=['TEST-a','TEST-b'];const offline=new OfflineLibrary(async(command,args)=>{calls.push([command,args]);if(command==='offline_remove')saved=saved.filter(id=>!args.ids.includes(id));return status(saved);});await offline.refresh();
 for(const action of ['pause','resume','cancel','retry'])await offline.control(action,{base:'https://test.invalid',token:'TEST'});
 await offline.remove(['TEST-a']);assert.equal(offline.complete,false);assert.equal(offline.plan(manifest.tracks).count,1);assert.equal(offline.has('TEST-b'),true);
 await offline.remove(['TEST-b']);assert.equal(offline.completed.length,0);assert.equal(calls.filter(([c])=>c==='offline_control').length,4);
 await assert.rejects(offline.remove(['unknown']),/danh mục/);
});
test('manifest revision and corrupt file status never keep a stale checkmark',async()=>{
 let snapshot=status(['TEST-a','TEST-b']);const offline=new OfflineLibrary(async()=>snapshot);await offline.refresh();assert.equal(offline.complete,true);
 snapshot={...status(['TEST-a']),items:[{assetId:'TEST-b',status:'error',bytes:0,error:'SHA-256 mismatch'}]};await offline.refresh();
 assert.equal(offline.item('TEST-b').status,'error');assert.equal(offline.source('TEST-b'),null);assert.equal(offline.complete,false);
 snapshot={...status(['TEST-a','TEST-b','unknown']),manifest:{...manifest,revision:'TEST-2',tracks:[track('TEST-a'),track('TEST-c')],assets:[manifest.assets[0],{...manifest.assets[1],assetId:'TEST-c'}]}};await offline.refresh();
 assert.equal(offline.has('TEST-b'),false);assert.equal(offline.complete,false);assert.equal(offline.plan(offline.tracks).ids[0],'TEST-c');
});
test('invalid native snapshots are rejected without replacing the last verified snapshot',async()=>{
 let snapshot=status(['TEST-a']);const offline=new OfflineLibrary(async()=>snapshot);await offline.refresh();
 snapshot={...status(),manifest:{...manifest,assets:[manifest.assets[0],manifest.assets[0]]}};await assert.rejects(offline.refresh(),/offline/);assert.equal(offline.has('TEST-a'),true);
 offline.setCatalog({...manifest,revision:'TEST-new'});await assert.rejects(offline.sync({token:'TEST'}),/offline/);assert.equal(offline.stale,true);
});
test('source encoding and network classification stay narrow',()=>{
 assert.equal(offlineSource('TEST:a/b'),'http://offline.localhost/TEST%3Aa%2Fb');assert.equal(formatBytes(1024),'1 KB');
 assert.equal(isNetworkFailure(Object.assign(new Error('timeout'),{network:true})),true);assert.equal(isNetworkFailure(Object.assign(new Error('auth'),{status:401})),false);
 assert.equal(isNetworkFailure(new TypeError('fetch')),true);assert.equal(isNetworkFailure(new Error('bad catalog')),false);
});
test('online playback resolves verified local files without a ticket and falls back once on transport failure',async()=>{
 const offline=new OfflineLibrary(async()=>status(['TEST-a']));await offline.initialize({online:true});let requests=0,fallbacks=0;
 const resolve=async()=>{requests++;return 'https://test.invalid/TEST-media';};
 assert.equal(await offline.resolve(track('TEST-a'),resolve),'http://offline.localhost/TEST-a');assert.equal(requests,0);
 assert.equal(await offline.resolve(track('TEST-b'),resolve),'https://test.invalid/TEST-media');assert.equal(requests,1);
 await assert.rejects(offline.resolve(track('TEST-b'),async()=>{throw Object.assign(Error('TEST timeout'),{network:true});},()=>fallbacks++),/timeout/);
 assert.equal(offline.offline,true);assert.equal(fallbacks,1);
 await assert.rejects(offline.resolve(track('TEST-b'),resolve),/chưa được tải/);assert.equal(requests,1);
 offline.setOffline(false);await assert.rejects(offline.resolve(track('TEST-b'),async()=>{throw Object.assign(Error('TEST auth'),{status:401});},()=>fallbacks++),/auth/);assert.equal(offline.offline,false);assert.equal(fallbacks,1);
});
test('late status reads cannot overwrite a completed mutation',async()=>{
 let reads=0,release;
 const offline=new OfflineLibrary(async command=>{
  if(command==='offline_start')return status(['TEST-a']);
  if(++reads===1)return status();
  return new Promise(resolve=>{release=()=>resolve(status());});
 });
 await offline.refresh();const refreshing=offline.refresh();await new Promise(resolve=>setImmediate(resolve));
 const starting=offline.start(['TEST-a'],{base:'https://test.invalid',token:'TEST'});await new Promise(resolve=>setImmediate(resolve));
 release();await Promise.all([refreshing,starting]);assert.equal(offline.has('TEST-a'),true);
});
test('new bundled revision invalidates full-library claim while old verified files remain playable',async()=>{
 const offline=new OfflineLibrary(async()=>status(['TEST-a','TEST-b']));await offline.initialize({online:true});assert.equal(offline.complete,true);
 offline.setCatalog({...manifest,revision:'TEST-2',tracks:[...manifest.tracks,track('TEST-c')]});
 assert.equal(offline.complete,false);assert.equal(offline.stale,true);assert.equal(offline.offline,false);assert.equal(offline.has('TEST-a'),true);
 await offline.sync({base:'https://test.invalid',token:'TEST'});assert.equal(offline.stale,false);assert.equal(offline.complete,true,'fresh server manifest is authoritative over a bundled older/different revision');
});
test('logout immediately cancels native session and discards late/queued authenticated work',async()=>{
 let resolveSync;const calls=[];
 const offline=new OfflineLibrary(async(command)=>{calls.push(command);if(command==='offline_sync')return new Promise(resolve=>{resolveSync=resolve;});return status(['TEST-a']);});
 await offline.refresh();const syncing=offline.sync({base:'https://test.invalid',token:'TEST'});await new Promise(resolve=>setImmediate(resolve));
 const starting=offline.start(['TEST-b'],{base:'https://test.invalid',token:'TEST'});const rejection=assert.rejects(starting,/hủy/);
 await offline.clearSession();assert.equal(calls.at(-1),'offline_control');assert.equal(offline.has('TEST-a'),true);
 resolveSync(status(['TEST-a','TEST-b']));await syncing;await rejection;assert.equal(calls.includes('offline_start'),false);assert.equal(offline.has('TEST-b'),false);
});
