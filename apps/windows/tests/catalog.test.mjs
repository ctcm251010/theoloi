import test from 'node:test';
import assert from 'node:assert/strict';
import { filterTracks, validateCatalog, canPlayQuick } from '../web/catalog.mjs';
const tracks = [
  {id:'g1',logicalId:'main-1',mode:'guide',section:'main',number:1,title:'Đức Chúa Trời',category:'Ngợi khen',durationSeconds:100},
  {id:'ga1',logicalId:'appendix-1',mode:'guide',section:'appendix',number:1,title:'Tình yêu',category:'Tạ ơn',durationSeconds:90},
  {id:'i1',logicalId:'main-1',mode:'instrumental',section:'main',number:1,title:'Đức Chúa Trời',category:'Ngợi khen',durationSeconds:110},
  {id:'s7',logicalId:'silent-7',mode:'silent',section:null,number:7,title:'Bình an',category:'Suy ngẫm',durationSeconds:120},
  {id:'g3',logicalId:'main-3',mode:'guide',section:'main',number:3,title:'Niềm vui',category:'Tạ ơn',durationSeconds:90},
];
test('Vietnamese search ignores accents and handles đ',()=>assert.deepEqual(filterTracks(tracks,{mode:'guide',query:'duc chua'}).map(x=>x.id),['g1']));
test('search normalizes repeated whitespace and decomposed Unicode',()=>assert.deepEqual(filterTracks(tracks,{mode:'guide',query:'  Đức   Chúa  '}).map(x=>x.id),['g1']));
test('number search preserves main and appendix namespaces',()=>{
  assert.deepEqual(filterTracks(tracks,{mode:'guide',query:'1'}).map(x=>x.id),['g1','ga1']);
  assert.deepEqual(filterTracks(tracks,{mode:'guide',query:'pl 1'}).map(x=>x.id),['ga1']);
  assert.deepEqual(filterTracks(tracks,{mode:'guide',query:'2'}),[]);
});
test('filters compose and silent numbers never join hymn numbers',()=>{
  assert.deepEqual(filterTracks(tracks,{mode:'guide',category:'Tạ ơn',section:'main'}).map(x=>x.id),['g3']);
  assert.deepEqual(filterTracks(tracks,{mode:'silent',query:'7'}).map(x=>x.id),['s7']);
});
test('catalog rejects duplicate identity and invalid durations',()=>{
  assert.equal(validateCatalog({schemaVersion:1,revision:'r',tracks}).length,5);
  assert.throws(()=>validateCatalog({schemaVersion:1,revision:'r',tracks:[tracks[0],tracks[0]]}));
  assert.throws(()=>validateCatalog({schemaVersion:1,revision:'r',tracks:[{...tracks[0],durationSeconds:Infinity}]}));
});
test('quick play fails closed independently of available flag',()=>{
 const approved={available:true,sourceStatus:'verified',rightsStatus:'approved',assetIds:['g1']};
 assert.equal(canPlayQuick(approved,tracks),true);
 for (const patch of [{sourceStatus:'candidate'},{rightsStatus:'unknown'},{assetIds:[]},{assetIds:['missing']},{available:false}]) assert.equal(canPlayQuick({...approved,...patch},tracks),false);
});
