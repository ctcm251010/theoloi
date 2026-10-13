"""Validate one signed Windows installer; --prepare offline or --apply private R2."""
import argparse
from contextlib import closing
import re

from catalog_lib import ROOT, load_json
from r2_pipeline import create_client, read_secrets, safe_error
from r2_state import UploadError
from windows_update import inspect_release, plain_path, validate_outputs, write_metadata, publish_installer


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", required=True, help="Exact production release/windows/VERSION-BUILDSTAMP directory")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--prepare", action="store_true", help="Write offline metadata; remote remains unverified")
    action.add_argument("--apply", action="store_true", help="Create-only upload one installer, GET/hash verify, then write metadata")
    parser.add_argument("--notes", help="Public release notes")
    return parser.parse_args(argv)


def target_config():
    target = load_json(plain_path(ROOT, "config/r2.json"))
    if (not isinstance(target, dict) or not re.fullmatch(r"[0-9a-f]{32}", target.get("accountId", ""))
            or target.get("endpoint") != "https://" + target["accountId"] + ".r2.cloudflarestorage.com"
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", target.get("bucket", ""))):
        raise UploadError("invalid_target_config")
    return target


def main(argv=None):
    args = arguments(argv)
    try:
        metadata, installer = inspect_release(ROOT, args.release_dir, args.notes)
        if args.prepare or args.apply:
            validate_outputs(ROOT)
        if args.apply:
            target = target_config()
            plain_path(ROOT, ".secrets/r2.env", writable=True)
            with closing(create_client(read_secrets(ROOT / ".secrets/r2.env", target), target, 1)) as client:
                publish_installer(client, target["bucket"], installer, metadata)
                write_metadata(ROOT, metadata)
        elif args.prepare:
            write_metadata(ROOT, metadata)
        label = "Verified remote" if args.apply else "Prepared remote-unverified" if args.prepare else "Dry-run"
        print(label + " version=" + metadata["version"] + " bytes=" + str(metadata["bytes"]) + " sha256=" + metadata["sha256"])
        return 0
    except Exception as exc:
        print("ERROR " + safe_error(exc)[1])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
