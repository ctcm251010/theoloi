"""Supplementary prayer tests use isolated synthetic bytes, never production uploads."""
from contextlib import redirect_stdout
import hashlib
import importlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import prayer_assets as pa
except ModuleNotFoundError:
    pa = None

from test_r2 import FakeS3, s3_error


def cli(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PrayerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(pa, "supplementary prayer pipeline is not implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = b"isolated prayer integrity fixture"
        self.digest = hashlib.sha256(self.content).hexdigest()
        self.entry = dict(pa.REGISTRY[0], bytes=len(self.content), sha256=self.digest)
        self.registry = patch.object(pa, "REGISTRY", (self.entry,))
        self.registry.start()
        self.addCleanup(self.registry.stop)
        self.audio = self.root / self.entry["localPath"]
        self.audio.parent.mkdir(parents=True)
        self.audio.write_bytes(self.content)
        self.report = self.audio.with_name("verification.json")
        self.proof = {"status": "PASS", "localPath": self.entry["localPath"],
            "sourceUrl": self.entry["sourceUrl"], "bytes": len(self.content),
            "sha256": self.digest, "durationSeconds": 69.427664,
            "codec": "aac", "decodeVerified": True}
        self.report.write_text(json.dumps(self.proof), encoding="utf-8")
        (self.root / "config").mkdir()
        (self.root / "config/r2.json").write_text(json.dumps({"accountId": "a" * 32,
            "bucket": "isolated-test", "endpoint": "https://" + "a" * 32 + ".r2.cloudflarestorage.com"}), encoding="utf-8")

    def test_prepare_keeps_prayer_separate_with_public_allowlist(self):
        manifest, quick = pa.prepare(self.root)
        self.assertEqual(len(manifest["assets"]), 1)
        ident = "watv:vi:prayer:our-wish"
        self.assertEqual(quick["tracks"], [{"id": ident, "logicalId": ident, "mode": "prayer",
            "section": None, "number": None, "title": "Cầu nguyện chúng con mong muốn",
            "category": "Cầu nguyện", "durationSeconds": 69.427664}])
        self.assertEqual(quick["assets"][ident], {"assetId": ident,
            "objectKey": "audio/v1/watv/vi/prayer/our-wish/" + self.digest + ".m4a",
            "bytes": len(self.content), "sha256": self.digest})
        self.assertEqual(set(quick), {"schemaVersion", "revision", "tracks", "assets"})
        self.assertEqual(manifest["rights"][ident]["confirmedAt"], "2026-10-13")
        self.assertEqual(manifest["rights"][ident]["status"], "user-confirmed")
        self.assertEqual(pa.prepare(self.root), (manifest, quick))
        canonical = json.dumps({"schemaVersion": 1, "tracks": quick["tracks"], "assets": quick["assets"]},
            ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertEqual(quick["revision"], "sha256:" + hashlib.sha256(canonical).hexdigest())
        self.assertFalse((self.root / "delivery").exists())

    def test_two_registered_prayers_preserve_identity_and_upload_only_selected_asset(self):
        second = dict(self.entry, assetId='watv:vi:prayer:unison-prayer', slug='unison-prayer', title='Nhạc không lời cầu nguyện thống thanh', localPath='media/prayer/watv/vi/unison-prayer/unison-prayer.m4a',durationSeconds=311.518912,confirmedAt='2026-10-14',sourceUrl=None)
        target=self.root/second['localPath']; target.parent.mkdir(parents=True);target.write_bytes(self.content)
        proof=dict(self.proof,localPath=second['localPath'],sourceUrl=None,durationSeconds=second['durationSeconds'])
        target.with_name('verification.json').write_text(json.dumps(proof),encoding='utf-8')
        with patch.object(pa,'REGISTRY',(self.entry,second)):
            manifest,quick=pa.prepare(self.root)
            self.assertEqual(len(quick['tracks']),2)
            pa.write_prepared(self.root,manifest,quick)
            module=cli('upload-prayer');remote=FakeS3();remote.close=lambda:None
            with patch.object(module,'ROOT',self.root),patch.object(module,'read_secrets',return_value={}),patch.object(module,'create_client',return_value=remote),redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(['--apply','--asset','watv:vi:prayer:unison-prayer','--verify-download']),0)
            self.assertEqual([x[0] for x in remote.calls].count('put'),1)
            self.assertIn('unison-prayer',next(iter(remote.objects)))

    def test_selected_unison_upload_preserves_all_unselected_our_wish_state_fields(self):
        second = dict(self.entry, assetId='watv:vi:prayer:unison-prayer', slug='unison-prayer',
            title='Nhạc không lời cầu nguyện thống thanh',
            localPath='media/prayer/watv/vi/unison-prayer/unison-prayer.m4a',
            durationSeconds=311.518912, confirmedAt='2026-10-14', sourceUrl=None)
        audio = self.root / second['localPath']
        audio.parent.mkdir(parents=True)
        audio.write_bytes(self.content)
        proof = dict(self.proof, localPath=second['localPath'], sourceUrl=None,
            durationSeconds=second['durationSeconds'])
        audio.with_name('verification.json').write_text(json.dumps(proof), encoding='utf-8')
        module = cli('upload-prayer')
        remote = FakeS3()
        remote.close = lambda: None
        with patch.object(pa, 'REGISTRY', (self.entry, second)), patch.object(module, 'ROOT', self.root), \
                patch.object(module, 'read_secrets', return_value={}), \
                patch.object(module, 'create_client', return_value=remote), redirect_stdout(io.StringIO()):
            manifest, quick = pa.prepare(self.root)
            pa.write_prepared(self.root, manifest, quick)
            target = module.target_config()
            for status in ('uploading', 'uploaded'):
                with self.subTest(status=status):
                    state = module.UploadState(self.root / pa.STATE, target)
                    state.register(list(manifest['assets'].values()))
                    state.update(self.entry['assetId'], status=status, attempts=2,
                        remote_bytes=len(self.content), etag='preserved-etag',
                        uploaded_at='2026-10-13T00:00:00+00:00')
                    before = state.get(self.entry['assetId'])
                    state.close()
                    self.assertEqual(module.main(['--apply', '--asset', second['assetId'], '--verify-download']), 0)
                    state = module.UploadState(self.root / pa.STATE, target)
                    try:
                        self.assertEqual(state.get(self.entry['assetId']), before)
                    finally:
                        state.close()

    def test_rejects_changed_or_missing_audio(self):
        self.audio.write_bytes(b"changed")
        with self.assertRaisesRegex(pa.UploadError, "prayer_local_integrity"):
            pa.prepare(self.root)
        self.audio.unlink()
        with self.assertRaisesRegex(pa.UploadError, "prayer_local_file"):
            pa.prepare(self.root)

    def test_rejects_missing_decode_or_mismatched_source_proof(self):
        for field, value in (("decodeVerified", False), ("sha256", "0" * 64),
                ("durationSeconds", 70), ("sourceUrl", "https://other.invalid"), ("status", "FAIL")):
            with self.subTest(field=field):
                self.report.write_text(json.dumps(dict(self.proof, **{field: value})), encoding="utf-8")
                with self.assertRaisesRegex(pa.UploadError, "prayer_source_verification"):
                    pa.prepare(self.root)

    def test_unconfirmed_rights_block_preparation(self):
        with patch.object(pa, "REGISTRY", (dict(self.entry, rightsConfirmed=False),)):
            with self.assertRaisesRegex(pa.UploadError, "prayer_rights_unconfirmed"):
                pa.prepare(self.root)

    def test_registry_path_traversal_blocked(self):
        with patch.object(pa, "REGISTRY", (dict(self.entry, localPath="../outside.m4a"),)):
            with self.assertRaisesRegex(pa.UploadError, "prayer_invalid_registry"):
                pa.prepare(self.root)

    def test_symlink_source_is_rejected(self):
        target = self.audio.with_name("actual.m4a")
        self.audio.rename(target)
        try:
            self.audio.symlink_to(target)
        except OSError:
            self.skipTest("Windows symlink privilege unavailable")
        with self.assertRaisesRegex(pa.UploadError, "prayer_unsafe_path"):
            pa.prepare(self.root)

    def test_prepare_cli_dry_run_and_explicit_write_preserve_originals(self):
        module = cli("prepare-prayer")
        originals = ("catalog/catalog.vi.json", "delivery/manifest.vi.json", "state/transfers.sqlite")
        for relative in originals:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"original")
        with patch.object(module, "ROOT", self.root), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main([]), 0)
            self.assertFalse((self.root / pa.MANIFEST).exists())
            self.assertEqual(module.main(["--write"]), 0)
        self.assertEqual(json.loads((self.root / pa.QUICK).read_text(encoding="utf-8"))["tracks"][0]["mode"], "prayer")
        for relative in originals:
            self.assertEqual((self.root / relative).read_bytes(), b"original")
        self.assertEqual(self.audio.read_bytes(), self.content)

    def test_prepared_manifest_tamper_blocked(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        manifest = json.loads((self.root / pa.MANIFEST).read_text(encoding="utf-8"))
        manifest["assets"][self.entry["assetId"]]["objectKey"] = "arbitrary"
        (self.root / pa.MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(pa.UploadError, "prayer_manifest_mismatch"):
            pa.load_prepared(self.root)

    def test_output_hardlink_does_not_overwrite_protected_input(self):
        destination = self.root / pa.MANIFEST
        destination.parent.mkdir(parents=True)
        victim = self.root / "protected.json"
        victim.write_bytes(b"protected")
        os.link(victim, destination)
        with self.assertRaisesRegex(pa.UploadError, "writable_hardlink"):
            pa.write_prepared(self.root, *pa.prepare(self.root))
        self.assertEqual(victim.read_bytes(), b"protected")

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_output_junction_is_rejected_before_protected_input_write(self):
        protected = self.root / "protected"
        protected.mkdir()
        victim = protected / "prayer-manifest.vi.json"
        victim.write_bytes(b"protected")
        link = self.root / "delivery"
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
            "New-Item -ItemType Junction -Path $env:AUDIOTP_TEST_LINK -Target $env:AUDIOTP_TEST_TARGET -ErrorAction Stop | Out-Null"],
            env=dict(os.environ, AUDIOTP_TEST_LINK=str(link), AUDIOTP_TEST_TARGET=str(protected)),
            check=True, capture_output=True)
        try:
            with self.assertRaisesRegex(pa.UploadError, "prayer_unsafe_path"):
                pa.write_prepared(self.root, *pa.prepare(self.root))
            self.assertEqual(victim.read_bytes(), b"protected")
            self.assertFalse((self.root / pa.QUICK).exists())
        finally:
            link.rmdir()

    def test_upload_state_hardlinks_rejected_before_any_mutation(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        module = cli("upload-prayer")
        protected = self.root / "original.sqlite"
        protected.write_bytes(b"original state bytes")
        state = self.root / pa.STATE
        state.parent.mkdir()
        os.link(protected, state)
        output = io.StringIO()
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", side_effect=AssertionError("credentials forbidden")), redirect_stdout(output):
            self.assertEqual(module.main(["--apply"]), 1)
        self.assertEqual(output.getvalue(), "ERROR writable_hardlink\n")
        self.assertEqual(protected.read_bytes(), b"original state bytes")
        self.assertFalse((self.root / pa.LOCK).exists())

    def test_upload_dry_run_and_status_do_not_create_state_or_client(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        module = cli("upload-prayer")
        with patch.object(module, "ROOT", self.root), patch.object(module, "create_client", side_effect=AssertionError("network forbidden")), patch.object(module, "read_secrets", side_effect=AssertionError("credentials forbidden")), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main([]), 0)
            self.assertEqual(module.main(["--status"]), 0)
        self.assertFalse((self.root / pa.STATE).exists())
        self.assertFalse((self.root / "state").exists())

    def test_apply_upload_download_hash_and_resume_use_separate_state(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        module = cli("upload-prayer")
        remote = FakeS3()
        remote.close = lambda: None
        target = {"accountId": "a" * 32, "bucket": "isolated-test", "endpoint": "https://" + "a" * 32 + ".r2.cloudflarestorage.com"}
        with patch.object(module, "ROOT", self.root), patch.object(module, "target_config", return_value=target), patch.object(module, "read_secrets", return_value={}), patch.object(module, "create_client", return_value=remote), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--apply", "--verify-download"]), 0)
            self.assertEqual(module.main(["--apply", "--verify-download"]), 0)
            self.assertEqual(module.main(["--status"]), 0)
        self.assertEqual([call[0] for call in remote.calls].count("put"), 1)
        self.assertEqual([call[0] for call in remote.calls].count("get"), 2)
        self.assertTrue((self.root / pa.STATE).is_file())
        self.assertFalse((self.root / "state/r2-transfers.sqlite").exists())

    def test_upload_failure_emits_safe_code_without_exception_secrets(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        module = cli("upload-prayer")
        output = io.StringIO()
        with patch.object(module, "ROOT", self.root), patch.object(module, "target_config", side_effect=RuntimeError("secret-session-do-not-print")), redirect_stdout(output):
            self.assertEqual(module.main(["--apply"]), 1)
        self.assertEqual(output.getvalue(), "ERROR internal_error\n")

    def test_failed_transfer_is_bounded_and_requires_explicit_retry(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        module = cli("upload-prayer")
        remote = FakeS3()
        remote.close = lambda: None
        remote.head_failures = [s3_error(503, message="private-remote-value") for _ in range(4)]
        output = io.StringIO()
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", return_value={}), patch.object(module, "create_client", return_value=remote), patch("threading.Event.wait", return_value=False), redirect_stdout(output):
            self.assertEqual(module.main(["--apply"]), 1)
            self.assertEqual(len(remote.calls), 3)
            self.assertEqual(module.main(["--apply"]), 1)
            self.assertEqual(len(remote.calls), 3)
            remote.head_failures.clear()
            self.assertEqual(module.main(["--apply", "--retry-failed", "--verify-download"]), 0)
        self.assertNotIn("private-remote-value", output.getvalue())
        self.assertIn("remote_http_503", output.getvalue())

    def test_status_reads_prepared_registry_without_requiring_local_audio(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        self.audio.unlink()
        module = cli("upload-prayer")
        with patch.object(module, "ROOT", self.root), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--status"]), 0)

    def test_source_permission_denial_is_safe_without_file_path(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            if path == self.audio:
                raise PermissionError("sensitive-filesystem-detail")
            return original(path, *args, **kwargs)
        module = cli("prepare-prayer")
        output = io.StringIO()
        with patch.object(module, "ROOT", self.root), patch.object(Path, "open", guarded), redirect_stdout(output):
            self.assertEqual(module.main([]), 1)
        self.assertEqual(output.getvalue(), "ERROR prayer_local_file\n")

    def test_existing_wrong_content_type_fails_instead_of_claiming_verified(self):
        pa.write_prepared(self.root, *pa.prepare(self.root))
        module = cli("upload-prayer")
        remote = FakeS3()
        remote.close = lambda: None
        asset = next(iter(pa.prepare(self.root)[0]['assets'].values()))
        remote.objects[asset['objectKey']] = {'body':self.audio.read_bytes(), 'metadata':{'sha256':asset['sha256'],'asset-id':asset['assetId']}}
        original = remote.head_object
        def bad_head(**kwargs):
            return dict(original(**kwargs), ContentType='text/html')
        remote.head_object = bad_head
        with patch.object(module, 'ROOT', self.root), patch.object(module, 'read_secrets', return_value={}), patch.object(module, 'create_client', return_value=remote), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(['--apply','--verify-download']),1)
        self.assertEqual([call[0] for call in remote.calls].count('put'),0)

    def test_upload_option_conflicts_fail_before_any_action(self):
        module = cli("upload-prayer")
        for options in (["--status", "--apply"], ["--verify-download"], ["--retry-failed"]):
            with self.subTest(options=options), redirect_stdout(io.StringIO()), patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    module.arguments(options)
                self.assertEqual(error.exception.code, 2)
