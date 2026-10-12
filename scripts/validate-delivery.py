"""Validate B8 schema, exact catalog/state mapping and every local file SHA-256."""
import argparse
from pathlib import Path
import sqlite3
import sys

from catalog_lib import CATALOG, ROOT, load_json
from delivery_lib import MANIFEST, SCHEMA, STATE, delivery_lock, inspect_inputs, validate_manifest, summary
from download_state import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root for relative localPath")
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    args = parser.parse_args()
    try:
        with delivery_lock(args.state):
            manifest = load_json(args.manifest)
            expected, warnings = inspect_inputs(args.catalog, args.state, args.root)
            errors = validate_manifest(manifest, load_json(args.schema), expected)
            if errors:
                raise ValueError("\n".join(errors))
            digest = sha256(args.manifest)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {args.manifest}\n{summary(manifest)}\nWarning assets: {len(warnings)}\nMissing assets: 0; duplicates: 0; hash mismatches: 0; invalid files: 0\nManifest SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
