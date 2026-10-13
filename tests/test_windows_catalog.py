"""Client projection must never ship raw HLS URLs or join by array position."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
MODULE = ROOT / 'scripts/windows_catalog.py'


class WindowsCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not all((ROOT / name).is_file() for name in ('catalog/catalog.vi.json','delivery/manifest.vi.json')):
            raise unittest.SkipTest('Private catalog/manifest integration requires authorized local inputs; never publish or substitute them')
        cls.catalog = json.loads((ROOT / 'catalog/catalog.vi.json').read_text(encoding='utf-8'))
        cls.manifest = json.loads((ROOT / 'delivery/manifest.vi.json').read_text(encoding='utf-8'))

    def module(self):
        self.assertTrue(MODULE.exists(), 'Client catalog projection has not been implemented')
        spec = importlib.util.spec_from_file_location('windows_catalog', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_exact_modes_id_mapping_and_safe_projection(self):
        data = self.module().project_catalog(self.catalog, self.manifest)
        self.assertEqual([sum(t['mode'] == mode for t in data['tracks']) for mode in ('guide','instrumental','silent')], [485,485,13])
        rows = {t['id']: t for t in data['tracks']}
        self.assertEqual(rows['watv:vi:guide:4177']['logicalId'], 'watv:vi:newsong:main:1')
        self.assertEqual(rows['watv:vi:instrumental:17407']['logicalId'], 'watv:vi:newsong:main:1')
        self.assertEqual(rows['watv:vi:silent:19976']['number'], 474)
        self.assertIsNone(rows['watv:vi:silent:19976']['section'])
        self.assertAlmostEqual(rows['watv:vi:guide:4177']['durationSeconds'], 125.016236)
        self.assertNotIn(34, [t['number'] for t in data['tracks'] if t['mode']=='guide' and t['section']=='main'])
        for row in rows.values():
            self.assertEqual(set(row), {'id','logicalId','mode','section','number','title','category','durationSeconds'})
        self.assertNotIn('https:', json.dumps(data))

    def test_manifest_mismatch_and_unknown_asset_fail_closed(self):
        module = self.module()
        for change in ('missing','extra','wrong_identity','wrong_variant','invalid_duration'):
            manifest = copy.deepcopy(self.manifest)
            if change == 'missing': del manifest['assets']['watv:vi:guide:4177']
            elif change == 'extra': manifest['assets']['surprise'] = manifest['assets']['watv:vi:guide:4177']
            elif change == 'wrong_identity': manifest['assets']['watv:vi:guide:4177']['logicalId'] = 'watv:vi:newsong:main:2'
            elif change == 'wrong_variant': manifest['assets']['watv:vi:guide:4177']['variant'] = 'silent'
            else: manifest['assets']['watv:vi:guide:4177']['durationSeconds'] = float('nan')
            with self.subTest(change=change), self.assertRaises(ValueError):
                module.project_catalog(self.catalog, manifest)

    def test_shuffled_maps_preserve_semantic_output(self):
        catalog = copy.deepcopy(self.catalog)
        catalog['songs'] = dict(reversed(list(catalog['songs'].items())))
        catalog['meditations'] = dict(reversed(list(catalog['meditations'].items())))
        self.assertEqual(self.module().project_catalog(catalog, self.manifest), self.module().project_catalog(self.catalog, self.manifest))

    @unittest.skipUnless((ROOT/'source/snapshots/watv-vi-2026-10-10.audio.json').is_file(), 'Private source snapshot required for quick-play integration')
    def test_quick_silent_order_comes_from_snapshot_ids_not_catalog_map_order(self):
        snapshot=json.loads((ROOT/'source/snapshots/watv-vi-2026-10-10.audio.json').read_text(encoding='utf-8'))
        module=self.module()
        cards=module.project_quick_play(self.catalog,self.manifest,snapshot)
        first=cards[0]
        self.assertEqual(first['firstAssetId'],'watv:vi:silent:19977')
        self.assertEqual(first['assetIds'],['watv:vi:silent:'+str(i) for i in range(19977,19964,-1)])
        self.assertEqual(first['rightsStatus'],'approved')
        for card in cards[1:]:
            self.assertFalse(card['available']);self.assertEqual(card['assetIds'],[]);self.assertEqual(card['rightsStatus'],'unknown')
        shuffled=copy.deepcopy(self.catalog);shuffled['meditations']=dict(reversed(list(shuffled['meditations'].items())))
        self.assertEqual(module.project_quick_play(shuffled,self.manifest,snapshot),cards)

    @unittest.skipUnless((ROOT/'source/snapshots/watv-vi-2026-10-10.audio.json').is_file(), 'Private source snapshot required for quick-play integration')
    def test_quick_projection_rejects_missing_duplicate_and_wrong_source_identity(self):
        snapshot=json.loads((ROOT/'source/snapshots/watv-vi-2026-10-10.audio.json').read_text(encoding='utf-8'))
        module=self.module()
        for change in ['missing','duplicate','wrong_id','wrong_number','wrong_title']:
            data=copy.deepcopy(snapshot);rows=data['lists']['silentSongList']
            if change=='missing': rows.pop()
            elif change=='duplicate': rows[-1]=rows[0]
            elif change=='wrong_id': rows[0]['newsongAudioId']=4177
            elif change=='wrong_number': rows[0]['newsongDispNo']=1
            else: rows[0]['title']='Unverified title'
            with self.subTest(change=change),self.assertRaises(ValueError):module.project_quick_play(self.catalog,self.manifest,data)


if __name__ == '__main__': unittest.main()
