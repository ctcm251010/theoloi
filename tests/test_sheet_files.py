"""Real local-file tests; fixtures are synthetic, never downloaded BookVN sheets."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import pymupdf
from pypdf import PdfWriter

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from catalog_lib import json_text,load_json
from sheet_catalog import build_sheet_catalog
from test_sheets import audio_fixture,snapshot_fixture

AVAILABLE=importlib.util.find_spec('sheet_pipeline') is not None
if AVAILABLE:
    import sheet_pipeline as lib
    from sheet_media import inspect_file


def local_catalog(audio):
    c=build_sheet_catalog(snapshot_fixture(),audio)
    row=copy.deepcopy(c['sheets']['bookvn:vi:post:10'])
    row.update(id='local:vi:fixture:1',provider='local',sourcePostId=None,sourcePageUrl=None,
               sourceGroup='local',sourceNumber=1,displayNumber=None,rawTitle='Synthetic sheet',
               title='Synthetic sheet',normalizedTitle='synthetic sheet',originalPdf=None,
               audioLinks=[],matchingStatus='unmatched',reviewIssues=[])
    row['usageRights']={'status':'confirmed','evidence':'Self-authored synthetic test fixture','evidenceUrl':None,
                        'permissions':{'store':True,'convert':True,'serve':False,'upload':False}}
    row['observedContent']={'inspectionStatus':'not-observed','format':'unknown','renderer':None,'pages':[],'pdfStatus':'not-observed'}
    c['sheets']={row['id']:row}
    return c


class SheetFileTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE,'local sheet file pipeline is not implemented')
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.inputs=self.root/'source/local-sheets'; self.inputs.mkdir(parents=True)
        self.audio=audio_fixture(); self.catalog=local_catalog(self.audio)
        writer=PdfWriter(); writer.add_blank_page(width=200,height=300)
        writer.add_metadata({'/Title':'Self-authored sample'})
        with (self.inputs/'original.pdf').open('wb') as f: writer.write(f)
        for name,color in [('red.png',(1,0,0)),('blue.png',(0,0,1))]:
            doc=pymupdf.open(); p=doc.new_page(width=24,height=36)
            p.draw_rect(p.rect,color=color,fill=color)
            p.get_pixmap().save(self.inputs/name);doc.close()
        self.state=self.root/'state/sheet-transfers.sqlite'
        self.manifest=self.root/'delivery/sheet-manifest.vi.json'

    def tearDown(self):
        if hasattr(self,'temp'): self.temp.cleanup()

    def plan(self,kind='original-pdf',inputs=None,edition='default'):
        if inputs is None: inputs=['source/local-sheets/original.pdf'] if kind=='original-pdf' else ['source/local-sheets/red.png','source/local-sheets/blue.png']
        return {'schemaVersion':1,'jobs':[{'sheetId':'local:vi:fixture:1','edition':edition,'kind':kind,'inputs':inputs}]}

    def process(self,plan=None,**kwargs):
        return lib.process_plan(plan or self.plan(),self.catalog,self.audio,self.root,**kwargs)

    def test_original_pdf_preserves_bytes_and_reports_integrity(self):
        result=self.process()
        self.assertEqual(result['counts']['completed'],1)
        m=load_json(self.manifest); item=next(iter(m['assets'].values())); f=item['files'][0]
        original=(self.inputs/'original.pdf').read_bytes()
        self.assertEqual((self.root/f['localPath']).read_bytes(),original)
        self.assertEqual(f['sha256'],hashlib.sha256(original).hexdigest())
        self.assertEqual(f['pageCount'],1)
        self.assertTrue(f['objectKey'].startswith('sheets/v1/local/vi/'))
        self.assertFalse(item['usageRights']['permissions']['upload'])
        self.assertEqual(lib.validate_manifest(m,self.catalog,self.audio,self.root),[])

    def test_images_to_pdf_preserves_page_order_pixels_and_dimensions(self):
        self.process(self.plan('image-derived-pdf'))
        item=next(iter(load_json(self.manifest)['assets'].values()))
        with pymupdf.open(self.root/item['files'][0]['localPath']) as doc:
            self.assertEqual(len(doc),2)
            for n,name in enumerate(['red.png','blue.png']):
                src=pymupdf.Pixmap(self.inputs/name)
                embedded=pymupdf.Pixmap(doc,doc[n].get_images()[0][0])
                self.assertEqual((embedded.width,embedded.height),(24,36))
                self.assertEqual(embedded.samples,src.samples)
        self.assertEqual(item['kind'],'image-derived-pdf')
        self.assertEqual([p['pageNumber'] for p in item['sourceFiles']],[1,2])

    def test_image_pages_keep_originals_and_page_order(self):
        self.process(self.plan('image-pages'))
        item=next(iter(load_json(self.manifest)['assets'].values()))
        self.assertEqual(len(item['files']),2)
        for n,name in enumerate(['red.png','blue.png'],1):
            self.assertEqual(item['files'][n-1]['pageNumber'],n)
            self.assertEqual((self.root/item['files'][n-1]['localPath']).read_bytes(),(self.inputs/name).read_bytes())

    def test_restricted_or_unknown_rights_fail_before_state_creation(self):
        for status in ('restricted','unknown'):
            self.catalog['sheets']['local:vi:fixture:1']['usageRights']['status']=status
            self.catalog['sheets']['local:vi:fixture:1']['usageRights']['permissions']={k:False for k in ('store','convert','serve','upload')}
            with self.assertRaises(ValueError): self.process()
            self.assertFalse(self.state.exists())
            self.assertFalse((self.root/'media').exists())

    def test_storage_permission_does_not_authorize_conversion(self):
        self.catalog['sheets']['local:vi:fixture:1']['usageRights']['permissions']['convert']=False
        with self.assertRaises(ValueError): self.process(self.plan('image-derived-pdf'))
        self.assertFalse(self.state.exists())

    def test_real_bookvn_catalog_is_not_eligible_for_processing(self):
        self.catalog=build_sheet_catalog(snapshot_fixture(),self.audio)
        p=self.plan();p['jobs'][0]['sheetId']='bookvn:vi:post:10'
        with self.assertRaises(ValueError): self.process(p)
        self.assertFalse(self.state.exists())

    def test_dry_run_creates_no_state_media_or_manifest(self):
        result=self.process(dry_run=True)
        self.assertTrue(result['dryRun'])
        self.assertFalse(self.state.exists()); self.assertFalse(self.manifest.exists())
        self.assertFalse((self.root/'media').exists())

    def test_dry_run_respects_resume_and_retry_selection_without_writing(self):
        self.process();before=self.state.read_bytes()
        dry=self.process(dry_run=True)
        self.assertEqual(dry['jobs'][0]['action'],'would-skip')
        retry=self.process(dry_run=True,retry_failed=True)
        self.assertEqual(retry['jobs'][0]['action'],'not-selected')
        self.assertEqual(before,self.state.read_bytes())

    def test_resume_skips_only_valid_completed_output(self):
        self.process()
        item=next(iter(load_json(self.manifest)['assets'].values())); output=self.root/item['files'][0]['localPath']
        before=output.stat().st_mtime_ns
        result=self.process()
        self.assertEqual(result['counts']['skipped'],1)
        self.assertEqual(output.stat().st_mtime_ns,before)
        output.write_bytes(b'corrupt')
        self.assertTrue(lib.validate_manifest(load_json(self.manifest),self.catalog,self.audio,self.root))
        repaired=self.process()
        self.assertEqual(repaired['counts']['skipped'],0)
        self.assertEqual(output.read_bytes(),(self.inputs/'original.pdf').read_bytes())

    def test_changed_input_rebuilds_and_retains_previous_artifact(self):
        self.process();old=next(iter(load_json(self.manifest)['assets'].values()))['files'][0]['localPath']
        writer=PdfWriter();writer.add_blank_page(width=100,height=200);writer.add_blank_page(width=100,height=200)
        with (self.inputs/'original.pdf').open('wb') as f: writer.write(f)
        result=self.process()
        self.assertEqual(result['counts']['skipped'],0)
        new=next(iter(load_json(self.manifest)['assets'].values()))['files'][0]
        self.assertNotEqual(new['localPath'],old);self.assertTrue((self.root/old).exists())
        self.assertEqual(new['pageCount'],2)

    def test_missing_input_fails_then_retry_failed_recovers(self):
        p=self.plan(inputs=['source/local-sheets/missing.pdf'])
        first=self.process(p)
        self.assertEqual(first['counts']['failed'],1)
        self.assertEqual(load_json(self.manifest)['assets'],{})
        (self.inputs/'missing.pdf').write_bytes((self.inputs/'original.pdf').read_bytes())
        retry=self.process(p,retry_failed=True)
        self.assertEqual(retry['counts']['completed'],1)
        self.assertEqual(retry['counts']['failed'],0)
        self.assertEqual(self.process(p,retry_failed=True)['counts']['processed'],0)

    def test_html_truncated_and_encrypted_pdf_are_rejected(self):
        (self.inputs/'html.pdf').write_bytes(b'<html>Please login</html>')
        (self.inputs/'truncated.pdf').write_bytes((self.inputs/'original.pdf').read_bytes()[:-20])
        w=PdfWriter();w.add_blank_page(width=10,height=10);w.encrypt('fixture-password')
        with (self.inputs/'encrypted.pdf').open('wb') as f:w.write(f)
        for name in ('html.pdf','truncated.pdf','encrypted.pdf'):
            with self.subTest(name=name),self.assertRaises(ValueError): inspect_file(self.inputs/name)

    def test_wrong_input_format_is_failed_not_completed(self):
        result=self.process(self.plan(inputs=['source/local-sheets/red.png']))
        self.assertEqual(result['counts']['failed'],1)
        self.assertEqual(load_json(self.manifest)['assets'],{})

    def test_progress_counts_all_attempted_jobs_including_later_missing_input(self):
        p=self.plan();p['jobs']+=self.plan(inputs=['source/local-sheets/missing.pdf'],edition='missing')['jobs']
        result=self.process(p)
        self.assertEqual(result['counts']['processed'],2)
        self.assertEqual(result['counts']['completed'],1)
        self.assertEqual(result['counts']['failed'],1)

    def test_cli_dry_run_process_resume_status_verify_and_failure_exit(self):
        catalog=self.root/'catalog.json';audio=self.root/'audio.json';plan=self.root/'plan.json'
        for p,data in [(catalog,self.catalog),(audio,self.audio),(plan,self.plan())]:p.write_text(json_text(data),encoding='utf-8')
        base=[sys.executable,'-X','utf8',str(ROOT/'scripts/sheet-files.py')]
        shared=['--root',str(self.root),'--catalog',str(catalog),'--audio-catalog',str(audio)]
        def run(args):return subprocess.run(base+args,capture_output=True,text=True,encoding='utf-8')
        dry=run(['process',*shared,'--plan',str(plan),'--dry-run'])
        self.assertEqual(dry.returncode,0,dry.stderr);self.assertFalse(self.state.exists())
        full=run(['process',*shared,'--plan',str(plan)])
        self.assertEqual(full.returncode,0,full.stderr)
        resumed=run(['process',*shared,'--plan',str(plan)])
        self.assertEqual(resumed.returncode,0,resumed.stderr);self.assertIn('skipped',resumed.stdout)
        status=run(['status','--root',str(self.root)])
        self.assertEqual(status.returncode,0,status.stderr)
        verify=run(['verify',*shared])
        self.assertEqual(verify.returncode,0,verify.stderr)
        plan.write_text(json_text(self.plan(inputs=['source/local-sheets/missing.pdf'],edition='missing')),encoding='utf-8')
        failed=run(['process',*shared,'--plan',str(plan)])
        self.assertEqual(failed.returncode,1,failed.stderr)

    def test_empty_manifest_reports_no_file_and_cannot_erase_populated_manifest(self):
        m=lib.build_manifest(self.catalog,self.audio,{})
        self.assertEqual(m['availability']['local:vi:fixture:1'],{'status':'no-file','assetIds':[]})
        self.assertEqual(lib.validate_manifest(m,self.catalog,self.audio,self.root),[])
        self.process();before=self.manifest.read_bytes()
        catalog=self.root/'catalog.json';audio=self.root/'audio.json'
        catalog.write_text(json_text(self.catalog),encoding='utf-8');audio.write_text(json_text(self.audio),encoding='utf-8')
        run=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/sheet-files.py'),'init-manifest','--root',str(self.root),
                            '--catalog',str(catalog),'--audio-catalog',str(audio)],capture_output=True,text=True)
        self.assertEqual(run.returncode,1)
        self.assertEqual(before,self.manifest.read_bytes())

    def test_existing_foreign_state_is_preserved_and_rejected(self):
        self.state.parent.mkdir(parents=True)
        db=sqlite3.connect(self.state)
        try:db.execute('CREATE TABLE unrelated(value TEXT)');db.commit()
        finally:db.close()
        before=self.state.read_bytes()
        with self.assertRaises(ValueError):self.process()
        self.assertEqual(before,self.state.read_bytes())

    def test_synthetic_demo_cli_creates_no_bookvn_files_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            root=Path(folder)
            command=[sys.executable,'-X','utf8',str(ROOT/'scripts/make-sheet-demo.py'),'--root',str(root)]
            result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(result.returncode,0,result.stderr)
            demo=root/'tmp/sheets-demo/sample-01'
            catalog=load_json(demo/'catalog/sheet-demo.json')
            self.assertEqual({s['provider'] for s in catalog['sheets'].values()},{'local'})
            self.assertEqual(inspect_file(demo/'source/local-sheets/original.pdf')['pageCount'],2)
            before=(demo/'source/local-sheets/original.pdf').read_bytes()
            again=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(again.returncode,1)
            self.assertEqual(before,(demo/'source/local-sheets/original.pdf').read_bytes())

    def test_unsafe_paths_secret_inputs_and_edition_are_rejected(self):
        for path in ('../source/local-sheets/original.pdf','source/local-sheets/../../.secrets/r2.env','C:/x.pdf','//host/x.pdf','.secrets/r2.env','source/local-sheets/NUL.pdf'):
            with self.subTest(path=path),self.assertRaises(ValueError): self.process(self.plan(inputs=[path]))
        for edition in ('../x','default/../../audio','CON','bad.','a:b'):
            with self.subTest(edition=edition),self.assertRaises(ValueError): self.process(self.plan(edition=edition))
        self.assertFalse(self.state.exists())

    def test_state_and_manifest_cannot_overwrite_audio_or_credential(self):
        for arg,path in [('state_path',self.root/'state/transfers.sqlite'),('manifest_path',self.root/'delivery/manifest.vi.json'),('state_path',self.root/'.secrets/r2.env')]:
            with self.subTest(arg=arg,path=path),self.assertRaises(ValueError): self.process(**{arg:path})
        self.assertFalse(self.state.exists())

    def test_duplicate_jobs_and_unknown_sheet_are_rejected(self):
        p=self.plan();p['jobs']*=2
        with self.assertRaises(ValueError):self.process(p)
        p=self.plan();p['jobs'][0]['sheetId']='local:vi:missing:1'
        with self.assertRaises(ValueError):self.process(p)

    def test_two_editions_do_not_collide(self):
        p=self.plan();p['jobs']+=self.plan(edition='second')['jobs']
        self.process(p)
        items=list(load_json(self.manifest)['assets'].values())
        self.assertEqual(len(items),2)
        self.assertNotEqual(items[0]['files'][0]['localPath'],items[1]['files'][0]['localPath'])

    def test_manifest_summary_reports_identical_bytes_without_merging_editions(self):
        p=self.plan();p['jobs']+=self.plan(edition='second')['jobs']
        self.process(p)
        summary=lib.manifest_file_summary(load_json(self.manifest))
        self.assertEqual((summary['files'],summary['uniqueSha256']),(2,1))
        self.assertEqual(len(summary['duplicateHashes']),1)
        self.assertEqual(len(summary['duplicateHashes'][0]['occurrences']),2)

    def test_later_subset_plan_preserves_previous_edition_in_manifest(self):
        self.process()
        self.process(self.plan(edition='second'))
        items=list(load_json(self.manifest)['assets'].values())
        self.assertEqual({x['edition'] for x in items},{'default','second'})

    def test_failed_update_retains_last_valid_manifest_artifact(self):
        self.process();before=load_json(self.manifest)['assets']
        (self.inputs/'original.pdf').unlink()
        self.assertEqual(self.process()['counts']['failed'],1)
        self.assertEqual(load_json(self.manifest)['assets'],before)
        self.assertEqual(lib.validate_manifest(load_json(self.manifest),self.catalog,self.audio,self.root),[])

    def test_populated_manifest_cannot_be_replaced_from_fresh_state(self):
        self.process();before=self.manifest.read_bytes()
        other=self.root/'state/sheet-other.sqlite'
        with self.assertRaises(ValueError):self.process(state_path=other)
        self.assertFalse(other.exists())
        self.assertEqual(self.manifest.read_bytes(),before)

    def test_malformed_stored_artifact_is_rejected_without_state_or_manifest_changes(self):
        self.process()
        for broken in ('null','{}','not-json'):
            with self.subTest(broken=broken):
                db=sqlite3.connect(self.state)
                try:db.execute('UPDATE sheet_jobs SET artifact_json=?',(broken,));db.commit()
                finally:db.close()
                before=self.state.read_bytes();manifest=self.manifest.read_bytes()
                with self.assertRaises(ValueError):self.process()
                self.assertEqual(self.state.read_bytes(),before)
                self.assertEqual(self.manifest.read_bytes(),manifest)

    def test_manifest_rejects_hash_key_rights_and_audio_tampering(self):
        self.process();m=load_json(self.manifest)
        for mutation in ('key','hash','rights','link','availability','outside'):
            with self.subTest(mutation=mutation):
                bad=copy.deepcopy(m);item=next(iter(bad['assets'].values()))
                if mutation=='key':item['files'][0]['objectKey']='audio/evil.m4a'
                if mutation=='hash':item['files'][0]['sha256']='0'*64
                if mutation=='rights':item['usageRights']['permissions']['serve']=True
                if mutation=='link':item['audioLinks']=[{'songId':'not-a-song'}]
                if mutation=='availability':bad['availability']={}
                if mutation=='outside':item['files'][0]['localPath']='../outside.pdf'
                self.assertTrue(lib.validate_manifest(bad,self.catalog,self.audio,self.root))

    def test_status_read_only_and_lock_prevents_overlapping_writers(self):
        self.assertEqual(lib.read_status(self.state)['counts']['total'],0)
        self.assertFalse(self.state.exists())
        with lib.SheetLock(self.root/'state/sheet-processing.lock'):
            with self.assertRaises(ValueError):self.process()
        self.assertEqual(self.process()['counts']['completed'],1)

    def test_junction_input_is_rejected(self):
        if sys.platform!='win32':self.skipTest('Windows junction test')
        outside=self.root/'outside';outside.mkdir();(outside/'original.pdf').write_bytes((self.inputs/'original.pdf').read_bytes())
        junction=self.inputs/'alias'
        created=subprocess.run(['cmd','/c','mklink','/J',str(junction),str(outside)],capture_output=True)
        self.assertEqual(created.returncode,0,created.stderr)
        try:
            with self.assertRaises(ValueError):self.process(self.plan(inputs=['source/local-sheets/alias/original.pdf']))
        finally:junction.rmdir()


if __name__=='__main__':unittest.main()
