"""B8 tests use tiny synthetic files; no media commands or network."""
import copy
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from catalog_lib import load_json
from download_state import BatchLock, PROFILE, enumerate_jobs, sha256

AVAILABLE = importlib.util.find_spec("delivery_lib") is not None
if AVAILABLE:
    import delivery_lib as dl


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE, "B8 delivery implementation missing")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        full = load_json(ROOT / "catalog/catalog.vi.json")
        self.catalog = dict(full, songs={k: full["songs"][k] for k in ("main:1", "appendix:1")},
                            meditations={k: full["meditations"][k] for k in list(full["meditations"])[:1]})
        self.rows = []
        for i, job in enumerate(enumerate_jobs(self.catalog, self.root)):
            p = Path(job["final_path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(f"synthetic artifact {i}".encode())
            proof = {"probeExitCode": 0, "decodeExitCode": 0,
                     "verifiedAt": "2026-10-10T18:00:00+00:00",
                     "remux": "AAC streamcopy, M4A, faststart",
                     "source": {"streams": [{"codec_type": "audio", "codec_name": "aac",
                                             "sample_rate": "44100", "channels": 2}],
                                "format": {"duration": "12.5"}},
                     "output": {"streams": [{"codec_type": "audio", "codec_name": "aac",
                                             "sample_rate": "44100", "channels": 2}],
                                "format": {"duration": "12.5", "size": str(p.stat().st_size),
                                           "format_name": "mov,mp4,m4a,3gp,3g2,mj2"}}}
            self.rows.append(dict(job, status="completed", byte_size=p.stat().st_size, sha256=sha256(p),
                                  probed_duration=12.5, source_duration=12.5, codec="aac", sample_rate=44100,
                                  channels=2, probe_verified=1, decode_verified=1,
                                  verification_json=json.dumps(proof), warnings_json="[]"))
        self.schema = load_json(ROOT / "schemas/delivery.schema.json")

    def audit(self):
        return dl.audit_assets(self.catalog, self.rows, self.root)

    def manifest(self):
        return dl.make_manifest(self.audit()[0], "a" * 64, "2026-10-11T00:00:00+00:00")

    def test_verified_identity_keys_and_measured_metadata(self):
        assets, warnings = self.audit()
        self.assertEqual(len(assets), 5)
        self.assertEqual(warnings, {})
        main = assets["watv:vi:guide:4177"]
        self.assertEqual(main["logicalId"], "watv:vi:newsong:main:1")
        self.assertEqual(main["durationSeconds"], 12.5)
        self.assertEqual(main["objectKey"], f"audio/v1/watv/vi/newsong/main/0001/guide/4177/{main['sha256']}.m4a")
        appendix = next(a for a in assets.values() if a.get("section") == "appendix")
        self.assertIn("/appendix/0001/", appendix["objectKey"])
        meditation = next(a for a in assets.values() if a["kind"] == "meditation")
        self.assertNotIn("section", meditation)
        self.assertNotIn("number", meditation)
        self.assertEqual(meditation["variant"], "silent")
        self.assertEqual(meditation["logicalId"], meditation["assetId"])
        self.assertIn("/meditations/", meditation["objectKey"])
        self.assertFalse(any(a.get("section") == "main" and a.get("number") == 34 for a in assets.values()))
        for a in assets.values():
            self.assertFalse(Path(a["localPath"]).is_absolute())
            self.assertEqual(sha256(self.root / a["localPath"]), a["sha256"])

    def test_integrity_missing_extra_and_status_block_entire_build(self):
        for mode in ("corrupt", "missing", "extra_file", "pending", "missing_row", "extra_row", "duplicate_row", "duplicate_path"):
            with self.subTest(mode=mode):
                rows = copy.deepcopy(self.rows)
                p = Path(rows[0]["final_path"])
                original = p.read_bytes()
                extra = self.root / "media/audio/v1/watv/vi/unexpected.part.m4a"
                if mode == "corrupt": p.write_bytes(b"x" * len(original))
                elif mode == "missing": p.unlink()
                elif mode == "extra_file": extra.write_bytes(b"extra")
                elif mode == "pending": rows[0]["status"] = "pending"
                elif mode == "missing_row": rows.pop()
                elif mode == "extra_row": rows.append(dict(rows[0], asset_id="watv:vi:guide:999999"))
                elif mode == "duplicate_row": rows.append(rows[0])
                elif mode == "duplicate_path": rows[1]["final_path"] = rows[0]["final_path"]
                try:
                    with self.assertRaises(dl.DeliveryError):
                        dl.audit_assets(self.catalog, rows, self.root)
                finally:
                    p.write_bytes(original)
                    if extra.exists(): extra.unlink()

    def test_state_evidence_and_catalog_join_must_match(self):
        changes = {"sha256": "bad", "byte_size": 0, "probe_verified": 0, "decode_verified": 0,
                   "probed_duration": float("nan"), "codec": "mp3", "sample_rate": 48000,
                   "channels": 1, "fingerprint": "b" * 64, "logical_id": "watv:vi:newsong:main:2",
                   "variant": "silent", "verification_json": "{}", "profile": "{}"}
        for key, value in changes.items():
            with self.subTest(key=key):
                rows = copy.deepcopy(self.rows)
                rows[0][key] = value
                with self.assertRaises(dl.DeliveryError):
                    dl.audit_assets(self.catalog, rows, self.root)

    def test_revision_and_keys_stable_across_time_order_and_project_location(self):
        m = self.manifest()
        later = dl.make_manifest(dict(reversed(list(m["assets"].items()))), "a" * 64, "2026-10-12T00:00:00+00:00")
        self.assertEqual(m["revision"], later["revision"])
        different_catalog = dl.make_manifest(m["assets"], "b" * 64, later["generatedAt"])
        self.assertNotEqual(m["revision"], different_catalog["revision"])
        changed = copy.deepcopy(m["assets"])
        changed[next(iter(changed))]["sha256"] = "b" * 64
        self.assertNotEqual(m["revision"], dl.make_manifest(changed, "a" * 64, later["generatedAt"])["revision"])
        self.assertFalse(dl.validate_manifest(m, self.schema, m, require_counts=False))
        # SQLite's machine-specific paths are checked, but never enter delivery.
        other = self.root / "moved-project"
        moved = copy.deepcopy(self.rows)
        for row, job in zip(moved, enumerate_jobs(self.catalog, other)):
            dest = Path(job["final_path"])
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(Path(row["final_path"]).read_bytes())
            row.update(job)
        moved_assets, _ = dl.audit_assets(self.catalog, moved, other)
        self.assertEqual(m["assets"], moved_assets)
        self.assertEqual(m["revision"], dl.make_manifest(moved_assets, "a" * 64)["revision"])

    def test_malformed_probe_is_rejected(self):
        for value in ("null", "[]", "{bad", '{"probeExitCode":true}', self.rows[0]["verification_json"].replace('"12.5"', '"NaN"')):
            rows = copy.deepcopy(self.rows)
            rows[0]["verification_json"] = value
            with self.subTest(value=value[:35]):
                with self.assertRaises(dl.DeliveryError): dl.audit_assets(self.catalog, rows, self.root)

    def test_redirected_file_is_rejected(self):
        target = Path(self.rows[0]["final_path"])
        original = target.read_bytes()
        outside = self.root / "outside.m4a"
        outside.write_bytes(original)
        target.unlink()
        try:
            try:
                os.symlink(outside, target)
            except OSError:
                target.write_bytes(original)
                self.skipTest("Windows account cannot create file symlinks")
            with self.assertRaises(dl.DeliveryError): self.audit()
        finally:
            if target.is_symlink(): target.unlink()
            target.write_bytes(original)

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_windows_junction_in_media_root_is_rejected(self):
        target = self.root / "outside-folder"
        target.mkdir()
        link = self.root / "media/audio/v1/watv/vi/redirect"
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "New-Item -ItemType Junction -Path $env:AUDIOTP_TEST_LINK -Target $env:AUDIOTP_TEST_TARGET -ErrorAction Stop | Out-Null"],
                       env=dict(os.environ, AUDIOTP_TEST_LINK=str(link), AUDIOTP_TEST_TARGET=str(target)),
                       check=True, capture_output=True)
        try:
            self.assertTrue(link.is_junction())
            with self.assertRaises(dl.DeliveryError): self.audit()
        finally:
            link.rmdir()

    def test_unreadable_extra_subtree_blocks_audit(self):
        from unittest.mock import patch
        hidden = self.root / "media/audio/v1/watv/vi/unreadable-extra"
        hidden.mkdir()
        (hidden / "unexpected.part.m4a").write_bytes(b"extra")
        real_scandir = os.scandir

        def denied_scan(path):
            if Path(path) == hidden:
                raise PermissionError("simulated unreadable subtree")
            return real_scandir(path)

        with patch("delivery_lib.os.scandir", side_effect=denied_scan):
            with self.assertRaises(dl.DeliveryError): self.audit()

    def test_builder_rejects_protected_or_aliased_output_before_audit(self):
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("build_delivery", ROOT / "scripts/build-delivery.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        fixture_manifest = self.manifest()
        for relative in ("catalog/catalog.vi.json", "source/snapshot.json", "state/transfers.sqlite",
                         "media/audio/v1/watv/vi/newsong/main/0001/guide.m4a", "schemas/delivery.schema.json",
                         "delivery/../catalog/catalog.vi.json", "delivery/output.m4a", "delivery/input.json"):
            with self.subTest(relative=relative):
                output = self.root / relative
                output.parent.mkdir(parents=True, exist_ok=True)
                original = output.read_bytes() if output.exists() else b"protected original"
                output.write_bytes(original)
                args = ["build-delivery.py", "--root", str(self.root), "--output", str(output)]
                if relative == "delivery/input.json": args += ["--catalog", str(output)]
                try:
                    with patch.object(sys, "argv", args), redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()), \
                         patch.object(builder, "inspect_inputs", return_value=(fixture_manifest, {})) as audit, \
                         patch.object(builder, "validate_manifest", return_value=[]):
                        self.assertEqual(builder.main(), 1)
                        audit.assert_not_called()
                    self.assertEqual(output.read_bytes(), original)
                finally:
                    output.write_bytes(original)

    @unittest.skipUnless(os.name == "nt", "Windows junction behavior")
    def test_builder_rejects_delivery_directory_junction(self):
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location("build_delivery", ROOT / "scripts/build-delivery.py")
        builder = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        fixture_manifest = self.manifest()
        # Alias under delivery points back into the protected catalog tree.
        target = self.root / "catalog"
        target.mkdir()
        source = target / "catalog.vi.json"
        source.write_bytes(b"original catalog")
        delivery = self.root / "delivery"
        delivery.mkdir()
        link = delivery / "alias"
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "New-Item -ItemType Junction -Path $env:AUDIOTP_TEST_LINK -Target $env:AUDIOTP_TEST_TARGET -ErrorAction Stop | Out-Null"],
                       env=dict(os.environ, AUDIOTP_TEST_LINK=str(link), AUDIOTP_TEST_TARGET=str(target)),
                       check=True, capture_output=True)
        try:
            args = ["build-delivery.py", "--root", str(self.root), "--output", str(link / "catalog.vi.json")]
            with patch.object(sys, "argv", args), redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()), \
                 patch.object(builder, "inspect_inputs", return_value=(fixture_manifest, {})) as audit, \
                 patch.object(builder, "validate_manifest", return_value=[]):
                self.assertEqual(builder.main(), 1)
                audit.assert_not_called()
            self.assertEqual(source.read_bytes(), b"original catalog")
        finally:
            link.rmdir()

    def test_strict_schema_and_semantic_validation_reject_tampering(self):
        good = self.manifest()
        for mode in ("status", "source", "tmp", "absolute", "traversal", "wrong_key", "wrong_number", "duration", "sha", "meditation_variant", "bad_time", "revision", "extra_asset"):
            with self.subTest(mode=mode):
                m = copy.deepcopy(good)
                a = m["assets"]["watv:vi:guide:4177"]
                if mode == "status": a["status"] = "completed"
                elif mode == "source": a["source"] = {"hlsUrl": "https://example.com"}
                elif mode == "tmp": a["localPath"] = "tmp/downloads/output.part.m4a"
                elif mode == "absolute": a["localPath"] = "D:/Workspace/AudioTP/file.m4a"
                elif mode == "traversal": a["localPath"] = "media/audio/v1/watv/vi/../../file.m4a"
                elif mode == "wrong_key": a["objectKey"] = next(x["objectKey"] for x in m["assets"].values() if x["assetId"] != a["assetId"])
                elif mode == "wrong_number": a["number"] = 34
                elif mode == "duration": a["durationSeconds"] = 13
                elif mode == "sha": a["sha256"] += "\n"
                elif mode == "meditation_variant": next(x for x in m["assets"].values() if x["kind"] == "meditation")["variant"] = "guide"
                elif mode == "bad_time": m["generatedAt"] = "yesterday"
                elif mode == "revision": m["revision"] = "sha256:" + "b" * 64
                elif mode == "extra_asset": m["assets"]["watv:vi:guide:999999"] = dict(a, assetId="watv:vi:guide:999999")
                self.assertTrue(dl.validate_manifest(m, self.schema, good, require_counts=False))
        self.assertTrue(dl.validate_manifest(good, self.schema, good), "Production validator must reject a five-asset subset")

    def test_readonly_database_and_existing_batch_lock(self):
        p = self.root / "state/transfers.sqlite"
        p.parent.mkdir()
        db = sqlite3.connect(p)
        db.execute("CREATE TABLE jobs(asset_id TEXT)")
        db.execute("INSERT INTO jobs VALUES ('one')")
        db.commit(); db.close()
        before = p.read_bytes()
        self.assertEqual(dl.read_rows(p), [{"asset_id": "one"}])
        self.assertEqual(p.read_bytes(), before)
        with self.assertRaises(sqlite3.OperationalError):
            dl.read_rows(self.root / "missing.sqlite")
        with BatchLock(p.with_name("download-media.lock")):
            with self.assertRaises(RuntimeError):
                with dl.delivery_lock(p): pass

    def test_failed_atomic_write_preserves_previous_manifest(self):
        p = self.root / "delivery/manifest.vi.json"
        p.parent.mkdir()
        p.write_bytes(b"previous valid result")
        from unittest.mock import patch
        with patch("delivery_lib.os.replace", side_effect=OSError("simulated disk error")):
            with self.assertRaises(OSError): dl.write_atomic(p, self.manifest())
        self.assertEqual(p.read_bytes(), b"previous valid result")
        self.assertEqual(list(p.parent.iterdir()), [p])


if __name__ == "__main__":
    unittest.main()
