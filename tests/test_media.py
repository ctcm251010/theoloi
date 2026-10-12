"""Offline tests for the bounded B4/B5 experiment, never real media/network."""
import copy
import importlib.util
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
AVAILABLE = importlib.util.find_spec("media_test_lib") is not None
if AVAILABLE:
    import media_test_lib as media
import catalog_lib as catalog

BASE = "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/test.m4a/playlist.m3u8"


def probe(codec="aac", duration="126.1", rate="44100", channels=2):
    return {"format": {"duration": duration}, "streams": [
        {"codec_type": "audio", "codec_name": codec, "sample_rate": rate, "channels": channels}]}


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE, "B4/B5 experiment helpers not implemented")

    def test_fixed_sample_allowlist_and_missing_input(self):
        c = catalog.load_json(catalog.CATALOG)
        rows = media.select_samples(c)
        self.assertEqual(len(rows), 11)
        self.assertEqual(len({r["asset"]["assetId"] for r in rows}), 11)
        self.assertEqual({r["key"] for r in rows}, {"main:1", "main:335", "main:343", "main:452", "appendix:1", "watv:vi:silent:19977"})
        del c["songs"]["main:335"]
        with self.assertRaises(ValueError):
            media.select_samples(c)

    def test_master_media_and_clear_method_none(self):
        master = media.inspect_playlist('#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=128291,CODECS="mp4a.40.2"\nchunklist.m3u8\n', BASE)
        self.assertEqual(master["type"], "master")
        self.assertTrue(master["children"][0].endswith("chunklist.m3u8"))
        parsed = media.inspect_playlist('#EXTM3U\n#EXT-X-KEY:METHOD=NONE\n#EXTINF:10.5,\na.ts\n#EXTINF:1.5,\nb.ts\n#EXT-X-ENDLIST\n', BASE)
        self.assertEqual(parsed["type"], "media")
        self.assertEqual(parsed["duration"], 12)
        self.assertEqual(parsed["segmentExtensions"], [".ts"])
        self.assertFalse(parsed["encrypted"])

    def test_stop_encryption_and_unsafe_references_before_fetch(self):
        for tag in ('#EXT-X-KEY:METHOD=AES-128,URI="key.bin"',
                    '#EXT-X-SESSION-KEY:METHOD=SAMPLE-AES,URI="key.bin"',
                    '#EXT-X-KEY:URI="key.bin"'):
            with self.subTest(tag=tag), self.assertRaises(media.AccessStop):
                media.inspect_playlist(f'#EXTM3U\n{tag}\n#EXTINF:1,\na.ts\n#EXT-X-ENDLIST\n', BASE)
        for reference in ('http://vod.watv.org/a.ts', 'https://other.example/a.ts',
                          'file:///etc/passwd', 'a.ts?token=secret', 'https://user:pass@vod.watv.org/a.ts'):
            with self.subTest(reference=reference), self.assertRaises(media.AccessStop):
                media.inspect_playlist(f'#EXTM3U\n#EXTINF:1,\n{reference}\n#EXT-X-ENDLIST\n', BASE)

    def test_malformed_live_and_oversized_playlists_fail(self):
        for text in ('<html>Login</html>', '#EXTM3U\n', '#EXTM3U\n#EXTINF:1,\na.ts\n',
                     '#EXTM3U\n#EXTINF:601,\na.ts\n#EXT-X-ENDLIST\n',
                     '#EXTM3U\n#EXTINF:nan,\na.ts\n#EXT-X-ENDLIST\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                media.inspect_playlist(text, BASE)

    def test_integrity_profile_duration_and_stream_mismatches(self):
        self.assertEqual(media.validate_output(probe(), probe()), [])
        self.assertEqual(media.validate_output(probe(), probe(duration="126.2")), [])
        for bad in (probe(codec="mp3"), probe(duration="129"), probe(duration="0"),
                    probe(duration="NaN"), probe(rate="48000"), probe(channels=1),
                    {"streams": [], "format": {"duration": "126"}},
                    {"streams": probe()["streams"] * 2, "format": {"duration": "126"}}):
            with self.subTest(output=bad):
                self.assertTrue(media.validate_output(probe(), bad))
        self.assertTrue(media.validate_output(probe(codec="opus"), probe(codec="opus")))

    def test_cli_has_no_bulk_or_arbitrary_url_mode(self):
        cli = [sys.executable, str(ROOT / "scripts/test-media.py")]
        result = subprocess.run(cli + ["--list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 11)
        for option in ("--all", "--url", "--catalog", "--sample"):
            with self.subTest(option=option):
                result = subprocess.run(cli + [option, "invalid"], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("unrecognized arguments", result.stderr)

    def test_failed_and_timed_out_processes_keep_evidence_and_raise(self):
        spec = importlib.util.spec_from_file_location("media_runner", ROOT / "scripts/test-media.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            with self.assertRaises(ValueError):
                runner.command(folder, "failure", [sys.executable, "-c", "import sys;print('error',file=sys.stderr);sys.exit(7)"])
            self.assertEqual(catalog.load_json(folder / "failure.command.json")["exitCode"], 7)
            self.assertIn("error", (folder / "failure.stderr.txt").read_text())
            with self.assertRaises(ValueError):
                runner.command(folder, "timeout", [sys.executable, "-c", "while True: pass"], timeout=0.05)
            self.assertTrue(catalog.load_json(folder / "timeout.command.json")["timedOut"])

    def test_pinned_playlist_contains_only_validated_media_references(self):
        self.assertTrue(hasattr(media, "pinned_playlist"), "Pinned checked input not implemented")
        text = '#EXTM3U\n#EXT-X-SESSION-DATA:DATA-ID="example",URI="https://other.example/data"\n#EXT-X-KEY:METHOD=NONE\n#EXTINF:10.5,\na.aac\n#EXTINF:1.5,\nb.aac\n#EXT-X-ENDLIST\n'
        parsed = media.inspect_playlist(text, BASE)
        pinned = media.pinned_playlist(parsed)
        self.assertNotIn("KEY", pinned)
        self.assertNotIn("SESSION-DATA", pinned)
        self.assertNotIn("other.example", pinned)
        self.assertIn("https://vod.watv.org/", pinned)
        reparsed = media.inspect_playlist(pinned, BASE)
        self.assertEqual(reparsed["segments"], parsed["segments"])
        self.assertEqual(reparsed["duration"], 12)

    def test_redirected_playlist_resolves_children_against_final_url(self):
        spec = importlib.util.spec_from_file_location("media_runner_redirect", ROOT / "scripts/test-media.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        final = BASE.replace("test.m4a/playlist.m3u8", "moved.m4a/playlist.m3u8")

        class Response:
            status = 200
            headers = {"Content-Type": "application/vnd.apple.mpegurl"}
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def geturl(self): return final
            def read(self, limit): return b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=128000\nchild.m3u8\n'

        class Opener:
            def open(self, *args, **kwargs): return Response()

        with tempfile.TemporaryDirectory() as name, patch.object(runner.urllib.request, "build_opener", return_value=Opener()):
            parsed, access = runner.read_playlist(BASE, Path(name), "redirect")
            self.assertEqual(access["finalUrl"], final)
            self.assertEqual(parsed["children"], [final.rsplit("/", 1)[0] + "/child.m3u8"])


if __name__ == "__main__":
    unittest.main()
