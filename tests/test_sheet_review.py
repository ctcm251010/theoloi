"""Identity review only: synthetic decisions never change production catalog/rights."""
import copy
import contextlib
import io
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from catalog_lib import load_json,json_text
from sheet_catalog import build_sheet_catalog,digest_json
from test_sheets import audio_fixture,snapshot_fixture
AVAILABLE=importlib.util.find_spec('sheet_review') is not None
if AVAILABLE:import sheet_review as lib


class SheetReviewTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE,'review library not implemented')
        self.audio=audio_fixture();self.catalog=build_sheet_catalog(snapshot_fixture(),self.audio)
        self.store=lib.new_store();self.sid='bookvn:vi:post:10';self.song=self.audio['songs']['main:1']['id']
    def decision(self,kind='approve',sid=None,song='default'):
        return {'sheetId':sid or self.sid,'songId':self.song if song=='default' else song,'decision':kind,
                'evidence':'Compared authorized title and musical identity; synthetic fixture',
                'reviewer':'Synthetic reviewer','provenance':'local-test:checked-by-human','reviewed':True}
    def batch(self,decisions=None,store=None):
        return {'schemaVersion':1,'catalogSha256':digest_json(self.catalog),'audioCatalogSha256':digest_json(self.audio),
                'baseRevision':(store or self.store)['revision'],'decisions':decisions or [self.decision()]}
    def apply(self,decisions=None,store=None):
        return lib.apply_batch(store or self.store,self.batch(decisions,store),self.catalog,self.audio)

    def test_approval_exports_identity_and_keeps_original_rights_and_catalog_bytes(self):
        before=json_text(self.catalog);s=self.apply();out=lib.export_verified(s,self.catalog,self.audio)
        self.assertEqual(len(out['links']),1);link=out['links'][0]
        self.assertEqual((link['sheetId'],link['songId'],link['status']),(self.sid,self.song,'verified'))
        self.assertEqual(link['usageRights']['status'],'restricted')
        self.assertFalse(any(link['usageRights']['permissions'].values()))
        self.assertEqual(before,json_text(self.catalog));self.assertEqual(self.store['events'],[])
        self.assertEqual(lib.validate_store(s),[])

    def test_reject_and_defer_suspend_prior_approval_and_preserve_history(self):
        for action in ('reject','defer'):
            with self.subTest(action=action):
                approved=self.apply();later=self.apply([self.decision(action)],approved)
                self.assertEqual(len(later['events']),2)
                self.assertEqual(lib.export_verified(later,self.catalog,self.audio)['links'],[])

    def test_unmatched_can_defer_without_inventing_audio_link(self):
        s=self.apply([self.decision('defer','bookvn:vi:post:11',None)])
        self.assertIsNone(s['events'][0]['songId'])
        for action in ('approve','reject'):
            with self.subTest(action=action),self.assertRaises(ValueError):self.apply([self.decision(action,song=None)])

    def test_unknown_ids_missing_evidence_unreviewed_and_rights_fields_fail(self):
        for field,value in [('sheetId','missing'),('songId','watv:vi:silent:19965'),('evidence',' '),
                            ('reviewer',''),('provenance',''),('reviewed',False),('usageRights',{'status':'confirmed'})]:
            d=self.decision();d[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.apply([d])
        self.assertEqual(self.store['events'],[])

    def test_batch_stale_revision_catalog_pin_and_invalid_last_row_are_atomic(self):
        for mode in ('revision','catalog','audio','last-row','duplicate'):
            b=self.batch()
            if mode=='revision':b['baseRevision']='0'*64
            if mode=='catalog':b['catalogSha256']='0'*64
            if mode=='audio':b['audioCatalogSha256']='0'*64
            if mode=='last-row':b['decisions'].append(self.decision(sid='missing'))
            if mode=='duplicate':b['decisions']*=2
            with self.subTest(mode=mode),self.assertRaises(ValueError):lib.apply_batch(self.store,b,self.catalog,self.audio)
            self.assertEqual(self.store['events'],[])

    def test_batch_limit_and_one_active_audio_per_source(self):
        b=self.batch([self.decision('defer',song=None)]*51)
        with self.assertRaises(ValueError):lib.apply_batch(self.store,b,self.catalog,self.audio)
        s=self.apply();other=self.audio['songs']['appendix:1']['id']
        with self.assertRaises(ValueError):self.apply([self.decision(song=other)],s)
        changed=self.apply([self.decision('reject'),self.decision(song=other)],s)
        self.assertEqual(lib.export_verified(changed,self.catalog,self.audio)['links'][0]['songId'],other)

    def test_stale_identity_blocks_export_but_rights_change_does_not_approve_rights(self):
        s=self.apply();changed=copy.deepcopy(self.catalog);changed['sheets'][self.sid]['edition']='new-unreviewed-edition'
        with self.assertRaises(ValueError):lib.export_verified(s,changed,self.audio)
        changed=copy.deepcopy(self.audio);changed['songs']['main:1']['title']='Changed identity'
        c=copy.deepcopy(self.catalog);c['audioCatalogSha256']=digest_json(changed)
        with self.assertRaises(ValueError):lib.export_verified(s,c,changed)
        changed=copy.deepcopy(self.catalog);changed['sheets'][self.sid]['usageRights']['evidence']='Different restrictive notice'
        out=lib.export_verified(s,changed,self.audio)
        self.assertEqual(out['links'][0]['usageRights']['status'],'restricted')

    def test_defer_cannot_bypass_explicit_reject_before_switching_songs(self):
        other=self.audio['songs']['appendix:1']['id'];approved=self.apply()
        deferred=self.apply([self.decision('defer')],approved)
        with self.assertRaises(ValueError):self.apply([self.decision(song=other)],deferred)
        with self.assertRaises(ValueError):self.apply([self.decision('defer'),self.decision(song=other)],approved)
        rejected=self.apply([self.decision('reject')],deferred)
        switched=self.apply([self.decision(song=other)],rejected)
        self.assertEqual(lib.export_verified(switched,self.catalog,self.audio)['links'][0]['songId'],other)

    def test_writer_lock_and_interrupted_atomic_replace_preserve_store(self):
        from sheet_pipeline import SheetLock
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            root=Path(folder);(root/'catalog').mkdir();(root/'reviews').mkdir()
            cat=root/'catalog/sheet-fixture.json';audio=root/'catalog/audio-fixture.json';store=root/'reviews/sheet-mapping-decisions.vi.json'
            cat.write_text(json_text(self.catalog),encoding='utf-8');audio.write_text(json_text(self.audio),encoding='utf-8')
            store.write_text(json_text(self.store),encoding='utf-8');before=store.read_bytes()
            argv=['decide','--root',str(root),'--catalog',str(cat),'--audio-catalog',str(audio),
                  '--sheet',self.sid,'--song',self.song,'--decision','approve','--evidence','Synthetic test evidence',
                  '--reviewer','Synthetic reviewer','--provenance','synthetic-test','--reviewed','--apply']
            with SheetLock(root/'reviews/sheet-review.lock'):
                run=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/review-mapping.py')]+argv,capture_output=True,text=True)
                self.assertEqual(run.returncode,1);self.assertEqual(store.read_bytes(),before)
            spec=importlib.util.spec_from_file_location('review_cli_test',ROOT/'scripts/review-mapping.py')
            cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
            with patch('sheet_paths.os.replace',side_effect=KeyboardInterrupt),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):cli.main(argv)
            self.assertEqual(store.read_bytes(),before)
            self.assertEqual(list((root/'reviews').glob('*.part')),[])
            # The interrupted owner released the OS lock; a later writer can apply.
            run=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'scripts/review-mapping.py')]+argv,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(len(load_json(store)['events']),1)

    def test_history_tamper_and_revision_tamper_fail(self):
        s=self.apply()
        for mode in ('evidence','chain','revision','sequence','timestamp'):
            bad=copy.deepcopy(s)
            if mode=='evidence':bad['events'][0]['evidence']='tampered'
            if mode=='chain':bad['events'][0]['previousHash']='a'*64
            if mode=='revision':bad['revision']='b'*64
            if mode=='sequence':bad['events'][0]['sequence']=4
            if mode=='timestamp':bad['events'][0]['createdAt']='not-a-date'
            with self.subTest(mode=mode):self.assertTrue(lib.validate_store(bad))
            with self.assertRaises(ValueError):lib.export_verified(bad,self.catalog,self.audio)

    def test_real_queue_prioritizes_464_and_ten_appendix_sources_without_approvals(self):
        c=load_json(ROOT/'catalog/sheet-sources.vi.json');a=load_json(ROOT/'catalog/catalog.vi.json')
        rows=lib.review_queue(self.store,c,a)['rows']
        self.assertEqual(len(rows),542)
        self.assertEqual((rows[0]['sourceGroup'],rows[0]['sourceNumber']),('main',464))
        self.assertTrue(all(r['priority']=='duplicate-title' for r in rows[1:11]))
        self.assertEqual(lib.export_verified(self.store,c,a)['links'],[])

    def test_many_sources_one_audio_stays_separate_and_high_confidence_is_not_approval(self):
        s=self.apply([self.decision('defer')]);self.assertEqual(lib.export_verified(s,self.catalog,self.audio)['links'],[])
        s=self.apply([self.decision(),self.decision(sid='bookvn:vi:post:12')])
        self.assertEqual(len(lib.export_verified(s,self.catalog,self.audio)['links']),2)

    def test_cli_dry_run_batch_confirm_export_and_protected_outputs(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            root=Path(folder);(root/'catalog').mkdir();(root/'reviews').mkdir()
            cat=root/'catalog/sheet-fixture.json';audio=root/'catalog/audio-fixture.json';batch=root/'reviews/sheet-review-batch.json'
            cat.write_text(json_text(self.catalog),encoding='utf-8');audio.write_text(json_text(self.audio),encoding='utf-8')
            batch.write_text(json_text(self.batch()),encoding='utf-8')
            base=[sys.executable,'-X','utf8',str(ROOT/'scripts/review-mapping.py')]
            common=['--root',str(root),'--catalog',str(cat),'--audio-catalog',str(audio)]
            def run(command,*args):return subprocess.run(base+[command]+common+list(args),capture_output=True,text=True,encoding='utf-8')
            r=run('batch','--input',str(batch));self.assertEqual(r.returncode,0,r.stderr)
            self.assertFalse((root/'reviews/sheet-mapping-decisions.vi.json').exists())
            r=run('batch','--input',str(batch),'--apply','--confirm-count','2');self.assertEqual(r.returncode,1)
            r=run('batch','--input',str(batch),'--apply','--confirm-count','1');self.assertEqual(r.returncode,0,r.stderr)
            store=root/'reviews/sheet-mapping-decisions.vi.json';before=store.read_bytes()
            r=run('export');self.assertEqual(r.returncode,0,r.stderr)
            out=load_json(root/'delivery/sheet-verified-mapping.vi.json');self.assertEqual(len(out['links']),1)
            r=run('queue');self.assertEqual(r.returncode,0,r.stderr)
            r=run('status');self.assertEqual(r.returncode,0,r.stderr)
            r=run('init');self.assertEqual(r.returncode,1);self.assertEqual(store.read_bytes(),before)
            r=run('export','--output',str(audio));self.assertEqual(r.returncode,1)
            # Hard-link alias cannot change protected data or store inputs.
            alias=root/'reviews/sheet-alias.json';alias.hardlink_to(audio)
            original=audio.read_bytes();r=run('init','--store',str(alias))
            self.assertEqual(r.returncode,1);self.assertEqual(audio.read_bytes(),original)

    def test_local_html_builder_requires_explicit_selection_and_escapes_untrusted_titles(self):
        self.assertIsNotNone(importlib.util.find_spec('sheet_review_html'),'HTML review generator missing')
        from sheet_review_html import render_review_html
        queue=lib.review_queue(self.store,self.catalog,self.audio)
        queue['rows'][0]['title']='</script><img src="https://example.invalid/leak">'
        html=render_review_html(queue)
        class Parser(HTMLParser):
            def __init__(self):super().__init__();self.scripts=[];self.current=None;self.images=0
            def handle_starttag(self,tag,attrs):
                if tag=='img':self.images+=1
                if tag=='script':self.current='';self.scripts.append(dict(attrs))
            def handle_data(self,data):
                if self.current is not None:self.current+=data
            def handle_endtag(self,tag):
                if tag=='script':self.scripts[-1]['body']=self.current;self.current=None
        parser=Parser();parser.feed(html)
        self.assertEqual(parser.images,0);self.assertEqual(len(parser.scripts),2)
        self.assertEqual(json.loads(parser.scripts[0]['body'])['rows'][0]['title'],queue['rows'][0]['title'])
        # Execute the real UI batch constructor in a JS engine, with no DOM/network.
        with tempfile.TemporaryDirectory() as folder:
            script=Path(folder)/'ui-test.js'
            script.write_text(parser.scripts[1]['body']+'\n'+f"const q={json.dumps(queue)}; const good={json.dumps(self.decision())};"+'''
const assert=require('node:assert/strict');
assert.throws(()=>AudioTPReview.buildBatch(q,[], 'Reviewer','Evidence ref'));
for(const change of [{reviewed:false},{evidence:''},{songId:'unknown'},{sheetId:'unknown'}]) {
  assert.throws(()=>AudioTPReview.buildBatch(q,[{...good,...change}], 'Reviewer','Evidence ref'));
}
assert.throws(()=>AudioTPReview.buildBatch(q,Array(51).fill(good), 'Reviewer','Evidence ref'));
const b=AudioTPReview.buildBatch(q,[good], 'Reviewer','Evidence ref');
assert.equal(b.decisions.length,1); assert.equal(b.decisions[0].reviewed,true);
assert.equal(b.baseRevision,q.baseRevision); assert.equal(b.decisions[0].decision,'approve');
console.log('UI batch constructor PASS');
''',encoding='utf-8')
            run=subprocess.run(['node',str(script)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)


if __name__=='__main__':unittest.main()
