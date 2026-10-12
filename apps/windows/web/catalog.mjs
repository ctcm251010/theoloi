export const MODES = ['guide', 'instrumental', 'silent'];
export const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g,'d').replace(/Đ/g,'D').toLowerCase().replace(/\s+/g,' ').trim();

export function validateCatalog(data) {
  if (data?.schemaVersion !== 1 || typeof data.revision !== 'string' || !Array.isArray(data.tracks)) throw Error('Danh mục không đúng định dạng.');
  const ids = new Set();
  for (const t of data.tracks) {
    if (!t || typeof t.id !== 'string' || !t.id || ids.has(t.id) || typeof t.logicalId !== 'string' || !MODES.includes(t.mode) || !['main','appendix',null].includes(t.section) || !Number.isInteger(t.number) || t.number < 1 || typeof t.title !== 'string' || typeof t.category !== 'string' || !Number.isFinite(t.durationSeconds) || t.durationSeconds < 0) throw Error('Danh mục có bản ghi không hợp lệ.');
    ids.add(t.id);
  }
  return data.tracks;
}

export function filterTracks(tracks, {mode='guide', query='', category='', section=''}={}) {
  const q = normalize(query);
  const numeric = q.match(/^(?:(pl|phu luc|main|chinh)\s*)?(\d+)$/);
  return tracks.filter(t => t.mode === mode && (!category || t.category === category) && (!section || t.section === section) && (!q || (numeric ? t.number === Number(numeric[2]) && (!numeric[1] || (['pl','phu luc'].includes(numeric[1]) ? t.section === 'appendix' : t.section === 'main')) : normalize(t.title).includes(q))));
}

export function canPlayQuick(card, tracks) {
  return !!card && card.available === true && card.sourceStatus === 'verified' && card.rightsStatus === 'approved' && Array.isArray(card.assetIds) && card.assetIds.length > 0 && card.assetIds.every(id => tracks.some(t=>t.id === id));
}

export const formatTime = seconds => Number.isFinite(seconds) && seconds >= 0 ? `${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}` : '0:00';
export const displayNumber = t => `${t.section === 'appendix' ? 'PL ' : ''}${t.number}`;
