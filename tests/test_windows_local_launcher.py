"""Launcher tests use disposable artifacts and mock processes, never real media/cloud."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock

FILE=Path(__file__).resolve().parents[1]/'scripts/start-windows-local.py'


def module():
    spec=importlib.util.spec_from_file_location('windows_local_launcher',FILE)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def release(root,status='LOCAL_LIBRARY_NOT_FOR_DISTRIBUTION',folder='LOCAL-0.2.0-fixture'):
    target=root/'release/windows'/folder;target.mkdir(parents=True)
    data=b'MZ self-authored disposable launcher fixture'
    (target/'AudioTP.exe').write_bytes(data)
    report={'status':status,'apiBase':'http://127.0.0.1:8872','files':[{'name':'AudioTP.exe','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}]}
    (target/'build-report.json').write_text(json.dumps(report));return target


class LocalLauncherTests(unittest.TestCase):
    def test_launcher_guard_prevents_two_apps_and_releases_after_exit(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with m.single_launcher(root) as first:
                self.assertTrue(first)
                with m.single_launcher(root) as second:self.assertFalse(second)
            with m.single_launcher(root) as later:self.assertTrue(later)

    def test_existing_backend_is_reused_and_never_stopped(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=release(root);app=MagicMock();app.wait.return_value=0
            with patch.object(m,'ROOT',root),patch.object(m,'backend_ready',return_value=True),patch.object(m.subprocess,'Popen',return_value=app) as popen:
                self.assertEqual(m.main([]),0)
            popen.assert_called_once_with([str(target/'AudioTP.exe')],cwd=target)
            app.terminate.assert_not_called();app.kill.assert_not_called()

    def test_backend_started_here_is_stopped_after_app_exits(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);release(root);backend=MagicMock();backend.poll.return_value=None;app=MagicMock();app.wait.return_value=0
            with patch.object(m,'ROOT',root),patch.object(m,'backend_ready',side_effect=[False,True]),patch.object(m,'port_in_use',return_value=False),patch.object(m.shutil,'which',return_value='node'),patch.object(m.subprocess,'Popen',side_effect=[backend,app]) as popen:
                self.assertEqual(m.main([]),0)
            self.assertIn('--desktop',popen.call_args_list[0].args[0]);backend.terminate.assert_called_once();app.terminate.assert_not_called()

    def test_selects_only_real_local_build_and_detects_tampered_exe(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=release(root)
            release(root,'TEST_ONLY_NOT_FOR_DISTRIBUTION','TEST-0.2.0-newer')
            exe,base=m.find_release(root)
            self.assertEqual(exe,target/'AudioTP.exe');self.assertEqual(base,'http://127.0.0.1:8872')
            exe.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError,'hash|integrity'):m.find_release(root)

    def test_rejects_missing_build_wrong_status_or_non_loopback(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with self.assertRaises(ValueError):m.find_release(root)
            target=release(root,'TEST_ONLY_NOT_FOR_DISTRIBUTION')
            with self.assertRaises(ValueError):m.find_release(root)
            report=json.loads((target/'build-report.json').read_text());report.update(status='LOCAL_LIBRARY_NOT_FOR_DISTRIBUTION',apiBase='https://evil.test')
            (target/'build-report.json').write_text(json.dumps(report))
            with self.assertRaises(ValueError):m.find_release(root)

    def test_check_does_not_launch_processes_or_connect_to_backend(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);release(root)
            with patch.object(m,'ROOT',root),patch.object(m.subprocess,'Popen') as popen,patch.object(m,'backend_ready') as ready:
                self.assertEqual(m.main(['--check']),0)
            popen.assert_not_called();ready.assert_not_called()

    def test_busy_unrelated_port_fails_without_killing_or_launching_anything(self):
        m=module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);release(root)
            with patch.object(m,'ROOT',root),patch.object(m,'backend_ready',return_value=False),patch.object(m,'port_in_use',return_value=True),patch.object(m.subprocess,'Popen') as popen,patch.object(m.shutil,'which',return_value='node'):
                with self.assertRaisesRegex(RuntimeError,'port|cổng'):m.main([])
            popen.assert_not_called()


if __name__=='__main__':unittest.main()
