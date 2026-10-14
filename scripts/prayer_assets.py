"""Reviewed supplementary prayer registry; never edits the 983-asset catalog."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from types import MappingProxyType

from catalog_lib import load_json, json_text
from delivery_lib import check_plain_path
from r2_state import UploadError, reject_hardlink

MANIFEST = Path("delivery/prayer-manifest.vi.json")
QUICK = Path("workers/media-api/generated/quick-audio.json")
STATE = Path("state/prayer-r2-transfers.sqlite")
LOCK = Path("state/upload-prayer.lock")
REGISTRY = (MappingProxyType({
    "assetId": "watv:vi:prayer:our-wish",
    "localPath": "media/prayer/watv/vi/our-wish/our-wish.m4a",
    "slug": "our-wish",
    "title": "Cầu nguyện chúng con mong muốn",
    "bytes": 1123614,
    "sha256": "e03022c18f74a5c94a38bb04fb10c5186fa9e8916d43348deb65a3a5402b68f6",
    "durationSeconds": 69.427664,
    "sourceUrl": "https://vod.watv.org/watv_media_newsong/_definst_/mp4:WATV_PRAYER/pray/our_wish.m4a/playlist.m3u8",
    "rightsConfirmed": True,
    "identityConfirmed": True,
    "confirmedAt": "2026-10-13",
}), MappingProxyType({
    "assetId": "watv:vi:prayer:unison-prayer",
    "localPath": "media/prayer/watv/vi/unison-prayer/unison-prayer.m4a",
    "slug": "unison-prayer",
    "title": "Nhạc không lời cầu nguyện thống thanh",
    "bytes": 5038802,
    "sha256": "317ae73c27cc963181d71e11cdbb522924c329e31f0ffcb3bc15354a5579070e",
    "durationSeconds": 311.518912,
    "sourceUrl": None,
    "rightsConfirmed": True,
    "identityConfirmed": True,
    "confirmedAt": "2026-10-14",
}))


def plain_path(root, relative, writable=False):
    """Check the lexical path and every existing component before opening it."""
    root = Path(root).resolve()
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise UploadError("prayer_unsafe_path")
    path = root / relative
    try:
        check_plain_path(path, root)
    except ValueError:
        raise UploadError("prayer_unsafe_path") from None
    if writable:
        reject_hardlink(path)
    return path


def registered_documents():
    """Construct allowlisted private/public metadata from reviewed registry only."""
    tracks, assets, rights, provenance = [], {}, {}, {}
    for entry in REGISTRY:
        if entry.get("rightsConfirmed") is not True or entry.get("identityConfirmed") is not True:
            raise UploadError("prayer_rights_unconfirmed")
        slug, local = entry.get("slug", ""), entry.get("localPath", "")
        if (not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)
                or entry.get("assetId") != "watv:vi:prayer:" + slug
                or local != "media/prayer/watv/vi/" + slug + "/" + slug + ".m4a"
                or PurePosixPath(local).is_absolute() or ".." in PurePosixPath(local).parts
                or not re.fullmatch(r"[0-9a-f]{64}", entry.get("sha256", ""))
                or type(entry.get("bytes")) is not int or entry["bytes"] <= 0
                or (slug,entry.get("durationSeconds"),entry.get("confirmedAt")) not in (('our-wish',69.427664,'2026-10-13'),('unison-prayer',311.518912,'2026-10-14'))):
            raise UploadError("prayer_invalid_registry")
        ident = entry["assetId"]
        if ident in assets:
            raise UploadError("prayer_invalid_registry")
        tracks.append({"id": ident, "logicalId": ident, "mode": "prayer", "section": None,
            "number": None, "title": entry["title"], "category": "Cầu nguyện",
            "durationSeconds": entry["durationSeconds"]})
        assets[ident] = {"assetId": ident, "objectKey": "audio/v1/watv/vi/prayer/" + slug + "/" + entry["sha256"] + ".m4a",
            "bytes": entry["bytes"], "sha256": entry["sha256"]}
        rights[ident] = {"status": "user-confirmed", "identityStatus": "user-confirmed",
            "confirmedAt": entry["confirmedAt"], "scope": "AudioTP private R2 playback and Windows delivery"}
        provenance[ident] = {"sourceUrl": entry["sourceUrl"], "localVerificationPath": str(PurePosixPath(local).with_name("verification.json")),
            "verificationScope": "Existing local source report plus current file size/SHA-256; no new media decode"}
    body = {"schemaVersion": 1, "tracks": tracks, "assets": assets}
    canonical = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    quick = {"schemaVersion": 1, "revision": "sha256:" + hashlib.sha256(canonical).hexdigest(), "tracks": tracks, "assets": assets}
    manifest = {"schemaVersion": 1, "revision": quick["revision"], "tracks": tracks,
        "assets": {key: dict(value, localPath=next(e["localPath"] for e in REGISTRY if e["assetId"] == key)) for key, value in assets.items()},
        "rights": rights, "provenance": provenance}
    return manifest, quick


def prepare(root):
    """Verify exact approved local bytes and historical probe/decode report offline."""
    manifest, quick = registered_documents()
    for entry in REGISTRY:
        path = plain_path(root, entry["localPath"])
        proof_path = plain_path(root, Path(entry["localPath"]).with_name("verification.json"))
        try:
            with path.open("rb") as stream:
                before = os.fstat(stream.fileno())
                digest, size = hashlib.sha256(), 0
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
                after = os.fstat(stream.fileno())
            if (size != entry["bytes"] or digest.hexdigest() != entry["sha256"]
                    or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
                raise UploadError("prayer_local_integrity")
        except OSError:
            raise UploadError("prayer_local_file") from None
        try:
            proof = load_json(proof_path)
            if (not isinstance(proof, dict) or proof.get("status") != "PASS" or proof.get("decodeVerified") is not True
                    or proof.get("codec") != "aac"
                    or any(type(proof.get(key)) is not type(entry[key]) or proof[key] != entry[key]
                           for key in ("localPath", "sourceUrl", "bytes", "sha256", "durationSeconds"))):
                raise UploadError("prayer_source_verification")
        except (OSError, ValueError, TypeError):
            raise UploadError("prayer_source_verification") from None
    return manifest, quick


def write_prepared(root, manifest, quick):
    """Write only the two supplementary JSON artifacts using atomic replacement."""
    if (manifest, quick) != prepare(root):
        raise UploadError("prayer_manifest_mismatch")
    outputs = [(plain_path(root, relative, writable=True), data) for relative, data in ((MANIFEST, manifest), (QUICK, quick))]
    for path, data in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".prayer-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json_text(data))
                stream.flush()
                os.fsync(stream.fileno())
            # Recheck after creating the parent and immediately before replacement.
            plain_path(root, path.relative_to(Path(root).resolve()), writable=True)
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def load_prepared(root, verify_local=True):
    expected, _ = prepare(root) if verify_local else registered_documents()
    try:
        actual = load_json(plain_path(root, MANIFEST))
    except (OSError, ValueError, TypeError):
        raise UploadError("prayer_manifest_unavailable") from None
    if actual != expected:
        raise UploadError("prayer_manifest_mismatch")
    return actual
