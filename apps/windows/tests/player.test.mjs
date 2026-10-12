import test from 'node:test';
import assert from 'node:assert/strict';
import { Player } from '../web/player.mjs';
class Media extends EventTarget {
 src=''; currentSrc=''; currentTime=0; duration=12; volume=1; muted=false; paused=true;
 load(){this.currentSrc=this.src;this.currentTime=0;}
 pause(){this.paused=true;}
 async play(){this.paused=false;}
 emit(type){this.dispatchEvent(new Event(type));}
}
const a={id:'a',mode:'guide',title:'A'},b={id:'b',mode:'instrumental',title:'B'},c={id:'c',mode:'silent',title:'C'};
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject};};
const setup=(resolver=async t=>`./${t.id}.wav`,opts={})=>{const media=new Media();return {media,player:new Player(media,resolver,{timeoutMs:200,...opts})};};
test('selection captures its queue and supports pause resume seek volume mute',async()=>{
 const {player,media}=setup();const queue=[a,b];await player.select(a,queue);queue.splice(0);
 assert.equal(player.state.status,'playing');player.pause();assert.equal(media.paused,true);
 await player.resume();assert.equal(player.state.status,'playing');player.seek(99);assert.equal(media.currentTime,12);
 player.setVolume(0.3);player.toggleMute();assert.equal(media.volume,0.3);assert.equal(media.muted,true);
 await player.next();assert.equal(player.state.track.id,'b');await player.previous();assert.equal(player.state.track.id,'a');
});
test('stale source resolution cannot replace a newer selection',async()=>{
 const old=deferred();const {player,media}=setup(t=>t.id==='a'?old.promise:Promise.resolve('./b.wav'));
 const pending=player.select(a,[a,b]);await player.select(b,[a,b]);old.resolve('./a.wav');await pending;
 assert.equal(media.src,'./b.wav');assert.equal(player.state.track.id,'b');assert.equal(player.state.status,'playing');
});
test('pause during resolution never starts playback',async()=>{
 const d=deferred();const {player,media}=setup(()=>d.promise);const pending=player.select(a,[a]);player.pause();d.resolve('./a.wav');await pending;
 assert.equal(media.paused,true);assert.equal(player.state.status,'paused');
});
test('late play completion cannot undo pause',async()=>{
 const d=deferred();const {player,media}=setup();media.play=()=>{media.paused=false;return d.promise;};
 const pending=player.select(a,[a]);await Promise.resolve();await Promise.resolve();player.pause();d.resolve();await pending;
 assert.equal(media.paused,true);assert.equal(player.state.status,'paused');
});
test('late play completion after timeout cannot revive failed audio',async()=>{
 const d=deferred();const {player,media}=setup(undefined,{timeoutMs:5});
 media.play=()=>d.promise.then(()=>{media.paused=false;});
 await player.select(a,[a]);assert.equal(player.state.status,'error');
 d.resolve();await new Promise(r=>setImmediate(r));assert.equal(media.paused,true);assert.equal(player.state.status,'error');
});
test('media error during pending play remains an error after play resolves',async()=>{
 const d=deferred();const {player,media}=setup();media.play=()=>d.promise;
 const pending=player.select(a,[a]);await new Promise(r=>setImmediate(r));media.error={code:2};media.emit('error');d.resolve();await pending;
 assert.equal(player.state.status,'error');assert.equal(media.paused,true);
});
test('stop invalidates pending resolver and clears the media',async()=>{
 const d=deferred();const {player,media}=setup(()=>d.promise);const pending=player.select(a,[a]);player.stop();d.resolve('./a.wav');await pending;
 assert.equal(media.src,'');assert.equal(player.state.track,null);assert.equal(player.state.status,'idle');
});
test('resolver failure and timeout are recoverable by retry',async()=>{
 let broken=true;const {player}=setup(async()=>{if(broken)throw Error('denied');return './a.wav';});
 await player.select(a,[a]);assert.equal(player.state.status,'error');broken=false;await player.retry();assert.equal(player.state.status,'playing');
 const slow=setup(()=>new Promise(()=>{}),{timeoutMs:5});await slow.player.select(a,[a]);assert.equal(slow.player.state.status,'error');
});
test('media failure pauses audio and retry uses resolver again',async()=>{
 const {player,media}=setup();await player.select(a,[a]);media.error={code:2};media.emit('error');assert.equal(player.state.status,'error');assert.equal(media.paused,true);
 media.error=null;await player.retry();assert.equal(player.state.status,'playing');
});
test('non-finite media duration disables seeking',async()=>{
 const {player,media}=setup();await player.select(a,[a]);media.duration=Infinity;media.emit('durationchange');player.seek(9);
 assert.equal(player.state.duration,0);assert.equal(media.currentTime,0);
});
test('ended stops by default, continuous advances captured queue, repeat replays',async()=>{
 const {player,media}=setup();await player.select(a,[a,b]);media.emit('ended');assert.equal(player.state.status,'ended');
 player.setModes({continuous:true});await player.select(a,[a,b]);media.emit('ended');await new Promise(r=>setImmediate(r));assert.equal(player.state.track.id,'b');
 player.setModes({repeat:true});media.emit('ended');await new Promise(r=>setImmediate(r));assert.equal(player.state.track.id,'b');assert.equal(player.state.status,'playing');
});
test('shuffle chooses a different track and continuous never wraps by default',async()=>{
 const {player}=setup(undefined,{random:()=>0});player.setModes({shuffle:true});await player.select(b,[a,b,c]);await player.next();assert.equal(player.state.track.id,'a');
 player.setModes({shuffle:false});await player.select(c,[a,b,c]);await player.next();assert.equal(player.state.status,'ended');assert.equal(player.state.track.id,'c');
});
test('buffering recovers on playback, times out safely and pause cancels the timeout',async()=>{
 const {player,media}=setup(undefined,{timeoutMs:10});await player.select(a,[a]);media.emit('waiting');assert.equal(player.state.status,'buffering');media.emit('playing');assert.equal(player.state.status,'playing');
 media.emit('waiting');player.pause();await new Promise(r=>setTimeout(r,15));assert.equal(player.state.status,'paused');
 await player.resume();media.emit('stalled');await new Promise(r=>setTimeout(r,15));assert.equal(player.state.status,'error');assert.equal(media.paused,true);
});
test('expired media ticket refresh and retry retain seek position',async()=>{
 let refresh=false,calls=0;const {player,media}=setup(async()=>`./ticket-${++calls}`,{shouldRefresh:()=>refresh});
 await player.select(a,[a]);player.seek(7);player.pause();refresh=true;await player.resume();assert.equal(calls,2);assert.equal(media.currentTime,7);
 media.error={code:2};media.emit('error');media.error=null;await player.retry();assert.equal(calls,3);assert.equal(media.currentTime,7);
});
