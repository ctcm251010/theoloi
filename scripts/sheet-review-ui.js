/* Static local proposals only. This code has no HTTP, media or store writer. */
(() => {
  'use strict';
  function buildBatch(queue, decisions, reviewer, provenance) {
    if (!reviewer.trim() || !provenance.trim()) throw Error('Cần người review và provenance.');
    if (!decisions.length || decisions.length > 50) throw Error('Chọn từ 1 đến 50 mục đã kiểm tra.');
    const sources = new Set(queue.rows.map(r => r.sheetId));
    const songs = new Set(queue.songs.map(s => s.id));
    const seen = new Set();
    const checked = decisions.map(d => {
      const pair = JSON.stringify([d.sheetId, d.songId]);
      if (!sources.has(d.sheetId) || seen.has(pair)) throw Error('Source ID không hợp lệ hoặc trùng.');
      if (!['approve','reject','defer'].includes(d.decision)) throw Error('Chọn quyết định cho từng mục.');
      if (d.reviewed !== true || !d.evidence.trim()) throw Error('Cần evidence và xác nhận đã kiểm tra từng mục.');
      if (d.songId === null ? d.decision !== 'defer' : !songs.has(d.songId)) throw Error('Audio song ID không hợp lệ.');
      seen.add(pair);
      return {sheetId:d.sheetId, songId:d.songId, decision:d.decision, evidence:d.evidence.trim(),
              reviewer:reviewer.trim(), provenance:provenance.trim(), reviewed:true};
    });
    return {schemaVersion:1, catalogSha256:queue.catalogSha256, audioCatalogSha256:queue.audioCatalogSha256,
            baseRevision:queue.baseRevision, decisions:checked};
  }
  globalThis.AudioTPReview = {buildBatch};
  if (typeof document === 'undefined') return;
  const queue = JSON.parse(document.getElementById('queue-data').textContent);
  const bySong = new Map(queue.songs.map(s => [s.id,s]));
  const selections = new Map();
  let page = 0;
  const $ = id => document.getElementById(id);
  const element = (tag, text, cls) => {
    const e = document.createElement(tag);
    if (text !== undefined) e.textContent = text;
    if (cls) e.className = cls;
    return e;
  };
  function label(text, control) {const e=element('label',text); e.append(control); return e;}
  function selectedCount() {return [...selections.values()].filter(d=>d.reviewed).length;}
  function updateCount() {
    const n=selectedCount(); $('selected').textContent=`${n} mục đã chọn · thay đổi chưa được lưu vào overlay`;
    $('download').disabled=n===0 || n>50;
  }
  for (const s of queue.songs) {
    const o=document.createElement('option');o.value=s.id;o.label=`${s.section}:${s.number} · ${s.title}`;$('audio-options').append(o);
  }
  function render() {
    const term=$('search').value.trim().normalize('NFC').toLocaleLowerCase('vi');
    const scope=$('scope').value;
    const rows=queue.rows.filter(r => (scope==='all' || (scope==='priority' ? ['main-464','duplicate-title'].includes(r.priority) : r.matchingStatus==='unmatched'))
      && (!term || [r.sheetId,r.title,`${r.sourceGroup}:${r.sourceNumber}`].join(' ').normalize('NFC').toLocaleLowerCase('vi').includes(term)));
    page=Math.min(page, Math.max(0,Math.ceil(rows.length/25)-1));
    $('rows').replaceChildren();
    $('summary').textContent=`${queue.rows.length} nguồn · đang lọc ${rows.length} · revision ${queue.baseRevision.slice(0,12)} · rights giữ nguyên`;
    $('page').textContent=`${page+1}/${Math.max(1,Math.ceil(rows.length/25))}`;
    $('previous').disabled=page===0;$('next').disabled=(page+1)*25>=rows.length;
    for (const r of rows.slice(page*25,(page+1)*25)) {
      const d=selections.get(r.sheetId) || {sheetId:r.sheetId,songId:r.matchingStatus==='candidate' ? r.audioLinks[0].songId : null,decision:'',evidence:'',reviewed:false};
      const card=element('article');card.append(element('span',`${r.priority} · ${r.matchingStatus}`,'tag'),element('h2',`${r.sourceGroup}:${r.sourceNumber} · ${r.title}`),element('p',r.sheetId,'small'));
      card.append(element('p',`Edition: ${r.edition || 'chưa biết'} · quyền: ${r.usageRights.status} · mapping approve không cấp quyền tải/phục vụ.`,'small'));
      if (r.sourcePageUrl) {const a=element('a','Mở trang nguồn để tự kiểm tra');a.href=r.sourcePageUrl;a.target='_blank';a.rel='noopener noreferrer';card.append(a);}
      card.append(element('p',`Ứng viên: ${r.audioLinks.map(l=>`${l.songId} · ${bySong.get(l.songId)?.title || ''} (${l.confidence})`).join('; ') || 'chưa có'}`,'small'));
      if (r.reviewIssues.length) card.append(element('p',r.reviewIssues.join('; '),'small'));
      if (r.decisions.length) card.append(element('p',`Lịch sử hiệu lực: ${r.decisions.map(x=>`${x.decision} ${x.songId || '(chưa chọn audio)'}${x.stale?' · STALE':''}`).join('; ')}`,'small'));
      const choice=document.createElement('select');
      for(const [v,t] of [['','Chọn quyết định'],['approve','Approve — cùng tác phẩm'],['reject','Reject — không chấp nhận liên kết'],['defer','Defer — cần kiểm tra thêm']]) {
        const o=element('option',t);o.value=v;choice.append(o);
      }
      choice.value=d.decision;
      const song=document.createElement('input');song.setAttribute('list','audio-options');song.value=d.songId || '';song.placeholder='Exact audio song ID; defer có thể để trống';
      const audioTitle=element('p','','small');
      const fields=element('div',undefined,'choices');fields.append(label('Quyết định',choice),label('Audio song ID',song));card.append(fields,audioTitle);
      const evidence=document.createElement('textarea');evidence.value=d.evidence;evidence.placeholder='Đã đối chiếu gì? Chưa chắc điều gì? Không suy ra từ confidence.';
      card.append(label('Evidence cho mục này',evidence));
      const check=document.createElement('input');check.type='checkbox';check.checked=d.reviewed;
      const checkedLabel=label('Tôi đã kiểm tra mục này và chịu trách nhiệm về quyết định.',check);checkedLabel.className='check';card.append(checkedLabel);
      const change=()=>{
        d.songId=song.value.trim() || null;d.decision=choice.value;d.evidence=evidence.value;d.reviewed=check.checked;
        audioTitle.textContent=d.songId ? (bySong.has(d.songId) ? `Audio: ${bySong.get(d.songId).title}` : 'Audio ID chưa hợp lệ') : 'Chưa chọn audio';
        selections.set(r.sheetId,d);updateCount();
      };
      for (const control of [choice,song,evidence,check]) control.addEventListener('input',change);
      change();$('rows').append(card);
    }
    updateCount();
  }
  $('search').addEventListener('input',()=>{page=0;render();});
  $('scope').addEventListener('change',()=>{page=0;render();});
  $('previous').addEventListener('click',()=>{page--;render();});$('next').addEventListener('click',()=>{page++;render();});
  $('download').addEventListener('click',()=>{
    try {
      const batch=buildBatch(queue,[...selections.values()].filter(d=>d.reviewed),$('reviewer').value,$('provenance').value);
      const blob=new Blob([JSON.stringify(batch,null,2)+'\n'],{type:'application/json;charset=utf-8'});
      const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='sheet-review-batch.json';a.click();
      setTimeout(()=>URL.revokeObjectURL(url),1000);
      $('error').textContent='Đã xuất đề xuất. Chưa lưu quyết định; chạy CLI batch dry-run rồi --apply --confirm-count N.';
    } catch(e) {$('error').textContent=e.message;}
  });
  render();
})();
