"""Offline packaging behavior; no tool install, compiler, cloud or real secrets."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_windows_build import module

FILE_FIXTURE=Path(__file__).resolve().parents[1]/'apps/windows/test-fixtures.json'


def web_fixture(root):
    app=root/'apps/windows';(app/'web').mkdir(parents=True);(app/'src-tauri').mkdir()
    config={'version':'0.2.0','build':{'frontendDist':'../web'},'app':{'security':{'capabilities':[]}},'bundle':{'windows':{}}}
    (app/'src-tauri/tauri.conf.json').write_text(json.dumps(config))
    for name in ['index.html','styles.css','app.mjs','catalog.mjs','player.mjs','storage.mjs','ui-core.mjs','api-client.mjs','remember-access.mjs','favicon.svg']:
        (app/'web'/name).write_text('self-authored fixture')
    catalog={'schemaVersion':1,'revision':'self-authored','tracks':[{'id':'fixture:1','logicalId':'fixture:song:1','mode':'silent','section':None,'number':1,'title':'Tự soạn','category':'Fixture','durationSeconds':2}]}
    (app/'web/catalog.client.json').write_text(json.dumps(catalog))
    (app/'web/quick-play.json').write_text('[]')
    return app


class WindowsPackagingTests(unittest.TestCase):
    def test_local_library_packages_real_projection_and_pins_loopback_without_test_catalog(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root)
            original=(app/'web/catalog.client.json').read_bytes()
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app):
                stage,override,_=m.prepare_stage('http://127.0.0.1:8872',local_library=True)
                for origin in ['https://media.test','http://localhost:8872','http://127.0.0.1:8872/path']:
                    with self.assertRaises(ValueError):m.prepare_stage(origin,local_library=True)
                with self.assertRaises(ValueError):m.prepare_stage('http://127.0.0.1:8872',local_library=True,test_fixtures=True)
                self.assertEqual(m.main(['--prepare','--local-library','--api-base','http://127.0.0.1:8872']),0)
            catalog=json.loads((stage/'catalog.client.json').read_text())
            self.assertEqual(catalog,json.loads(original))
            self.assertFalse(any(t['id'].startswith('test:') for t in catalog['tracks']))
            self.assertEqual(json.loads((stage/'connection.json').read_text())['mode'],'local-library')
            config=json.loads(override.read_text())
            self.assertEqual(config['identifier'],'org.audiotp.local')
            self.assertIn('http://127.0.0.1:8872',config['app']['security']['csp'])
            self.assertEqual(config['bundle']['resources'],[])
            self.assertFalse(any(stage.rglob('*.m4a')))

    def test_mock_fixture_build_is_isolated_from_production_and_requires_loopback(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root)
            (app/'test-fixtures.json').write_bytes((FILE_FIXTURE).read_bytes())
            (app/'web/catalog.client.json').unlink();(app/'web/quick-play.json').unlink()
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app):
                stage,override,_=m.prepare_stage('http://127.0.0.1:8870',test_fixtures=True)
                with self.assertRaises(ValueError):m.prepare_stage('https://media.test',test_fixtures=True)
            config=json.loads(override.read_text())
            self.assertEqual(config['identifier'],'org.audiotp.acceptance')
            self.assertEqual(json.loads((stage/'connection.json').read_text())['mode'],'test-fixtures')
            self.assertTrue(all(t['id'].startswith('test:') for t in json.loads((stage/'catalog.client.json').read_text())['tracks']))
            self.assertFalse(any(stage.rglob('*.wav')))

    def test_prepare_without_toolchain_keeps_config_and_excludes_extra_files(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root);original=(app/'src-tauri/tauri.conf.json').read_bytes()
            (app/'web/private.env').write_text('do not package');(app/'web/fixtures').mkdir();(app/'web/fixtures/tone.wav').write_bytes(b'fixture')
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app),patch.object(m.subprocess,'run') as run:
                result=m.main(['--prepare','--api-base','https://library.test'])
            self.assertEqual(result,0);run.assert_not_called()
            stage=next((app/'web-release').iterdir());files={p.name for p in stage.iterdir()}
            self.assertNotIn('private.env',files);self.assertNotIn('fixtures',files)
            self.assertIn('remember-access.mjs',files)
            self.assertEqual((app/'src-tauri/tauri.conf.json').read_bytes(),original)
            self.assertEqual(json.loads((stage/'connection.json').read_text())['apiBase'],'https://library.test')
            override=json.loads(next((app/'build-backups').glob('*.override.json')).read_text())
            self.assertIn('connect-src \'self\' https://library.test ',override['app']['security']['csp'])
            self.assertNotIn('http://127.0.0.1',override['app']['security']['csp'])
            self.assertEqual(override['bundle']['resources'],[])

    def test_debug_without_endpoint_is_explicitly_catalog_only(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root)
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app):
                self.assertEqual(m.main(['--prepare','--debug']),0)
            connection=json.loads(next((app/'web-release').glob('*/connection.json')).read_text())
            self.assertEqual(connection['mode'],'catalog-only');self.assertEqual(connection['apiBase'],'')
            override=json.loads(next((app/'build-backups').glob('*.override.json')).read_text())
            self.assertNotIn('https:',override['app']['security']['csp'])

    def test_release_requires_origin_and_debug_cannot_make_installer(self):
        m=module()
        for args in [['--prepare'],['--build','--debug','--installer']]:
            with self.subTest(args=args),self.assertRaises(SystemExit) as error:
                m.main(args)
            self.assertEqual(error.exception.code,2)

    def test_generated_catalog_private_fields_are_rejected(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root);path=app/'web/catalog.client.json';catalog=json.loads(path.read_text());catalog['tracks'][0]['hlsUrl']='https://private.invalid/source';path.write_text(json.dumps(catalog))
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app),self.assertRaisesRegex(ValueError,'catalog'):
                m.prepare_stage('https://library.test')
            self.assertFalse((root/'release').exists())

    def test_quick_metadata_drops_internal_provenance(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root)
            card={'id':'quick:1','title':'Tự soạn','behavior':'asset-playlist','available':False,'reason':'Unavailable','assetIds':[],'sourceStatus':'not-imported','rightsStatus':'unknown','provenance':{'sequence':'private/internal/source.json'}}
            (app/'web/quick-play.json').write_text(json.dumps([card]))
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app):stage,_,_=m.prepare_stage('https://library.test')
            output=(stage/'quick-play.json').read_text();self.assertNotIn('private/internal',output);self.assertNotIn('provenance',output)

    def test_stage_rejects_source_symlink_to_outside_web(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root);source=app/'web/app.mjs';source.unlink();outside=root/'outside.mjs';outside.write_text('outside')
            try: source.symlink_to(outside)
            except OSError: self.skipTest('Windows symlink privilege unavailable')
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app),self.assertRaisesRegex(ValueError,'outside|symlink'):
                m.prepare_stage('https://library.test')

    def test_failed_compiler_never_changes_config(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=web_fixture(root);original=(app/'src-tauri/tauri.conf.json').read_bytes()
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app),patch.object(m.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'fixture-compiler')):
                with self.assertRaises(subprocess.CalledProcessError):m.build_release('https://library.test',False,{'node':'node','cargo':str(root/'bin/cargo')},root/'npm.js')
            self.assertEqual((app/'src-tauri/tauri.conf.json').read_bytes(),original);self.assertFalse((root/'release').exists())

    def test_non_pe_artifact_is_not_a_valid_release(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);artifact=root/'AudioTP.exe';artifact.write_bytes(b'not a Windows executable')
            with patch.object(m,'ROOT',root),self.assertRaisesRegex(ValueError,'PE|executable'):
                m.inspect_artifact(artifact,0)

    def test_stale_pe_artifact_is_rejected(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);artifact=root/'AudioTP.exe';data=bytearray(256);data[:2]=b'MZ';data[60:64]=(128).to_bytes(4,'little');data[128:132]=b'PE\0\0';artifact.write_bytes(data);os.utime(artifact,(1,1))
            with patch.object(m,'ROOT',root),self.assertRaisesRegex(ValueError,'stale'):
                m.inspect_artifact(artifact,2)


if __name__=='__main__':unittest.main()
