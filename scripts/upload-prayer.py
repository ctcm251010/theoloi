"""Single supplementary prayer upload; dry-run unless --apply is explicit."""
import argparse
import re
import signal
import threading

from catalog_lib import ROOT, load_json
from download_state import BatchLock
from prayer_assets import STATE, LOCK, load_prepared, plain_path
from r2_pipeline import create_client, read_secrets, read_status, safe_error, UploadRunner
from r2_state import UploadError, UploadState


class PrayerUploadRunner(UploadRunner):
    def verify_head(self, asset, head):
        super().verify_head(asset, head)
        if head.get('ContentType') != 'audio/mp4':
            raise UploadError('prayer_content_type_mismatch')


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Upload the one approved registry entry with create-only PUT")
    mode.add_argument("--status", action="store_true", help="Read-only local state, no credentials or network")
    parser.add_argument("--verify-download", action="store_true", help="Stream GET and verify the single registered file's full SHA-256")
    parser.add_argument("--retry-failed", action="store_true", help="Retry failed entry in one fresh round of at most three transient attempts")
    parser.add_argument('--asset',help='Exact supplementary asset ID; required when registry has multiple assets')
    args = parser.parse_args(argv)
    if (args.verify_download or args.retry_failed) and not args.apply:
        parser.error("--verify-download and --retry-failed require --apply")
    return args


def target_config():
    target = load_json(plain_path(ROOT, "config/r2.json"))
    if (not isinstance(target, dict) or not re.fullmatch(r"[0-9a-f]{32}", target.get("accountId", ""))
            or target.get("endpoint") != "https://" + target["accountId"] + ".r2.cloudflarestorage.com"
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", target.get("bucket", ""))):
        raise UploadError("invalid_target_config")
    return target


def print_status(summary):
    print(" ".join(key + "=" + str(value) for key, value in summary.items()))


def execute(args, assets, target):
    if len(assets) != 1:
        raise UploadError("prayer_requires_single_asset")
    for relative in ("state", str(STATE), str(STATE) + "-wal", str(STATE) + "-shm", str(STATE) + "-journal", str(LOCK), ".secrets/r2.env"):
        plain_path(ROOT, relative, writable=True)
    stop = threading.Event()
    previous = {}
    client = state = None
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, lambda *_: stop.set())
        with BatchLock(ROOT / LOCK):
            state = UploadState(ROOT / STATE, target)
            state.register(assets)
            asset = assets[0]
            if state.get(asset["assetId"])["status"] in ("uploading", "uploaded"):
                state.update(asset["assetId"], status="pending")
            if args.retry_failed:
                state.retry_failed([asset["assetId"]])
            if state.get(asset["assetId"])["status"] == "failed":
                print_status(state.summary(assets))
                return 1
            client = create_client(read_secrets(ROOT / ".secrets/r2.env", target), target, 1)
            result = PrayerUploadRunner(client, target["bucket"], ROOT, state, stop).process(asset, args.verify_download)
            row = state.get(asset["assetId"])
            print("prayer " + result + (" " + row["last_error"] if row["last_error"] else ""))
            print_status(state.summary(assets))
            return 130 if result == "interrupted" else (1 if result == "failed" else 0)
    finally:
        if client is not None:
            client.close()
        if state is not None:
            state.close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main(argv=None):
    args = arguments(argv)
    try:
        manifest = load_prepared(ROOT, verify_local=not args.status)
        assets = list(manifest["assets"].values())
        if args.asset:
            assets=[a for a in assets if a['assetId']==args.asset]
            if not assets:raise UploadError('prayer_unknown_asset')
        elif not args.status and len(assets)!=1:
            raise UploadError('prayer_select_asset_required')
        if args.status:
            plain_path(ROOT, STATE)
            for suffix in ("-wal", "-shm", "-journal"):
                plain_path(ROOT, str(STATE) + suffix)
            print_status(read_status(ROOT / STATE, assets, target_config()))
            return 0
        if not args.apply:
            print("Dry-run prayer-assets=" + str(len(assets)) + " bytes=" + str(sum(a["bytes"] for a in assets)))
            return 0
        return execute(args, assets, target_config())
    except Exception as exc:
        print("ERROR " + safe_error(exc)[1])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
