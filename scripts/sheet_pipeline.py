"""Offline, rights-gated local sheet processing. No network or cloud clients."""
import copy
import json
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from jsonschema import Draft202012Validator
from catalog_lib import ROOT,load_json,json_text
from sheet_catalog import SCHEMA,digest_json,validate_sheet_catalog
from sheet_media import inspect_file,images_to_pdf
from sheet_paths import plain_path,project_root,relative_input,output_path,sha256_file,write_json


def schema_errors(value,name):
    return [f'{list(e.absolute_path)}: {e.message}' for e in Draft202012Validator(load_json(ROOT/'schemas'/name)).iter_errors(value)]


class SheetLock:
    def __init__(self,path): self.path=Path(path);self.stream=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        stream=self.path.open('a+b')
        if stream.tell()==0:stream.write(b'0');stream.flush()
        stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            stream.close();raise ValueError('Another sheet process holds the lock') from exc
        self.stream=stream;return self
    def __exit__(self,*args):
        if self.stream:
            self.stream.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(),fcntl.LOCK_UN)
            self.stream.close();self.stream=None


def job_id(job): return ':'.join([job['sheetId'],job['edition'],job['kind']])


def require_rights(row,kind):
    rights=row['usageRights']
    if rights['status']!='confirmed' or not (rights['evidence'] or '').strip() or not rights['permissions']['store']:
        raise ValueError(f"{row['id']}: explicit confirmed storage rights required")
    if kind=='image-derived-pdf' and not rights['permissions']['convert']:
        raise ValueError(f"{row['id']}: conversion permission required")


def validate_plan(plan,catalog,audio,root):
    errors=schema_errors(plan,'sheet-plan.schema.json')+validate_sheet_catalog(catalog,audio,load_json(SCHEMA))
    if errors: raise ValueError('\n'.join(errors))
    seen=set()
    for job in plan['jobs']:
        jid=job_id(job)
        if jid in seen:raise ValueError('Duplicate job ID')
        seen.add(jid)
        if job['sheetId'] not in catalog['sheets']:raise ValueError('Unknown sheet ID')
        require_rights(catalog['sheets'][job['sheetId']],job['kind'])
        plain_path(Path('media/sheets')/job['edition'],root)
        for value in job['inputs']:relative_input(value,root)


def file_location(row,edition,kind,info):
    source=f"post-{row['sourcePostId']}" if row['sourcePostId'] is not None else digest_json(row['id'])
    key=f"sheets/v1/{row['provider']}/{row['locale']}/{source}/{edition}/{kind}/{info['sha256']}{info['extension']}"
    return 'media/'+key,key


def fingerprint(job,sources,rights):
    return digest_json({'job':job,'sourceFiles':sources,'usageRights':rights})


def inspect_inputs(job,root):
    infos=[]
    for n,value in enumerate(job['inputs'],1):
        info=inspect_file(relative_input(value,root))
        if job['kind']=='original-pdf' and info['mediaType']!='application/pdf':raise ValueError('original-pdf requires a PDF input')
        if job['kind']!='original-pdf' and not info['mediaType'].startswith('image/'):
            raise ValueError('Image operation requires PNG/JPEG inputs')
        infos.append(dict(info,localPath=value,pageNumber=n))
    return infos


def artifact_errors(item,row,root):
    errors=[]
    try:
        require_rights(row,item['kind'])
        if item['usageRights']!=row['usageRights'] or item['audioLinks']!=row['audioLinks']:
            raise ValueError('Manifest rights/audio links differ from catalog')
        job={'sheetId':item['sheetId'],'edition':item['edition'],'kind':item['kind'],
             'inputs':[x['localPath'] for x in item['sourceFiles']]}
        if item['jobId']!=job_id(job) or item['inputFingerprint']!=fingerprint(job,item['sourceFiles'],row['usageRights']):
            raise ValueError('Job/fingerprint differs')
        plain_path(Path('media/sheets')/item['edition'],root)
        for i,source in enumerate(item['sourceFiles'],1):
            relative_input(source['localPath'],root)
            if source['pageNumber']!=i:raise ValueError('Source page order differs')
        files=item['files'];sources=item['sourceFiles']
        if item['kind']=='original-pdf' and (len(files)!=1 or len(sources)!=1 or sources[0]['mediaType']!='application/pdf'):
            raise ValueError('Original PDF shape differs')
        if item['kind']=='image-derived-pdf' and (len(files)!=1 or files[0]['pageCount']!=len(sources) or any(not s['mediaType'].startswith('image/') for s in sources)):
            raise ValueError('Derived PDF page/source shape differs')
        if item['kind']=='image-pages' and len(files)!=len(sources):raise ValueError('Image page count differs')
        for i,file in enumerate(files,1):
            expected_local,key=file_location(row,item['edition'],item['kind'],file)
            if file['localPath']!=expected_local or file['objectKey']!=key or file['pageNumber']!=i:
                raise ValueError('File identity/path/key/order differs')
            path=output_path(file['localPath'],root,'media/sheets',file['extension'])
            actual=inspect_file(path)
            if any(file[k]!=v for k,v in actual.items()):raise ValueError('Output size/hash/format differs')
            if item['kind'] in ('original-pdf','image-derived-pdf') and actual['mediaType']!='application/pdf':raise ValueError('Output is not PDF')
            if item['kind']=='image-pages' and not actual['mediaType'].startswith('image/'):raise ValueError('Output is not image')
            if item['kind']!='image-derived-pdf' and (file['sha256'],file['bytes'])!=(sources[i-1]['sha256'],sources[i-1]['bytes']):
                raise ValueError('Original bytes were not preserved')
    except (OSError,ValueError,KeyError,TypeError) as exc:errors.append(str(exc))
    return errors


def build_manifest(catalog,audio,assets):
    assets=dict(sorted(assets.items()))
    availability={sid:{'status':'no-file','assetIds':[]} for sid in catalog['sheets']}
    for jid,item in assets.items():
        availability[item['sheetId']]['status']='available'
        availability[item['sheetId']]['assetIds'].append(jid)
    result={'schemaVersion':1,'sheetCatalogSha256':digest_json(catalog),'audioCatalogSha256':digest_json(audio),
            'assets':assets,'availability':availability}
    result['revision']=digest_json(result)
    return result


def validate_manifest(manifest,catalog,audio,root):
    errors=schema_errors(manifest,'sheet-manifest.schema.json')
    if errors:return errors
    errors+=validate_sheet_catalog(catalog,audio,load_json(SCHEMA))
    if manifest['sheetCatalogSha256']!=digest_json(catalog) or manifest['audioCatalogSha256']!=digest_json(audio):errors.append('Catalog pin differs')
    body={k:v for k,v in manifest.items() if k!='revision'}
    if manifest['revision']!=digest_json(body):errors.append('Manifest revision differs')
    for jid,item in manifest['assets'].items():
        if jid!=item['jobId'] or item['sheetId'] not in catalog['sheets']:errors.append('Unknown manifest identity');continue
        errors+=artifact_errors(item,catalog['sheets'][item['sheetId']],root)
    try:
        if manifest['availability']!=build_manifest(catalog,audio,manifest['assets'])['availability']:
            errors.append('Availability differs from completed assets')
    except (KeyError,TypeError) as exc:errors.append(f'Invalid availability: {exc}')
    return errors


def manifest_file_summary(manifest):
    by_hash={};total=0
    for jid,item in manifest['assets'].items():
        for file in item['files']:
            total+=1
            by_hash.setdefault(file['sha256'],[]).append({'jobId':jid,'pageNumber':file['pageNumber'],'objectKey':file['objectKey']})
    return {'files':total,'uniqueSha256':len(by_hash),
            'duplicateHashes':[{'sha256':h,'occurrences':items} for h,items in sorted(by_hash.items()) if len(items)>1]}


STATE_APP_ID=0x41545348


def _state_rows(path):
    """Read only, including identity checks before any writable connection."""
    if not Path(path).exists():return []
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    try:
        if db.execute('PRAGMA application_id').fetchone()[0]!=STATE_APP_ID or db.execute('PRAGMA user_version').fetchone()[0]!=1:
            raise ValueError('Not an AudioTP sheet state database; existing file preserved')
        if db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Sheet state integrity check failed')
        db.row_factory=sqlite3.Row
        rows=[dict(r) for r in db.execute('SELECT * FROM sheet_jobs ORDER BY job_id')]
        if any(r['status'] not in ('completed','failed','pending') for r in rows):raise ValueError('Unknown sheet state status')
        schema=load_json(ROOT/'schemas/sheet-manifest.schema.json')
        validator=Draft202012Validator({'$ref':'#/$defs/asset','$defs':schema['$defs']})
        for row in rows:
            if not row['job_id'] or not row['sheet_id'] or not isinstance(row['attempts'],int) or row['attempts']<0:
                raise ValueError('Invalid sheet state row')
            if row['artifact_json'] is None:
                if row['status']=='completed':raise ValueError('Completed sheet state has no artifact')
                continue
            try:item=json.loads(row['artifact_json'])
            except (ValueError,TypeError) as exc:raise ValueError('Malformed stored sheet artifact; state preserved') from exc
            if not validator.is_valid(item):raise ValueError('Invalid stored sheet artifact schema; state preserved')
            if item['jobId']!=row['job_id'] or item['sheetId']!=row['sheet_id'] or item['inputFingerprint']!=row['fingerprint']:
                raise ValueError('Stored sheet artifact identity/fingerprint differs; state preserved')
        return rows
    except sqlite3.Error as exc:raise ValueError(f'Invalid sheet state: {exc}') from exc
    finally:db.close()


def _connect(path):
    exists=Path(path).exists()
    if exists:_state_rows(path)
    db=sqlite3.connect(path,timeout=5);db.row_factory=sqlite3.Row
    try:
        if not exists:
            db.execute('CREATE TABLE sheet_jobs (job_id TEXT PRIMARY KEY, sheet_id TEXT NOT NULL, status TEXT NOT NULL, fingerprint TEXT, attempts INTEGER NOT NULL DEFAULT 0, error TEXT, artifact_json TEXT)')
            db.execute(f'PRAGMA application_id={STATE_APP_ID}')
            db.execute('PRAGMA user_version=1')
            db.commit()
        return db
    except BaseException:db.close();raise


def read_status(path):
    path=Path(path)
    counts={'total':0,'completed':0,'failed':0,'pending':0,'remaining':0}
    rows=[{k:r[k] for k in ('job_id','sheet_id','status','attempts','error')} for r in _state_rows(path)]
    for row in rows:counts[row['status']]+=1
    counts['total']=len(rows);counts['remaining']=counts['failed']+counts['pending']
    return {'counts':counts,'jobs':rows,'stateFile':str(path)}


def _publish(job,row,sources,root):
    tmp_root=output_path('tmp/sheets/staging',root,'tmp/sheets','')
    tmp_root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sheet-',dir=tmp_root) as folder:
        staging=Path(folder)
        inputs=[relative_input(x,root) for x in job['inputs']]
        if job['kind']=='image-derived-pdf':
            outputs=[staging/'derived.pdf'];images_to_pdf(inputs,outputs[0])
        else:
            outputs=[]
            for n,path in enumerate(inputs,1):
                dest=staging/f'page-{n}{sources[n-1]["extension"]}'
                shutil.copyfile(path,dest);outputs.append(dest)
        infos=[inspect_file(p) for p in outputs]
        if inspect_inputs(job,root)!=sources:raise ValueError('Inputs changed during processing')
        files=[]
        for n,(path,info) in enumerate(zip(outputs,infos),1):
            local,key=file_location(row,job['edition'],job['kind'],info)
            destination=output_path(local,root,'media/sheets',info['extension'])
            destination.parent.mkdir(parents=True,exist_ok=True)
            plain_path(destination,root)
            valid_existing=False
            if destination.exists():
                try:valid_existing=inspect_file(destination)==info
                except (OSError,ValueError):pass
            if not valid_existing:os.replace(path,destination)
            files.append(dict(info,localPath=local,objectKey=key,pageNumber=n))
        item={'jobId':job_id(job),'sheetId':row['id'],'edition':job['edition'],'kind':job['kind'],
              'inputFingerprint':fingerprint(job,sources,row['usageRights']),'files':files,'sourceFiles':sources,
              'usageRights':copy.deepcopy(row['usageRights']),'audioLinks':copy.deepcopy(row['audioLinks'])}
        errors=artifact_errors(item,row,root)
        if errors:raise ValueError('; '.join(errors))
        return item


def _check_existing_manifest(path,state_rows,catalog):
    """Do not silently replace a populated manifest using unrelated/lost state."""
    if not path.exists():return
    existing=load_json(path)
    errors=schema_errors(existing,'sheet-manifest.schema.json')
    if errors:raise ValueError('Existing sheet manifest is invalid; restore it before processing: '+'; '.join(errors))
    stored={r['job_id']:r for r in state_rows}
    for jid,item in existing['assets'].items():
        if item['sheetId'] not in catalog['sheets']:
            raise ValueError('Existing manifest contains a sheet outside this catalog; use its matching catalog/state')
        if jid not in stored or not stored[jid]['artifact_json']:
            raise ValueError('Existing manifest has assets absent from state; restore matching sheet state or use a separate manifest')


def process_plan(plan,catalog,audio,root,state_path=None,manifest_path=None,dry_run=False,retry_failed=False,progress=None):
    root=project_root(root)
    state=output_path(state_path or 'state/sheet-transfers.sqlite',root,'state','.sqlite')
    manifest_path=output_path(manifest_path or 'delivery/sheet-manifest.vi.json',root,'delivery','.json')
    lock_path=output_path('state/sheet-processing.lock',root,'state','.lock')
    validate_plan(plan,catalog,audio,root)
    if dry_run:
        stored={r['job_id']:r for r in _state_rows(state)}
        _check_existing_manifest(manifest_path,list(stored.values()),catalog)
        checks=[]
        for job in plan['jobs']:
            old=stored.get(job_id(job));row=catalog['sheets'][job['sheetId']]
            if retry_failed and (old is None or old['status']!='failed'):
                checks.append({'jobId':job_id(job),'action':'not-selected'});continue
            try:
                sources=inspect_inputs(job,root);action='would-process'
                if old and old['status']=='completed' and old['fingerprint']==fingerprint(job,sources,row['usageRights']):
                    item=json.loads(old['artifact_json']);item['audioLinks']=copy.deepcopy(row['audioLinks'])
                    if not artifact_errors(item,row,root):action='would-skip'
                checks.append({'jobId':job_id(job),'action':action})
            except (OSError,ValueError) as exc:checks.append({'jobId':job_id(job),'action':'would-fail','error':str(exc)})
        return {'dryRun':True,'jobs':checks,'counts':{'planned':len(checks),'failed':sum(c['action']=='would-fail' for c in checks)}}
    skipped=processed=0
    with SheetLock(lock_path):
        _check_existing_manifest(manifest_path,_state_rows(state),catalog)
        state.parent.mkdir(parents=True,exist_ok=True)
        db=_connect(state)
        try:
            for job in plan['jobs']:
                db.execute('INSERT OR IGNORE INTO sheet_jobs(job_id,sheet_id,status) VALUES(?,?,?)',(job_id(job),job['sheetId'],'pending'))
            db.commit()
            for n,job in enumerate(plan['jobs'],1):
                jid=job_id(job);row=catalog['sheets'][job['sheetId']]
                old=dict(db.execute('SELECT * FROM sheet_jobs WHERE job_id=?',(jid,)).fetchone())
                if retry_failed and old['status']!='failed':continue
                attempted=False
                try:
                    sources=inspect_inputs(job,root);fp=fingerprint(job,sources,row['usageRights'])
                    if old['status']=='completed' and old['fingerprint']==fp:
                        item=json.loads(old['artifact_json'])
                        item['audioLinks']=copy.deepcopy(row['audioLinks'])
                        if not artifact_errors(item,row,root):
                            skipped+=1
                            if progress:progress(n,len(plan['jobs']),jid,'skipped')
                            continue
                    processed+=1;attempted=True
                    item=_publish(job,row,sources,root)
                    db.execute('UPDATE sheet_jobs SET status=?,fingerprint=?,attempts=attempts+1,error=NULL,artifact_json=? WHERE job_id=?',
                               ('completed',fp,json_text(item),jid))
                    outcome='completed'
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    if not attempted:processed+=1
                    db.execute('UPDATE sheet_jobs SET status=?,attempts=attempts+1,error=? WHERE job_id=?',('failed',str(exc)[:700],jid))
                    outcome='failed'
                db.commit()
                if progress:progress(n,len(plan['jobs']),jid,outcome)
            assets={}
            current_ids={job_id(j) for j in plan['jobs']}
            for stored in list(db.execute('SELECT * FROM sheet_jobs ORDER BY job_id')):
                if stored['sheet_id'] not in catalog['sheets'] or not stored['artifact_json']:continue
                try:
                    item=json.loads(stored['artifact_json']);row=catalog['sheets'][stored['sheet_id']]
                    if item['jobId']!=stored['job_id'] or item['sheetId']!=stored['sheet_id']:
                        raise ValueError('Stored artifact identity differs')
                    item['audioLinks']=copy.deepcopy(row['audioLinks'])
                    errors=artifact_errors(item,row,root)
                except (ValueError,KeyError,TypeError) as exc:errors=[f'Invalid stored artifact: {exc}']
                if errors:
                    db.execute("UPDATE sheet_jobs SET status='failed',error=? WHERE job_id=?",('; '.join(errors)[:700],stored['job_id']))
                else:assets[item['jobId']]=item
            db.commit()
            manifest=build_manifest(catalog,audio,assets)
            errors=validate_manifest(manifest,catalog,audio,root)
            if errors:raise ValueError('; '.join(errors))
            write_json(manifest_path,manifest,root)
            states=[r['status'] for r in db.execute('SELECT job_id,status FROM sheet_jobs') if r['job_id'] in current_ids]
            counts={s:states.count(s) for s in ('completed','failed','pending')}
            counts.update(remaining=counts['failed']+counts['pending'],total=len(states),skipped=skipped,processed=processed)
            return {'dryRun':False,'counts':counts,'manifestPath':str(manifest_path),'stateFile':str(state)}
        finally:db.close()
