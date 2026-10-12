"""B6/B7 behavior tests; no real network or external FFmpeg here."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import catalog_lib
AVAILABLE = importlib.util.find_spec("download_state") is not None
if AVAILABLE:
    import download_state as ds


class StateTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE, "Production state/model missing")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.jobs = ds.enumerate_jobs(catalog_lib.load_json(catalog_lib.CATALOG), self.root)
        self.db = self.root / "state/transfers.sqlite"

    def test_enumeration_paths_fingerprints_and_gaps(self):
        self.assertEqual(len(self.jobs), 983)
        self.assertEqual(len({j["asset_id"] for j in self.jobs}), 983)
        self.assertEqual(len({j["final_path"] for j in self.jobs}), 983)
        main = next(j for j in self.jobs if j["key"] == "main:1" and j["variant"] == "guide")
        appendix = next(j for j in self.jobs if j["key"] == "appendix:1" and j["variant"] == "guide")
        silent = next(j for j in self.jobs if j["variant"] == "silent")
        self.assertTrue(main["final_path"].replace("\\", "/").endswith("newsong/main/0001/guide.m4a"))
        self.assertTrue(appendix["final_path"].replace("\\", "/").endswith("newsong/appendix/0001/guide.m4a"))
        self.assertIn("/meditations/", silent["final_path"].replace("\\", "/"))
        self.assertFalse({"main:34", "main:242", "main:300", "main:306", "main:367"} & {j["key"] for j in self.jobs})
        self.assertEqual(self.jobs, ds.enumerate_jobs(catalog_lib.load_json(catalog_lib.CATALOG), self.root))
        changed = catalog_lib.load_json(catalog_lib.CATALOG)
        changed["songs"]["main:1"]["variants"]["guide"]["source"]["hlsUrl"] += "?changed=1"
        self.assertNotEqual(main["fingerprint"], ds.enumerate_jobs(changed, self.root)[0]["fingerprint"])

    def test_state_persistence_interruption_and_failed_retry_round(self):
        state = ds.State(self.db)
        state.register(self.jobs[:2])
        job = self.jobs[0]
        state.update(job["asset_id"], status="downloading", attempts=1)
        state.close()
        state = ds.State(self.db)
        self.addCleanup(state.close)
        self.assertEqual(state.recover_interrupted(), 1)
        self.assertEqual(state.get(job["asset_id"])["status"], "pending")
        state.update(job["asset_id"], status="failed", failures=3, last_error="timeout", error_kind="transient")
        state.retry_failed()
        row = state.get(job["asset_id"])
        self.assertEqual((row["status"], row["failures"], row["attempts"]), ("pending", 0, 1))

    def test_changed_fingerprint_invalidates_completed_evidence(self):
        state = ds.State(self.db)
        self.addCleanup(state.close)
        state.register(self.jobs[:1]); job = self.jobs[0]
        state.update(job["asset_id"], status="completed", sha256="old", byte_size=100, decode_verified=1)
        changed = dict(job, fingerprint="changed")
        state.register([changed])
        row = state.get(job["asset_id"])
        self.assertEqual(row["status"], "pending")
        self.assertIsNone(row["sha256"])
        self.assertEqual(row["decode_verified"], 0)

    def test_exclusive_process_lock(self):
        with ds.BatchLock(self.root / "batch.lock"):
            with self.assertRaises(RuntimeError):
                with ds.BatchLock(self.root / "batch.lock"):
                    pass
        with ds.BatchLock(self.root / "batch.lock"):
            pass


PIPELINE_AVAILABLE = importlib.util.find_spec("download_pipeline") is not None
if PIPELINE_AVAILABLE:
    import download_pipeline as dp


class PipelineTests(unittest.TestCase):
    def setUp(self):
        StateTests.setUp(self)
        self.assertTrue(PIPELINE_AVAILABLE, "Production pipeline missing")
        self.state = ds.State(self.db)
        self.addCleanup(self.state.close)
        self.job = self.jobs[0]
        self.state.register([self.job])
        self.stop = threading.Event()

    def backend(self, transient=0, permanent=False, corrupt=False, interrupt=False):
        job = self.job

        class Fake:
            preparations = 0
            verifies = 0
            def prepare(inner, current, stop):
                inner.preparations += 1
                if permanent: raise dp.MediaFailure("auth denied", "access")
                if inner.preparations <= transient: raise dp.MediaFailure("timeout", "transient")
                if interrupt: raise dp.Interrupted()
                return {"source": {"streams": [{"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100", "channels": 2}], "format": {"duration": "125"}}, "input": "checked.m3u8"}
            def remux(inner, current, prepared, stop):
                Path(current["temp_path"]).write_bytes(b"valid-test-media")
            def verify(inner, current, path, prepared, stop):
                inner.verifies += 1
                if corrupt: raise dp.MediaFailure("decode failed", "integrity")
                return {"byte_size": Path(path).stat().st_size, "sha256": ds.sha256(path), "probed_duration": 125.0,
                        "source_duration": 125.0, "codec": "aac", "sample_rate": 44100, "channels": 2,
                        "channel_layout": "stereo", "probe_verified": 1, "decode_verified": 1,
                        "verification_json": '{"source":{"streams":[],"format":{}}}', "warnings_json": "[]"}
        return Fake()

    def run_job(self, backend):
        return dp.process(self.job, self.state, backend, self.stop, backoff=(0, 0))

    def test_completed_skip_and_tampered_or_missing_output_repair(self):
        first = self.backend()
        self.assertEqual(self.run_job(first), "completed")
        self.assertEqual(self.state.get(self.job["asset_id"])["status"], "completed")
        self.assertFalse(Path(self.job["temp_path"]).exists())
        second = self.backend()
        self.assertEqual(self.run_job(second), "skipped")
        self.assertEqual(second.preparations, 0)
        Path(self.job["final_path"]).write_bytes(b"tampered")
        self.assertEqual(self.run_job(second), "completed")
        self.assertEqual(second.preparations, 1)
        Path(self.job["final_path"]).unlink()
        self.assertEqual(self.run_job(second), "completed")

    def test_bounded_retry_and_failure_persistence(self):
        backend = self.backend(transient=2)
        self.assertEqual(self.run_job(backend), "completed")
        self.assertEqual(self.state.get(self.job["asset_id"])["attempts"], 3)
        self.assertEqual(backend.preparations, 3)
        self.state.update(self.job["asset_id"], status="pending", sha256=None, decode_verified=0, failures=0)
        backend = self.backend(transient=99)
        self.assertEqual(self.run_job(backend), "failed")
        self.assertEqual(backend.preparations, 3)
        row = self.state.get(self.job["asset_id"])
        self.assertEqual((row["status"], row["failures"], row["error_kind"]), ("failed", 3, "transient"))
        self.assertEqual(self.run_job(self.backend()), "failed")

    def test_permanent_access_failure_not_retried_and_no_final(self):
        backend = self.backend(permanent=True)
        self.assertEqual(self.run_job(backend), "failed")
        self.assertEqual(backend.preparations, 1)
        self.assertFalse(Path(self.job["final_path"]).exists())
        self.state.retry_failed()
        self.assertEqual(self.state.get(self.job["asset_id"])["status"], "failed")

    def test_decode_failure_never_published_and_unknown_final_quarantined(self):
        final = Path(self.job["final_path"])
        final.parent.mkdir(parents=True); final.write_bytes(b"unknown-final")
        self.assertEqual(self.run_job(self.backend(corrupt=True)), "failed")
        self.assertFalse(final.exists())
        self.assertTrue(list(Path(self.job["work_dir"]).glob("quarantine-*.m4a")))
        self.assertTrue(Path(self.job["temp_path"]).exists())
        self.assertEqual(self.state.get(self.job["asset_id"])["decode_verified"], 0)

    def test_interruption_recovery_and_crash_after_rename(self):
        self.assertEqual(self.run_job(self.backend(interrupt=True)), "interrupted")
        self.assertEqual(self.state.get(self.job["asset_id"])["status"], "pending")
        real_update = self.state.update
        def crash(asset_id, **fields):
            if fields.get("status") == "completed": raise RuntimeError("simulated power loss after rename")
            return real_update(asset_id, **fields)
        with patch.object(self.state, "update", side_effect=crash), self.assertRaises(RuntimeError):
            self.run_job(self.backend())
        self.assertTrue(Path(self.job["final_path"]).exists())
        self.assertEqual(self.state.get(self.job["asset_id"])["status"], "verifying")
        self.state.recover_interrupted()
        backend = self.backend()
        self.assertEqual(self.run_job(backend), "skipped")
        self.assertEqual(backend.preparations, 0)
        self.assertEqual(self.state.get(self.job["asset_id"])["status"], "completed")

    def test_ffprobe_parser_rejects_bad_duration_codec_video_or_profile_change(self):
        source = {"streams": [{"codec_type": "audio", "codec_name": "aac", "sample_rate": "44100", "channels": 2}], "format": {"duration": "125"}}
        output = copy.deepcopy(source); output["format"]["format_name"] = "mov,mp4,m4a,3gp,3g2,mj2"
        self.assertEqual(dp.validate_media(source, output)["codec"], "aac")
        for field, value in (("codec_name", "mp3"), ("codec_type", "video"), ("sample_rate", "48000"), ("channels", 1)):
            bad = copy.deepcopy(output); bad["streams"][0][field] = value
            with self.subTest(field=field), self.assertRaises(dp.MediaFailure):
                dp.validate_media(source, bad)
        for duration in ("nan", "0", "-1", None):
            bad = copy.deepcopy(output); bad["format"]["duration"] = duration
            with self.subTest(duration=duration), self.assertRaises(dp.MediaFailure):
                dp.validate_media(source, bad)


if __name__ == "__main__":
    unittest.main()
