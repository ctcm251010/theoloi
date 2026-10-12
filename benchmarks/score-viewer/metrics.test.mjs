import assert from 'node:assert/strict';
import {median,summarize,resourcesForRequests,beginRun} from './metrics.mjs';
assert.equal(median([7,1,3]),3);
assert.equal(median([10,2]),6);
assert.equal(median([null,undefined,NaN]),null);
const rows=[{format:'png',cache:'cold',phase:'first',ms:20,transferBytes:100,heapUsedBytes:null},
 {format:'png',cache:'cold',phase:'first',ms:40,transferBytes:200,heapUsedBytes:null},
 {format:'png',cache:'cold',phase:'next',ms:5},
 {format:'png',cache:'warm',phase:'first',ms:3,transferBytes:0,heapUsedBytes:null}];
const summary=summarize(rows);
assert.equal(summary[0].firstMs,30);assert.equal(summary[0].nextMs,5);
assert.equal(summary[0].heapUsedBytes,null);assert.equal(summary[0].firstTransferBytes,150);
assert.equal(summary[1].firstMs,3);assert.equal(summary[1].firstTransferBytes,0);
assert.throws(()=>resourcesForRequests(['/page.webp'],[]),/Missing resource timing/);
assert.throws(()=>resourcesForRequests(['/page.webp'],[{name:'/other.webp',transferSize:0}]),/Missing resource timing/);
assert.equal(resourcesForRequests(['/page.webp'],[{name:'/page.webp',transferSize:0}])[0].transferSize,0);
const state={rows:[1],finishedAt:'old run',lastError:'old error',environment:{}};
beginRun(state,'new run');assert.deepEqual(state.rows,[]);assert.equal(state.startedAt,'new run');assert.equal('finishedAt' in state,false);assert.equal('lastError' in state,false);
console.log('PASS metrics: medians, missing values, format/cache/phase separation');
