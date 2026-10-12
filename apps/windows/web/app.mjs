import {MODES,validateCatalog,filterTracks,formatTime,displayNumber} from './catalog.mjs';
import {Player} from './player.mjs';
import {MediaAPI,ConnectionGate} from './api-client.mjs';
import {LibraryStore} from './storage.mjs';
import {shortcutAction,libraryView,quickPresentation,QuickPanelState,quickPlaybackPlan} from './ui-core.mjs';

const $=id=>document.getElementById(id);
const modeNames={guide:'Hướng dẫn',instrumental:'Nhạc đệm',silent:'Nhạc ngẫm nghĩ'};
let storage;try{storage=window.localStorage;}catch{}
const store=new LibraryStore(storage);
const quickPreference='audiotp.quick-collapsed.v1';
let manualCollapsed=false;try{manualCollapsed=storage?.getItem(quickPreference)==='true';}catch{}
const quickPanel=new QuickPanelState({manualCollapsed});
let tracks=[],quickCards=[],revision='',mode='guide',view='all',visible=[],playbackEnabled=false,loadGeneration=0;
const rowNodes=new Map();
const quickNodes=new Map();
let activeQuickId='';
let lastRecorded='',lastTrack='',lastStatus='';
const media=$('audio');media.volume=.7;
let api=null,sourceKind='none';
const connections=new ConnectionGate();
const player=new Player(media,track=>{
 if(!playbackEnabled || !api)throw Error('Chưa kết nối nguồn nghe. Hãy kết nối thư viện trước.');
 return api.resolve(track);
},{shouldRefresh:track=>api?.needsRefresh(track) ?? false});

function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=text;return node;}
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('class','icon');svg.setAttribute('aria-hidden','true');const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href',`#i-${name}`);svg.append(use);return svg;}
function setText(id,text){if($(id).textContent!==text)$(id).textContent=text;}
function setIcon(node,name){node.replaceChildren(icon(name));}
function announce(text){setText('announcement',text);}
function openDialog(id){const dialog=$(id);if(!dialog.open)dialog.showModal();}
for(const [button,dialog] of [['settings-toggle','settings-dialog'],['connection-open','settings-dialog'],['filters-toggle','filters-dialog'],['playback-toggle','playback-dialog']]){
 $(button).addEventListener('click',()=>openDialog(dialog));
}
for(const button of document.querySelectorAll('[data-close-dialog]'))button.addEventListener('click',()=>$(button.dataset.closeDialog).close());
for(const dialog of document.querySelectorAll('dialog'))dialog.addEventListener('keydown',event=>{
 if(event.key==='Escape'){event.preventDefault();event.stopPropagation();dialog.close();}
});
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
  const [catalogResult,quickResult,connectionResult]=await Promise.allSettled([fetchJSON('./catalog.client.json'),fetchJSON('./quick-play.json'),fetchJSON('./connection.json')]);
  if(token!==loadGeneration)return;
  if(catalogResult.status==='rejected')throw catalogResult.reason;
  tracks=validateCatalog(catalogResult.value);revision=catalogResult.value.revision;
  quickCards=quickResult.status==='fulfilled' && Array.isArray(quickResult.value)?quickResult.value:[];
  renderQuick();renderCategories();renderRows();
  if(connectionResult.status==='fulfilled'){
   const config=connectionResult.value;
   if(typeof config.version==='string')setText('build-version',`${config.version} · ${config.buildNumber || 'development'}`);
   if(config.mode==='local-files' && config.apiBase===window.location.origin){await connectLibrary(config.apiBase,'',{local:true});}
   else if(config.apiBase){$('api-base').value=config.apiBase;}
  }
 }catch(error){if(token!==loadGeneration)return;statePanel('Chưa thể mở thư viện',error.name==='AbortError'?'Dữ liệu phản hồi quá lâu. Hãy thử tải lại.':error.message,{retry:true});}
}

function renderConnection(){
 const ready=!!api?.token;
 $('demo-mode').querySelector('option[value="listen"]').disabled=!ready;
 $('demo-mode').value=playbackEnabled?'listen':'catalog';
 $('disconnect').hidden=!ready;
 const notice=$('demo-notice').querySelector('p');
 // Browser offline status does not prevent listening to files on loopback.
 const offline=!navigator.onLine && sourceKind!=='local';
 notice.textContent=offline?'Mất kết nối. Hãy thử lại khi có mạng.':ready?'Đang ở chế độ chỉ xem danh mục.':'Kết nối thư viện để nghe nhạc.';
 $('demo-notice').hidden=playbackEnabled && !offline;
}
function connectionLost(){connections.cancel();api?.logout();api=null;sourceKind='none';playbackEnabled=false;activeQuickId='';player.stop();$('connect-button').disabled=false;renderConnection();renderQuick();renderRows();$('connection-settings').open=true;openDialog('settings-dialog');setText('connection-status','Phiên truy cập đã hết hạn. Hãy kết nối lại.');}
async function connectLibrary(base,code,{local=false}={}){
 playbackEnabled=false;activeQuickId='';player.stop();api?.logout();api=null;
 let next;
 const attempt=connections.begin({logout:()=>next?.logout()});
 $('connect-button').disabled=true;setText('connection-status','Đang kết nối…');
 try{
  next=new MediaAPI(base,{onUnauthorized:()=>{if(attempt.current())connectionLost();}});
  if(local)await next.localSession();else await next.login(code);
  const data=await next.catalog();const rows=validateCatalog(data);
  if(!attempt.current()){next.logout();return;}
  api=next;sourceKind=local?'local':'remote';tracks=rows;revision=data.revision;playbackEnabled=true;
  attempt.complete();
  setText('connection-status',local?'Đã kết nối thư viện trên máy.':'Đã kết nối thư viện trực tuyến.');
  $('connection-settings').open=false;
 }catch(error){if(attempt.current()){next?.logout();attempt.complete();setText('connection-status',error.message);$('connection-settings').open=true;}}
 finally{if(attempt.current()){$('access-code').value='';$('connect-button').disabled=false;renderConnection();renderQuick();renderCategories();renderRows();}}
}
$('connection-form').addEventListener('submit',event=>{event.preventDefault();const code=$('access-code').value;$('access-code').value='';void connectLibrary($('api-base').value.trim(),code);});
$('disconnect').addEventListener('click',()=>{api?.logout();api=null;sourceKind='none';connectionLost();setText('connection-status','Đã ngắt kết nối.');});
window.addEventListener('offline',renderConnection);window.addEventListener('online',renderConnection);
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
 const cards=quickCards.length?quickCards:[{id:'missing-1',title:'Nhạc ngẫm nghĩ'},{id:'missing-2',title:'Cầu nguyện chúng con mong muốn'},{id:'missing-3',title:'Nhạc không lời cầu nguyện thống thanh'}];
 for(const card of cards){
  const node=element('article','quick-item');
  const eligible=!!quickPlaybackPlan(card,tracks);
  const button=element('button','quick-item-button');button.disabled=!eligible || !playbackEnabled;
  button.title=String(card.reason || 'Chưa có nguồn audio được xác minh.');
  quickNodes.set(card.id,{card,button,node});
  if(eligible)button.addEventListener('click',()=>{
   const plan=quickPlaybackPlan(card,tracks);if(!plan || !playbackEnabled)return;
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
  const state=quickPresentation(card,tracks,{activeQuickId,status:player.state.status,playbackEnabled});
  button.disabled=state.disabled || !quickPlaybackPlan(card,tracks);
  const copy=element('span','quick-item-copy');copy.append(element('span','quick-item-title',card.title),element('small','',state.label));
  button.replaceChildren(icon(state.icon),copy);
  button.setAttribute('aria-label',`${card.title}: ${state.label}`);button.setAttribute('aria-busy',String(state.busy));
  node.classList.toggle('active-quick',state.active);node.classList.toggle('is-error',state.active && player.state.status==='error');
 }
}

function renderCategories(){
 const select=$('category');select.replaceChildren(new Option('Tất cả chủ đề',''));
 const categories=[...new Set(tracks.filter(t=>t.mode===mode).map(t=>t.category))].filter(Boolean).sort((a,b)=>a.localeCompare(b,'vi'));
 for(const category of categories)select.append(new Option(category,category));
 $('section').disabled=mode==='silent';
}
function renderRows(){
 renderQuickVisibility();
 const base=libraryView(tracks,view,store);
 visible=filterTracks(base,{mode,query:$('search').value,category:$('category').value,section:$('section').value});
 $('clear-filters').hidden=!($('search').value || $('category').value || $('section').value);
 $('filters-toggle').classList.toggle('has-filters',!!($('category').value || $('section').value));
 const list=$('track-list');list.replaceChildren();rowNodes.clear();
 if(!visible.length){statePanel(view==='favourites'?'Chưa có bài yêu thích':view==='history'?'Chưa có lần nghe nào':'Không tìm thấy bài phù hợp',view==='all'?'Thử tên bài không dấu, số bài hoặc “PL 1” cho phụ lục.':'Hãy chọn một bài trong thư viện hoặc thay đổi bộ lọc.');return;}
 $('catalog-state').hidden=true;$('track-table').hidden=false;
 const fragment=document.createDocumentFragment();
 for(const track of visible){
  const row=element('div','track-row');row.setAttribute('role','row');
  const numberCell=element('div','row-number');numberCell.setAttribute('role','cell');
  const play=element('button','row-play');play.dataset.action='play';play.dataset.id=track.id;play.disabled=!playbackEnabled;play.setAttribute('aria-label',`Phát ${displayNumber(track)}. ${track.title}`);play.title=playbackEnabled?'Phát bản nhạc':'Chưa kết nối nguồn nghe';play.append(element('span','number-text',displayNumber(track)),icon('play'));numberCell.append(play);
  const titleCell=element('div','title-cell');titleCell.setAttribute('role','cell');const title=element('button','track-name',track.title);title.dataset.action='play';title.dataset.id=track.id;title.disabled=!playbackEnabled;title.title=`${displayNumber(track)}. ${track.title} · ${modeNames[track.mode]}`;titleCell.append(title);
  const duration=element('span','track-duration',formatTime(track.durationSeconds));duration.setAttribute('role','cell');duration.title='Thời lượng bản nhạc đã xác minh';
  const favouriteCell=element('div','');favouriteCell.setAttribute('role','cell');const favourite=element('button','row-favourite');favourite.dataset.action='favourite';favourite.dataset.id=track.id;favourite.append(icon('heart'));favourite.setAttribute('aria-label',`Yêu thích: ${track.title}`);favourite.setAttribute('aria-pressed',String(store.favourites.includes(track.id)));favouriteCell.append(favourite);
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
 playbackEnabled=$('demo-mode').value==='listen' && !!api?.token;activeQuickId='';player.stop();lastRecorded='';
 renderConnection();renderQuick();renderRows();announce(playbackEnabled?'Đã bật phát nhạc.':'Đã dừng phát và chuyển sang xem danh mục.');
});

player.subscribe(state=>{
 const current=state.track,playing=state.status==='playing',loading=['loading','buffering'].includes(state.status);
 setText('now-title',current?`${displayNumber(current)}. ${current.title}`:'Chọn một bài để bắt đầu');
 setText('now-subtitle',current?modeNames[current.mode]:'');
 $('now-title').title=current?`${displayNumber(current)}. ${current.title}`:'';
 for(const id of ['play-toggle','previous','next','now-favourite'])$(id).disabled=!current;
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
 if(current?.id!==lastTrack || state.status!==lastStatus){updateActiveRows();updateQuickStates();lastTrack=current?.id || '';lastStatus=state.status;}
 if(playing && current && lastRecorded!==current.id){store.record(current,revision);lastRecorded=current.id;if(view==='history')renderRows();}
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
void loadCatalog();
