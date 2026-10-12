"""Durable upload state, separate from catalog and download state."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


def now():
    return datetime.now(timezone.utc).isoformat()


class UploadError(ValueError):
    def __init__(self, code, kind="permanent"):
        self.code, self.kind = code, kind
        super().__init__(code)


def target_identity(target):
    return json.dumps({k: target[k] for k in ("accountId", "bucket", "endpoint")}, sort_keys=True)


def reject_hardlink(path):
    path = Path(path)
    if path.is_file() and path.stat().st_nlink != 1:
        raise UploadError("writable_hardlink")


def summarize(rows, assets):
    selected = [rows.get(a["assetId"], "pending") for a in assets]
    verified = selected.count("verified")
    failed = selected.count("failed")
    return dict(assets=len(selected), uploaded=verified + selected.count("uploaded"),
                verified=verified, failed=failed, remaining=len(selected)-verified,
                pending=len(selected)-verified-failed)


class UploadState:
    def __init__(self, path, target):
        for suffix in ("", "-wal", "-shm", "-journal"):
            reject_hardlink(str(path) + suffix)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        try:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            identity = target_identity(target)
            row = self.db.execute("SELECT value FROM meta WHERE key='target'").fetchone()
            if row and row[0] != identity:
                raise UploadError("state_target_mismatch")
            self.db.execute("INSERT OR IGNORE INTO meta VALUES ('target', ?)", (identity,))
            self.db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                asset_id TEXT PRIMARY KEY, object_key TEXT UNIQUE NOT NULL,
                local_sha256 TEXT NOT NULL, local_bytes INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN
                    ('pending','uploading','uploaded','verified','failed')),
                attempts INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0,
                error_kind TEXT, last_error TEXT, remote_bytes INTEGER, etag TEXT,
                uploaded_at TEXT, verified_at TEXT, download_verified_at TEXT, updated_at TEXT NOT NULL)""")
            self.db.commit()
        except Exception:
            self.close()
            raise

    def register(self, assets):
        with self.db:
            for a in assets:
                existing = self.get(a["assetId"])
                identity = (a["objectKey"], a["sha256"], a["bytes"])
                if existing and tuple(existing[k] for k in ("object_key", "local_sha256", "local_bytes")) != identity:
                    # Reviewed B8 manifest is immutable in this version; never reuse old proof.
                    raise UploadError("state_asset_mismatch")
                self.db.execute("""INSERT OR IGNORE INTO jobs
                    (asset_id,object_key,local_sha256,local_bytes,updated_at) VALUES (?,?,?,?,?)""",
                    (a["assetId"], *identity, now()))

    def get(self, ident):
        row = self.db.execute("SELECT * FROM jobs WHERE asset_id=?", (ident,)).fetchone()
        return dict(row) if row else None

    def update(self, ident, **fields):
        allowed = {"status", "attempts", "failures", "error_kind", "last_error", "remote_bytes", "etag",
                   "uploaded_at", "verified_at", "download_verified_at"}
        if not fields.keys() <= allowed:
            raise UploadError("invalid_state_update")
        fields["updated_at"] = now()
        with self.db:
            self.db.execute("UPDATE jobs SET " + ",".join(k + "=?" for k in fields) + " WHERE asset_id=?",
                            (*fields.values(), ident))

    def recover(self):
        with self.db:
            self.db.execute("UPDATE jobs SET status='pending',updated_at=? WHERE status IN ('uploading','uploaded')", (now(),))

    def retry_failed(self, ids):
        changed = 0
        with self.db:
            for ident in ids:
                changed += self.db.execute("""UPDATE jobs SET status='pending',failures=0,
                    error_kind=NULL,last_error=NULL,updated_at=? WHERE asset_id=? AND status='failed'""",
                    (now(), ident)).rowcount
        return changed

    def summary(self, assets):
        return summarize(dict(self.db.execute("SELECT asset_id,status FROM jobs")), assets)

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None
