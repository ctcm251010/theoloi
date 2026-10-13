import {displayNumber} from './catalog.mjs';
const fields=['id','logicalId','mode','section','number','title','category','durationSeconds'].sort().join(',');
export function validateQuickAudio(data){
 if(!data || Object.keys(data).sort().join(',')!=='revision,schemaVersion,tracks' || data.schemaVersion!==1 || !/^sha256:[a-f0-9]{64}$/.test(data.revision) || !Array.isArray(data.tracks))throw Error('Dữ liệu Nghe nhanh không hợp lệ.');
 const ids=new Set();
 for(const t of data.tracks){
  if(!t || Object.keys(t).sort().join(',')!==fields || typeof t.id!=='string' || !/^watv:vi:prayer:[a-z0-9-]+$/.test(t.id) || t.logicalId!==t.id || ids.has(t.id) || t.mode!=='prayer' || t.section!==null || t.number!==null || typeof t.title!=='string' || !t.title.trim() || typeof t.category!=='string' || !t.category.trim() || !Number.isFinite(t.durationSeconds) || t.durationSeconds<=0)throw Error('Dữ liệu Nghe nhanh không hợp lệ.');
  ids.add(t.id);
 }
 return data.tracks;
}
// Only the explicitly reviewed recording can enable this card. The server
// publishes approved supplementary assets; no guessed filename/placeholder.
export function applyQuickAudio(cards,tracks){
 const id='watv:vi:prayer:our-wish';
 return cards.map(card=>card.id==='quick:our-wish-meditation'?{...card,behavior:'asset-playlist',available:tracks.some(t=>t.id===id),assetIds:tracks.some(t=>t.id===id)?[id]:[],firstAssetId:id,sourceStatus:tracks.some(t=>t.id===id)?'verified':'unverified',rightsStatus:tracks.some(t=>t.id===id)?'approved':'unknown',reason:tracks.some(t=>t.id===id)?'Bản thu đã xác minh.':'Chưa có nguồn audio được xác minh.'}:card);
}
export function trackLabel(track){return Number.isInteger(track.number)?`${displayNumber(track)}. ${track.title}`:track.title;}
