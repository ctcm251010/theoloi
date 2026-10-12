"""Manifest-driven R2 upload. Errors contain only static, non-secret codes."""
import base64
import hashlib
import os
from pathlib import Path
import re
import sqlite3

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectionError, HTTPClientError

from catalog_lib import load_json
from delivery_lib import SCHEMA, check_plain_path, validate_manifest
from r2_state import UploadError, now, summarize, target_identity

MANIFEST_SHA256 = "b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c"


def load_delivery(path):
    if hashlib.sha256(Path(path).read_bytes()).hexdigest() != MANIFEST_SHA256:
        raise UploadError("unreviewed_delivery_manifest")
    manifest = load_json(path)
    if validate_manifest(manifest, load_json(SCHEMA), manifest):
        raise UploadError("invalid_delivery_manifest")
    return manifest


def read_secrets(path, target):
    required = {"R2_ACCOUNT_ID", "R2_BUCKET", "R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY"}
    values = {}
    try:
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            if not sep or key not in required or key in values or not value:
                raise UploadError("invalid_secret_file")
            values[key] = value
        if values.keys() != required:
            raise UploadError("incomplete_secret_file")
        for key, field in (("R2_ACCOUNT_ID", "accountId"), ("R2_BUCKET", "bucket"), ("R2_ENDPOINT", "endpoint")):
            if values[key] != target[field]:
                raise UploadError("credential_target_mismatch")
        if not re.fullmatch(r"[0-9a-fA-F]{32}", values["R2_ACCESS_KEY_ID"]) or not re.fullmatch(r"[0-9a-fA-F]{64}", values["R2_SECRET_ACCESS_KEY"]):
            raise UploadError("invalid_credential_format")
        return values
    except (OSError, UnicodeError):
        raise UploadError("unreadable_secret_file") from None


def create_client(values, target, workers):
    return boto3.session.Session().client("s3", endpoint_url=target["endpoint"], region_name="auto",
        aws_access_key_id=values["R2_ACCESS_KEY_ID"], aws_secret_access_key=values["R2_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", proxies={}, connect_timeout=10, read_timeout=45,
            max_pool_connections=max(4, workers), retries={"mode": "standard", "total_max_attempts": 1},
            request_checksum_calculation="when_required", response_checksum_validation="when_required"))


def safe_error(exc):
    if isinstance(exc, UploadError):
        return exc.kind, exc.code
    if isinstance(exc, ClientError):
        status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if type(status) is int and 100 <= status <= 599:
            return ("transient" if status in (408, 429) or status >= 500 else "permanent", "remote_http_" + str(status))
        return "permanent", "remote_error"
    if isinstance(exc, (ConnectionError, HTTPClientError)):
        return "transient", "network_connection"
    if isinstance(exc, OSError):
        return "permanent", "local_file"
    return "permanent", "internal_error"


def read_status(path, assets, target):
    if not Path(path).exists():
        return summarize({}, assets)
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    try:
        db.execute("BEGIN")
        row = db.execute("SELECT value FROM meta WHERE key='target'").fetchone()
        if not row or row[0] != target_identity(target):
            raise UploadError("state_target_mismatch")
        return summarize(dict(db.execute("SELECT asset_id,status FROM jobs")), assets)
    finally:
        db.close()


class UploadRunner:
    def __init__(self, client, bucket, root, state, stop, wait=None):
        self.client, self.bucket, self.root, self.state, self.stop = client, bucket, Path(root).resolve(), state, stop
        self.wait = wait or stop.wait

    def head(self, a):
        try:
            return self.client.head_object(Bucket=self.bucket, Key=a["objectKey"])
        except ClientError as exc:
            if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return None
            raise

    def verify_head(self, a, head):
        meta = head.get("Metadata", {}) if head else {}
        if not head or head.get("ContentLength") != a["bytes"] or meta.get("sha256") != a["sha256"] or meta.get("asset-id") != a["assetId"]:
            raise UploadError("remote_conflict")

    def verify_get(self, a):
        response = self.client.get_object(Bucket=self.bucket, Key=a["objectKey"])
        body, digest, size = response["Body"], hashlib.sha256(), 0
        try:
            for chunk in iter(lambda: body.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
                if size > a["bytes"]:
                    raise UploadError("remote_integrity")
        finally:
            body.close()
        if size != a["bytes"] or digest.hexdigest() != a["sha256"]:
            raise UploadError("remote_integrity")

    def transfer(self, a, verify_download):
        path = self.root / a["localPath"]
        if not path.is_relative_to(self.root) or ".." in path.parts:
            raise UploadError("local_integrity")
        check_plain_path(path, self.root)
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            digest, md5, size = hashlib.sha256(), hashlib.md5(), 0
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk); md5.update(chunk); size += len(chunk)
            after = os.fstat(stream.fileno())
            if size != a["bytes"] or digest.hexdigest() != a["sha256"] or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise UploadError("local_integrity")
            stream.seek(0)
            head = self.head(a)
            uploaded = False
            if head is None:
                self.state.update(a["assetId"], status="uploading")
                try:
                    self.client.put_object(Bucket=self.bucket, Key=a["objectKey"], Body=stream,
                        ContentLength=size, ContentMD5=base64.b64encode(md5.digest()).decode("ascii"),
                        ContentType="audio/mp4", CacheControl="public, max-age=31536000, immutable",
                        Metadata={"sha256": a["sha256"], "asset-id": a["assetId"]}, IfNoneMatch="*")
                    uploaded = True
                    self.state.update(a["assetId"], status="uploaded", uploaded_at=now())
                except ClientError as exc:
                    if exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 412:
                        raise
                head = self.head(a)
            self.verify_head(a, head)
            if verify_download:
                self.verify_get(a)
            fields = dict(status="verified", remote_bytes=head["ContentLength"], etag=head.get("ETag"),
                          verified_at=now(), error_kind=None, last_error=None)
            if verify_download:
                fields["download_verified_at"] = now()
            self.state.update(a["assetId"], **fields)
            return "uploaded" if uploaded else "skipped"

    def process(self, a, verify_download=False):
        ident = a["assetId"]
        if self.state.get(ident)["status"] == "failed":
            return "failed"
        while not self.stop.is_set():
            row = self.state.get(ident)
            self.state.update(ident, attempts=row["attempts"]+1)
            try:
                return self.transfer(a, verify_download)
            except Exception as exc:
                kind, code = safe_error(exc)
                failures = row["failures"] + 1
                terminal = kind != "transient" or failures >= 3
                self.state.update(ident, status="failed" if terminal else "pending", failures=failures,
                                  error_kind=kind, last_error=code, verified_at=None, download_verified_at=None)
                if terminal:
                    return "failed"
                if self.wait(min(8, 2 ** failures)):
                    break
        return "interrupted"
