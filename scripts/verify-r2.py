"""User-run B10: independent LIST/HEAD audit, no object bodies or R2 writes."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
import json
import re
import signal
import threading
import uuid

from catalog_lib import ROOT, load_json
from delivery_lib import check_plain_path
from r2_pipeline import create_client, load_delivery, MANIFEST_SHA256, read_secrets, safe_error
from r2_state import UploadError


def read_only_guard(model, **kwargs):
    """Block every SDK operation except LIST/HEAD before request construction."""
    if model.name not in {"ListObjectsV2", "HeadObject"}:
        raise UploadError("read_only_operation_blocked")


def read_call(method, stop, **params):
    for attempt in range(3):
        if stop.is_set():
            raise UploadError("interrupted")
        try:
            return method(**params)
        except Exception as exc:
            kind, _ = safe_error(exc)
            if kind != "transient" or attempt == 2:
                raise
            if stop.wait(2 ** (attempt + 1)):
                raise UploadError("interrupted") from None


def inventory(client, bucket, stop):
    """No Prefix/Delimiter: include extras anywhere in this dedicated bucket."""
    objects, tokens, token, pages = {}, set(), None, 0
    while True:
        params = {"Bucket": bucket, "MaxKeys": 1000}
        if token is not None:
            params["ContinuationToken"] = token
        page = read_call(client.list_objects_v2, stop, **params)
        pages += 1
        if not isinstance(page, dict) or not isinstance(page.get('Contents', []), list):
            raise UploadError('invalid_inventory_response')
        for obj in page.get("Contents", []):
            if not isinstance(obj, dict):
                raise UploadError('invalid_inventory_response')
            key, size = obj.get("Key"), obj.get("Size")
            if not isinstance(key, str) or not key or type(size) is not int or size < 0 or key in objects:
                raise UploadError("invalid_or_changing_inventory")
            if not isinstance(obj.get('ETag'), str) or not obj['ETag'].strip():
                raise UploadError('invalid_inventory_etag')
            objects[key] = {"bytes": size, "etag": obj.get("ETag")}
        truncated = page.get("IsTruncated")
        if type(truncated) is not bool:
            raise UploadError("invalid_inventory_pagination")
        if not truncated:
            return objects, pages
        token = page.get("NextContinuationToken")
        if not isinstance(token, str) or not token or token in tokens:
            raise UploadError("invalid_inventory_pagination")
        tokens.add(token)


def head_check(client, bucket, asset, listed, stop):
    key = asset["objectKey"]
    row = {"assetId": asset["assetId"], "objectKey": key, "expectedBytes": asset["bytes"],
           "status": "FAIL", "issues": []}
    try:
        head = read_call(client.head_object, stop, Bucket=bucket, Key=key)
    except Exception as exc:
        _, code = safe_error(exc)
        row["issues"] = ["missing_head" if code == "remote_http_404" else code]
        row["headSucceeded"] = False
        return row
    row["headSucceeded"] = isinstance(head, dict)
    if not isinstance(head, dict) or not isinstance(head.get('Metadata', {}), dict):
        row['issues'] = ['invalid_head_response']
        return row
    size = head.get("ContentLength")
    # Persist booleans/static issue names, never arbitrary remote metadata values.
    row["remoteBytes"] = size if type(size) is int else None
    metadata = head.get("Metadata", {})
    checks = {
        "size": type(size) is int and size == asset["bytes"],
        "metadata_sha256": metadata.get("sha256") == asset["sha256"],
        "metadata_asset_id": metadata.get("asset-id") == asset["assetId"],
        "content_type": head.get("ContentType") == "audio/mp4",
        "listed": listed is not None,
        "list_size": listed is not None and listed["bytes"] == asset["bytes"],
        # ETag is only an opaque change detector, never a SHA-256 digest.
        "list_head_etag": listed is not None and isinstance(listed['etag'], str) and bool(listed['etag'].strip())
        and isinstance(head.get('ETag'), str) and bool(head['ETag'].strip()) and listed['etag'] == head['ETag'],
    }
    row["checks"] = checks
    row["issues"] = [name for name, matches in checks.items() if not matches]
    row["status"] = "PASS" if not row["issues"] else "FAIL"
    return row


def audit(client, target, assets, workers, stop, report):
    keys, identities = set(), set()
    for asset in assets:
        if (not isinstance(asset, dict) or not isinstance(asset.get('objectKey'), str) or not asset['objectKey']
            or not isinstance(asset.get('assetId'), str) or not asset['assetId']
            or type(asset.get('bytes')) is not int or asset['bytes'] <= 0
            or not isinstance(asset.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', asset['sha256'])
            or asset['objectKey'] in keys or asset['assetId'] in identities):
            raise UploadError('invalid_or_duplicate_expected_asset')
        keys.add(asset['objectKey']); identities.add(asset['assetId'])
    listed, pages = inventory(client, target["bucket"], stop)
    expected = {a["objectKey"] for a in assets}
    report.update(inventoryComplete=True, listPages=pages, actualObjectCount=len(listed),
                  actualBytes=sum(o["bytes"] for o in listed.values()),
                  missingKeys=sorted(expected - listed.keys()), extraKeys=sorted(listed.keys() - expected))
    iterator = iter(assets)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        pending = set()
        while True:
            while len(pending) < workers and not stop.is_set():
                asset = next(iterator, None)
                if asset is None:
                    break
                pending.add(pool.submit(head_check, client, target["bucket"], asset,
                                        listed.get(asset["objectKey"]), stop))
            if not pending:
                break
            done, pending = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
            for future in done:
                report["objects"].append(future.result())
                count = len(report["objects"])
                if count % 100 == 0 or count == len(assets):
                    print(f"HEAD checked: {count}/{len(assets)}", flush=True)


def finish_report(report, stop):
    report["finishedAt"] = datetime.now(timezone.utc).isoformat()
    rows = report["objects"]
    report["objects"] = sorted(rows, key=lambda r: r["objectKey"])
    # A key seen by LIST but gone by HEAD also counts as missing (changing bucket).
    report["missingKeys"] = sorted(set(report["missingKeys"]) |
                                   {r["objectKey"] for r in rows if "missing_head" in r["issues"]})
    if stop.is_set() and "interrupted" not in report["errors"]:
        report["errors"].append("interrupted")
    report["summary"] = {
        "expected": report["expectedObjectCount"], "actual": report["actualObjectCount"],
        "checked": len(rows), "matched": sum(r["status"] == "PASS" for r in rows),
        "missing": len(report["missingKeys"]), "extra": len(report["extraKeys"]),
        "mismatched": sum(r["headSucceeded"] and r["status"] == "FAIL" for r in rows),
        "headErrors": sum(not r["headSucceeded"] for r in rows), "errors": len(report["errors"]),
    }
    report["status"] = "PASS" if (
        report["inventoryComplete"] and report["expectedObjectCount"] is not None
        and report["actualObjectCount"] == report["expectedObjectCount"]
        and len(rows) == report["expectedObjectCount"]
        and all(r["status"] == "PASS" for r in rows)
        and not report["missingKeys"] and not report["extraKeys"] and not report["errors"]
    ) else "FAIL"


def report_destination():
    base = ROOT / "logs/r2-verification"
    check_plain_path(base, ROOT)
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder = base / (stamp + "-" + uuid.uuid4().hex[:8])
    folder.mkdir()  # New directory per run; never overwrite previous reports/inputs.
    return folder / "report.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    args = parser.parse_args(argv)
    stop, client, secrets = threading.Event(), None, []
    report = {"schemaVersion": 1, "status": "FAIL", "startedAt": datetime.now(timezone.utc).isoformat(),
              "mode": "inventory-and-head-metadata", "contentSha256Verified": False,
              "hashVerification": "metadata-match-only; not an independent hash of remote bytes",
              "stateUsedForRemoteVerdict": False, "allowedOperations": ["ListObjectsV2", "HeadObject"],
              "expectedObjectCount": None, "actualObjectCount": None, "inventoryComplete": False,
              "missingKeys": [], "extraKeys": [], "objects": [], "errors": []}
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        destination = report_destination()
    except Exception as exc:
        print("FAIL: cannot create report; " + safe_error(exc)[1])
        return 1
    try:
        manifest = load_delivery(ROOT / "delivery/manifest.vi.json")
        assets = list(manifest["assets"].values())
        target = load_json(ROOT / "config/r2.json")
        account = target.get("accountId", "")
        if not re.fullmatch(r"[0-9a-f]{32}", account) or target.get("endpoint") != "https://" + account + ".r2.cloudflarestorage.com" or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", target.get("bucket", "")):
            raise UploadError("invalid_target_config")
        report.update(bucket=target["bucket"], accountId=account, manifestSha256=MANIFEST_SHA256,
                      expectedObjectCount=len(assets), expectedBytes=sum(a["bytes"] for a in assets))
        check_plain_path(ROOT / ".secrets/r2.env", ROOT)
        values = read_secrets(ROOT / ".secrets/r2.env", target)
        secrets = [values["R2_ACCESS_KEY_ID"], values["R2_SECRET_ACCESS_KEY"]]
        client = create_client(values, target, args.workers)
        client.meta.events.register("provide-client-params.s3", read_only_guard)
        print(f"B10 READ ONLY: LIST entire bucket + HEAD {len(assets)} objects; no GET/PUT/DELETE.", flush=True)
        audit(client, target, assets, args.workers, stop, report)
    except Exception as exc:
        report["errors"].append(safe_error(exc)[1])
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                report['errors'].append('client_cleanup_error')
    finish_report(report, stop)
    try:
        encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        # Unexpected remote object names cannot leak these credentials into a report.
        for value in secrets:
            encoded = encoded.replace(value, "[REDACTED]")
        with destination.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
    except Exception as exc:
        print("FAIL: cannot save report; " + safe_error(exc)[1])
        return 1
    print(report["status"] + ": " + " ".join(k + "=" + str(v) for k, v in report["summary"].items()))
    print("SHA-256: metadata match only; remote content was not downloaded or hashed.")
    print("Report: " + str(destination))
    return 130 if stop.is_set() else (0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
