"""B6/B7: durable AAC/M4A downloader, verified resume and offline audit. No upload."""
import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import shutil
import signal
import sys
import threading

from catalog_lib import CATALOG, ROOT, SCHEMA, SNAPSHOT, load_json, validate_catalog
from download_state import BatchLock, CATALOG_HASH, PROFILE, State, enumerate_jobs, now, sha256
from download_pipeline import Backend, audit, process

DB = ROOT / "state/transfers.sqlite"
SUMMARY = ROOT / "state/download-summary.json"
LOG = logging.getLogger("download-media")


def summary(state, run=None):
    rows = state.rows()
    completed = [r for r in rows if r["status"] == "completed"]
    failures = [{k: r[k] for k in ("logical_id", "variant", "asset_id", "source_url", "attempts", "error_kind", "last_error")}
                for r in rows if r["status"] == "failed"]
    event_counts = dict(state.db.execute("SELECT kind,COUNT(*) FROM events GROUP BY kind").fetchall())
    value = {"phase": "B6/B7 operational summary; not a delivery manifest", "generatedAt": now(),
             "catalogSha256": sha256(CATALOG), "catalogAssets": len(rows), "attempted": sum(r["attempts"] > 0 for r in rows),
             "completed": len(completed), "failed": len(failures), "pending": sum(r["status"] not in ("completed", "failed") for r in rows),
             "guideCompleted": sum(r["variant"] == "guide" for r in completed),
             "instrumentalCompleted": sum(r["variant"] == "instrumental" for r in completed),
             "meditationsCompleted": sum(r["variant"] == "silent" for r in completed),
             "totalBytes": sum(r["byte_size"] or 0 for r in completed),
             "codecDistribution": dict(Counter(r["codec"] for r in completed)),
             "sampleRateDistribution": dict(Counter(str(r["sample_rate"]) for r in completed)),
             "durationRangeSeconds": [min((r["probed_duration"] for r in completed), default=None), max((r["probed_duration"] for r in completed), default=None)],
             "sha256Count": sum(bool(r["sha256"]) for r in completed),
             "probeVerified": sum(r["probe_verified"] for r in completed), "decodeVerified": sum(r["decode_verified"] for r in completed),
             "attemptCount": sum(r["attempts"] for r in rows), "retryCount": event_counts.get("retry", 0),
             "retryRounds": event_counts.get("retry_round", 0), "skippedResumed": event_counts.get("skip_verified", 0) + event_counts.get("recovered_verified_temp", 0),
             "auditPassed": event_counts.get("audit_pass", 0), "events": event_counts,
             "warningAssets": sum(bool(json.loads(r["warnings_json"] or "[]")) for r in completed),
             "remainingFailures": failures, "profile": PROFILE, "lastRun": run}
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    temporary = SUMMARY.with_suffix(".json.tmp")
    temporary.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    temporary.replace(SUMMARY)
    return value


def setup_logging():
    (ROOT / "logs").mkdir(exist_ok=True)
    LOG.setLevel(logging.DEBUG)
    file = RotatingFileHandler(ROOT / "logs/download-media.log", maxBytes=8 * 1024 * 1024, backupCount=2, encoding="utf-8")
    file.setLevel(logging.DEBUG)
    file.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    LOG.addHandler(file); LOG.addHandler(console)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--asset", action="append", help="Restrict to an exact catalog assetId; may repeat")
    parser.add_argument("--limit", type=int, help="Restrict to first N semantically enumerated assets")
    parser.add_argument("--retry-failed", action="store_true", help="Only retry transient failed assets, one new finite round")
    parser.add_argument("--verify-only", action="store_true", help="Offline full probe/decode/hash audit of completed files")
    args = parser.parse_args()
    if args.asset and args.limit is not None: parser.error("Choose --asset or --limit")
    if args.retry_failed and args.verify_only: parser.error("Retry and audit are separate modes")
    if sha256(CATALOG) != CATALOG_HASH: parser.error("Immutable B3 catalog baseline differs")
    catalog = load_json(CATALOG)
    errors = validate_catalog(catalog, load_json(SNAPSHOT), load_json(SCHEMA))
    if errors: parser.error("Catalog validation failed: " + "; ".join(errors[:5]))
    jobs = enumerate_jobs(catalog)
    if len(jobs) != 983: parser.error("Expected exactly 983 B3 assets")
    selected = jobs
    if args.asset:
        identifiers = set(args.asset)
        if identifiers - {j["asset_id"] for j in jobs}: parser.error("Unknown assetId")
        selected = [j for j in jobs if j["asset_id"] in identifiers]
    if args.limit is not None:
        if not 1 <= args.limit <= 983: parser.error("--limit must be 1..983")
        selected = selected[:args.limit]
    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None: parser.error(f"Missing {binary}")
    if shutil.disk_usage(ROOT).free < 1024 ** 3 and not args.verify_only:
        parser.error("Less than 1 GiB free; controlled stop before media work")
    setup_logging()
    stop = threading.Event()
    previous_handler = signal.signal(signal.SIGINT, lambda *unused: stop.set())
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run = {"id": run_id, "startedAt": now(), "mode": "audit" if args.verify_only else "download",
           "workers": args.workers, "selected": len(selected), "completed": 0, "skipped": 0, "failed": 0, "audited": 0, "interrupted": 0}
    try:
        with BatchLock(ROOT / "state/download-media.lock"):
            state = State(DB)
            try:
                state.register(jobs)
                recovered = state.recover_interrupted()
                if args.retry_failed:
                    failed = {r["asset_id"] for r in state.rows() if r["status"] == "failed" and r["error_kind"] == "transient"}
                    selected = [j for j in selected if j["asset_id"] in failed]
                    state.retry_failed({j["asset_id"] for j in selected})
                    run["selected"] = len(selected)
                state.db.execute("INSERT INTO runs(id,started_at) VALUES(?,?)", (run_id, run["startedAt"]))
                state.db.commit()
                LOG.info("START %s selected=%s workers=%s recovered=%s", run["mode"], len(selected), args.workers, recovered)

                def worker(job):
                    connection = State(DB)
                    try:
                        return (audit if args.verify_only else process)(job, connection, Backend(), stop)
                    finally:
                        connection.close()

                iterator = iter(selected)
                finished = 0
                with ThreadPoolExecutor(max_workers=args.workers) as pool:
                    active = {}
                    def submit_next():
                        if stop.is_set(): return
                        job = next(iterator, None)
                        if job: active[pool.submit(worker, job)] = job
                    for _ in range(args.workers): submit_next()
                    while active:
                        done, _ = wait(active, timeout=1, return_when=FIRST_COMPLETED)
                        for future in done:
                            job = active.pop(future)
                            try:
                                outcome = future.result()
                            except Exception as exc:
                                LOG.exception("Worker fatal error; stop safely: %s", exc)
                                stop.set(); outcome = "interrupted"
                            run[outcome] += 1
                            finished += 1
                            row = state.get(job["asset_id"])
                            LOG.info("[%s/%s] %s %s %s bytes=%s SHA256=%s completed=%s failed=%s remaining=%s",
                                     finished, len(selected), job["key"], job["variant"], outcome.upper(), row["byte_size"] or 0,
                                     (row["sha256"] or "")[:16], run["completed"] + run["skipped"], run["failed"], len(selected) - finished)
                            if finished % 10 == 0: summary(state, run)
                            submit_next()
                run.update(finishedAt=now(), stopped=stop.is_set())
                value = summary(state, run)
                state.db.execute("UPDATE runs SET finished_at=?,summary_json=? WHERE id=?", (run["finishedAt"], json.dumps(run), run_id))
                state.db.commit()
                LOG.info("SUMMARY completed=%s failed=%s pending=%s skipped_this_run=%s audited_this_run=%s bytes=%s",
                         value["completed"], value["failed"], value["pending"], run["skipped"], run["audited"], value["totalBytes"])
                if sha256(CATALOG) != CATALOG_HASH: raise RuntimeError("Catalog mutated during batch")
                if stop.is_set(): return 2
                return 0 if run["failed"] == 0 and run["interrupted"] == 0 else 1
            finally:
                state.close()
    except (OSError, RuntimeError) as exc:
        LOG.error("STOP: %s", exc)
        return 2
    finally:
        signal.signal(signal.SIGINT, previous_handler)


if __name__ == "__main__":
    sys.exit(main())
