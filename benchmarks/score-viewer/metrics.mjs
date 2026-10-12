export function median(values) {
  const v=values.filter(Number.isFinite).sort((a,b)=>a-b);
  if(!v.length)return null;
  const middle=Math.floor(v.length/2);
  return v.length%2?v[middle]:(v[middle-1]+v[middle])/2;
}
export function resourcesForRequests(paths,resources){
  for(const path of paths)if(!resources.some(x=>x.name===path))throw new Error(`Missing resource timing evidence: ${path}`);
  return resources;
}
export function beginRun(result,startedAt){
  result.rows=[];delete result.lastError;delete result.finishedAt;result.startedAt=startedAt;
}
export function summarize(rows) {
  const result=[];
  for(const format of ['pdf','png','webp','avif','vector'])for(const cache of ['cold','warm']){
    const items=rows.filter(r=>r.format===format&&r.cache===cache);
    if(!items.length)continue;
    const category=phase=>items.filter(r=>r.phase===phase);
    result.push({format,cache,samples:category('first').length,
      firstMs:median(category('first').map(x=>x.ms)),nextMs:median(category('next').map(x=>x.ms)),
      firstWorkMs:median(category('first').map(x=>x.workMs)),nextWorkMs:median(category('next').map(x=>x.workMs)),
      firstFrameWaitMs:median(category('first').map(x=>x.frameWaitMs)),
      revisitMs:median(category('revisit').map(x=>x.ms)),
      firstTransferBytes:median(category('first').map(x=>x.transferBytes)),
      heapUsedBytes:median(category('first').map(x=>x.heapUsedBytes))});
  }
  return result;
}
