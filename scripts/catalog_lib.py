"""Offline B3 catalog normalization and validation. This module never fetches URLs."""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "source/snapshots/watv-vi-2026-10-10.audio.json"
CATALOG = ROOT / "catalog/catalog.vi.json"
SCHEMA = ROOT / "schemas/catalog.schema.json"
LISTS = {"guide": "guideSongList", "instrumental": "instrumentalSongList", "silent": "silentSongList"}
RAW_FIELDS = {"title", "newsongDispNo", "playTime", "categoryNm", "jsonKey", "songUrl", "appendixYn", "newsongAudioId"}
DURATION = re.compile(r"[0-9]{2}:[0-5][0-9]:[0-5][0-9]\Z")
MAIN_NUMBERS = set(range(1, 486)) - {34, 242, 300, 306, 367}


def load_json(path):
    """Reject duplicate keys and NaN/Infinity instead of silently accepting them."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def nonfinite(value):
        raise ValueError(f"Nonfinite JSON number: {value}")

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique, parse_constant=nonfinite)


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def duration_seconds(value):
    if not isinstance(value, str) or not DURATION.fullmatch(value):
        raise ValueError(f"Invalid HH:MM:SS duration: {value!r}")
    hour, minute, second = map(int, value.split(":"))
    return hour * 3600 + minute * 60 + second


def source_maps(snapshot):
    """Validate all raw records and index each list by semantic source key."""
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("lists"), dict):
        raise ValueError("Snapshot must contain a lists object")
    if set(snapshot["lists"]) != set(LISTS.values()):
        raise ValueError("Snapshot must contain exactly the three audio lists")
    maps, audio_ids, urls = {}, set(), set()
    for kind, list_name in LISTS.items():
        rows = snapshot["lists"][list_name]
        if not isinstance(rows, list):
            raise ValueError(f"{list_name} must be an array")
        mapping = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != RAW_FIELDS:
                raise ValueError(f"{list_name}: malformed record or unexpected fields")
            for field in ("newsongDispNo", "newsongAudioId", "jsonKey"):
                if type(row[field]) is not int or row[field] <= 0:
                    raise ValueError(f"{list_name}: {field} must be a positive integer")
            if type(row["appendixYn"]) is not int or row["appendixYn"] not in (0, 1):
                raise ValueError(f"{list_name}: invalid appendixYn")
            for field in ("title", "categoryNm", "songUrl"):
                if not isinstance(row[field], str) or not row[field].strip():
                    raise ValueError(f"{list_name}: empty/invalid {field}")
            duration_seconds(row["playTime"])
            url = urlsplit(row["songUrl"])
            if (url.scheme != "https" or url.hostname != "vod.watv.org" or url.username or url.password
                    or url.query or url.fragment or any(c.isspace() for c in row["songUrl"])
                    or not url.path.startswith("/watv_media_newsong/_definst_/mp4:WATV_NEWSONG/")
                    or not url.path.endswith(".m4a/playlist.m3u8")):
                raise ValueError(f"{list_name}: invalid source HLS URL")
            if row["jsonKey"] != row["newsongAudioId"]:
                raise ValueError(f"{list_name}: jsonKey differs from audio ID")
            if row["newsongAudioId"] in audio_ids or row["songUrl"] in urls:
                raise ValueError(f"{list_name}: duplicate source audio ID or HLS URL")
            audio_ids.add(row["newsongAudioId"])
            urls.add(row["songUrl"])
            key = (row["appendixYn"], row["newsongDispNo"])
            if key in mapping:
                raise ValueError(f"{list_name}: duplicate pairing key {key}")
            mapping[key] = row
        maps[kind] = mapping
    if set(maps["guide"]) != set(maps["instrumental"]):
        raise ValueError("Guide/instrumental source key sets differ")
    return maps


def asset(row, kind):
    return {"assetId": f"watv:vi:{kind}:{row['newsongAudioId']}",
            "sourceDuration": row["playTime"], "durationSeconds": duration_seconds(row["playTime"]),
            "source": {"audioId": str(row["newsongAudioId"]), "jsonKey": str(row["jsonKey"]), "hlsUrl": row["songUrl"]}}


def build_catalog(snapshot):
    maps = source_maps(snapshot)
    catalog = {"schemaVersion": 1, "provider": "watv", "locale": "vi", "collectionId": "newsong", "songs": {}, "meditations": {}}
    for (appendix, number), guide in sorted(maps["guide"].items()):
        instrumental = maps["instrumental"][(appendix, number)]
        if any(guide[f] != instrumental[f] for f in ("title", "categoryNm")):
            raise ValueError(f"Title/category mismatch for {(appendix, number)}")
        section = "appendix" if appendix else "main"
        key = f"{section}:{number}"
        catalog["songs"][key] = {"id": f"watv:vi:newsong:{key}", "section": section, "number": number,
            "title": guide["title"], "category": guide["categoryNm"],
            "variants": {"guide": asset(guide, "guide"), "instrumental": asset(instrumental, "instrumental")}}
    for row in sorted(maps["silent"].values(), key=lambda r: r["newsongAudioId"]):
        key = f"watv:vi:silent:{row['newsongAudioId']}"
        catalog["meditations"][key] = {"id": key, "sourceDisplayNumber": row["newsongDispNo"],
            "title": row["title"], "category": row["categoryNm"], "asset": asset(row, "silent")}
    return catalog


def catalog_counts(catalog):
    songs = catalog["songs"]
    return {"songs": len(songs), "main": sum(s["section"] == "main" for s in songs.values()),
            "appendix": sum(s["section"] == "appendix" for s in songs.values()),
            "meditations": len(catalog["meditations"]),
            "assets": sum(len(s["variants"]) for s in songs.values()) + len(catalog["meditations"])}


def validate_catalog(catalog, snapshot, schema):
    """Validate schema, B3 invariants, and every field against the source join.

    The B3 counts/number sets deliberately belong here, not in the reusable schema.
    No URL is opened. Structural failures return before semantic traversal.
    """
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [f"Schema /{'/'.join(map(str, e.absolute_path))}: {e.message}"
              for e in validator.iter_errors(catalog)]
    if errors:
        return errors
    try:
        expected = build_catalog(snapshot)
    except (ValueError, TypeError) as exc:
        return [f"Source snapshot: {exc}"]

    required_counts = {"songs": 485, "main": 480, "appendix": 5, "meditations": 13, "assets": 983}
    for label, data in (("Catalog", catalog), ("Source snapshot", expected)):
        counts = catalog_counts(data)
        if counts != required_counts:
            errors.append(f"{label} counts: expected {required_counts}, got {counts}")
        for section, numbers in (("main", MAIN_NUMBERS), ("appendix", set(range(1, 6)))):
            actual = {s["number"] for s in data["songs"].values() if s["section"] == section}
            if actual != numbers:
                errors.append(f"{label} {section} numbers: missing {sorted(numbers - actual)}, unexpected {sorted(actual - numbers)}")

    logical_ids, asset_ids, audio_ids, urls = set(), set(), set(), set()

    def unique(value, seen, label, path):
        if value in seen:
            errors.append(f"{path}: duplicate {label} {value!r}")
        seen.add(value)

    def check_asset(value, kind, path):
        source = value["source"]
        unique(value["assetId"], asset_ids, "assetId", path)
        unique(source["audioId"], audio_ids, "source audioId", path)
        unique(source["hlsUrl"], urls, "HLS URL", path)
        if value["assetId"] != f"watv:vi:{kind}:{source['audioId']}":
            errors.append(f"{path}: assetId does not match variant/source audioId")
        if source["jsonKey"] != source["audioId"]:
            errors.append(f"{path}: jsonKey differs from audioId")
        if duration_seconds(value["sourceDuration"]) != value["durationSeconds"]:
            errors.append(f"{path}: durationSeconds differs from sourceDuration")

    for key, song in catalog["songs"].items():
        path = f"songs/{key}"
        if key != f"{song['section']}:{song['number']}" or song["id"] != f"watv:vi:newsong:{key}":
            errors.append(f"{path}: key/section/number/id mismatch")
        unique(song["id"], logical_ids, "logical ID", path)
        if set(song["variants"]) != {"guide", "instrumental"}:
            errors.append(f"{path}: B3 requires both guide and instrumental")
        for kind, value in song["variants"].items():
            check_asset(value, kind, f"{path}/variants/{kind}")
    for key, meditation in catalog["meditations"].items():
        path = f"meditations/{key}"
        if key != meditation["id"] or key != f"watv:vi:silent:{meditation['asset']['source']['audioId']}":
            errors.append(f"{path}: meditation key/id/source mismatch")
        unique(meditation["id"], logical_ids, "logical ID", path)
        check_asset(meditation["asset"], "silent", f"{path}/asset")

    # Equality alone gives poor diagnostics. Compare each leaf so equal counts and
    # globally unique but swapped assets cannot hide an incorrect source pairing.
    def compare(actual, wanted, path):
        if isinstance(wanted, dict):
            for key in sorted(set(actual) | set(wanted)):
                child = f"{path}/{key}"
                if key not in actual:
                    errors.append(f"{child}: missing from catalog")
                elif key not in wanted:
                    errors.append(f"{child}: absent from source snapshot")
                else:
                    compare(actual[key], wanted[key], child)
        elif actual != wanted:
            errors.append(f"{path}: differs from source-derived value {wanted!r}")

    compare(catalog, expected, "")
    return errors
