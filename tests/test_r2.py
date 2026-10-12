"""R2 tests: synthetic bytes and fake S3, never live credentials or media."""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr

from botocore.exceptions import ClientError, ReadTimeoutError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from catalog_lib import load_json
AVAILABLE = importlib.util.find_spec("r2_pipeline") is not None
if AVAILABLE:
    import r2_pipeline as rp
    from r2_state import UploadState, UploadError


def s3_error(status, code="TestError", message="simulated"):
    return ClientError({"Error": {"Code": code, "Message": message},
                        "ResponseMetadata": {"HTTPStatusCode": status}}, "HeadObject")


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.head_failures = []
        self.lost_put_response = False
        self.bad_download = False

    def head_object(self, **kw):
        self.calls.append(("head", kw["Key"]))
        if self.head_failures: raise self.head_failures.pop(0)
        if kw["Key"] not in self.objects: raise s3_error(404, "NoSuchKey")
        obj = self.objects[kw["Key"]]
        return {"ContentLength": len(obj["body"]), "Metadata": dict(obj["metadata"]),
                "ContentType": "audio/mp4", "ETag": '"opaque-not-sha256"'}

    def put_object(self, **kw):
        self.calls.append(("put", kw["Key"]))
        if kw.get("IfNoneMatch") != "*": raise AssertionError("Unconditional PUT forbidden")
        if kw["Key"] in self.objects: raise s3_error(412, "PreconditionFailed")
        body = kw["Body"].read()
        assert kw["ContentLength"] == len(body)
        assert kw["ContentMD5"] == base64.b64encode(hashlib.md5(body).digest()).decode()
        assert kw["ContentType"] == "audio/mp4"
        self.objects[kw["Key"]] = {"body": body, "metadata": dict(kw["Metadata"])}
        if self.lost_put_response:
            self.lost_put_response = False
            raise ReadTimeoutError(endpoint_url="https://example.invalid")
        return {"ETag": '"opaque-not-sha256"'}

    def get_object(self, **kw):
        self.calls.append(("get", kw["Key"]))
        obj = self.objects[kw["Key"]]
        return {"ContentLength": len(obj["body"]), "Body": io.BytesIO(b"wrong bytes" if self.bad_download else obj["body"])}


class R2Tests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE, "R2 uploader implementation missing")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.target = {"accountId": "a" * 32, "bucket": "unit-test-media",
                       "endpoint": "https://" + "a" * 32 + ".r2.cloudflarestorage.com"}
        data = b"tiny synthetic audio artifact"
        path = self.root / "media/audio/v1/watv/vi/newsong/main/0001/guide.m4a"
        path.parent.mkdir(parents=True)
        path.write_bytes(data)
        self.asset = {"assetId": "watv:vi:guide:4177", "sha256": hashlib.sha256(data).hexdigest(),
                      "bytes": len(data), "localPath": path.relative_to(self.root).as_posix(),
                      "objectKey": "audio/v1/watv/vi/newsong/main/0001/guide/4177/" + hashlib.sha256(data).hexdigest() + ".m4a"}
        self.path = path
        self.dbpath = self.root / "state/r2-transfers.sqlite"
        self.state = UploadState(self.dbpath, self.target)
        self.addCleanup(lambda: self.state.close())
        self.state.register([self.asset])
        self.client = FakeS3()
        self.stop = threading.Event()
        self.runner = rp.UploadRunner(self.client, self.target["bucket"], self.root, self.state, self.stop,
                                      wait=lambda seconds: False)

    def test_upload_remote_verification_and_resume_skip(self):
        self.assertEqual(self.runner.process(self.asset, verify_download=True), "uploaded")
        row = self.state.get(self.asset["assetId"])
        self.assertEqual(row["status"], "verified")
        self.assertEqual(row["remote_bytes"], self.asset["bytes"])
        self.assertTrue(row["verified_at"])
        self.assertTrue(row["download_verified_at"])
        self.assertNotEqual(row["etag"].strip('"'), self.asset["sha256"])
        self.assertEqual(self.runner.process(self.asset, verify_download=True), "skipped")
        self.assertEqual(sum(c[0] == "put" for c in self.client.calls), 1)
        self.assertEqual(self.state.summary([self.asset]), {"assets": 1, "uploaded": 1, "verified": 1,
                                                          "failed": 0, "remaining": 0, "pending": 0})

    def test_hash_mismatch_stops_before_network_even_if_verified(self):
        self.assertEqual(self.runner.process(self.asset), "uploaded")
        self.client.calls.clear()
        self.path.write_bytes(b"X" * self.asset["bytes"])
        self.assertEqual(self.runner.process(self.asset), "failed")
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.state.get(self.asset["assetId"])["last_error"], "local_integrity")

    def test_remote_conflict_and_access_denied_never_put(self):
        self.client.objects[self.asset["objectKey"]] = {"body": self.path.read_bytes(), "metadata": {"sha256": "wrong"}}
        self.assertEqual(self.runner.process(self.asset), "failed")
        self.assertEqual(self.state.get(self.asset["assetId"])["last_error"], "remote_conflict")
        self.assertFalse(any(c[0] == "put" for c in self.client.calls))
        self.state.retry_failed([self.asset["assetId"]])
        self.client.objects.clear(); self.client.calls.clear()
        self.client.head_failures = [s3_error(403, "AccessDenied", "FAKE_SECRET_NEVER_LOG")]
        self.assertEqual(self.runner.process(self.asset), "failed")
        self.assertEqual(len(self.client.calls), 1)
        self.assertNotIn("FAKE_SECRET_NEVER_LOG", json.dumps(self.state.get(self.asset["assetId"])))

    def test_lost_put_response_reconciles_without_duplicate_upload(self):
        self.client.lost_put_response = True
        self.assertEqual(self.runner.process(self.asset), "skipped")
        self.assertEqual(sum(c[0] == "put" for c in self.client.calls), 1)
        self.assertEqual(self.state.get(self.asset["assetId"])["status"], "verified")

    def test_crash_recovery_after_upload_before_state_commit(self):
        self.client.objects[self.asset["objectKey"]] = {"body": self.path.read_bytes(),
            "metadata": {"sha256": self.asset["sha256"], "asset-id": self.asset["assetId"]}}
        self.state.update(self.asset["assetId"], status="uploading")
        self.state.close()
        self.state = UploadState(self.dbpath, self.target)
        self.state.recover()
        self.runner.state = self.state
        self.assertEqual(self.runner.process(self.asset), "skipped")
        self.assertFalse(any(c[0] == "put" for c in self.client.calls))

    def test_retry_is_bounded_persisted_and_failed_only(self):
        self.client.head_failures = [s3_error(503) for _ in range(5)]
        self.assertEqual(self.runner.process(self.asset), "failed")
        self.assertEqual(len(self.client.calls), 3)
        self.assertEqual(self.state.get(self.asset["assetId"])["failures"], 3)
        self.assertEqual(self.runner.process(self.asset), "failed")
        self.assertEqual(len(self.client.calls), 3)
        self.assertEqual(self.state.retry_failed([self.asset["assetId"]]), 1)
        self.client.head_failures.clear()
        self.assertEqual(self.runner.process(self.asset), "uploaded")
        self.assertEqual(self.state.retry_failed([self.asset["assetId"]]), 0)

    def test_download_hash_mismatch_does_not_become_verified(self):
        self.client.bad_download = True
        self.assertEqual(self.runner.process(self.asset, verify_download=True), "failed")
        self.assertEqual(self.state.get(self.asset["assetId"])["status"], "failed")
        self.assertEqual(self.state.get(self.asset["assetId"])["last_error"], "remote_integrity")

    def test_interrupted_before_work_preserves_pending(self):
        self.stop.set()
        self.assertEqual(self.runner.process(self.asset), "interrupted")
        self.assertEqual(self.client.calls, [])
        self.assertEqual(self.state.get(self.asset["assetId"])["status"], "pending")

    def test_target_binding_cannot_reuse_state_for_another_bucket(self):
        other = dict(self.target, bucket="different-bucket")
        with self.assertRaises(UploadError): UploadState(self.dbpath, other)

    def test_credentials_validate_target_and_errors_do_not_echo_values(self):
        p = self.root / "secret.env"
        values = {"R2_ACCOUNT_ID": self.target["accountId"], "R2_BUCKET": self.target["bucket"],
                  "R2_ENDPOINT": self.target["endpoint"], "R2_ACCESS_KEY_ID": "b" * 32,
                  "R2_SECRET_ACCESS_KEY": "c" * 64}
        p.write_text("\n".join(k + "=" + v for k,v in values.items()), encoding="utf-8")
        credentials = rp.read_secrets(p, self.target)
        self.assertEqual(credentials["R2_BUCKET"], self.target["bucket"])
        p.write_text(p.read_text() + "\nR2_SECRET_ACCESS_KEY=DO_NOT_PRINT_THIS", encoding="utf-8")
        with self.assertRaises(UploadError) as caught: rp.read_secrets(p, self.target)
        self.assertNotIn("DO_NOT_PRINT_THIS", str(caught.exception))
        kind, code = rp.safe_error(s3_error(503, "DO_NOT_PRINT_THIS", "DO_NOT_PRINT_THIS"))
        self.assertEqual(kind, "transient")
        self.assertNotIn("DO_NOT_PRINT_THIS", code)

    def test_sdk_model_supports_conditional_put_and_checksums_without_network(self):
        values = {"R2_ACCESS_KEY_ID": "b" * 32, "R2_SECRET_ACCESS_KEY": "c" * 64}
        client = rp.create_client(values, self.target, 2)
        self.addCleanup(client.close)
        shape = client.meta.service_model.operation_model("PutObject").input_shape.members
        self.assertTrue({"IfNoneMatch", "ContentMD5", "Metadata", "ContentLength"} <= shape.keys())
        self.assertEqual(client.meta.config.retries["total_max_attempts"], 1)
        self.assertEqual(client.meta.config.request_checksum_calculation, "when_required")

    def test_pinned_delivery_rejects_changed_manifest_and_readonly_status(self):
        manifest = rp.load_delivery(ROOT / "delivery/manifest.vi.json")
        self.assertEqual(len(manifest["assets"]), 983)
        p = self.root / "manifest.json"
        p.write_bytes((ROOT / "delivery/manifest.vi.json").read_bytes() + b"\n")
        with self.assertRaises(UploadError): rp.load_delivery(p)
        before = self.dbpath.read_bytes()
        self.assertEqual(rp.read_status(self.dbpath, [self.asset], self.target)["remaining"], 1)
        self.assertEqual(before, self.dbpath.read_bytes())
        absent = self.root / "absent.sqlite"
        self.assertEqual(rp.read_status(absent, [self.asset], self.target)["pending"], 1)
        self.assertFalse(absent.exists())

    def cli(self):
        spec = importlib.util.spec_from_file_location("upload_r2", ROOT / "scripts/upload-r2.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_cli_retry_selection_excludes_verified_and_pending(self):
        cli = self.cli()
        pending = dict(self.asset, assetId="pending", objectKey="pending-key")
        failed = dict(self.asset, assetId="failed", objectKey="failed-key")
        self.state.register([pending, failed])
        self.state.update(self.asset["assetId"], status="verified")
        self.state.update("failed", status="failed")
        assets = {a["assetId"]: a for a in (self.asset, pending, failed)}
        self.assertEqual(cli.select_assets(assets, retry_failed=True, state=self.state), [failed])
        with self.assertRaises(UploadError): cli.select_assets(assets, ids=["unknown"])
        with self.assertRaises(UploadError): cli.select_assets(assets, ids=["pending", "pending"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.arguments(["--verify-download"])

    def test_cli_full_resume_synthetic_and_status_without_credentials(self):
        cli = self.cli()
        assets = {self.asset["assetId"]: self.asset}
        for n in range(3):
            a = dict(self.asset, assetId="synthetic-" + str(n), objectKey="synthetic-key-" + str(n))
            assets[a["assetId"]] = a
        with patch.object(cli, "ROOT", self.root), patch.object(cli, "STATE", self.dbpath), \
             patch.object(cli, "create_client", return_value=self.client), \
             patch.object(cli, "read_secrets", return_value={}), patch.object(self.client, "close", create=True), \
             patch.object(cli.signal, "signal"), redirect_stdout(io.StringIO()):
            self.assertEqual(cli.execute(cli.arguments([]), assets, self.target), 0)
            self.assertEqual(self.state.summary(list(assets.values()))["verified"], 4)
            self.assertEqual(cli.execute(cli.arguments([]), assets, self.target), 0)
            self.assertEqual(sum(c[0] == "put" for c in self.client.calls), 4)
            self.assertEqual(cli.execute(cli.arguments(["--retry-failed"]), assets, self.target), 0)
        with patch.object(cli, "STATE", self.dbpath), \
             patch.object(cli, "load_delivery", return_value={"assets": assets}), \
             patch.object(cli, "target_config", return_value=self.target), \
             patch.object(cli, "read_secrets", side_effect=AssertionError("status must not load credentials")), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["--status"]), 0)

    def test_conditional_put_race_reconciles_instead_of_overwriting(self):
        original_put = self.client.put_object
        def racing_put(**kw):
            self.client.objects[kw["Key"]] = {"body": self.path.read_bytes(), "metadata": dict(kw["Metadata"])}
            return original_put(**kw)
        with patch.object(self.client, "put_object", side_effect=racing_put):
            self.assertEqual(self.runner.process(self.asset), "skipped")
        self.assertEqual(self.state.get(self.asset["assetId"])["status"], "verified")

    def test_cli_rejects_writable_hardlinks_before_any_mutation(self):
        cli = self.cli()
        for relative in ("state/r2-transfers.sqlite", "state/r2-transfers.sqlite-wal",
                         "state/r2-transfers.sqlite-shm", "state/upload-r2.lock",
                         "logs/r2-upload.log", "logs/r2-upload.log.1"):
            with self.subTest(relative=relative):
                case = self.root / relative.replace("/", "_").replace(".", "_")
                case.mkdir()
                protected = case / "protected.sqlite"
                db = sqlite3.connect(protected)
                db.execute("CREATE TABLE jobs (asset_id TEXT, status TEXT)")
                db.commit(); db.close()
                before = protected.read_bytes()
                alias = case / relative
                alias.parent.mkdir(parents=True, exist_ok=True)
                os.link(protected, alias)
                with patch.object(cli, "ROOT", case), patch.object(cli, "STATE", case / "state/r2-transfers.sqlite"), \
                     patch.object(cli, "read_secrets", side_effect=AssertionError("must reject before credentials")), \
                     patch.object(cli.signal, "signal"), redirect_stdout(io.StringIO()):
                    try:
                        with self.assertRaises(UploadError):
                            cli.execute(cli.arguments([]), {self.asset["assetId"]: self.asset}, self.target)
                    finally:
                        self.assertEqual(protected.read_bytes(), before, "protected hard-linked bytes changed")


if __name__ == "__main__":
    unittest.main()
