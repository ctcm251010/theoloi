import test from 'node:test';
import assert from 'node:assert/strict';
import {validateQuickAudio,applyQuickAudio,trackLabel} from '../web/supplementary.mjs';
import {quickPlaybackPlan} from '../web/ui-core.mjs';
import {validateCatalog} from '../web/catalog.mjs';
import {readFile} from 'node:fs/promises';
test('connection field is labelled shared password without embedding its value',async()=>{
 const html=await readFile(new URL('../web/index.html',import.meta.url),'utf8');
 assert.match(html,/<label>Mật khẩu chung<input id="access-code" type="password"/);
 assert.ok(!/<input id="access-code"[^>]*\bvalue=/.test(html));
});
const id='watv:vi:prayer:our-wish';
const track={id,logicalId:id,mode:'prayer',section:null,number:null,title:'Cầu nguyện chúng con mong muốn',category:'Cầu nguyện',durationSeconds:69.427664};
const data=()=>({schemaVersion:1,revision:'sha256:'+'a'.repeat(64),tracks:[{...track}]});
test('unison quick card uses only the exact new asset and never substitutes our-wish',()=>{
 const unison={...track,id:'watv:vi:prayer:unison-prayer',logicalId:'watv:vi:prayer:unison-prayer',title:'Nhạc không lời cầu nguyện thống thanh',durationSeconds:311.518912};
 const rows=validateQuickAudio({...data(),tracks:[track,unison]});
 const card={id:'quick:unison-prayer',title:unison.title,available:false,assetIds:[]};
 assert.equal(quickPlaybackPlan(applyQuickAudio([card],rows)[0],rows).first.id,unison.id);
 assert.equal(quickPlaybackPlan(applyQuickAudio([card],[track])[0],[track]),null);
});
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
