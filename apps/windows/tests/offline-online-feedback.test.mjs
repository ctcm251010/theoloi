import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

// Execute the actual DOM handler and notice renderer, not a duplicate policy.
const source=await readFile(new URL('../web/app.mjs',import.meta.url),'utf8');
function ui(reachable){
 const notice={textContent:''},banner={hidden:true,querySelector:()=>notice};
 const button={disabled:false,textContent:'Nghe online'};
 const nodes={'offline-toggle':button,'demo-notice':banner,'connection-open':{},disconnect:{},'demo-mode':{querySelector:()=>({})}};
 const context={onlineSwitchMessage:'',onlineSwitchPending:false,api:{token:'TEST'},offline:{offline:true,completed:['TEST-a'],has:()=>true,setOffline(value){this.offline=value;}},connection:{enabled:true,test:false},networkUnavailable:true,playbackEnabled:true,player:{state:{}},$ :id=>nodes[id],renderUpdates(){},canRemember:()=>false,announce(){},renderQuick(){},renderCategories(){},renderRows(){},restoreAccess(){throw Error('must not log in during network failure');}};
 context.checkReachability=reachable;context.renderOffline=()=>{};
 context.enterOffline=()=>{context.networkUnavailable=true;context.offline.setOffline(true);context.renderConnection();};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('function renderConnection(){'),source.indexOf('function connectionLost(')),context);
 const start=source.indexOf("$('offline-toggle').addEventListener('click',")+"$('offline-toggle').addEventListener('click',".length;
 const end=source.indexOf('\nfunction requireDownloadSession()',start);
 const click=vm.runInContext('('+source.slice(start,end).trim().slice(0,-2)+')',context);
 return {context,notice,banner,button,click};
}
test('failed online switch shows visible network guidance while keeping downloaded playback available',async()=>{
 const view=ui(async()=>false);await view.click();
 assert.equal(view.context.offline.offline,true);
 assert.equal(view.context.playbackEnabled,true);
 assert.equal(view.banner.hidden,false,'failure must be visible, not only announced to screen readers');
 assert.match(view.notice.textContent,/Internet/);
 assert.match(view.notice.textContent,/đã tải/);
 assert.equal(view.button.disabled,false);
 view.context.renderConnection();assert.equal(view.banner.hidden,false,'a later render must preserve feedback');
});
test('pending online switch responds immediately and a successful retry clears failure feedback',async()=>{
 let finish;let calls=0;
 const view=ui(()=>{calls++;return calls===1?Promise.resolve(false):new Promise(resolve=>finish=resolve);});
 await view.click();const pending=view.click();
 assert.equal(view.button.disabled,true);
 assert.equal(view.button.textContent,'Đang kết nối…');
 finish(true);await pending;
 assert.equal(view.context.offline.offline,false);
 assert.equal(view.context.networkUnavailable,false);
 assert.equal(view.context.onlineSwitchMessage,'');
 assert.equal(view.banner.hidden,true);
 assert.equal(view.button.disabled,false);
});
test('successful Settings reconnection also clears the prior failure without an OS online event',async()=>{
 const view=ui(async()=>false);await view.click();
 const ctx=view.context,nodes={'connect-button':{},'connection-settings':{},'access-code':{}};
 const oldLookup=ctx.$;ctx.$=id=>nodes[id] || oldLookup(id);
 Object.assign(ctx,{updates:{clear(){},async check(){}},connections:{begin:()=>({current:()=>true,complete(){}})},setText(){},validateCatalog:catalog=>catalog.tracks,MediaAPI:class {logout(){} async login(){} async catalog(){return {tracks:[],revision:'TEST'};} async quickAudio(){return null;}},api:null});
 ctx.offline.available=false;ctx.pendingInstall=false;ctx.isNetworkFailure=error=>{throw error;};
 const begin=source.indexOf('async function connectLibrary('),end=source.indexOf("$('connection-form').addEventListener",begin);
 vm.runInContext(source.slice(begin,end),ctx);
 await ctx.connectLibrary('http://127.0.0.1:8875','public-TEST');
 assert.equal(ctx.networkUnavailable,false);
 assert.equal(ctx.onlineSwitchMessage,'','a successful login must remove stale network advice');
});
