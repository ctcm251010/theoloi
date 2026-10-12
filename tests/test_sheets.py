"""Offline matching tests: a changed number/title/permission must affect the result."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from catalog_lib import json_text, load_json

AVAILABLE = importlib.util.find_spec('sheet_catalog') is not None
if AVAILABLE:
    import sheet_catalog as lib


def audio_fixture():
    return {'songs': {
        'main:1': {'id': 'watv:vi:newsong:main:1', 'section': 'main', 'number': 1, 'title': 'Ngày Thật Tôn Quý'},
        'main:2': {'id': 'watv:vi:newsong:main:2', 'section': 'main', 'number': 2, 'title': 'Bài thứ hai'},
        'appendix:1': {'id': 'watv:vi:newsong:appendix:1', 'section': 'appendix', 'number': 1, 'title': 'Bây giờ Nước Thiên Đàng sắp kíp!'}}, 'meditations': {}}


def snapshot_fixture():
    return {'schemaVersion': 1, 'provider': 'bookvn', 'locale': 'vi', 'observedDate': '2026-10-12',
            'captureMethod': 'retained-browser-dom-metadata', 'scope': 'observed-category-pages-only',
            'catalogPages': [{'url': 'https://bookvn.net/category/newsong/', 'count': 3}],
            'notice': {'text': 'Cấm tải về, chụp, phân phát mọi tài liệu.', 'evidenceUrl': 'https://bookvn.net/category/newsong/'},
            'records': [
                {'postId': 10, 'pageUrl': 'https://bookvn.net/newsong/newsong1/', 'rawTitle': '1. Ngày Thật Tôn Quy\u0301'},
                {'postId': 11, 'pageUrl': 'https://bookvn.net/newsong/newsong-appendix1/', 'rawTitle': '1. Bài khác hoàn toàn'},
                {'postId': 12, 'pageUrl': 'https://bookvn.net/newsong/newsong-appx005/', 'rawTitle': 'Bây giờ Nước Thiên Đàng sắp kíp!'}],
            'observations': [{'postId': 10, 'pageUrl': 'https://bookvn.net/newsong/newsong1/', 'format': 'image-pages',
                              'renderer': 'css-background-image', 'pages': [{'pageNumber': 1, 'sourceUrl': 'https://bookvn.net/wp-content/uploads/2023/02/nsv-001-1.png', 'mediaType': 'image/png'}],
                              'pdfStatus': 'not-found-in-observed-dom'}], 'anomalies': []}


class SheetCatalogTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE, 'sheet catalog/matcher is not implemented')
        self.audio = audio_fixture()
        self.snapshot = snapshot_fixture()

    def build(self):
        return lib.build_sheet_catalog(self.snapshot, self.audio)

    def test_unicode_whitespace_title_normalization_preserves_accents(self):
        self.assertEqual(lib.normalize_title('  Ngày\u00a0Thật  Tôn Quy\u0301\n'), 'ngày thật tôn quý')
        self.assertNotEqual(lib.normalize_title('Quý'), lib.normalize_title('Quy'))

    def test_main_matches_number_and_title_without_source_order(self):
        c = self.build()
        link = c['sheets']['bookvn:vi:post:10']['audioLinks'][0]
        self.assertEqual(link['songId'], 'watv:vi:newsong:main:1')
        self.assertEqual(link['verificationStatus'], 'needs-review')
        self.assertGreater(link['confidence'], .9)
        self.snapshot['records'].reverse()
        self.assertEqual(json_text(self.build()['sheets']), json_text(c['sheets']))

    def test_equal_appendix_number_does_not_join_different_title(self):
        row = self.build()['sheets']['bookvn:vi:post:11']
        self.assertEqual(row['matchingStatus'], 'unmatched')
        self.assertEqual(row['audioLinks'], [])

    def test_appx_matches_title_despite_different_number(self):
        row = self.build()['sheets']['bookvn:vi:post:12']
        self.assertEqual(row['sourceNumber'], 5)
        self.assertIsNone(row['displayNumber'])
        self.assertEqual(row['audioLinks'][0]['songId'], 'watv:vi:newsong:appendix:1')
        self.assertIn('appendix-number-not-a-join-key', row['audioLinks'][0]['evidence'])

    def test_title_number_conflict_is_not_a_verified_match(self):
        self.snapshot['records'][0]['rawTitle'] = '1. Bài thứ hai'
        row = self.build()['sheets']['bookvn:vi:post:10']
        self.assertEqual(row['matchingStatus'], 'conflict')
        self.assertIn('number-title-disagree', row['reviewIssues'])
        self.assertTrue(all(l['verificationStatus'] == 'needs-review' for l in row['audioLinks']))

    def test_multiple_audio_titles_produce_ambiguous_candidates(self):
        self.audio['songs']['appendix:2'] = {'id': 'watv:vi:newsong:appendix:2', 'section': 'appendix', 'number': 2,
                                           'title': self.audio['songs']['appendix:1']['title']}
        row = self.build()['sheets']['bookvn:vi:post:12']
        self.assertEqual(row['matchingStatus'], 'ambiguous')
        self.assertEqual(len(row['audioLinks']), 2)

    def test_uninspected_records_do_not_inherit_sample_pages(self):
        c = self.build()
        row = c['sheets']['bookvn:vi:post:12']
        self.assertEqual(row['observedContent']['inspectionStatus'], 'not-observed')
        self.assertEqual(row['observedContent']['pages'], [])
        self.assertEqual(row['observedContent']['pdfStatus'], 'not-observed')
        self.assertFalse(any(row['usageRights']['permissions'].values()))
        self.assertEqual(row['usageRights']['status'], 'restricted')

    def test_duplicate_ids_urls_and_semantic_keys_are_rejected(self):
        for kind in ('id','url','key'):
            with self.subTest(kind=kind):
                s = copy.deepcopy(self.snapshot)
                extra = copy.deepcopy(s['records'][0])
                if kind != 'id': extra['postId'] = 99
                if kind == 'id': extra['pageUrl'] = 'https://bookvn.net/newsong/newsong20/'; extra['rawTitle'] = '20. New'
                if kind == 'key': extra['pageUrl'] += '?version=2'
                s['records'].append(extra)
                with self.assertRaises(ValueError): lib.build_sheet_catalog(s,self.audio)

    def test_malformed_null_boolean_title_and_credential_urls_fail(self):
        for field, value in [('postId',True),('rawTitle',' '),('rawTitle',None),('pageUrl','https://u:p@bookvn.net/newsong/newsong1/'),('pageUrl','https://bookvn.net/newsong/newsong2/')]:
            with self.subTest(field=field,value=value):
                s = copy.deepcopy(self.snapshot); s['records'][0][field] = value
                with self.assertRaises(ValueError): lib.build_sheet_catalog(s,self.audio)

    def test_observation_for_unknown_record_and_wrong_page_order_fail(self):
        for mode in ('id','page','url'):
            with self.subTest(mode=mode):
                s = copy.deepcopy(self.snapshot)
                if mode == 'id': s['observations'][0]['postId'] = 999
                if mode == 'page': s['observations'][0]['pages'][0]['pageNumber'] = 2
                if mode == 'url': s['observations'][0]['pages'][0]['sourceUrl'] = 'https://bookvn.net/private.png?token=x'
                with self.assertRaises(ValueError): lib.build_sheet_catalog(s,self.audio)

    def test_duplicate_source_titles_are_reported_without_merging(self):
        self.snapshot['records'].append({'postId':13,'pageUrl':'https://bookvn.net/newsong/newsong-appendix51/',
                                         'rawTitle':'51. Bây giờ Nước Thiên Đàng sắp kíp!'})
        c = self.build(); report = lib.mapping_report(c,self.audio)
        self.assertEqual(len(c['sheets']),4)
        self.assertEqual(len(report['duplicateTitles']),1)
        self.assertEqual(len(report['duplicateTitles'][0]['sheetIds']),2)

    def test_schema_and_source_semantics_reject_rights_link_and_title_tampering(self):
        schema = load_json(ROOT/'schemas/sheet-catalog.schema.json')
        self.assertEqual(lib.validate_sheet_catalog(self.build(),self.audio,schema,self.snapshot), [])
        for mode in ('rights','link','title','extra','verified'):
            with self.subTest(mode=mode):
                c = self.build(); row=c['sheets']['bookvn:vi:post:10']
                if mode == 'rights': row['usageRights']['permissions']['store'] = True
                if mode == 'link': row['audioLinks'][0]['songId'] = 'watv:vi:newsong:main:999'
                if mode == 'title': row['title'] = 'Wrong'
                if mode == 'extra': row['downloaded'] = True
                if mode == 'verified': row['audioLinks'][0]['verificationStatus'] = 'verified'
                self.assertTrue(lib.validate_sheet_catalog(c,self.audio,schema,self.snapshot))

    def test_real_snapshot_counts_and_candidate_mapping(self):
        snapshot=load_json(ROOT/'source/snapshots/bookvn-vi-2026-10-12.sheets.json')
        audio=load_json(ROOT/'catalog/catalog.vi.json')
        c=lib.build_sheet_catalog(snapshot,audio)
        report=lib.mapping_report(c,audio)
        self.assertEqual(report['counts']['sheets'],542)
        self.assertEqual(report['counts']['byGroup'],{'main':480,'appx':5,'numbered-appendix':57})
        self.assertEqual(len(report['duplicateTitles']),5)
        self.assertEqual(report['mainNumberGaps'],[34,242,300,306,367])
        self.assertEqual(sum(r['observedContent']['inspectionStatus']=='observed' for r in c['sheets'].values()),7)
        self.assertEqual(c['sheets']['bookvn:vi:post:100854']['audioLinks'][0]['songId'],'watv:vi:newsong:appendix:1')
        self.assertEqual(lib.validate_sheet_catalog(c,audio,load_json(ROOT/'schemas/sheet-catalog.schema.json'),snapshot),[])

    def test_cli_build_validate_and_output_protection(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            # Catalog CLI output boundaries belong to the selected project root.
            root=Path(folder); (root/'catalog').mkdir(); (root/'docs').mkdir(); (root/'delivery').mkdir()
            args=[sys.executable,'-X','utf8',str(ROOT/'scripts/sheets.py')]
            built=subprocess.run(args+['build','--root',str(root),'--output',str(root/'catalog/sheet-test.json'),
                                       '--report',str(root/'docs/sheet-test.md'),'--mapping',str(root/'delivery/sheet-test.json')],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(built.returncode,0,built.stderr)
            checked=subprocess.run(args+['validate','--catalog',str(root/'catalog/sheet-test.json')],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(checked.returncode,0,checked.stderr)
            target=root/'catalog/catalog.vi.json'; target.write_text('protected')
            bad=subprocess.run(args+['build','--root',str(root),'--output',str(target)],capture_output=True,text=True,encoding='utf-8')
            self.assertNotEqual(bad.returncode,0)
            self.assertEqual(target.read_text(),'protected')


if __name__=='__main__': unittest.main()
