"""Build B8 delivery offline; audit all 983 files before atomic publication."""
import argparse
from pathlib import Path
import sqlite3
import sys

from catalog_lib import CATALOG, ROOT, load_json
from delivery_lib import MANIFEST, SCHEMA, STATE, delivery_lock, inspect_inputs, validate_manifest, validate_output_path, write_atomic, summary
from download_state import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--root", type=Path, default=ROOT, help="Project root for relative localPath")
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--output", type=Path, default=MANIFEST, help="JSON file inside projectRoot/delivery")
    args = parser.parse_args()
    try:
        args.output = validate_output_path(args.output, args.root, (args.catalog, args.state, args.schema))
        with delivery_lock(args.state):
            manifest, warnings = inspect_inputs(args.catalog, args.state, args.root)
            errors = validate_manifest(manifest, load_json(args.schema), manifest)
            if errors:
                raise ValueError("\n".join(errors))
            write_atomic(args.output, manifest)
            digest = sha256(args.output)
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {args.output}\n{summary(manifest)}\nWarning assets: {len(warnings)}\nRevision: {manifest['revision']}\nManifest SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
