import test from 'node:test';
import assert from 'node:assert/strict';
import {OfflineLibrary,offlineQuickPlan} from '../web/offline.mjs';
import {filterTracks} from '../web/catalog.mjs';
import {libraryView} from '../web/ui-core.mjs';
const tracks=['a','b','c'].map((id,i)=>({id:`TEST-${id}`,logicalId:id,mode:i===2?'silent':'guide',section:'main',number:i+1,title:`TEST bài ${id}`,category:'TEST',durationSeconds:1}));
const snapshot={manifest:{schemaVersion:1,revision:'TEST',tracks,assets:tracks.map(t=>({assetId:t.id,bytes:10,sha256:'a'.repeat(64),contentType:'audio/wav'}))},completed:['TEST-a','TEST-c'],items:[],job:{status:'idle'}};
test('offline search favourites history and playback queue intersect verified identities',async()=>{
 const offline=new OfflineLibrary(async()=>snapshot);await offline.initialize({online:false});const store={favourites:['TEST-a','TEST-b'],history:[{id:'TEST-b'},{id:'TEST-c'},{id:'TEST-a'}]};
 assert.deepEqual(libraryView(offline.filter(tracks),'favourites',store).map(t=>t.id),['TEST-a']);
 assert.deepEqual(libraryView(offline.filter(tracks),'history',store).map(t=>t.id),['TEST-c','TEST-a']);
 assert.deepEqual(filterTracks(offline.filter(tracks),{mode:'guide',query:'bài b'}),[]);
 assert.deepEqual(filterTracks(offline.filter(tracks),{mode:'silent'}).map(t=>t.id),['TEST-c']);
});
test('quick playlist keeps its reviewed identity and skips unavailable tracks only in offline mode',async()=>{
 const offline=new OfflineLibrary(async()=>snapshot);await offline.initialize({online:false});
 const card={id:'TEST-quick',behavior:'asset-playlist',available:true,sourceStatus:'verified',rightsStatus:'approved',assetIds:['TEST-b','TEST-c']};
 assert.deepEqual(offlineQuickPlan(card,tracks,offline).queue.map(t=>t.id),['TEST-c']);
 assert.equal(offlineQuickPlan({...card,assetIds:['TEST-b']},tracks,offline),null);
 offline.setOffline(false);assert.deepEqual(offlineQuickPlan(card,tracks,offline).queue.map(t=>t.id),['TEST-b','TEST-c']);
});
