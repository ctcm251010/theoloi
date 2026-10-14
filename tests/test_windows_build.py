"""Offline release safeguards; never install tools or compile in these tests."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

FILE=Path(__file__).resolve().parents[1]/'scripts/build-windows.py'


def module():
    spec=importlib.util.spec_from_file_location('windows_build',FILE)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def web_file(name):
    if name=='quick-play.json': return '[]'
    if name=='catalog.client.json':
        return json.dumps({'schemaVersion':1,'revision':'fixture','tracks':[{'id':'fixture:1','logicalId':'fixture:song:1','mode':'silent','section':None,'number':1,'title':'Tự soạn','category':'Fixture','durationSeconds':1}]})
    return 'fixture'


class WindowsBuildTests(unittest.TestCase):
    def test_production_origin_rejects_insecure_or_credential_urls(self):
        m=module();self.assertEqual(m.api_origin('https://library.test/'),'https://library.test')
        for value in ['http://library.test','https://code@library.test','https://library.test/a','https://library.test/?token=x','https://library.test/#x','https://host;script-src','https://bad host','']:
            with self.subTest(value=value),self.assertRaises(ValueError):m.api_origin(value)

    def test_missing_toolchain_cannot_create_a_release(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp,patch.object(m,'ROOT',Path(tmp)),patch.object(m,'preflight',return_value=({'missing':['cargo'],'status':'BLOCKED'},{},None)),patch.object(m.subprocess,'run') as run:
            self.assertEqual(m.main(['--build','--api-base','https://library.test']),2)
            run.assert_not_called();self.assertFalse((Path(tmp)/'release').exists())

    def test_failed_build_restores_config_and_stages_no_demo_audio(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=root/'apps/windows';(app/'src-tauri').mkdir(parents=True);(app/'web').mkdir()
            config=app/'src-tauri/tauri.conf.json';original=json.dumps({'version':'0.2.0','build':{},'app':{'security':{}}}).encode();config.write_bytes(original)
            names=['index.html','styles.css','app.mjs','catalog.mjs','player.mjs','storage.mjs','ui-core.mjs','api-client.mjs','remember-access.mjs','supplementary.mjs','app-updates.mjs','offline.mjs','catalog.client.json','quick-play.json','favicon.svg']
            for name in names:(app/'web'/name).write_text(web_file(name))
            (app/'web/fixtures').mkdir();(app/'web/fixtures/guide.wav').write_bytes(b'not-for-release')
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app),patch.object(m,'preflight',return_value=({'missing':[],'status':'READY'},{'node':'node','cargo':str(root/'bin/cargo')},root/'npm.js')),patch.object(m.subprocess,'run',side_effect=subprocess.CalledProcessError(1,'synthetic-build')):
                with self.assertRaises(subprocess.CalledProcessError):m.main(['--build','--api-base','https://library.test'])
            self.assertEqual(config.read_bytes(),original);self.assertFalse((root/'release').exists());self.assertFalse(any((app/'web-release').rglob('*.wav')))
            staged=list((app/'web-release').glob('*/connection.json'));self.assertEqual(json.loads(staged[0].read_text())['apiBase'],'https://library.test')
            self.assertFalse((app/'build.lock').exists());self.assertEqual(next((app/'build-backups').glob('*.tauri.json')).read_bytes(),original)

    def test_existing_build_lock_prevents_config_changes_and_subprocesses(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=root/'apps/windows';app.mkdir(parents=True);lock=app/'build.lock';lock.write_text('synthetic active build')
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app),patch.object(m,'preflight',return_value=({'missing':[]},{'node':'node'},root/'npm.js')),patch.object(m.subprocess,'run') as run:
                with self.assertRaises(FileExistsError):m.main(['--build','--api-base','https://library.test'])
                run.assert_not_called();self.assertEqual(lock.read_text(),'synthetic active build')

    def test_bad_binary_marker_cannot_create_distribution_folder(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);app=root/'apps/windows';(app/'src-tauri/target/release').mkdir(parents=True);(app/'web').mkdir()
            config=app/'src-tauri/tauri.conf.json';original=json.dumps({'version':'0.2.0','build':{},'app':{'security':{}}}).encode();config.write_bytes(original)
            for name in ['index.html','styles.css','app.mjs','catalog.mjs','player.mjs','storage.mjs','ui-core.mjs','api-client.mjs','remember-access.mjs','supplementary.mjs','app-updates.mjs','offline.mjs','catalog.client.json','quick-play.json','favicon.svg']:(app/'web'/name).write_text(web_file(name))
            (app/'src-tauri/target/release/AudioTP.exe').write_bytes(b'MZ synthetic '+str(root).encode())
            with patch.object(m,'ROOT',root),patch.object(m,'APP',app),patch.object(m,'preflight',return_value=({'missing':[]},{'node':'node','cargo':str(root/'bin/cargo')},root/'npm.js')),patch.object(m.subprocess,'run'):
                with self.assertRaisesRegex(ValueError,'prohibited'):m.main(['--build','--api-base','https://library.test'])
            self.assertFalse((root/'release').exists());self.assertEqual(config.read_bytes(),original);self.assertFalse((app/'build.lock').exists())


if __name__=='__main__':unittest.main()
