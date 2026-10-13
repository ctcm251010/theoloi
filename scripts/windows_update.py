"""Bounded, create-only publication of one reviewed Windows installer."""
import base64
import binascii
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import tempfile
import threading

from botocore.exceptions import ClientError

from catalog_lib import load_json, json_text
from delivery_lib import check_plain_path
from r2_pipeline import safe_error
from r2_state import UploadError, reject_hardlink

DELIVERY = Path("delivery/windows-update.json")
GENERATED = Path("workers/media-api/generated/updates.json")
MAX_INSTALLER_BYTES = 50 * 1024 * 1024
API_ORIGIN = "https://audiotp-media-api.ctcm251010.workers.dev"
VERSION = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"


def plain_path(root, path, writable=False):
    root = Path(root).resolve()
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    if not path.is_relative_to(root) or ".." in path.parts:
        raise UploadError("update_unsafe_path")
    try:
        check_plain_path(path, root)
    except ValueError:
        raise UploadError("update_unsafe_path") from None
    if writable:
        reject_hardlink(path)
    return path


def decode_base64(value):
    try:
        decoded = base64.b64decode(value, validate=True)
        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError
        return decoded
    except (ValueError, binascii.Error, UnicodeError):
        raise UploadError("update_invalid_signature") from None


def parse_signature(value):
    """Validate public .sig structure; the app's pinned key verifies cryptography."""
    if not isinstance(value, str) or not value or len(value) > 8192:
        raise UploadError("update_invalid_signature")
    try:
        lines = decode_base64(value).decode("utf-8").replace("\r\n", "\n").rstrip().split("\n")
        if len(lines) != 4 or not lines[0].startswith("untrusted comment: ") or not lines[2].startswith("trusted comment: "):
            raise ValueError
        packet, global_signature = decode_base64(lines[1]), decode_base64(lines[3])
        if len(packet) != 74 or packet[:2] not in (b"Ed", b"ED") or len(global_signature) != 64:
            raise ValueError
        return value
    except (ValueError, UnicodeError):
        raise UploadError("update_invalid_signature") from None


def file_measurements(path, maximum):
    """Hash bounded data and reject changes observed during the read."""
    try:
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if not 0 < before.st_size <= maximum:
                raise UploadError("update_size_limit")
            digest, size, prefix = hashlib.sha256(), 0, b""
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                if size > maximum:
                    raise UploadError("update_size_limit")
                digest.update(chunk)
                if not prefix:
                    prefix = chunk
            after = os.fstat(stream.fileno())
            if (size != before.st_size or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
                raise UploadError("update_local_integrity")
        return size, digest.hexdigest(), prefix
    except OSError:
        raise UploadError("update_local_file") from None


def inspect_release(root, release_dir, notes=None):
    root = Path(root).resolve()
    folder = plain_path(root, release_dir)
    match = re.fullmatch("(" + VERSION + r")-([0-9]{8}T[0-9]{12}Z)", folder.name)
    if folder.parent != root / "release/windows" or not match:
        raise UploadError("update_invalid_release_dir")
    version, stamp = match.groups()
    if any(int(part) > 9007199254740991 for part in version.split(".")):
        raise UploadError("update_invalid_report")
    try:
        published = datetime.strptime(stamp, "%Y%m%dT%H%M%S%fZ").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        report = load_json(plain_path(root, folder / "build-report.json"))
    except (OSError, ValueError, TypeError):
        raise UploadError("update_invalid_report") from None
    if (not isinstance(report, dict) or report.get("status") != "BUILT_NOT_ACCEPTED"
            or report.get("version") != version or report.get("buildNumber") != stamp
            or report.get("apiBase") != API_ORIGIN or report.get("installer") is not True
            or not isinstance(report.get("files"), list)):
        raise UploadError("update_invalid_report")
    name = "AudioTP_" + version + "_x64-setup.exe"
    records = {}
    for item in report["files"]:
        if (not isinstance(item, dict) or set(item) != {"name", "bytes", "sha256"}
                or item.get("name") not in ("AudioTP.exe", name, name + ".sig") or item["name"] in records
                or type(item.get("bytes")) is not int or item["bytes"] <= 0
                or not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])):
            raise UploadError("update_invalid_report")
        records[item["name"]] = item
    if name not in records or name + ".sig" not in records:
        raise UploadError("update_invalid_report")
    installer = plain_path(root, folder / name)
    signature_path = plain_path(root, folder / (name + ".sig"))
    size, sha256, prefix = file_measurements(installer, MAX_INSTALLER_BYTES)
    signature_size, signature_hash, raw_signature = file_measurements(signature_path, 8192)
    if any((actual_size, actual_hash) != (records[n]["bytes"], records[n]["sha256"])
            for n, actual_size, actual_hash in ((name, size, sha256), (name + ".sig", signature_size, signature_hash))):
        raise UploadError("update_local_integrity")
    pe = int.from_bytes(prefix[60:64], "little") if len(prefix) >= 64 else len(prefix)
    if prefix[:2] != b"MZ" or pe < 64 or prefix[pe:pe+4] != b"PE\0\0":
        raise UploadError("update_invalid_pe")
    try:
        signature = parse_signature(raw_signature.decode("utf-8").rstrip("\r\n"))
    except UnicodeError:
        raise UploadError("update_invalid_signature") from None
    if notes is None:
        notes = "Cập nhật AudioTP " + version + "."
    if not isinstance(notes, str) or len(notes) > 10000 or any(ord(char) < 32 and char not in "\n\r\t" for char in notes):
        raise UploadError("update_invalid_notes")
    return {"version": version, "pubDate": published, "notes": notes,
        "objectKey": "updates/windows-x86_64/" + version + "/" + name,
        "bytes": size, "sha256": sha256, "signature": signature}, installer


def validate_outputs(root):
    return [plain_path(root, path, writable=True) for path in (DELIVERY, GENERATED)]


def write_metadata(root, metadata):
    for path in validate_outputs(root):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".update-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json_text(metadata))
                stream.flush()
                os.fsync(stream.fileno())
            plain_path(root, path, writable=True)
            os.replace(temporary, path)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()


def verify_remote_head(head, metadata):
    if (not head or head.get("ContentLength") != metadata["bytes"]
            or head.get("ContentType") != "application/octet-stream"
            or head.get("Metadata", {}).get("sha256") != metadata["sha256"]
            or head.get("Metadata", {}).get("asset-id") != "audiotp:windows:x86_64:" + metadata["version"]):
        raise UploadError("update_remote_conflict")


def publish_installer(client, bucket, installer, metadata, wait=None):
    """Three transient attempts, no overwrite, always verify full remote bytes."""
    wait = wait or threading.Event().wait
    for attempt in range(3):
        try:
            head = None
            try:
                head = client.head_object(Bucket=bucket, Key=metadata["objectKey"])
            except ClientError as exc:
                if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 404:
                    raise
            if head is None:
                with installer.open("rb") as stream:
                    before = os.fstat(stream.fileno())
                    digest, md5, size = hashlib.sha256(), hashlib.md5(), 0
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                        md5.update(chunk)
                        size += len(chunk)
                        if size > MAX_INSTALLER_BYTES:
                            raise UploadError("update_size_limit")
                    after = os.fstat(stream.fileno())
                    if (size != metadata["bytes"] or digest.hexdigest() != metadata["sha256"]
                            or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
                        raise UploadError("update_local_integrity")
                    stream.seek(0)
                    try:
                        client.put_object(Bucket=bucket, Key=metadata["objectKey"], Body=stream, ContentLength=size,
                            ContentMD5=base64.b64encode(md5.digest()).decode("ascii"), ContentType="application/octet-stream",
                            CacheControl="private, no-store", Metadata={"sha256": metadata["sha256"], "asset-id": "audiotp:windows:x86_64:" + metadata["version"]},
                            IfNoneMatch="*")
                    except ClientError as exc:
                        if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
                            raise
                head = client.head_object(Bucket=bucket, Key=metadata["objectKey"])
            verify_remote_head(head, metadata)
            response = client.get_object(Bucket=bucket, Key=metadata["objectKey"])
            body, digest, size = response["Body"], hashlib.sha256(), 0
            try:
                for chunk in iter(lambda: body.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
                    if size > metadata["bytes"] or size > MAX_INSTALLER_BYTES:
                        raise UploadError("update_remote_integrity")
            finally:
                body.close()
            if size != metadata["bytes"] or digest.hexdigest() != metadata["sha256"]:
                raise UploadError("update_remote_integrity")
            return
        except Exception as exc:
            kind, code = safe_error(exc)
            if kind != "transient" or attempt == 2:
                raise UploadError(code, kind) from None
            if wait(2 ** (attempt + 1)):
                raise UploadError("update_interrupted")
