import {MODES,validateCatalog,filterTracks,formatTime,displayNumber} from './catalog.mjs';
import {Player} from './player.mjs';
import {MediaAPI,ConnectionGate} from './api-client.mjs';
import {LibraryStore} from './storage.mjs';
import {RememberedAccess} from './remember-access.mjs';
import {validateQuickAudio,applyQuickAudio,trackLabel} from './supplementary.mjs';
import {AppUpdates} from './app-updates.mjs';
import {OfflineLibrary,offlineQuickPlan,formatBytes,isNetworkFailure} from './offline.mjs';
import {shortcutAction,libraryView,quickPresentation,QuickPanelState,connectionPolicy,shouldBootstrapLocal,shouldPromptConnection} from './ui-core.mjs';

const $=id=>document.getElementById(id);
const modeNames={guide:'Hướng dẫn',instrumental:'Nhạc đệm',silent:'Nhạc ngẫm nghĩ',prayer:'Cầu nguyện'};
let storage;try{storage=window.localStorage;}catch{}
const store=new LibraryStore(storage);
const quickPreference='audiotp.quick-collapsed.v1';
let manualCollapsed=false;try{manualCollapsed=storage?.getItem(quickPreference)==='true';}catch{}
const quickPanel=new QuickPanelState({manualCollapsed});
let tracks=[],quickTracks=[],quickCards=[],revision='',mode='guide',view='all',visible=[],playbackEnabled=false,loadGeneration=0;
const playbackTracks=()=>[...tracks,...quickTracks];
const rowNodes=new Map();
const quickNodes=new Map();
let activeQuickId='';
let lastRecorded='',lastTrack='',lastStatus='';
const media=$('audio');media.volume=.7;
let api=null,sourceKind='none';
let connection=connectionPolicy();
let localConnection=false;
const connections=new ConnectionGate();
const remembered=new RememberedAccess(window.__TAURI__?.core?.invoke);
const updates=new AppUpdates(window.__TAURI__?.core?.invoke,{listen:window.__TAURI__?.event?.listen});
const offline=new OfflineLibrary(window.__TAURI__?.core?.invoke);
let offlineInitialized=false,offlinePolling=false,offlinePollTimer=null,networkUnavailable=!navigator.onLine,pendingInstall=false,startupProbeDone=false,offlineRowsFingerprint='';
let confirmOperation=null;
let onlineSwitchMessage='',onlineSwitchPending=false;
let restoringAccess=false;
function canRemember(){return remembered.available && connection.enabled && connection.locked && !connection.test && !localConnection && connection.base.startsWith('https://');}
async function forgetAccess(){
 $('remember-access').checked=false;
 try{await remembered.clear();return true;}catch{announce('Chưa xóa được đăng nhập đã lưu. Hãy thử đăng xuất lại.');return false;}
}
async function restoreAccess(){
 if(!canRemember() || restoringAccess)return false;
 restoringAccess=true;const generation=connections.generation;
 try{
  const code=await remembered.read(connection.base);
  if(!code || generation!==connections.generation)return false;
  $('remember-access').checked=true;
  await connectLibrary(connection.base,code,{remember:true,restored:true});
  return !!api?.token;
 }catch{if(generation===connections.generation)setText('connection-status','Không mở được đăng nhập đã lưu. Hãy nhập lại mã hoặc đăng xuất để xóa.');return false;}
 finally{restoringAccess=false;}
}
const player=new Player(media,track=>offline.resolve(track,()=>{
 if(!playbackEnabled || !api)throw Error('Chưa kết nối nguồn nghe. Hãy kết nối thư viện trước.');
 return api.resolve(track);
},enterOffline),{shouldRefresh:track=>offline.has(track?.id)?false:api?.needsRefresh(track) ?? false});

function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('class','icon');svg.setAttribute('aria-hidden','true');const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href',`#i-${name}`);svg.append(use);return svg;}
function setText(id,text){if($(id).textContent!==text)$(id).textContent=text;}
function setIcon(node,name){node.replaceChildren(icon(name));}
function announce(text){setText('announcement',text);}
function openDialog(id){
 // The asynchronous startup connection prompt must not cover a release modal.
 if(id==='settings-dialog' && $('update-dialog').open)return;
 const dialog=$(id);if(!dialog.open)dialog.showModal();
}
for(const [button,dialog] of [['settings-toggle','settings-dialog'],['connection-open','settings-dialog'],['filters-toggle','filters-dialog'],['playback-toggle','playback-dialog']]){
 $(button).addEventListener('click',()=>openDialog(dialog));
}
for(const button of document.querySelectorAll('[data-close-dialog]'))button.addEventListener('click',()=>$(button.dataset.closeDialog).close());
for(const dialog of document.querySelectorAll('dialog'))dialog.addEventListener('keydown',event=>{
 if(event.key==='Escape'){event.preventDefault();event.stopPropagation();if(dialog.id==='update-dialog'){if(updates.state.status==='installing')return;updates.defer();}dialog.close();}
});
$('settings-dialog').addEventListener('close',()=>{if(!api?.token)pendingInstall=false;});
function applyTheme(){document.documentElement.dataset.theme=store.theme;$('theme-toggle').querySelector('span').textContent=store.theme==='dark'?'Giao diện sáng':'Giao diện tối';}
applyTheme();
$('theme-toggle').addEventListener('click',()=>{store.setTheme(store.theme==='dark'?'light':'dark');applyTheme();});

function statePanel(title,message,{retry=false,loading=false}={}){
 const panel=$('catalog-state');panel.replaceChildren();panel.hidden=false;$('track-table').hidden=true;
 if(loading)panel.append(element('span','loading-ring'));
 panel.append(element('h3','',title),element('p','',message));
 if(retry){const button=element('button','text-button','Tải lại danh mục');button.addEventListener('click',loadCatalog);panel.append(button);}
}

async function fetchJSON(path){const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),10000);try{const response=await fetch(path,{signal:controller.signal,cache:'no-cache'});if(!response.ok)throw Error(`Không tải được dữ liệu (${response.status}).`);return await response.json();}finally{clearTimeout(timer);}}
async function loadCatalog(){
 quickPanel.setAutoHidden(true);renderQuickVisibility();
 const token=++loadGeneration;statePanel('Đang mở thư viện','Chuẩn bị danh mục âm nhạc của bạn…',{loading:true});
 try {
  if(!offlineInitialized){try{await offline.initialize({online:navigator.onLine});}catch{announce('Chưa kiểm tra được file offline trên máy.');}offlineInitialized=true;}
  const [catalogResult,quickResult,connectionResult]=await Promise.allSettled([fetchJSON('./catalog.client.json'),fetchJSON('./quick-play.json'),fetchJSON('./connection.json')]);
  if(token!==loadGeneration)return;
  if(catalogResult.status==='rejected' && !offline.tracks.length)throw catalogResult.reason;
  if(catalogResult.status==='fulfilled')offline.setCatalog(catalogResult.value);
  const catalog=offline.stale && catalogResult.status==='fulfilled'?catalogResult.value:offline.state.manifest || catalogResult.value;
  tracks=validateCatalog(catalog);revision=catalog.revision;
  playbackEnabled=offline.offline && offline.completed.length>0;
  quickCards=quickResult.status==='fulfilled' && Array.isArray(quickResult.value)?quickResult.value:[];
  renderQuick();renderCategories();renderRows();
  if(connectionResult.status==='fulfilled'){
   const config=connectionResult.value;
   connection=connectionPolicy(config);
   localConnection=shouldBootstrapLocal(config,window.location.origin);
   // Native media must send Origin so the opt-in loopback server can enforce CORS.
   if(config.mode==='local-library')media.crossOrigin='anonymous';
   $('api-base').value=connection.base;$('api-base').readOnly=connection.locked;
   $('api-base').disabled=!connection.enabled;$('access-code').disabled=!connection.enabled;$('connect-button').disabled=!connection.enabled;
   $('access-code').required=!localConnection;
   $('access-code').closest('label').hidden=localConnection;
   $('remember-row').hidden=!canRemember();$('remember-note').hidden=!canRemember();
   if(!connection.enabled)setText('connection-status','Bản kiểm tra chỉ xem danh mục; chưa cấu hình máy chủ nghe.');
   if(connection.test)setText('connection-status','BẢN KIỂM THỬ — chỉ phát âm mẫu tự tạo, không phải thư viện WATV.');
   renderConnection();
   if(typeof config.version==='string')setText('build-version',`${config.version} · ${config.buildNumber || 'development'}`);
   if(updates.available && !localConnection && !connection.test && connection.enabled)void updates.startup();
   if(localConnection){await connectLibrary(config.apiBase,'',{local:true});}
   else if(config.apiBase){
    $('api-base').value=config.apiBase;
    if(!offline.offline && !offline.busy && !networkUnavailable)await restoreAccess();
    probeStartupConnection();
    if(!updates.state.notification && !offline.offline && !offline.busy && !offline.completed.length && !networkUnavailable && shouldPromptConnection({mode:config.mode,connected:!!api?.token,pending:!!connections.pending})){
     $('connection-settings').open=true;openDialog('settings-dialog');$('access-code').focus();
    }
   }
  }
 }catch(error){if(token!==loadGeneration)return;statePanel('Chưa thể mở thư viện',error.name==='AbortError'?'Dữ liệu phản hồi quá lâu. Hãy thử tải lại.':error.message,{retry:true});}
}

function renderConnection(){
 renderUpdates();
 const ready=!!api?.token || (offline.offline && offline.completed.length>0);
 $('demo-mode').querySelector('option[value="listen"]').disabled=!ready;
 $('demo-mode').value=playbackEnabled?'listen':'catalog';
 $('disconnect').hidden=!api?.token && !canRemember();
 const notice=$('demo-notice').querySelector('p');
 // Browser offline status does not prevent listening to files on loopback.
 notice.textContent=onlineSwitchMessage || (offline.offline?(offline.completed.length?'Đang nghe các bài đã tải trên máy.':'Chưa có bài offline. Kết nối Internet rồi tải bài để nghe khi mất mạng.'):!connection.enabled?'Bản kiểm tra chỉ xem danh mục; chưa cấu hình máy chủ nghe.':connection.test?'BẢN KIỂM THỬ — âm mẫu tự tạo, không phải nhạc WATV.':networkUnavailable?'Thư viện trực tuyến chưa kết nối được. Các bài đã tải vẫn nghe được.':ready?'Đang ở chế độ chỉ xem danh mục.':'Kết nối thư viện để nghe nhạc.');
 $('demo-notice').hidden=playbackEnabled && !connection.test && !onlineSwitchMessage;
 $('connection-open').hidden=offline.offline && offline.completed.length>0;
}
function connectionLost({manual=false}={}){
 updates.clear();quickTracks=[];
 void offline.clearSession().catch(()=>announce('Chưa xác nhận được việc dừng tác vụ tải. Hãy thử Hủy tải.'));
 connections.cancel();api?.logout();api=null;sourceKind='none';activeQuickId='';
 if(!offline.has(player.state.track?.id))player.stop();
 if(offline.completed.length)offline.setOffline(true);
 playbackEnabled=offline.offline && offline.completed.length>0;$('connect-button').disabled=false;renderConnection();renderQuick();renderRows();$('connection-settings').open=true;
 setText('connection-status','Phiên truy cập đã hết hạn. Hãy kết nối lại.');
 if(playbackEnabled){setText('connection-status',manual?'Đã đăng xuất. Các bài đã tải vẫn nghe offline được.':'Phiên trực tuyến đã hết hạn. Bạn vẫn nghe được các bài đã tải.');return;}
 if(!manual && canRemember() && $('remember-access').checked && !restoringAccess){void restoreAccess().then(ready=>{if(!ready)openDialog('settings-dialog');});}
 else openDialog('settings-dialog');
}
async function connectLibrary(base,code,{local=false,remember=false,restored=false}={}){
 if(!connection.enabled || (connection.locked && base!==connection.base)){setText('connection-status','Địa chỉ nghe không khớp cấu hình bản cài đặt.');return;}
 updates.clear();quickTracks=[];playbackEnabled=offline.completed.length>0;activeQuickId='';if(!offline.has(player.state.track?.id))player.stop();api?.logout();api=null;
 let next;
 const attempt=connections.begin({logout:()=>next?.logout()});
 $('connect-button').disabled=true;setText('connection-status','Đang kết nối…');
 try{
  next=new MediaAPI(base,{onUnauthorized:()=>{if(attempt.current())connectionLost();}});
  if(local)await next.localSession();else await next.login(code);
  const data=await next.catalog();const rows=validateCatalog(data);
  let supplemental=[];
  try{const quick=await next.quickAudio();if(quick)supplemental=validateQuickAudio(quick);}catch(error){if(error.status===401)throw error;}
  if(!attempt.current()){next.logout();return;}
  let storageWarning='';
  if(canRemember()){
   try{if(remember && !restored && $('remember-access').checked)await remembered.save(base,code);else if(!remember || !$('remember-access').checked)await remembered.clear();}
   catch{storageWarning=' Chưa cập nhật được đăng nhập đã lưu; hãy thử lại trước khi đóng app.';}
  }
  if(!attempt.current()){next.logout();return;}
  api=next;sourceKind=local?'local':'remote';tracks=rows;quickTracks=supplemental;revision=data.revision;playbackEnabled=true;networkUnavailable=false;onlineSwitchMessage='';
  attempt.complete();
  setText('connection-status',(local?'Đã kết nối thư viện trên máy.':'Đã kết nối thư viện trực tuyến.')+storageWarning);
  $('connection-settings').open=!!storageWarning;
  if(offline.available && !local){try{await offline.sync({base:api.base,token:api.token});if(attempt.current() && offline.tracks.length){tracks=offline.tracks;revision=offline.state.manifest.revision;}}catch(error){announce(`Chưa làm mới được danh mục tải về. ${error.message || error}`);}}
  if(!attempt.current())return;
  if(!local && !connection.test){if(pendingInstall){pendingInstall=false;await updates.check(api.token);void updates.install(api.token);}else void updates.check(api.token,{automatic:true});}
 }catch(error){if(attempt.current()){next?.logout();attempt.complete();if(restored && error.status===401)await forgetAccess();if(attempt.current()){if(isNetworkFailure(error)){enterOffline();setText('connection-status','Chưa kết nối được máy chủ. Bạn có thể nghe các bài đã tải.');}else{setText('connection-status',error.message);$('connection-settings').open=true;}}}}
 finally{code='';if(attempt.current()){$('access-code').value='';$('connect-button').disabled=false;renderConnection();renderQuick();renderCategories();renderRows();}}
}
$('connection-form').addEventListener('submit',event=>{event.preventDefault();const code=$('access-code').value;$('access-code').value='';void connectLibrary($('api-base').value.trim(),code,{local:localConnection,remember:canRemember() && $('remember-access').checked});});
$('remember-access').addEventListener('change',()=>{if(!$('remember-access').checked)void forgetAccess();});
$('disconnect').addEventListener('click',()=>{const forgotten=forgetAccess();connectionLost({manual:true});void forgotten.then(ok=>setText('connection-status',ok?'Đã đăng xuất và xóa đăng nhập đã lưu.':'Đã ngắt kết nối nhưng chưa xóa được đăng nhập đã lưu. Hãy thử lại.'));});
window.addEventListener('offline',()=>{if(sourceKind!=='local')enterOffline();});window.addEventListener('online',()=>{networkUnavailable=false;onlineSwitchMessage='';renderConnection();announce('Mạng đã trở lại. Có thể chọn Nghe online.');});
renderConnection();

function renderQuickVisibility(){
 quickPanel.setQuery($('search').value);quickPanel.observePlayback(player.state);
 const {hidden,expanded}=quickPanel.presentation();
 $('quick-section').hidden=hidden;
 $('quick-cards').hidden=quickPanel.manualCollapsed;
 $('quick-cards').classList.toggle('quick-auto-hidden',!expanded && !quickPanel.manualCollapsed);
 $('quick-cards').inert=!expanded;
 $('quick-toggle').setAttribute('aria-expanded',String(expanded));
 $('quick-toggle').setAttribute('aria-label',expanded?'Thu gọn Nghe nhanh':'Mở rộng Nghe nhanh');
 setText('quick-toggle',expanded?'Thu gọn':'Mở rộng');
}
$('quick-toggle').addEventListener('click',()=>{
 quickPanel.setManualCollapsed(quickPanel.presentation().expanded);
 try{storage?.setItem(quickPreference,String(quickPanel.manualCollapsed));}catch{}
 renderQuickVisibility();
});

function renderQuick(){
 quickPanel.setAutoHidden(false);
 const container=$('quick-cards');container.replaceChildren();
 quickNodes.clear();
 const cards=applyQuickAudio(quickCards.length?quickCards:[{id:'missing-1',title:'Nhạc ngẫm nghĩ'},{id:'quick:our-wish-meditation',title:'Cầu nguyện chúng con mong muốn'},{id:'missing-3',title:'Nhạc không lời cầu nguyện thống thanh'}],quickTracks);
 for(const card of cards){
  const node=element('article','quick-item');
  const eligible=!!offlineQuickPlan(card,playbackTracks(),offline);
  const button=element('button','quick-item-button');button.disabled=!eligible || !playbackEnabled;
  button.title=String(card.reason || 'Chưa có nguồn audio được xác minh.');
  quickNodes.set(card.id,{card,button,node});
  if(eligible)button.addEventListener('click',()=>{
   const plan=offlineQuickPlan(card,playbackTracks(),offline);if(!plan || !playbackEnabled)return;
   if(plan.view)selectView(plan.view);
   if(plan.mode){$('search').value='';$('category').value='';selectMode(plan.mode);}
    if(activeQuickId===card.id && player.state.track && player.state.status!=='ended'){void player.toggle();return;}
   activeQuickId=card.id;void player.select(plan.first,plan.queue);
  });
  node.append(button);container.append(node);
 }
 updateQuickStates();renderQuickVisibility();
}

function updateQuickStates(){
 for(const {card,button,node} of quickNodes.values()){
  const state=quickPresentation(card,playbackTracks(),{activeQuickId,status:player.state.status,playbackEnabled});
  const plan=offlineQuickPlan(card,playbackTracks(),offline);button.disabled=state.disabled || !plan;
  const label=offline.offline && !plan?'Chưa có bài offline':state.label;
  if(offline.offline && !plan)button.title='Chưa tải bài này để nghe offline.';
  const copy=element('span','quick-item-copy');copy.append(element('span','quick-item-title',card.title),element('small','',label));
  button.replaceChildren(icon(state.icon),copy);
  button.setAttribute('aria-label',`${card.title}: ${label}`);button.setAttribute('aria-busy',String(state.busy));
  node.classList.toggle('active-quick',state.active);node.classList.toggle('is-error',state.active && player.state.status==='error');
 }
}

function renderCategories(){
 const select=$('category'),selected=select.value;select.replaceChildren(new Option('Tất cả chủ đề',''));
 const categories=[...new Set(offline.filter(tracks).filter(t=>t.mode===mode).map(t=>t.category))].filter(Boolean).sort((a,b)=>a.localeCompare(b,'vi'));
 for(const category of categories)select.append(new Option(category,category));
 if(categories.includes(selected))select.value=selected;
 $('section').disabled=mode==='silent';
}
function renderRows(){
 renderQuickVisibility();
 const base=libraryView(offline.filter(tracks),view,store);
 visible=filterTracks(base,{mode,query:$('search').value,category:$('category').value,section:$('section').value});
 $('clear-filters').hidden=!($('search').value || $('category').value || $('section').value);
 $('filters-toggle').classList.toggle('has-filters',!!($('category').value || $('section').value));
 const list=$('track-list');list.replaceChildren();rowNodes.clear();
 if(!visible.length){statePanel(offline.offline?'Chưa có bài offline phù hợp':view==='favourites'?'Chưa có bài yêu thích':view==='history'?'Chưa có lần nghe nào':'Không tìm thấy bài phù hợp',offline.offline?'Chỉ hiển thị bài đã tải. Chọn Nghe online khi có mạng để tải thêm bài.':view==='all'?'Thử tên bài không dấu, số bài hoặc “PL 1” cho phụ lục.':'Hãy chọn một bài trong thư viện hoặc thay đổi bộ lọc.');return;}
 $('catalog-state').hidden=true;$('track-table').hidden=false;
 const fragment=document.createDocumentFragment();
 for(const track of visible){
  const row=element('div','track-row');row.setAttribute('role','row');
  const numberCell=element('div','row-number');numberCell.setAttribute('role','cell');
  const play=element('button','row-play');play.dataset.action='play';play.dataset.id=track.id;play.disabled=!playbackEnabled;play.setAttribute('aria-label',`Phát ${displayNumber(track)}. ${track.title}`);play.title=playbackEnabled?'Phát bản nhạc':'Chưa kết nối nguồn nghe';play.append(element('span','number-text',displayNumber(track)),icon('play'));numberCell.append(play);
  const titleCell=element('div','title-cell');titleCell.setAttribute('role','cell');const title=element('button','track-name',track.title);title.dataset.action='play';title.dataset.id=track.id;title.disabled=!playbackEnabled;title.title=`${displayNumber(track)}. ${track.title} · ${modeNames[track.mode]}`;titleCell.append(title);
  const duration=element('span','track-duration',formatTime(track.durationSeconds));duration.setAttribute('role','cell');duration.title='Thời lượng bản nhạc đã xác minh';
  const favouriteCell=element('div','row-actions');favouriteCell.setAttribute('role','cell');
  const download=element('button','row-download');download.dataset.action='download';download.dataset.id=track.id;
  const item=offline.item(track.id),complete=offline.has(track.id),working=['running','downloading','queued','verifying'].includes(item.status),failed=['error','failed'].includes(item.status);
  download.append(icon(complete?'check':failed?'alert':'download'));download.classList.toggle('is-error',failed);download.classList.toggle('is-complete',complete);
  const label=complete?'Đã tải · Xóa bản trên máy':failed?`Tải lỗi · Thử lại${item.error?`: ${item.error}`:''}`:working?'Đang tải…':'Tải về nghe offline';
  download.title=offline.available?label:'Tải offline chỉ hỗ trợ trong ứng dụng Windows';download.setAttribute('aria-label',`${label}: ${track.title}`);download.setAttribute('aria-busy',String(working));download.disabled=!offline.available || working;
  const favourite=element('button','row-favourite');favourite.dataset.action='favourite';favourite.dataset.id=track.id;favourite.append(icon('heart'));favourite.setAttribute('aria-label',`Yêu thích: ${track.title}`);favourite.setAttribute('aria-pressed',String(store.favourites.includes(track.id)));favouriteCell.append(download,favourite);
  row.append(numberCell,titleCell,duration,favouriteCell);fragment.append(row);rowNodes.set(track.id,row);
 }
 list.append(fragment);updateActiveRows();
}
function updateActiveRows(){
 for(const [id,row]of rowNodes){
  const active=id===player.state.track?.id;row.classList.toggle('active-track',active);
  const title=row.querySelector('.track-name');
  if(active)row.setAttribute('aria-current','true');else row.removeAttribute('aria-current');
  row.querySelector('.row-play use').setAttribute('href',active && player.state.status==='playing'?'#i-pause':'#i-play');
  row.querySelector('.row-play').setAttribute('aria-label',`${active && player.state.status==='playing'?'Tạm dừng':'Phát'} ${title.title}`);
 }
}
$('track-list').addEventListener('click',event=>{
 const target=event.target.closest('button[data-action]');if(!target)return;
 const track=tracks.find(t=>t.id===target.dataset.id);if(!track)return;
 if(target.dataset.action==='favourite'){toggleFavourite(track.id);return;}
 if(target.dataset.action==='download'){if(offline.has(track.id))confirmRemove([track.id]);else void startDownload([track.id]);return;}
 if(!playbackEnabled)return;
 activeQuickId='';
 if(player.state.track?.id===track.id){void player.toggle();return;}
 void player.select(track,visible);
});
function toggleFavourite(id){store.toggleFavourite(id);const wasFocused=document.activeElement?.dataset?.id;renderRows();const current=player.state.track;$('now-favourite').setAttribute('aria-pressed',String(!!current && store.favourites.includes(current.id)));announce(store.favourites.includes(id)?'Đã thêm vào yêu thích.':'Đã bỏ khỏi yêu thích.');if(wasFocused && rowNodes.has(wasFocused))rowNodes.get(wasFocused).querySelector('.row-favourite').focus();}

function selectMode(next){
 mode=next;$('section').value='';
 for(const tab of document.querySelectorAll('[role=tab]')){const active=tab.dataset.mode===mode;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;}
 $('catalog-panel').setAttribute('aria-labelledby',`tab-${mode}`);renderCategories();renderRows();
}
for(const tab of document.querySelectorAll('[role=tab]')){
 tab.addEventListener('click',()=>selectMode(tab.dataset.mode));
 tab.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();let index=MODES.indexOf(mode);index=event.key==='Home'?0:event.key==='End'?2:(index+(event.key==='ArrowRight'?1:2))%3;selectMode(MODES[index]);$(`tab-${MODES[index]}`).focus();});
}
function selectView(next){
 view=next;for(const nav of document.querySelectorAll('[data-view]')){const active=nav.dataset.view===view;nav.classList.toggle('active',active);if(active)nav.setAttribute('aria-current','page');else nav.removeAttribute('aria-current');}
 setText('page-title',{all:'Thư viện',favourites:'Yêu thích',history:'Gần đây'}[view]);renderRows();
}
for(const button of document.querySelectorAll('[data-view]'))button.addEventListener('click',()=>selectView(button.dataset.view));
$('search').addEventListener('input',renderRows);$('category').addEventListener('change',renderRows);$('section').addEventListener('change',renderRows);
$('clear-filters').addEventListener('click',()=>{$('search').value='';$('category').value='';$('section').value='';renderRows();$('search').focus();});
$('reset-filters').addEventListener('click',()=>{$('category').value='';$('section').value='';renderRows();});
$('demo-mode').addEventListener('change',()=>{
 playbackEnabled=$('demo-mode').value==='listen' && (!!api?.token || offline.completed.length>0);activeQuickId='';player.stop();lastRecorded='';
 renderConnection();renderQuick();renderRows();announce(playbackEnabled?'Đã bật phát nhạc.':'Đã dừng phát và chuyển sang xem danh mục.');
});

player.subscribe(state=>{
 const current=state.track,playing=state.status==='playing',loading=['loading','buffering'].includes(state.status);
 setText('now-title',current?trackLabel(current):'Chọn một bài để bắt đầu');
 setText('now-subtitle',current?modeNames[current.mode]:'');
 $('now-title').title=current?trackLabel(current):'';
 for(const id of ['play-toggle','previous','next','now-favourite'])$(id).disabled=!current;
 $('now-favourite').disabled=!current || current.mode==='prayer';
 $('play-toggle').setAttribute('aria-label',playing || loading?'Tạm dừng':'Phát nhạc');setIcon($('play-toggle'),playing || loading?'pause':'play');
 $('now-favourite').setAttribute('aria-pressed',String(!!current && store.favourites.includes(current.id)));
 $('seek').disabled=!state.duration || loading;$('seek').max=String(state.duration);$('seek').value=String(state.position);$('seek').setAttribute('aria-valuetext',`${formatTime(state.position)} trên ${formatTime(state.duration)}`);
 setText('elapsed',formatTime(state.position));setText('duration',formatTime(state.duration));
 $('mute').setAttribute('aria-pressed',String(state.muted));$('mute').setAttribute('aria-label',state.muted?'Bật tiếng':'Tắt tiếng');setIcon($('mute'),state.muted?'muted':'volume');
 for(const key of ['repeat','shuffle','continuous'])$(key).setAttribute('aria-pressed',String(state[key]));
 const statusText={idle:'Chọn bài để nghe.',loading:'Đang tải bản nhạc…',buffering:'Đang chờ dữ liệu âm thanh…',playing:'Đang phát',paused:'Đã tạm dừng',ended:'Bản nhạc đã kết thúc',error:state.error};
 setText('player-status',statusText[state.status] || '');$('player-status').classList.toggle('is-error',state.status==='error');$('retry-play').hidden=state.status!=='error';
 $('player-status').classList.toggle('sr-only',!['loading','buffering','error','ended'].includes(state.status));
 renderQuickVisibility();
 if(current?.id!==lastTrack || state.status!==lastStatus){
  if(state.status==='error' && current && sourceKind==='remote' && !offline.has(current.id) && !offline.offline){
   const failedId=current.id;void checkReachability().then(ready=>{if(!ready && player.state.status==='error' && player.state.track?.id===failedId)enterOffline();});
  }
  updateActiveRows();updateQuickStates();lastTrack=current?.id || '';lastStatus=state.status;
 }
 if(playing && current && current.mode!=='prayer' && lastRecorded!==current.id){store.record(current,revision);lastRecorded=current.id;if(view==='history')renderRows();}
});
$('play-toggle').addEventListener('click',()=>void player.toggle());$('previous').addEventListener('click',()=>void player.previous());$('next').addEventListener('click',()=>void player.next());
$('seek').addEventListener('input',()=>player.seek(Number($('seek').value)));$('volume').addEventListener('input',()=>player.setVolume(Number($('volume').value)));$('mute').addEventListener('click',()=>player.toggleMute());$('retry-play').addEventListener('click',()=>void player.retry());
$('now-favourite').addEventListener('click',()=>{if(player.state.track)toggleFavourite(player.state.track.id);});
for(const key of ['repeat','shuffle','continuous'])$(key).addEventListener('click',()=>player.setModes({[key]:!player.state[key]}));
document.addEventListener('keydown',event=>{
 if(event.key==='/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.closest?.('dialog,input,textarea,select,button,[contenteditable="true"]')){event.preventDefault();$('search').focus();return;}
 const action=shortcutAction(event);if(!action || event.repeat)return;event.preventDefault();
 if(action==='toggle')void player.toggle();else if(action==='forward')player.seek(player.state.position+5);else if(action==='backward')player.seek(player.state.position-5);else if(action==='mute')player.toggleMute();else if(action==='next')void player.next();else if(action==='previous')void player.previous();
});
window.addEventListener('pagehide',()=>player.stop());
async function checkReachability(){
 if(!navigator.onLine)return false;
 if(!connection.base)return false;
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),4000);
 try{const response=await fetch(`${connection.base}/v1/health`,{signal:controller.signal,credentials:'omit',redirect:'error',cache:'no-store',referrerPolicy:'no-referrer'});return response.ok;}catch{return false;}finally{clearTimeout(timer);}
}
function probeStartupConnection(){
 if(startupProbeDone || !connection.base || api?.token || connections.pending || !offline.completed.length || offline.offline || localConnection)return;
 startupProbeDone=true;
 // One bounded readiness request; the local catalog is already available.
 void checkReachability().then(async ready=>{if(!ready && !api?.token)enterOffline();else if(ready && !api?.token && !offline.offline && !connections.pending)await restoreAccess();});
}
function enterOffline(){
 networkUnavailable=true;
 if(player.state.track && !offline.has(player.state.track.id))player.stop();
 offline.setOffline(true);playbackEnabled=offline.completed.length>0;
 renderConnection();renderQuick();renderCategories();renderRows();
}
function renderOffline(){
 $('offline-toggle').textContent=onlineSwitchPending?'Đang kết nối…':offline.offline?'Nghe online':'Nghe offline';
 $('offline-toggle').setAttribute('aria-pressed',String(offline.offline));
 $('offline-toggle').title=offline.offline?'Chuyển sang thư viện trực tuyến khi có kết nối':'Tải nhạc về máy để nghe khi mạng yếu hoặc không có Internet.';
 $('download-open').hidden=offline.complete;
 $('download-open').disabled=!offline.available;
 $('download-open').title=offline.available?'Tải bài để nghe khi không có Internet':'Tải offline chỉ hỗ trợ trong ứng dụng Windows';
 $('trash-open').hidden=!offline.completed.length;
 const count=offline.stale?offline.expectedCatalog.tracks.length:offline.tracks.length;
 setText('offline-summary',offline.available?`${offline.completed.length}${count?` / ${count}`:''} bài trên máy${offline.offline?' · Offline':''}${offline.stale?' · Cần làm mới danh mục':''}`:'Tải offline trong ứng dụng Windows');
 const job=offline.state.job,active=offline.busy,paused=job.status==='paused',failed=Number(job.failed)>0 || ['error','failed'].includes(job.status);
 $('download-job').hidden=!Number(job.total) || (!active && !paused && !failed);
 const labels={initializing:'Đang kiểm tra file trên máy',running:'Đang tải',downloading:'Đang tải',queued:'Chờ tải',verifying:'Đang xác minh',paused:'Đã tạm dừng',cancelled:'Đã hủy',completed:'Đã hoàn tất',error:'Có bài tải lỗi',failed:'Có bài tải lỗi',idle:'Sẵn sàng'};
 setText('download-progress-text',`${labels[job.status] || job.status} · ${job.completed || 0}/${job.total || 0} bài · ${formatBytes(job.bytes)} / ${formatBytes(job.totalBytes)}${job.failed?` · ${job.failed} bài lỗi`:''}`);
 $('download-progress').max=Math.max(1,Number(job.totalBytes)||Number(job.total)||1);$('download-progress').value=Number(job.totalBytes)?Number(job.bytes)||0:Number(job.completed)||0;
 $('download-pause').hidden=!active;$('download-resume').hidden=!paused;$('download-retry').hidden=!failed;$('download-cancel').hidden=!active && !paused;
 if(active && !offlinePollTimer)offlinePollTimer=setTimeout(pollOffline,1000);
 if(!active && offlinePollTimer){clearTimeout(offlinePollTimer);offlinePollTimer=null;}
}
async function pollOffline(){
 offlinePollTimer=null;if(offlinePolling)return;offlinePolling=true;
 try{await offline.refresh();}catch{announce('Chưa đọc được tiến độ tải. Bạn có thể mở Tải về để thử lại.');}
 finally{offlinePolling=false;if(offline.busy && !offlinePollTimer)offlinePollTimer=setTimeout(pollOffline,1000);}
}
offline.subscribe(()=>{
 renderOffline();
 if(!offlineInitialized)return;
 probeStartupConnection();
 if(offline.offline){playbackEnabled=offline.completed.length>0;player.queue=offline.filter(player.queue);if(player.state.track && !offline.has(player.state.track.id))player.stop();}
 const fingerprint=JSON.stringify([offline.offline,offline.state.manifest?.revision,offline.completed,offline.state.items.map(item=>[item.assetId,item.status,item.error])]);
 if(fingerprint===offlineRowsFingerprint)return;offlineRowsFingerprint=fingerprint;
 renderConnection();renderQuick();renderCategories();renderRows();
});
$('offline-toggle').addEventListener('click',async()=>{
 if(onlineSwitchPending)return;
 onlineSwitchMessage='';
 if(!offline.offline){if(player.state.track && !offline.has(player.state.track.id))player.stop();offline.setOffline(true);return;}
 onlineSwitchPending=true;$('offline-toggle').disabled=true;$('offline-toggle').textContent='Đang kết nối…';
 try{
  if(!await checkReachability()){enterOffline();onlineSwitchMessage='Chưa kết nối được thư viện trực tuyến. Hãy kiểm tra kết nối Internet rồi thử lại. Bạn vẫn có thể nghe các bài đã tải.';renderConnection();return;}
  networkUnavailable=false;offline.setOffline(false);playbackEnabled=!!api?.token;
  if(!api?.token){const restored=await restoreAccess();if(!restored){$('connection-settings').open=true;openDialog('settings-dialog');$('access-code').focus();}}
  renderConnection();renderQuick();renderCategories();renderRows();
 }finally{onlineSwitchPending=false;$('offline-toggle').disabled=false;renderOffline();}
});
function requireDownloadSession(){if(api?.token)return {base:api.base,token:api.token};$('connection-settings').open=true;openDialog('settings-dialog');setText('connection-status','Kết nối thư viện trực tuyến để tải thêm bài. Những bài đã tải vẫn được giữ.');return null;}
async function startDownload(ids){
 const session=requireDownloadSession();if(!session)return;
 try{await offline.start(ids,session);}catch(error){announce(`Chưa tải được. ${error.message || error}`);setText('offline-confirm-error',String(error.message || error));}
}
function confirmOffline(title,message,operation){
 confirmOperation=operation;setText('offline-confirm-title',title);setText('offline-confirm-message',message);setText('offline-confirm-error','');$('offline-confirm-submit').disabled=false;openDialog('offline-confirm-dialog');
}
$('offline-confirm-submit').addEventListener('click',async()=>{
 if(!confirmOperation)return;$('offline-confirm-submit').disabled=true;
 try{await confirmOperation();$('offline-confirm-dialog').close();confirmOperation=null;}
 catch(error){setText('offline-confirm-error',String(error.message || error));}
 finally{$('offline-confirm-submit').disabled=false;}
});
$('download-open').addEventListener('click',async()=>{
 if(!offline.state.manifest || offline.stale){const session=requireDownloadSession();if(!session)return;try{await offline.sync(session);}catch(error){announce(`Chưa mở được danh mục tải. ${error.message || error}`);return;}}
 const group=offline.plan(offline.tracks.filter(t=>t.mode===mode)),all=offline.plan();
 setText('download-capacity',`Dung lượng trống trên máy: ${formatBytes(offline.state.freeBytes)}. Các bài đã xác minh sẽ được bỏ qua.`);
 setText('download-group',`Tải ${modeNames[mode]} · ${group.count} bài · ${formatBytes(group.bytes)}`);$('download-group').disabled=!group.count;
 setText('download-all',`Tải toàn bộ thư viện · ${all.count} bài · ${formatBytes(all.bytes)}`);$('download-all').disabled=!all.count;
 openDialog('download-dialog');
});
function confirmDownload(group){
 const plan=offline.plan(group?offline.tracks.filter(t=>t.mode===mode):offline.tracks);$('download-dialog').close();
 if(!plan.count)return;
 confirmOffline('Tải về nghe offline',`Tải ${plan.count} bài (${formatBytes(plan.bytes)})${group?` thuộc ${modeNames[mode]}`:' trong toàn bộ thư viện'} về máy này? Các bài đã tải hợp lệ được bỏ qua.`,async()=>{
  const session=requireDownloadSession();if(!session)throw Error('Cần kết nối thư viện trước khi tải.');await offline.start(plan.ids,session);
 });
}
$('download-group').addEventListener('click',()=>confirmDownload(true));$('download-all').addEventListener('click',()=>confirmDownload(false));
for(const action of ['pause','resume','cancel','retry'])$(`download-${action}`).addEventListener('click',async()=>{
 let session={};if(['resume','retry'].includes(action)){session=requireDownloadSession();if(!session)return;}
 try{await offline.control(action,session);}catch(error){announce(`Chưa thay đổi được tác vụ tải. ${error.message || error}`);}
});
function confirmRemove(ids){
 const selected=[...new Set(ids)].filter(id=>offline.has(id));if(!selected.length)return;
 $('trash-dialog').close();confirmOffline('Xóa bài offline',`Xóa ${selected.length} bài đã tải trên máy này? File gốc trên thư viện trực tuyến được giữ nguyên.`,async()=>{
  if(selected.includes(player.state.track?.id))player.stop();await offline.remove(selected);announce(`Đã xóa ${selected.length} bài trên máy.`);
 });
}
$('trash-open').addEventListener('click',()=>{
 const group=offline.tracks.filter(t=>t.mode===mode && offline.has(t.id));setText('trash-group',`Xóa ${modeNames[mode]} · ${group.length} bài`);$('trash-group').disabled=!group.length;
 setText('trash-all',`Xóa toàn bộ thư viện offline · ${offline.completed.length} bài`);
 const list=$('trash-selection');list.replaceChildren();
 for(const track of offline.tracks.filter(t=>offline.has(t.id))){const label=element('label','trash-choice');const input=element('input');input.type='checkbox';input.value=track.id;label.append(input,element('span','',`${modeNames[track.mode]} · ${displayNumber(track)}. ${track.title}`));list.append(label);}
 $('trash-selected').disabled=true;openDialog('trash-dialog');
});
$('trash-selection').addEventListener('change',()=>{$('trash-selected').disabled=!$('trash-selection').querySelector('input:checked');});
$('trash-selected').addEventListener('click',()=>confirmRemove([...$('trash-selection').querySelectorAll('input:checked')].map(input=>input.value)));
$('trash-group').addEventListener('click',()=>confirmRemove(offline.tracks.filter(t=>t.mode===mode).map(t=>t.id)));
$('trash-all').addEventListener('click',()=>confirmRemove(offline.completed));
media.addEventListener('error',()=>{if(player.state.track && offline.has(player.state.track.id))void offline.refresh().catch(()=>{});});
function renderUpdates(){
 const state=updates.state;
 const enabled=updates.available && connection.enabled && !localConnection && !connection.test && connection.base==='https://audiotp-media-api.ctcm251010.workers.dev';
 $('update-check').hidden=!enabled;
 $('update-check').disabled=['checking','installing'].includes(state.status);
 setText('update-status',state.message);
 $('update-notice').hidden=!enabled || !['available','installing','error'].includes(state.status);
 setText('update-message',state.message);
 $('update-install').disabled=!['available','error'].includes(state.status);
 setText('update-install',state.status==='installing'?'Đang cập nhật…':state.status==='error'?'Thử lại':'Cập nhật');
 const show=enabled && state.notification && ['available','installing','error','checking'].includes(state.status);
 if(show){setText('update-versions',`Phiên bản hiện tại: ${state.currentVersion || $('build-version').textContent.split(' · ')[0]} · Phiên bản mới: ${state.version || ''}`);setText('update-modal-message',state.message);$('update-progress').hidden=!state.progress;if(state.progress){if(Number.isFinite(state.progress.percent))$('update-progress').value=state.progress.percent;else $('update-progress').removeAttribute('value');}openDialog('update-dialog');}
 else if($('update-dialog').open)$('update-dialog').close();
 $('update-now').disabled=['checking','installing'].includes(state.status);$('update-defer').disabled=state.status==='installing';
}
updates.subscribe(renderUpdates);
$('update-check').addEventListener('click',async()=>{$('settings-dialog').close();await updates.check(api?.token);});
async function installUpdate(){
 if(!api?.token){pendingInstall=true;updates.defer();$('update-dialog').close();$('connection-settings').open=true;openDialog('settings-dialog');setText('connection-status','Kết nối thư viện để xác minh và cài đặt bản cập nhật chính thức.');return;}
 if(updates.state.status==='error')await updates.check(api.token);
 player.pause();void updates.install(api.token);
}
$('update-install').addEventListener('click',()=>{if(updates.state.status==='error')void updates.check(api?.token);else installUpdate();});
$('update-now').addEventListener('click',installUpdate);
$('update-defer').addEventListener('click',()=>{updates.defer();$('update-dialog').close();});
// One small authenticated check at login, then at most once per six hours while
// visible. Never download an installer without the user's click.
const updateTimer=setInterval(()=>{if(!document.hidden && api?.token && sourceKind==='remote' && !connection.test)void updates.check(api.token,{automatic:true});},6*60*60*1000);
window.addEventListener('pagehide',()=>{clearInterval(updateTimer);clearTimeout(offlinePollTimer);updates.clear();});
void loadCatalog();
