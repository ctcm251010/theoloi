"""Offline B8 delivery audit. Never downloads, runs media tools, or updates state."""
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile

from jsonschema import Draft202012Validator, FormatChecker

from catalog_lib import ROOT, CATALOG, SNAPSHOT, SCHEMA as CATALOG_SCHEMA, load_json, json_text, validate_catalog
from download_state import BatchLock, CATALOG_HASH, PROFILE, enumerate_jobs, now, sha256
from download_pipeline import validate_media
from hls_source import MediaFailure

MANIFEST = ROOT / "delivery/manifest.vi.json"
SCHEMA = ROOT / "schemas/delivery.schema.json"
STATE = ROOT / "state/transfers.sqlite"
MEDIA = Path("media/audio/v1/watv/vi")
COUNTS = {"assets": 983, "guide": 485, "instrumental": 485, "meditations": 13}
HASH = re.compile(r"[0-9a-f]{64}\Z")
FORMATS = FormatChecker()


@FORMATS.checks("date-time", raises=(ValueError, TypeError))
def iso_datetime(value):
    # jsonschema's optional RFC3339 dependency is absent in the pinned venv.
    # Enforce our UTC/offset ISO timestamps without silently skipping format.
    if not isinstance(value, str):
        return True
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:[Zz]|[+-][0-9]{2}:[0-5][0-9])", value):
        return False
    return datetime.fromisoformat(value.upper()).tzinfo is not None


class DeliveryError(ValueError):
    pass


def delivery_lock(state_path):
    return BatchLock(Path(state_path).with_name("download-media.lock"))


def read_rows(path):
    """mode=ro never creates a missing database or changes job state."""
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN")
        if [row[0] for row in db.execute("PRAGMA quick_check")] != ["ok"]:
            raise DeliveryError("SQLite quick_check failed")
        return [dict(row) for row in db.execute("SELECT * FROM jobs ORDER BY asset_id")]
    finally:
        db.close()


def redirected(path):
    return path.is_symlink() or path.is_junction()


def check_plain_path(path, root):
    """Reject filesystem redirects, including Windows directory junctions."""
    relative = path.relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        if redirected(current):
            raise DeliveryError(f"Redirected path is not a final artifact: {current}")


def published_files(root):
    base = root / MEDIA
    check_plain_path(base, root)
    result = set()
    def failed_scan(exc):
        raise DeliveryError(f"Cannot completely inventory media root: {exc}") from exc

    for folder, dirs, files in os.walk(base, followlinks=False, onerror=failed_scan):
        for name in dirs + files:
            path = Path(folder) / name
            if redirected(path):
                raise DeliveryError(f"Redirected path in media root: {path}")
        result.update(Path(folder) / name for name in files)
    return result


def validate_output_path(path, root=ROOT, inputs=()):
    """Only delivery JSON outputs are writable; inputs and redirects are blocked."""
    root = Path(root).resolve()
    output = Path(os.path.abspath(path))
    if not output.is_relative_to(root / "delivery") or output.suffix.lower() != ".json":
        raise DeliveryError("Output must be a .json file inside projectRoot/delivery; protected inputs are never writable")
    check_plain_path(output, root)
    if output.resolve() in {Path(p).resolve() for p in inputs}:
        raise DeliveryError("Output collides with a catalog, schema, or state input")
    return output


def verified_measurements(row):
    if row["status"] != "completed" or row["probe_verified"] != 1 or row["decode_verified"] != 1:
        raise DeliveryError("Not completed with both probe and decode verified")
    if type(row["byte_size"]) is not int or row["byte_size"] <= 0:
        raise DeliveryError("Invalid byte size")
    if not isinstance(row["sha256"], str) or not HASH.fullmatch(row["sha256"]):
        raise DeliveryError("Invalid SHA-256")
    proof = json.loads(row["verification_json"])
    if any(type(proof.get(k)) is not int or proof[k] != 0 for k in ("probeExitCode", "decodeExitCode")):
        raise DeliveryError("Missing successful B7 probe/decode evidence")
    stamp = datetime.fromisoformat(proof["verifiedAt"])
    if stamp.tzinfo is None or proof.get("remux") != "AAC streamcopy, M4A, faststart":
        raise DeliveryError("Invalid verification timestamp/remux profile")
    measured = validate_media(proof["source"], proof["output"])
    for field in ("probed_duration", "source_duration", "codec", "sample_rate", "channels"):
        if row[field] != measured[field]:
            raise DeliveryError(f"State differs from B7 measured {field}")
    if any(type(row[k]) is not int or row[k] <= 0 for k in ("sample_rate", "channels")):
        raise DeliveryError("Invalid measured sample rate/channels")
    if not math.isfinite(row["probed_duration"]) or row["probed_duration"] <= 0:
        raise DeliveryError("Invalid measured duration")
    if int(proof["output"]["format"]["size"]) != row["byte_size"]:
        raise DeliveryError("Probe byte size differs from state")
    return measured


def audit_assets(catalog, rows, root=ROOT):
    """All-or-nothing audit; small catalogs are supported only for unit tests.

    Production inspect_inputs pins and validates the full B3 catalog first.
    The caller holds delivery_lock throughout audit and publication.
    """
    root = Path(root).resolve()
    jobs = enumerate_jobs(catalog, root)
    expected = {j["asset_id"] for j in jobs}
    by_id, errors, assets, warnings = {}, [], {}, {}
    paths = set()
    for row in rows:
        ident = row.get("asset_id")
        if ident in by_id:
            errors.append(f"Duplicate state assetId: {ident}")
        by_id[ident] = row
        final = row.get("final_path")
        if final in paths:
            errors.append(f"Duplicate final path: {final}")
        paths.add(final)
    if expected != set(by_id):
        errors.append(f"State asset set mismatch; missing={sorted(expected - by_id.keys())}, extra={sorted(by_id.keys() - expected)}")

    for job in jobs:
        ident = job["asset_id"]
        row = by_id.get(ident)
        if row is None:
            continue
        try:
            for field in ("logical_id", "key", "variant", "source_url", "fingerprint", "metadata_duration"):
                if row[field] != job[field]:
                    raise DeliveryError(f"Catalog/state {field} mismatch")
            if json.loads(row["profile"]) != PROFILE:
                raise DeliveryError("State output profile mismatch")
            final = Path(job["final_path"])
            if Path(row["final_path"]) != final:
                raise DeliveryError("State final_path differs from catalog-derived final path")
            check_plain_path(final, root)
            verified_measurements(row)
            before = final.stat()
            if not final.is_file() or before.st_size != row["byte_size"]:
                raise DeliveryError("Missing final file or byte size mismatch")
            actual_hash = sha256(final)
            after = final.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise DeliveryError("Final file changed during hashing")
            if actual_hash != row["sha256"]:
                raise DeliveryError("Final file SHA-256 mismatch")

            silent = job["variant"] == "silent"
            content = catalog["meditations"][job["key"]] if silent else catalog["songs"][job["key"]]
            source_asset = content["asset"] if silent else content["variants"][job["variant"]]
            audio_id = source_asset["source"]["audioId"]
            a = {"assetId": ident, "logicalId": content["id"], "kind": "meditation" if silent else "song",
                 "audioId": audio_id, "variant": job["variant"]}
            if silent:
                prefix = f"audio/v1/watv/vi/meditations/{audio_id}"
            else:
                a.update(section=content["section"], number=content["number"])
                prefix = f"audio/v1/watv/vi/newsong/{content['section']}/{content['number']:04d}/{job['variant']}/{audio_id}"
            a.update(localPath=final.relative_to(root).as_posix(), objectKey=f"{prefix}/{actual_hash}.m4a",
                     bytes=after.st_size, sha256=actual_hash, durationSeconds=row["probed_duration"],
                     codec=row["codec"], sampleRate=row["sample_rate"], channels=row["channels"], container="m4a")
            assets[ident] = a
            notes = json.loads(row.get("warnings_json") or "[]")
            if not isinstance(notes, list) or any(not isinstance(n, str) for n in notes):
                raise DeliveryError("Malformed state warnings")
            if notes:
                warnings[ident] = notes
        except (OSError, ValueError, KeyError, TypeError, AttributeError, MediaFailure) as exc:
            errors.append(f"{ident}: {exc}")

    expected_paths = {Path(j["final_path"]) for j in jobs}
    try:
        actual_paths = published_files(root)
        if actual_paths != expected_paths:
            errors.append(f"Published file set mismatch; missing={sorted(str(p) for p in expected_paths - actual_paths)}, extra={sorted(str(p) for p in actual_paths - expected_paths)}")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    if errors:
        raise DeliveryError("\n".join(errors))
    return assets, warnings


def content_revision(manifest):
    content = {k: v for k, v in manifest.items() if k not in ("revision", "generatedAt")}
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def make_manifest(assets, catalog_hash, generated_at=None):
    manifest = {"schemaVersion": 1, "provider": "watv", "locale": "vi", "collectionId": "newsong",
                "catalogSha256": catalog_hash, "revision": "", "generatedAt": generated_at or now(),
                "outputProfile": dict(PROFILE), "assets": dict(sorted(assets.items()))}
    manifest["revision"] = content_revision(manifest)
    return manifest


def counts(manifest):
    kinds = Counter(a["variant"] for a in manifest["assets"].values())
    return {"assets": len(manifest["assets"]), "guide": kinds["guide"], "instrumental": kinds["instrumental"],
            "meditations": kinds["silent"]}


def validate_manifest(manifest, schema, expected, require_counts=True):
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FORMATS)
    errors = [f"Schema /{'/'.join(map(str, e.absolute_path))}: {e.message}" for e in validator.iter_errors(manifest)]
    if errors:
        return errors
    if require_counts and counts(manifest) != COUNTS:
        errors.append(f"Counts: expected {COUNTS}, got {counts(manifest)}")
    if manifest["catalogSha256"] != expected["catalogSha256"] or manifest["outputProfile"] != expected["outputProfile"]:
        errors.append("Catalog SHA-256/output profile mismatch")
    if manifest["revision"] != content_revision(manifest):
        errors.append("Content revision mismatch")
    if set(manifest["assets"]) != set(expected["assets"]):
        errors.append("Missing or unexpected catalog assets")
    ids, keys, paths = set(), set(), set()
    for key, a in manifest["assets"].items():
        for field, seen in (("assetId", ids), ("objectKey", keys), ("localPath", paths)):
            if a[field] in seen:
                errors.append(f"Duplicate {field}: {a[field]}")
            seen.add(a[field])
        if key != a["assetId"]:
            errors.append(f"Asset map key differs from assetId: {key}")
        if a != expected["assets"].get(key):
            errors.append(f"{key}: artifact differs from verified catalog/state/file mapping")
    return errors


def inspect_inputs(catalog_path=CATALOG, state_path=STATE, root=ROOT):
    raw_hash = sha256(catalog_path)
    if raw_hash != CATALOG_HASH:
        raise DeliveryError("B8 requires the reviewed B3 catalog SHA-256; catalog changed")
    catalog = load_json(catalog_path)
    errors = validate_catalog(catalog, load_json(SNAPSHOT), load_json(CATALOG_SCHEMA))
    if errors:
        raise DeliveryError("\n".join(errors))
    assets, warnings = audit_assets(catalog, read_rows(state_path), root)
    manifest = make_manifest(assets, raw_hash)
    if counts(manifest) != COUNTS:
        raise DeliveryError(f"B8 requires all 983 completed verified assets: {counts(manifest)}")
    return manifest, warnings


def write_atomic(path, manifest):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".manifest-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json_text(manifest).encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def summary(manifest):
    assets = list(manifest["assets"].values())
    return {**counts(manifest), "totalBytes": sum(a["bytes"] for a in assets),
            "uniqueSha256": len({a["sha256"] for a in assets}),
            "uniqueObjectKeys": len({a["objectKey"] for a in assets}),
            "codec": dict(Counter(a["codec"] for a in assets)),
            "sampleRate": dict(Counter(a["sampleRate"] for a in assets)),
            "channels": dict(Counter(a["channels"] for a in assets)),
            "durationRangeSeconds": [min(a["durationSeconds"] for a in assets), max(a["durationSeconds"] for a in assets)]}
