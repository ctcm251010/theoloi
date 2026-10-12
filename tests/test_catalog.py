"""Behavior tests for B3: these must catch mispairing and false validation passes."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
AVAILABLE = importlib.util.find_spec("catalog_lib") is not None
if AVAILABLE:
    import catalog_lib as lib


def record(number, audio_id, appendix=0, title="Bài mẫu", duration="00:02:06"):
    return {"title": title, "newsongDispNo": number, "playTime": duration,
            "categoryNm": "Chủ đề", "jsonKey": audio_id,
            "songUrl": f"https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/{audio_id}.m4a/playlist.m3u8",
            "appendixYn": appendix, "newsongAudioId": audio_id}


def small_snapshot():
    return {"lists": {
        "guideSongList": [record(1, 10), record(1, 11, 1, "Phụ lục")],
        "instrumentalSongList": [record(1, 21, 1, "Phụ lục", "00:02:04"), record(1, 20)],
        "silentSongList": [record(1, 30, title="Ngẫm nghĩ", duration="00:00:49")]}}


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE, "B3 catalog builder/validator is not implemented")

    def test_join_distinguishes_appendix_when_arrays_are_reversed(self):
        c = lib.build_catalog(small_snapshot())
        self.assertEqual(set(c["songs"]), {"main:1", "appendix:1"})
        self.assertEqual(c["songs"]["main:1"]["variants"]["instrumental"]["source"]["audioId"], "20")
        self.assertEqual(c["songs"]["appendix:1"]["variants"]["instrumental"]["durationSeconds"], 124)
        self.assertEqual(c["songs"]["appendix:1"]["variants"]["guide"]["durationSeconds"], 126)
        self.assertEqual(set(c["meditations"]), {"watv:vi:silent:30"})

    def test_builder_rejects_conflicting_titles_or_duplicate_pair_keys(self):
        for mutation in ("title", "duplicate"):
            with self.subTest(mutation=mutation):
                s = small_snapshot()
                if mutation == "title":
                    s["lists"]["instrumentalSongList"][1]["title"] = "Sai bài"
                else:
                    s["lists"]["guideSongList"].append(record(1, 999))
                with self.assertRaises(ValueError):
                    lib.build_catalog(s)

    def test_builder_rejects_null_missing_boolean_and_empty_source_fields(self):
        for field, value in (("title", "  "), ("playTime", "00:65:00"),
                             ("newsongDispNo", True), ("appendixYn", 2),
                             ("songUrl", "http://example.org/playlist.m3u8"),
                             ("jsonKey", 999), ("categoryNm", None)):
            with self.subTest(field=field):
                s = small_snapshot()
                s["lists"]["guideSongList"][0][field] = value
                with self.assertRaises(ValueError):
                    lib.build_catalog(s)
        s = small_snapshot()
        del s["lists"]["guideSongList"][0]["title"]
        with self.assertRaises(ValueError):
            lib.build_catalog(s)
        s["lists"]["guideSongList"][0] = None
        with self.assertRaises(ValueError):
            lib.build_catalog(s)

    def test_duplicate_json_keys_and_nonfinite_numbers_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            for content in ('{"songs":{},"songs":{}}', '{"x":NaN}', '{"x":Infinity}'):
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    lib.load_json(path)


class FullSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(AVAILABLE, "B3 library is missing")
        self.assertTrue(hasattr(lib, "validate_catalog"), "B3 schema/semantic validator is not implemented")
        self.snapshot = lib.load_json(lib.SNAPSHOT)
        self.catalog = lib.build_catalog(self.snapshot)
        self.schema = lib.load_json(lib.SCHEMA)

    def test_real_snapshot_counts_and_representative_records(self):
        c = self.catalog
        self.assertEqual(len(c["songs"]), 485)
        self.assertEqual(sum(v["section"] == "main" for v in c["songs"].values()), 480)
        self.assertEqual(sum(v["section"] == "appendix" for v in c["songs"].values()), 5)
        self.assertEqual(len(c["meditations"]), 13)
        self.assertNotIn("main:34", c["songs"])
        self.assertNotEqual(c["songs"]["main:1"]["id"], c["songs"]["appendix:1"]["id"])
        for key in ("main:1", "main:33", "main:35", "appendix:1", "appendix:5"):
            row = c["songs"][key]
            self.assertNotEqual(row["variants"]["guide"]["source"]["audioId"], row["variants"]["instrumental"]["source"]["audioId"])
        self.assertEqual(c["songs"]["main:1"]["variants"]["guide"]["source"]["audioId"], "4177")
        self.assertEqual(c["songs"]["appendix:1"]["variants"]["guide"]["source"]["audioId"], "25495")
        self.assertEqual(c["meditations"]["watv:vi:silent:19977"]["asset"]["durationSeconds"], 49)
        self.assertEqual(c["meditations"]["watv:vi:silent:19976"]["sourceDisplayNumber"], 474)
        self.assertEqual(lib.validate_catalog(c, self.snapshot, self.schema), [])

    def test_reordered_source_is_byte_identical(self):
        for rows in self.snapshot["lists"].values():
            rows.reverse()
        self.assertEqual(lib.json_text(lib.build_catalog(self.snapshot)), lib.json_text(self.catalog))

    def test_schema_rejects_malformed_and_transfer_fields(self):
        from jsonschema import Draft202012Validator, FormatChecker
        validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        changes = [
            (("schemaVersion",), 2), (("provider",), "other"), (("locale",), "en"),
            (("collectionId",), "silent"), (("songs", "main:1", "section"), "silent"),
            (("songs", "main:1", "number"), 0), (("songs", "main:1", "number"), True),
            (("songs", "main:1", "title"), "  "), (("songs", "main:1", "category"), None),
            (("songs", "main:1", "variants"), {}),
            (("songs", "main:1", "variants", "silent"), {}),
            (("songs", "main:1", "variants", "guide", "sourceDuration"), "00:60:00"),
            (("songs", "main:1", "variants", "guide", "durationSeconds"), -1),
            (("songs", "main:1", "variants", "guide", "source", "hlsUrl"), "http://example.org/playlist.m3u8"),
            (("meditations", "watv:vi:silent:19977", "sourceDisplayNumber"), None),
        ]
        for path, value in changes:
            with self.subTest(path=path):
                c = copy.deepcopy(self.catalog)
                target = c
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                self.assertTrue(list(validator.iter_errors(c)))
                self.assertTrue(lib.validate_catalog(c, self.snapshot, self.schema))
        for field in ("downloaded", "uploaded", "localPath", "failed", "retry", "r2Url"):
            for level in ("root", "song", "asset", "source", "meditation"):
                with self.subTest(field=field, level=level):
                    c = copy.deepcopy(self.catalog)
                    targets = {"root": c, "song": c["songs"]["main:1"],
                               "asset": c["songs"]["main:1"]["variants"]["guide"],
                               "source": c["songs"]["main:1"]["variants"]["guide"]["source"],
                               "meditation": c["meditations"]["watv:vi:silent:19977"]}
                    targets[level][field] = "forbidden"
                    self.assertTrue(list(validator.iter_errors(c)))

    def test_semantics_reject_count_key_id_duration_and_source_swaps(self):
        def mutate(name, c):
            row = c["songs"]["main:1"]
            guide = row["variants"]["guide"]
            other = c["songs"]["main:2"]
            if name == "missing-song": del c["songs"]["main:35"]
            elif name == "fake-main":
                v = c["songs"].pop("main:35"); v.update(number=34, id="watv:vi:newsong:main:34"); c["songs"]["main:34"] = v
            elif name == "wrong-appendix": c["songs"].pop("appendix:5")
            elif name == "key-mismatch": c["songs"]["main:999"] = c["songs"].pop("main:1")
            elif name == "duplicate-logical-id": row["id"] = other["id"]
            elif name == "duplicate-asset-id": guide["assetId"] = other["variants"]["guide"]["assetId"]
            elif name == "duplicate-audio-id": guide["source"]["audioId"] = other["variants"]["guide"]["source"]["audioId"]
            elif name == "duplicate-url": guide["source"]["hlsUrl"] = other["variants"]["guide"]["source"]["hlsUrl"]
            elif name == "wrong-duration": guide["durationSeconds"] += 1
            elif name == "wrong-title": row["title"] = "Wrong but schema-valid title"
            elif name == "wrong-category": row["category"] = "Wrong category"
            elif name == "swapped-assets":
                row["variants"]["guide"], other["variants"]["guide"] = other["variants"]["guide"], guide
            elif name == "meditation-in-songs": c["songs"]["main:472"] = c["meditations"].pop("watv:vi:silent:19977")
            elif name == "missing-meditation": c["meditations"].pop("watv:vi:silent:19977")
            elif name == "meditation-key": c["meditations"]["watv:vi:silent:999"] = c["meditations"].pop("watv:vi:silent:19977")
            elif name == "single-variant": row["variants"].pop("instrumental")
        names = ("missing-song", "fake-main", "wrong-appendix", "key-mismatch", "duplicate-logical-id",
                 "duplicate-asset-id", "duplicate-audio-id", "duplicate-url", "wrong-duration", "wrong-title",
                 "wrong-category", "swapped-assets", "meditation-in-songs", "missing-meditation", "meditation-key", "single-variant")
        for name in names:
            with self.subTest(name=name):
                c = copy.deepcopy(self.catalog)
                mutate(name, c)
                self.assertTrue(lib.validate_catalog(c, self.snapshot, self.schema))

    def test_schema_allows_future_single_variant_but_b3_rejects_it(self):
        from jsonschema import Draft202012Validator, FormatChecker
        del self.catalog["songs"]["main:1"]["variants"]["instrumental"]
        self.assertFalse(list(Draft202012Validator(self.schema, format_checker=FormatChecker()).iter_errors(self.catalog)))
        self.assertTrue(lib.validate_catalog(self.catalog, self.snapshot, self.schema))

    def test_schema_and_validator_reject_trailing_newline_in_anchored_fields(self):
        from jsonschema import Draft202012Validator, FormatChecker
        validator = Draft202012Validator(self.schema, format_checker=FormatChecker())
        paths = [
            ("songs", "main:1", "id"),
            ("songs", "main:1", "variants", "guide", "assetId"),
            ("songs", "main:1", "variants", "guide", "sourceDuration"),
            ("songs", "main:1", "variants", "guide", "source", "audioId"),
            ("songs", "main:1", "variants", "guide", "source", "jsonKey"),
            ("songs", "main:1", "variants", "guide", "source", "hlsUrl"),
            ("meditations", "watv:vi:silent:19977", "id"),
        ]
        for path in paths:
            with self.subTest(path=path):
                c = copy.deepcopy(self.catalog)
                target = c
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] += "\n"
                self.assertTrue(list(validator.iter_errors(c)))
                self.assertTrue(lib.validate_catalog(c, self.snapshot, self.schema))
        for collection, key in (("songs", "main:1"), ("meditations", "watv:vi:silent:19977")):
            with self.subTest(collection=collection):
                c = copy.deepcopy(self.catalog)
                c[collection][key + "\n"] = c[collection].pop(key)
                self.assertTrue(list(validator.iter_errors(c)))
                self.assertTrue(lib.validate_catalog(c, self.snapshot, self.schema))

    def test_cli_exit_codes_and_offline_rebuild(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json"
            build = subprocess.run([sys.executable, str(ROOT / "scripts/build-catalog.py"), "--output", str(path)], capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), lib.json_text(self.catalog))
            validate = [sys.executable, str(ROOT / "scripts/validate-catalog.py"), "--catalog", str(path)]
            result = subprocess.run(validate, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS", result.stdout)
            path.write_text('{"songs":{},"songs":{}}', encoding="utf-8")
            result = subprocess.run(validate, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Duplicate JSON key", result.stderr)
            path.write_text("null", encoding="utf-8")
            self.assertNotEqual(subprocess.run(validate, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
