"""Build the B3 catalog offline from the retained safe audio snapshot."""
import argparse
import hashlib
from pathlib import Path
import sys

from catalog_lib import CATALOG, SCHEMA, SNAPSHOT, build_catalog, json_text, load_json, validate_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    parser.add_argument("--output", type=Path, default=CATALOG)
    args = parser.parse_args()
    try:
        snapshot = load_json(args.snapshot)
        catalog = build_catalog(snapshot)
        errors = validate_catalog(catalog, snapshot, load_json(args.schema))
        if errors:
            raise ValueError("\n".join(errors))
        content = json_text(catalog).encode("utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(content)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: built {args.output}\nSHA-256: {hashlib.sha256(content).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
