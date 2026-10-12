import {canPlayQuick} from './catalog.mjs';

// User intent outlives search, seek and track changes. No timers or DOM effects.
export class QuickPanelState {
 constructor({manualCollapsed=false}={}){this.manualCollapsed=!!manualCollapsed;this.autoHidden=false;this.query='';}
 setQuery(value){this.query=String(value ?? '').trim();}
 setManualCollapsed(value){this.manualCollapsed=!!value;if(!value)this.autoHidden=false;}
 setAutoHidden(value){this.autoHidden=!!value;}
 observePlayback({status,position,duration}){
  if(this.autoHidden && !this.manualCollapsed && !this.query && status==='playing' && Number.isFinite(duration) && duration>0 && Number.isFinite(position) && position>=duration*.5)this.autoHidden=false;
 }
 presentation(){return {hidden:!!this.query,expanded:!this.manualCollapsed && !this.autoHidden};}
}

export function quickPlaybackPlan(card,tracks){
 if(!canPlayQuick(card,tracks) || new Set(card.assetIds).size!==card.assetIds.length)return null;
 const lookup=new Map(tracks.map(t=>[t.id,t]));const queue=card.assetIds.map(id=>lookup.get(id));
 if(card.behavior==='silent-library'){
  const silent=tracks.filter(t=>t.mode==='silent');
  if(card.firstAssetId!==queue[0].id || queue.length!==silent.length || queue.some(t=>t.mode!=='silent'))return null;
  return {mode:'silent',view:'all',first:queue[0],queue};
 }
 if(card.behavior==='asset-playlist')return {mode:null,view:null,first:queue[0],queue};
 return null;
}

export function quickPresentation(card,tracks,{activeQuickId='',status='idle',playbackEnabled=false}={}) {
 const eligible=canPlayQuick(card,tracks);
 if(!eligible)return {disabled:true,label:'Chưa khả dụng',icon:'lock',busy:false,active:false};
 const active=activeQuickId===card.id;
 const labels={loading:'Đang tải…',buffering:'Đang tải…',playing:'Tạm dừng',paused:'Phát tiếp',error:'Thử lại',ended:'Phát lại'};
 return {disabled:!playbackEnabled,label:active?(labels[status] || 'Phát'):'Phát',icon:active && ['playing','loading','buffering'].includes(status)?'pause':'play',busy:active && ['loading','buffering'].includes(status),active};
}

export function shortcutAction(event) {
  if(event.ctrlKey || event.altKey || event.metaKey || event.target?.closest?.('dialog,input,select,textarea,button,a,[contenteditable="true"],[role="button"]'))return null;
  return ({' ':'toggle',ArrowRight:'forward',ArrowLeft:'backward',m:'mute',M:'mute',n:'next',N:'next',p:'previous',P:'previous',MediaTrackNext:'next',MediaTrackPrevious:'previous'})[event.key] || null;
}
export function libraryView(tracks,view,store) {
  if(view==='favourites')return tracks.filter(t=>store.favourites.includes(t.id));
  if(view==='history'){const lookup=new Map(tracks.map(t=>[t.id,t]));return store.history.map(x=>lookup.get(x.id)).filter(Boolean);}
  return tracks;
}
