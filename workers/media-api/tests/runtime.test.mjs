// Actual local workerd/R2 runtime. No real Cloudflare bucket or credentials.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {existsSync} from 'node:fs';
import {Miniflare,convertV4MiniflareOptions} from 'miniflare';

test('bundled Worker authenticates and streams a real M4A from isolated local workerd R2',{skip:!existsSync(new URL('../../../delivery/manifest.vi.json',import.meta.url)) || !existsSync(new URL('../../../tmp/worker-build/index.js',import.meta.url))?'Private manifest/media and prepared production bundle required':false},async t=>{
 const code='runtime-test-code-not-a-production-secret';
 const mf=new Miniflare(convertV4MiniflareOptions({rootPath:fileURLToPath(new URL("../../../",import.meta.url)),modules:true,scriptPath:fileURLToPath(new URL('../../../tmp/worker-build/index.js',import.meta.url)),compatibilityDate:'2026-10-12',compatibilityFlags:['nodejs_compat'],cf:false,host:'127.0.0.1',port:0,r2Buckets:['MEDIA'],r2Persist:false,bindings:{SERVING_ENABLED:'true',AUTH_EPOCH:'runtime-test',SIGNING_KEY:'runtime-test-signing-012345678901234567890',GROUP_CODE_SHA256:createHash('sha256').update(code).digest('hex'),ALLOWED_ORIGINS:'http://tauri.localhost',SESSION_SECONDS:'43200'},ratelimits:{LOGIN_LIMITER:{namespace_id:'1',simple:{limit:100,period:60}},REQUEST_LIMITER:{namespace_id:'2',simple:{limit:100,period:60}}}}));
 t.after(()=>mf.dispose());
 const manifest=JSON.parse(await readFile(new URL('../../../delivery/manifest.vi.json',import.meta.url),'utf8'));
 const a=manifest.assets['watv:vi:guide:4177'];const bytes=await readFile(new URL('../../../'+a.localPath,import.meta.url));
 const bucket=await mf.getR2Bucket('MEDIA');await bucket.put(a.objectKey,bytes,{httpMetadata:{contentType:'audio/mp4'},customMetadata:{sha256:a.sha256,'asset-id':a.assetId}});
 const login=await mf.dispatchFetch('https://runtime.test/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});assert.equal(login.status,200);const session=await login.json();
 const r=await mf.dispatchFetch('https://runtime.test/v1/play-tickets',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+session.token},body:JSON.stringify({assetId:a.assetId})});assert.equal(r.status,200);const ticket=await r.json();
 const url='https://runtime.test'+ticket.path+'?ticket='+ticket.ticket;
 const response=await mf.dispatchFetch(url,{headers:{Range:'bytes=0-1023'}});assert.equal(response.status,206);assert.equal(response.headers.get('Content-Range'),`bytes 0-1023/${bytes.length}`);assert.deepEqual(Buffer.from(await response.arrayBuffer()),bytes.subarray(0,1024));
 const head=await mf.dispatchFetch(url,{method:'HEAD'});assert.equal(head.status,200);assert.equal(Number(head.headers.get('Content-Length')),bytes.length);assert.equal(await head.text(),'');
 const invalid=await mf.dispatchFetch(url,{headers:{Range:'bytes=999999999-'}});assert.equal(invalid.status,416);
 const noTicket=await mf.dispatchFetch('https://runtime.test'+ticket.path);assert.equal(noTicket.status,401);
});
