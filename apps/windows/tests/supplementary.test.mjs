import test from 'node:test';
import assert from 'node:assert/strict';
import {validateQuickAudio,applyQuickAudio,trackLabel} from '../web/supplementary.mjs';
import {quickPlaybackPlan} from '../web/ui-core.mjs';
import {validateCatalog} from '../web/catalog.mjs';
const id='watv:vi:prayer:our-wish';
const track={id,logicalId:id,mode:'prayer',section:null,number:null,title:'Cầu nguyện chúng con mong muốn',category:'Cầu nguyện',durationSeconds:69.427664};
const data=()=>({schemaVersion:1,revision:'sha256:'+'a'.repeat(64),tracks:[{...track}]});
test('prayer belongs only to supplementary pool and plays exact asset through quick plan',()=>{
 const extra=validateQuickAudio(data());
 assert.throws(()=>validateCatalog(data()));
 const cards=applyQuickAudio([{id:'quick:our-wish-meditation',title:track.title,available:false,assetIds:[]}],extra);
 const plan=quickPlaybackPlan(cards[0],extra);
 assert.equal(plan.first.id,id);assert.equal(plan.mode,null);assert.equal(plan.queue.length,1);
 assert.equal(trackLabel(track),track.title);
});
test('no source or other prayer never enables our-wish or collective card',()=>{
 const cards=[{id:'quick:our-wish-meditation',available:false,assetIds:[]},{id:'quick:unison-prayer',available:false,assetIds:[]}];
 assert.equal(applyQuickAudio(cards,[])[0].available,false);
 assert.equal(applyQuickAudio(cards,[track])[1].available,false);
});
test('supplementary validation fails closed on duplicates, private fields, wrong numbering and namespace',()=>{
 for(const mutate of [x=>x.tracks.push({...track}),x=>x.tracks[0].objectKey='private',x=>x.tracks[0].number=1,x=>x.tracks[0].id='watv:vi:newsong:guide:1',x=>x.tracks[0].mode='silent',x=>x.tracks[0].durationSeconds=NaN]){
  const value=data();mutate(value);assert.throws(()=>validateQuickAudio(value));
 }
});
