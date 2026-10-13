"""Windows update publisher: isolated PE fixtures and fake private object store."""
import base64
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import windows_update as wu
except ModuleNotFoundError:
    wu = None
from test_r2 import s3_error


def cli():
    spec = importlib.util.spec_from_file_location("publish_windows_update", ROOT / "scripts/publish-windows-update.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encoded_signature(packet=b"ED" + bytes(72)):
    inner = "untrusted comment: fixture only\n" + base64.b64encode(packet).decode() + "\ntrusted comment: fixture only\n" + base64.b64encode(bytes(64)).decode() + "\n"
    return base64.b64encode(inner.encode()).decode()


class FakeInstallerStore:
    def __init__(self):
        self.object = None
        self.calls = []
        self.failures = []
        self.corrupt_download = False

    def head_object(self, **options):
        self.calls.append(("head", options))
        if self.failures:
            raise self.failures.pop(0)
        if self.object is None:
            raise s3_error(404)
        return {"ContentLength": len(self.object["body"]), "Metadata": self.object["metadata"],
            "ContentType": "application/octet-stream"}

    def put_object(self, **options):
        self.calls.append(("put", {k:v for k,v in options.items() if k != "Body"}))
        if self.object is not None:
            raise s3_error(412)
        if options.get("IfNoneMatch") != "*":
            raise AssertionError("create-only PUT required")
        if options.get("ContentType") != "application/octet-stream":
            raise AssertionError("installer content type required")
        body = options["Body"].read()
        if options["ContentLength"] != len(body):
            raise AssertionError("wrong installer byte count")
        self.object = {"body": body, "metadata": options["Metadata"]}
        return {}

    def get_object(self, **options):
        self.calls.append(("get", options))
        body = b"corrupted" if self.corrupt_download else self.object["body"]
        return {"ContentLength": len(body), "Body": io.BytesIO(body)}

    def close(self):
        pass


class WindowsUpdatePublishTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(wu, "Windows update publisher is not implemented")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.relative = Path("release/windows/1.0.1-20261013T080000123456Z")
        self.folder = self.root / self.relative
        self.folder.mkdir(parents=True)
        self.name = "AudioTP_1.0.1_x64-setup.exe"
        self.installer = self.folder / self.name
        data = bytearray(128)
        data[:2] = b"MZ"
        data[60:64] = (64).to_bytes(4, "little")
        data[64:68] = b"PE\0\0"
        self.data = bytes(data)
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.installer.write_bytes(self.data)
        self.signature = encoded_signature()
        self.sig = self.folder / (self.name + ".sig")
        self.sig.write_text(self.signature + "\n", encoding="utf-8")
        self.report = {"status":"BUILT_NOT_ACCEPTED", "version":"1.0.1", "buildNumber":"20261013T080000123456Z",
            "apiBase":"https://audiotp-media-api.ctcm251010.workers.dev", "installer":True,
            "files":[{"name":self.name,"bytes":len(self.data),"sha256":self.digest},
                {"name":self.name+".sig","bytes":self.sig.stat().st_size,"sha256":hashlib.sha256(self.sig.read_bytes()).hexdigest()}]}
        self.write_report()
        self.target = {"accountId":"a"*32,"bucket":"isolated-test","endpoint":"https://"+"a"*32+".r2.cloudflarestorage.com"}
        (self.root / "config").mkdir()
        (self.root / "config/r2.json").write_text(json.dumps(self.target), encoding="utf-8")

    def write_report(self):
        (self.folder / "build-report.json").write_text(json.dumps(self.report), encoding="utf-8")

    def test_inspection_produces_exact_deterministic_worker_envelope(self):
        metadata, path = wu.inspect_release(self.root, self.relative, "Signed update")
        self.assertEqual(path, self.installer)
        self.assertEqual(metadata, {"version":"1.0.1", "pubDate":"2026-10-13T08:00:00Z", "notes":"Signed update",
            "objectKey":"updates/windows-x86_64/1.0.1/AudioTP_1.0.1_x64-setup.exe",
            "bytes":128,"sha256":self.digest,"signature":self.signature})
        self.assertFalse((self.root / "delivery").exists())

    def test_changed_installer_or_signature_fails_report_integrity(self):
        self.installer.write_bytes(self.data + b"changed")
        with self.assertRaisesRegex(wu.UploadError, "update_local_integrity"):
            wu.inspect_release(self.root, self.relative)
        self.installer.write_bytes(self.data)
        self.sig.write_text(encoded_signature(b"Ed"+bytes(72)), encoding="utf-8")
        with self.assertRaisesRegex(wu.UploadError, "update_local_integrity"):
            wu.inspect_release(self.root, self.relative)

    def test_missing_signature_duplicate_report_and_test_build_rejected(self):
        for change in (lambda:self.report.update(status="TEST_ONLY_NOT_FOR_DISTRIBUTION"),
                lambda:self.report["files"].append(dict(self.report["files"][0])),
                lambda:self.report.update(installer=False)):
            original = json.loads(json.dumps(self.report))
            change()
            self.write_report()
            with self.assertRaises(wu.UploadError):
                wu.inspect_release(self.root, self.relative)
            self.report = original
        self.write_report()
        self.sig.unlink()
        with self.assertRaisesRegex(wu.UploadError, "update_local_file"):
            wu.inspect_release(self.root, self.relative)

    def test_non_pe_and_oversized_installers_rejected_before_network(self):
        self.installer.write_bytes(b"not a PE")
        self.report["files"][0].update(bytes=8, sha256=hashlib.sha256(b"not a PE").hexdigest())
        self.write_report()
        with self.assertRaisesRegex(wu.UploadError, "update_invalid_pe"):
            wu.inspect_release(self.root, self.relative)
        with self.installer.open("wb") as stream:
            stream.truncate(50 * 1024 * 1024 + 1)
        with self.assertRaisesRegex(wu.UploadError, "update_size_limit"):
            wu.inspect_release(self.root, self.relative)

    def test_signature_rejects_noncanonical_base64_and_bad_minisign_packets(self):
        for value in ("not base64", self.signature + "=", encoded_signature(b"xx" + bytes(72)),
                encoded_signature(b"ED" + bytes(71)), base64.b64encode(b"only one line").decode()):
            with self.subTest(value=value[:20]), self.assertRaisesRegex(wu.UploadError, "update_invalid_signature"):
                wu.parse_signature(value)

    def test_unreviewed_release_paths_and_report_versions_rejected(self):
        for value in ("../outside", self.root / "unrelated", "release/windows/TEST-1.0.1-20261013T080000123456Z"):
            with self.subTest(value=str(value)), self.assertRaises(wu.UploadError):
                wu.inspect_release(self.root, value)
        self.report["version"] = "1.0.2"
        self.write_report()
        with self.assertRaisesRegex(wu.UploadError, "update_invalid_report"):
            wu.inspect_release(self.root, self.relative)

    def test_dry_run_does_not_authenticate_or_create_metadata(self):
        module = cli()
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", side_effect=AssertionError("credential forbidden")), patch.object(module, "create_client", side_effect=AssertionError("network forbidden")), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--release-dir", str(self.relative)]), 0)
        self.assertFalse((self.root / wu.DELIVERY).exists())
        self.assertFalse((self.root / wu.GENERATED).exists())

    def test_offline_prepare_writes_metadata_and_states_remote_unverified(self):
        module = cli()
        output = io.StringIO()
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", side_effect=AssertionError("credential forbidden")), redirect_stdout(output):
            self.assertEqual(module.main(["--release-dir", str(self.relative), "--prepare"]), 0)
        self.assertIn("remote-unverified", output.getvalue())
        self.assertEqual(json.loads((self.root / wu.DELIVERY).read_text()), json.loads((self.root / wu.GENERATED).read_text()))

    def test_apply_uploads_only_installer_and_requires_download_hash_before_metadata(self):
        module, remote = cli(), FakeInstallerStore()
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", return_value={}), patch.object(module, "create_client", return_value=remote), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--release-dir", str(self.relative), "--apply"]), 0)
            self.assertEqual(module.main(["--release-dir", str(self.relative), "--apply"]), 0)
        self.assertEqual([call[0] for call in remote.calls], ["head", "put", "head", "get", "head", "get"])
        self.assertEqual(remote.object["metadata"], {"sha256":self.digest,"asset-id":"audiotp:windows:x86_64:1.0.1"})
        self.assertEqual(remote.object["body"], self.data)
        self.assertTrue((self.root / wu.GENERATED).is_file())

    def test_conflict_and_corrupt_get_leave_metadata_unwritten(self):
        module, remote = cli(), FakeInstallerStore()
        remote.corrupt_download = True
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", return_value={}), patch.object(module, "create_client", return_value=remote), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--release-dir", str(self.relative), "--apply"]), 1)
        self.assertFalse((self.root / wu.GENERATED).exists())
        self.assertFalse((self.root / wu.DELIVERY).exists())
        remote.object["metadata"]["sha256"] = "0" * 64
        before = len(remote.calls)
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", return_value={}), patch.object(module, "create_client", return_value=remote), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--release-dir", str(self.relative), "--apply"]), 1)
        self.assertEqual([name for name,_ in remote.calls[before:]], ["head"])

    def test_transient_errors_are_bounded_and_safe(self):
        metadata, path = wu.inspect_release(self.root, self.relative)
        remote = FakeInstallerStore()
        remote.failures = [s3_error(503, message="private-remote-error") for _ in range(4)]
        with self.assertRaisesRegex(wu.UploadError, "remote_http_503"):
            wu.publish_installer(remote, self.target["bucket"], path, metadata, wait=lambda _:False)
        self.assertEqual(len(remote.calls), 3)

    def test_output_hardlink_rejected_before_upload_and_original_bytes_preserved(self):
        module = cli()
        protected = self.root / "original.json"
        protected.write_bytes(b"protected")
        output = self.root / wu.GENERATED
        output.parent.mkdir(parents=True)
        os.link(protected, output)
        with patch.object(module, "ROOT", self.root), patch.object(module, "read_secrets", side_effect=AssertionError("credentials forbidden")), redirect_stdout(io.StringIO()):
            self.assertEqual(module.main(["--release-dir", str(self.relative), "--apply"]), 1)
        self.assertEqual(protected.read_bytes(), b"protected")

    def test_cli_errors_never_print_secret_exception_messages(self):
        module = cli()
        output = io.StringIO()
        with patch.object(module, "ROOT", self.root), patch.object(module, "create_client", side_effect=RuntimeError("private-credential-value")), patch.object(module, "read_secrets", return_value={}), redirect_stdout(output):
            self.assertEqual(module.main(["--release-dir", str(self.relative), "--apply"]), 1)
        self.assertEqual(output.getvalue(), "ERROR internal_error\n")

    def test_client_close_failure_is_reported_without_exception_details(self):
        module, remote = cli(), FakeInstallerStore()
        remote.close = lambda: (_ for _ in ()).throw(RuntimeError("private-close-detail"))
        output = io.StringIO()
        with patch.object(module, "ROOT", self.root), patch.object(module, "create_client", return_value=remote), patch.object(module, "read_secrets", return_value={}), redirect_stdout(output):
            try:
                result = module.main(["--release-dir", str(self.relative), "--apply"])
            except RuntimeError:
                result = "unhandled exception"
            self.assertEqual(result, 1)
        self.assertEqual(output.getvalue(), "ERROR internal_error\n")
