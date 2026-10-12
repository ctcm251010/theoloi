import test from 'node:test';
import assert from 'node:assert/strict';
import { LibraryStore } from '../web/storage.mjs';
const memory=()=>{const values=new Map();return {getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v)};};
test('favourites and bounded history store metadata identities only',()=>{
 const storage=memory(),s=new LibraryStore(storage);s.toggleFavourite('g1');s.record({id:'g1',title:'T',url:'secret'},'r');s.record({id:'g2'},'r');s.record({id:'g1'},'r');
 assert.deepEqual(new LibraryStore(storage).favourites,['g1']);assert.deepEqual(s.history.map(x=>x.id),['g1','g2']);assert.equal(JSON.stringify(s.history).includes('secret'),false);
 for(let i=0;i<110;i++)s.record({id:`x${i}`},'r');assert.equal(s.history.length,100);
});
test('malformed or unavailable storage never breaks browsing',()=>{
 const bad=new LibraryStore({getItem:()=>'{bad',setItem:()=>{throw Error('denied')}});bad.toggleFavourite('a');assert.deepEqual(bad.favourites,['a']);
 const injected=new LibraryStore({getItem:()=>JSON.stringify({favourites:['ok',{},null],history:[{id:'ok',revision:'r',playedAt:1,url:'secret'}]}),setItem(){}});
 assert.deepEqual(injected.favourites,['ok']);assert.equal(JSON.stringify(injected.history).includes('secret'),false);
});
test('old demo history is not presented as actual listening; favourites and theme are preserved',()=>{
 const storage=memory();storage.setItem('audiotp.library.v1',JSON.stringify({favourites:['g1'],theme:'light',history:[{id:'g1',revision:'r',playedAt:1}]}));
 const s=new LibraryStore(storage);assert.deepEqual(s.history,[]);assert.deepEqual(s.favourites,['g1']);assert.equal(s.theme,'light');s.record({id:'g2'},'r');assert.deepEqual(new LibraryStore(storage).history.map(x=>x.id),['g2']);
});
