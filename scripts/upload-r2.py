"""B9 CLI. Full upload is run by the user outside Codex."""
import argparse
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re
import signal
import threading

from catalog_lib import ROOT, load_json
from download_state import BatchLock
from r2_pipeline import create_client, load_delivery, read_secrets, read_status, safe_error, UploadRunner
from r2_state import UploadError, UploadState, reject_hardlink

STATE = ROOT / "state/r2-transfers.sqlite"


def select_assets(assets, ids=None, limit=None, retry_failed=False, state=None):
    if ids and (len(ids) != len(set(ids)) or any(i not in assets for i in ids)):
        raise UploadError("unknown_or_duplicate_asset")
    selected = [assets[i] for i in ids] if ids else list(assets.values())
    if retry_failed:
        selected = [a for a in selected if state.get(a["assetId"])["status"] == "failed"]
    return selected[:limit] if limit is not None else selected


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    parser.add_argument("--asset", action="append", help="Exact manifest assetId; repeat for a subset")
    parser.add_argument("--limit", type=int, help="Process at most N selected assets")
    parser.add_argument("--retry-failed", action="store_true", help="Only failed assets, one fresh bounded retry round")
    parser.add_argument("--status", action="store_true", help="Read-only local status; no credentials/network")
    parser.add_argument("--verify-download", action="store_true", help="Stream GET/hash only an explicit subset of at most 5 assets")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.verify_download and (not args.asset or len(args.asset) > 5):
        parser.error("--verify-download requires 1 to 5 explicit --asset IDs")
    if args.status and (args.asset or args.limit or args.retry_failed or args.verify_download):
        parser.error("--status cannot be combined with selection/upload options")
    return args


def target_config():
    target = load_json(ROOT / "config/r2.json")
    if not re.fullmatch(r"[0-9a-f]{32}", target.get("accountId", "")) or target.get("endpoint") != "https://" + target["accountId"] + ".r2.cloudflarestorage.com" or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", target.get("bucket", "")):
        raise UploadError("invalid_target_config")
    return target


def print_status(summary):
    print(" ".join(k + "=" + str(v) for k, v in summary.items()))


def execute(args, assets, target):
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    # Reject redirects and hard-link aliases before any writable open.
    from delivery_lib import check_plain_path
    for relative in ("state", "state/r2-transfers.sqlite", "state/r2-transfers.sqlite-wal",
                     "state/r2-transfers.sqlite-shm", "state/r2-transfers.sqlite-journal",
                     "state/upload-r2.lock", "logs", "logs/r2-upload.log", "logs/r2-upload.log.1",
                     "logs/r2-upload.log.2", "logs/r2-upload.log.3", ".secrets/r2.env"):
        check_plain_path(ROOT / relative, ROOT)
        reject_hardlink(ROOT / relative)
    with BatchLock(ROOT / "state/upload-r2.lock"):
        state = UploadState(STATE, target)
        client = None
        logger = logging.getLogger("audiotp.r2")
        handler = None
        try:
            state.register(list(assets.values()))
            state.recover()
            selected = select_assets(assets, args.asset, args.limit, args.retry_failed, state)
            if args.retry_failed:
                state.retry_failed([a["assetId"] for a in selected])
            print("Selected=" + str(len(selected)) + " workers=" + str(args.workers))
            if not selected:
                print_status(state.summary(list(assets.values())))
                return 0
            client = create_client(read_secrets(ROOT / ".secrets/r2.env", target), target, args.workers)
            (ROOT / "logs").mkdir(exist_ok=True)
            handler = RotatingFileHandler(ROOT / "logs/r2-upload.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            logger.addHandler(handler); logger.setLevel(logging.INFO); logger.propagate = False

            def work(a):
                local_state = UploadState(STATE, target)
                try:
                    result = UploadRunner(client, target["bucket"], ROOT, local_state, stop).process(a, args.verify_download)
                    row = local_state.get(a["assetId"])
                    message = a["assetId"] + " " + result + (" " + row["last_error"] if row["last_error"] else "")
                    logger.info(message)
                    return message, result
                finally:
                    local_state.close()

            outcomes = {"uploaded": 0, "skipped": 0, "failed": 0, "interrupted": 0}
            iterator = iter(selected)
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                pending = set()
                while True:
                    while len(pending) < args.workers and not stop.is_set():
                        item = next(iterator, None)
                        if item is None:
                            break
                        pending.add(pool.submit(work, item))
                    if not pending:
                        break
                    done, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                    for future in done:
                        message, result = future.result()
                        outcomes[result] += 1
                        print(message, flush=True)
            print_status(state.summary(list(assets.values())))
            print("Run " + " ".join(k + "=" + str(v) for k,v in outcomes.items()))
            return 130 if stop.is_set() else (1 if outcomes["failed"] else 0)
        finally:
            state.close()
            if client:
                client.close()
            if handler:
                logger.removeHandler(handler); handler.close()


def main(argv=None):
    args = arguments(argv)
    try:
        assets = load_delivery(ROOT / "delivery/manifest.vi.json")["assets"]
        target = target_config()
        if args.status:
            print_status(read_status(STATE, list(assets.values()), target))
            return 0
        return execute(args, assets, target)
    except Exception as exc:
        _, code = safe_error(exc)
        print("ERROR " + code)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
