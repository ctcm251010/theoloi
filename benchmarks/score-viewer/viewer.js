import {summarize,resourcesForRequests,beginRun} from './metrics.mjs?v=2';
const $=id=>document.getElementById(id);
const labels={pdf:'A · PDF',png:'B · PNG',webp:'B · WebP',avif:'B · AVIF',vector:'C · SVG + HTML'};
let session=null,page=1,scale=1,busy=false,pdfjs=null,pdfjsInitMs=null,fontSerial=0;
const result={schemaVersion:1,method:'media-fetch-to-two-animation-frames; library init separate; no process cold/GC isolation',
  environment:{userAgent:navigator.userAgent,platform:navigator.platform,devicePixelRatio:devicePixelRatio,hardwareConcurrency:navigator.hardwareConcurrency,
    viewport:{width:innerWidth,height:innerHeight},timeOrigin:performance.timeOrigin,url:location.href,visibilityAtInit:document.visibilityState},rows:[]};
const frame=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
function setBusy(value){busy=value;for(const id of ['open','benchmark','prev','next','fit','zoom','format','cache','rounds'])$(id).disabled=value;}
async function action(fn){if(busy)return;setBusy(true);try{await fn();}catch(error){$('status').textContent='FAIL: '+error.message;result.lastError=String(error);update();}finally{setBusy(false);}}
async function loadPDFLibrary(){if(pdfjs)return;const t=performance.now();pdfjs=await import('./vendor/pdf.mjs');pdfjs.GlobalWorkerOptions.workerSrc=new URL('./vendor/pdf.worker.mjs',import.meta.url).href;pdfjsInitMs=performance.now()-t;result.pdfjsModuleInitMs=pdfjsInitMs;}
async function dispose(){
  if(!session)return;
  $('stage').replaceChildren();
  if(session.canvas){session.canvas.width=0;session.canvas.height=0;}
  if(session.url)URL.revokeObjectURL(session.url);
  if(session.task)await session.task.destroy();
  if(session.font)document.fonts.delete(session.font);
  session.cache.clear();session=null;
}
async function fresh(format,cache){await dispose();if(format==='pdf')await loadPDFLibrary();session={format,condition:cache,cache:new Map(),pdf:null,task:null,font:null,url:null,canvas:null};page=1;}
async function bytes(path){session.requestPaths.push(new URL(path,location.href).pathname);const response=await fetch(path,{cache:session.condition==='cold'?'reload':'default'});if(!response.ok)throw new Error(`${response.status}: ${path}`);return response.arrayBuffer();}
async function pageData(n){
  if(session.cache.has(n))return {value:session.cache.get(n),hit:true};
  const path=`fixtures/page-${n}.${session.format==='vector'?'vector.json':session.format}`;
  const data=await bytes(path);
  const value=session.format==='vector'?JSON.parse(new TextDecoder().decode(data)):data;
  session.cache.set(n,value);while(session.cache.size>2)session.cache.delete(session.cache.keys().next().value);
  return {value,hit:false};
}
async function render(n,phase='manual',round=0){
  if(!session)throw new Error('Mở tài liệu trước.');
  if(n<1||n>4)throw new Error('Trang ngoài phạm vi.');
  page=n;performance.clearResourceTimings();session.requestPaths=[];
  const start=performance.now(),heapBefore=performance.memory?.usedJSHeapSize??null,visibilityStart=document.visibilityState;
  const stage=$('stage');stage.replaceChildren();
  if(session.canvas){session.canvas.width=0;session.canvas.height=0;session.canvas=null;}
  if(session.url){URL.revokeObjectURL(session.url);session.url=null;}
  stage.style.width=`${760*scale}px`;stage.style.height=`${1060*scale}px`;
  let appCacheHit=false,estimatedPixelBytes=0;
  if(session.format==='pdf'){
    appCacheHit=!!session.pdf;
    if(!session.pdf){const data=await bytes('fixtures/original.pdf');session.task=pdfjs.getDocument({data,disableAutoFetch:true,isEvalSupported:false});session.pdf=await session.task.promise;}
    const p=await session.pdf.getPage(n),viewport=p.getViewport({scale:scale*(devicePixelRatio||1)});
    const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
    canvas.style.width=`${760*scale}px`;canvas.style.height=`${1060*scale}px`;stage.append(canvas);session.canvas=canvas;
    await p.render({canvasContext:canvas.getContext('2d'),viewport}).promise;p.cleanup();estimatedPixelBytes=canvas.width*canvas.height*4;
  }else{
    const loaded=await pageData(n);appCacheHit=loaded.hit;
    if(session.format==='vector'){
      if(!session.font){const data=await bytes('fixtures/score-font.ttf');const family='ScoreNoto'+(++fontSerial),font=new FontFace(family,data);await font.load();document.fonts.add(font);session.font=font;session.family=family;}
      // Only generator-owned JSON is accepted by this prototype; not untrusted catalog SVG.
      const parsed=new DOMParser().parseFromString(loaded.value.svg,'image/svg+xml');
      if(parsed.querySelector('parsererror,image,script,foreignObject'))throw new Error('Invalid self-authored SVG');
      stage.append(document.importNode(parsed.documentElement,true));
      const layer=document.createElement('div');layer.className='score-text-layer';layer.style.transform=`scale(${scale})`;
      for(const t of loaded.value.texts){const span=document.createElement('span');span.className='score-text';span.textContent=t.text;span.style.cssText=`left:${t.x}px;top:${t.y-t.size*1.069}px;font-size:${t.size}px;font-family:${session.family}`;layer.append(span);}stage.append(layer);
    }else{
      const img=document.createElement('img');img.alt=`Bản nhạc tự soạn, trang ${n}`;img.loading='lazy';img.style.width=`${760*scale}px`;img.style.height=`${1060*scale}px`;
      session.url=URL.createObjectURL(new Blob([loaded.value],{type:'image/'+session.format}));img.src=session.url;stage.append(img);await img.decode();estimatedPixelBytes=img.naturalWidth*img.naturalHeight*4;
    }
  }
  const workMs=performance.now()-start;
  await frame();
  const ms=performance.now()-start,resources=performance.getEntriesByType('resource').filter(x=>x.startTime>=start&&x.name.startsWith(location.origin)).map(x=>({name:new URL(x.name).pathname,duration:x.duration,transferSize:x.transferSize,encodedBodySize:x.encodedBodySize,decodedBodySize:x.decodedBodySize}));
  resourcesForRequests(session.requestPaths,resources);
  const row={format:session.format,cache:session.condition,phase,round,page:n,scale,dpr:devicePixelRatio,ms,workMs,frameWaitMs:ms-workMs,visibilityStart,visibilityEnd:document.visibilityState,appCacheHit,
    transferBytes:resources.reduce((sum,x)=>sum+x.transferSize,0),resources,heapBeforeBytes:heapBefore,
    heapUsedBytes:performance.memory?.usedJSHeapSize??null,estimatedActivePixelBytes:estimatedPixelBytes};
  result.rows.push(row);$('page').textContent=`Trang ${n} / 4`;
  $('readout').textContent=`${labels[session.format]} · ${(scale*100).toFixed(0)}% · ${ms.toFixed(1)} ms · transfer ${row.transferBytes.toLocaleString()} bytes · ${appCacheHit?'cache phiên':'trang mới'}`;
  return row;
}
function update(){result.summary=summarize(result.rows.filter(x=>x.phase!=='manual'));$('raw').textContent=JSON.stringify(result,null,2);
  const table=document.createElement('table'),head=document.createElement('tr');
  for(const value of ['Định dạng','Cache','n','Trang đầu ms','Trang 2 ms','Quay lại ms','Transfer đầu bytes']){const th=document.createElement('th');th.textContent=value;head.append(th);}table.append(head);
  for(const r of result.summary){const tr=document.createElement('tr');for(const value of [labels[r.format],r.cache,r.samples,r.firstMs?.toFixed(1),r.nextMs?.toFixed(1),r.revisitMs?.toFixed(1),r.firstTransferBytes]){const td=document.createElement('td');td.textContent=value;tr.append(td);}table.append(tr);}$('summary').replaceChildren(table);
}
$('open').onclick=()=>action(async()=>{await fresh($('format').value,$('cache').value);await render(1);$('status').textContent='Đã mở. Chỉ trang hiện tại được dựng.';update();});
for(const [id,delta]of [['prev',-1],['next',1]])$(id).onclick=()=>action(async()=>{await render(Math.max(1,Math.min(4,page+delta)));update();});
function fitScale(){return Math.min(($('viewport').clientWidth-40)/760,($('viewport').clientHeight-40)/1060);}
$('zoom').onchange=()=>action(async()=>{scale=$('zoom').value==='fit'?fitScale():Number($('zoom').value);await render(page);update();});
$('fit').onclick=()=>action(async()=>{scale=fitScale();await render(page);$('zoom').value='fit';update();});
$('benchmark').onclick=()=>action(async()=>{
  const rounds=Number($('rounds').value);if(!Number.isInteger(rounds)||rounds<1||rounds>10)throw new Error('Số vòng phải từ 1 đến 10.');
  beginRun(result,new Date().toISOString());scale=1;$('zoom').value='1';await loadPDFLibrary();
  for(let round=1;round<=rounds;round++)for(const format of ['pdf','png','webp','avif','vector'])for(const cache of ['cold','warm']){
    $('status').textContent=`Đang đo vòng ${round}/${rounds}: ${format} ${cache}`;
    await fresh(format,cache);await render(1,'first',round);await render(2,'next',round);await render(1,'revisit',round);update();
  }
  result.finishedAt=new Date().toISOString();$('status').textContent=`PASS: ${result.rows.length} quan sát. Môi trường loopback, chưa phải WebView2/R2.`;update();
});
$('export').onclick=()=>{update();const url=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='audiotp-score-benchmark.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
await fetch('fixtures/manifest.json').then(x=>x.json()).then(x=>{result.fixture=x;}).catch(error=>{$('status').textContent=String(error);});
