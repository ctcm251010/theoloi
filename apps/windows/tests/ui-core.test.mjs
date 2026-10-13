import test from 'node:test';
import {shouldPromptConnection} from '../web/ui-core.mjs';

test('first online launch exposes connection unless restored or already connecting',()=>{
 assert.equal(shouldPromptConnection({mode:'remote'}),true);
 assert.equal(shouldPromptConnection({mode:'remote',connected:true}),false);
 assert.equal(shouldPromptConnection({mode:'remote',pending:true}),false);
 for(const mode of ['local-library','test-fixtures','catalog-only',undefined])assert.equal(shouldPromptConnection({mode}),false);
});
import assert from 'node:assert/strict';
import { shortcutAction, libraryView, quickPresentation, QuickPanelState, quickPlaybackPlan, connectionPolicy, shouldBootstrapLocal } from '../web/ui-core.mjs';
test('real local library is pinned and auto-connects only from native or loopback frontend',()=>{
 const config={mode:'local-library',apiBase:'http://127.0.0.1:8872'};
 assert.deepEqual(connectionPolicy(config),{enabled:true,base:config.apiBase,locked:true,test:false});
 for(const origin of ['http://tauri.localhost','https://tauri.localhost','tauri://localhost','http://127.0.0.1:8873'])assert.equal(shouldBootstrapLocal(config,origin),true);
 for(const origin of ['https://evil.test','http://tauri.localhost.evil','http://localhost:8873'])assert.equal(shouldBootstrapLocal(config,origin),false);
 for(const apiBase of ['https://media.test','http://evil.test','http://127.0.0.1:8872/path','http://user@127.0.0.1:8872'])assert.equal(shouldBootstrapLocal({...config,apiBase},'http://tauri.localhost'),false);
 assert.equal(shouldBootstrapLocal({mode:'remote',apiBase:config.apiBase},'http://tauri.localhost'),false);
 assert.equal(shouldBootstrapLocal({mode:'local-files',apiBase:config.apiBase},config.apiBase),true);
 assert.equal(shouldBootstrapLocal({mode:'local-files',apiBase:config.apiBase},'http://tauri.localhost'),false);
});
test('catalog-only packaging disables connection, remote pins its origin, preview remains usable',()=>{
 assert.deepEqual(connectionPolicy({mode:'catalog-only'}),{enabled:false,base:'',locked:true,test:false});
 assert.deepEqual(connectionPolicy({mode:'remote',apiBase:'https://media.test'}),{enabled:true,base:'https://media.test',locked:true,test:false});
 assert.deepEqual(connectionPolicy({mode:'test-fixtures',apiBase:'http://127.0.0.1:8870'}),{enabled:true,base:'http://127.0.0.1:8870',locked:true,test:true});
 assert.deepEqual(connectionPolicy({mode:'local-files',apiBase:'http://127.0.0.1:8766'}),{enabled:true,base:'http://127.0.0.1:8766',locked:false,test:false});
 assert.deepEqual(connectionPolicy({}),{enabled:true,base:'',locked:false,test:false});
});
test('keyboard shortcuts never intercept forms, buttons or editable ancestors',()=>{
 for(const tag of ['INPUT','SELECT','TEXTAREA','BUTTON','A'])assert.equal(shortcutAction({key:' ',target:{closest:()=>({tagName:tag})}}),null);
 assert.equal(shortcutAction({key:' ',target:{closest:()=>null}}),'toggle');
 assert.equal(shortcutAction({key:'ArrowRight',target:{closest:()=>null}}),'forward');
 for(const key of ['n','N','MediaTrackNext'])assert.equal(shortcutAction({key,target:{closest:()=>null}}),'next');
 for(const key of ['p','P','MediaTrackPrevious'])assert.equal(shortcutAction({key,target:{closest:()=>null}}),'previous');
 assert.equal(shortcutAction({key:'n',target:{closest:()=>({tagName:'INPUT'})}}),null);
 assert.equal(shortcutAction({key:' ',ctrlKey:true,target:{closest:()=>null}}),null);
});
test('open dialog content never triggers background playback shortcuts',()=>{
 const target={closest:selector=>selector.includes('dialog')?{tagName:'DIALOG'}:null};
 for(const key of [' ','ArrowRight','n','m'])assert.equal(shortcutAction({key,target}),null);
 assert.equal(shortcutAction({key:' ',target:{closest:()=>null}}),'toggle');
});
test('favourite and history views preserve actual catalog identities and history order',()=>{
 const tracks=[{id:'a'},{id:'b'},{id:'c'}];const store={favourites:['b'],history:[{id:'c'},{id:'missing'},{id:'a'}]};
 assert.deepEqual(libraryView(tracks,'favourites',store).map(x=>x.id),['b']);
 assert.deepEqual(libraryView(tracks,'history',store).map(x=>x.id),['c','a']);
});
test('quick controls follow the shared player only for their active reviewed context',()=>{
 const tracks=[{id:'a'}],card={id:'q',available:true,sourceStatus:'verified',rightsStatus:'approved',assetIds:['a']};
 for(const [status,label] of [['loading','Đang tải…'],['playing','Tạm dừng'],['paused','Phát tiếp'],['error','Thử lại'],['ended','Phát lại']]){
  const state=quickPresentation(card,tracks,{activeQuickId:'q',status,playbackEnabled:true});
  assert.equal(state.label,label);assert.equal(state.disabled,false);
 }
 assert.equal(quickPresentation(card,tracks,{activeQuickId:'other',status:'playing',playbackEnabled:true}).label,'Phát');
 assert.equal(quickPresentation({...card,rightsStatus:'unknown'},tracks,{activeQuickId:'q',status:'playing',playbackEnabled:true}).disabled,true);
 assert.equal(quickPresentation(card,tracks,{playbackEnabled:false}).disabled,true);
});
test('quick panel search takes priority over playback and clears without losing manual intent',()=>{
 const panel=new QuickPanelState();
 assert.deepEqual(panel.presentation(),{hidden:false,expanded:true});
 panel.setQuery('  cầu nguyện ');panel.observePlayback({status:'playing',position:80,duration:100});
 assert.equal(panel.presentation().hidden,true);
 panel.setManualCollapsed(true);panel.setQuery('');
 assert.deepEqual(panel.presentation(),{hidden:false,expanded:false});
 panel.observePlayback({status:'playing',position:90,duration:100});
 assert.equal(panel.presentation().expanded,false);
 panel.setManualCollapsed(false);panel.setQuery('   ');
 assert.deepEqual(panel.presentation(),{hidden:false,expanded:true});
});
test('half playback restores only an automatic collapse and latches across backward seeking',()=>{
 const panel=new QuickPanelState();panel.setAutoHidden(true);
 panel.observePlayback({status:'playing',position:49,duration:100});assert.equal(panel.presentation().expanded,false);
 for(const duration of [0,NaN,Infinity]){panel.observePlayback({status:'playing',position:80,duration});assert.equal(panel.presentation().expanded,false);}
 panel.observePlayback({status:'paused',position:80,duration:100});assert.equal(panel.presentation().expanded,false);
 panel.setQuery('1');panel.observePlayback({status:'playing',position:50,duration:100});assert.equal(panel.autoHidden,true);
 panel.setQuery('');panel.observePlayback({status:'playing',position:50,duration:100});assert.equal(panel.presentation().expanded,true);
 panel.observePlayback({status:'playing',position:10,duration:100});assert.equal(panel.presentation().expanded,true);
 const manual=new QuickPanelState({manualCollapsed:true});manual.setAutoHidden(true);manual.observePlayback({status:'playing',position:90,duration:100});
 assert.equal(manual.presentation().expanded,false);
});
test('silent quick play follows explicit source IDs independent of catalog or filtered view order',()=>{
 const tracks=[{id:'g',mode:'guide'},{id:'s2',mode:'silent'},{id:'s1',mode:'silent'}];
 const card={id:'q',behavior:'silent-library',firstAssetId:'s1',assetIds:['s1','s2'],available:true,sourceStatus:'verified',rightsStatus:'approved'};
 const plan=quickPlaybackPlan(card,tracks);
 assert.equal(plan.mode,'silent');assert.equal(plan.view,'all');assert.equal(plan.first.id,'s1');assert.deepEqual(plan.queue.map(t=>t.id),['s1','s2']);
 for(const patch of [{firstAssetId:'s2'},{assetIds:['s1','s1']},{assetIds:['s1']},{assetIds:['g','s1']},{rightsStatus:'unknown'},{behavior:'guess-by-title'}])assert.equal(quickPlaybackPlan({...card,...patch},tracks),null);
 assert.equal(quickPlaybackPlan({...card,available:false},tracks),null);
});
