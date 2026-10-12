"""Durable B6/B7 jobs and local paths; content catalog stays immutable."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from catalog_lib import ROOT

CATALOG_HASH = "e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4"
PROFILE = {"version": 1, "container": "m4a/ipod", "codec": "source-aac", "strategy": "copy",
           "faststart": True, "sampleRate": "source", "channels": "source", "bitrate": "source"}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def enumerate_jobs(catalog, root=ROOT):
    root = Path(root).resolve()
    media = root / "media/audio/v1/watv/vi"
    jobs = []

    def add(key, logical_id, variant, asset, final):
        identifier = asset["assetId"]
        work = root / "tmp/downloads" / identifier.replace(":", "_")
        fingerprint = hashlib.sha256(json.dumps({"assetId": identifier, "source": asset["source"], "profile": PROFILE},
                                    sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        jobs.append({"asset_id": identifier, "logical_id": logical_id, "key": key, "variant": variant,
                     "source_url": asset["source"]["hlsUrl"], "fingerprint": fingerprint,
                     "profile": json.dumps(PROFILE, sort_keys=True), "metadata_duration": asset["durationSeconds"],
                     "final_path": str(final), "temp_path": str(work / "output.part.m4a"), "work_dir": str(work)})

    for key, song in sorted(catalog["songs"].items(), key=lambda item: (item[1]["section"] == "appendix", item[1]["number"])):
        for variant in ("guide", "instrumental"):
            if variant in song["variants"]:
                add(key, song["id"], variant, song["variants"][variant],
                    media / "newsong" / song["section"] / f"{song['number']:04d}" / f"{variant}.m4a")
    for key, row in sorted(catalog["meditations"].items()):
        add(key, row["id"], "silent", row["asset"], media / "meditations" / f"{row['asset']['source']['audioId']}.m4a")
    if len({j["asset_id"] for j in jobs}) != len(jobs) or len({j["final_path"] for j in jobs}) != len(jobs):
        raise ValueError("Duplicate asset IDs or final paths")
    return jobs


class State:
    """One connection per worker, committed transitions, WAL + FULL durability."""
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
          asset_id TEXT PRIMARY KEY, logical_id TEXT NOT NULL, key TEXT NOT NULL, variant TEXT NOT NULL,
          source_url TEXT NOT NULL, fingerprint TEXT NOT NULL, profile TEXT NOT NULL, metadata_duration REAL,
          final_path TEXT NOT NULL, temp_path TEXT NOT NULL, work_dir TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','downloading','verifying','completed','failed')),
          attempts INTEGER NOT NULL DEFAULT 0, failures INTEGER NOT NULL DEFAULT 0,
          started_at TEXT, finished_at TEXT, updated_at TEXT, last_error TEXT, error_kind TEXT,
          byte_size INTEGER, sha256 TEXT, probed_duration REAL, source_duration REAL, codec TEXT,
          sample_rate INTEGER, channels INTEGER, channel_layout TEXT,
          probe_verified INTEGER NOT NULL DEFAULT 0, decode_verified INTEGER NOT NULL DEFAULT 0,
          verification_json TEXT, warnings_json TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, asset_id TEXT, at TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT
        );
        CREATE TABLE IF NOT EXISTS runs (
          id TEXT PRIMARY KEY, started_at TEXT, finished_at TEXT, summary_json TEXT
        );
        """)
        self.columns = {r["name"] for r in self.db.execute("PRAGMA table_info(jobs)")}

    def register(self, jobs):
        with self.db:
            for job in jobs:
                previous = self.get(job["asset_id"])
                if previous is None:
                    fields = list(job)
                    self.db.execute(f"INSERT INTO jobs ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})", list(job.values()))
                elif previous["fingerprint"] != job["fingerprint"]:
                    self.update(job["asset_id"], **{k: v for k, v in job.items() if k != "asset_id"},
                                status="pending", failures=0, sha256=None, byte_size=None, probe_verified=0,
                                decode_verified=0, verification_json=None, last_error="Source/profile fingerprint changed")

    def get(self, asset_id):
        row = self.db.execute("SELECT * FROM jobs WHERE asset_id=?", (asset_id,)).fetchone()
        return dict(row) if row else None

    def rows(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM jobs ORDER BY asset_id")]

    def update(self, asset_id, **fields):
        if set(fields) - self.columns:
            raise ValueError("Unknown state column")
        fields["updated_at"] = now()
        with self.db:
            self.db.execute(f"UPDATE jobs SET {','.join(k + '=?' for k in fields)} WHERE asset_id=?", [*fields.values(), asset_id])

    def event(self, asset_id, kind, detail=""):
        with self.db:
            self.db.execute("INSERT INTO events(asset_id,at,kind,detail) VALUES(?,?,?,?)", (asset_id, now(), kind, detail))

    def recover_interrupted(self):
        count = 0
        for row in self.rows():
            if row["status"] in ("downloading", "verifying"):
                # Keep verified evidence. Worker reconciles tmp/final before any
                # network work, including a crash immediately after atomic rename.
                self.update(row["asset_id"], status="pending", last_error="Interrupted run; reconcile retained evidence")
                self.event(row["asset_id"], "interrupted_recovery")
                count += 1
        return count

    def retry_failed(self, asset_ids=None):
        count = 0
        for row in self.rows():
            if (row["status"] == "failed" and row["error_kind"] == "transient"
                    and (asset_ids is None or row["asset_id"] in asset_ids)):
                self.update(row["asset_id"], status="pending", failures=0)
                self.event(row["asset_id"], "retry_round")
                count += 1
        return count

    def close(self):
        self.db.close()


class BatchLock:
    """OS advisory lock, released on process death; no stale PID guessing."""
    def __init__(self, path):
        self.path = Path(path)
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        if self.path.stat().st_size == 0:
            self.stream.write(b"0"); self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.stream.close()
            raise RuntimeError("Another download/verify batch already holds the state lock") from exc
        return self

    def __exit__(self, *args):
        self.stream.seek(0)
        if os.name == "nt":
            import msvcrt
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(self.stream, fcntl.LOCK_UN)
        self.stream.close()
