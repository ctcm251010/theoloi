"""Validate JSON Schema and source-aware B3 semantics offline; exit 1 on failure."""
import argparse
import hashlib
from pathlib import Path
import sys

from catalog_lib import CATALOG, SCHEMA, SNAPSHOT, catalog_counts, load_json, validate_catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--schema", type=Path, default=SCHEMA)
    args = parser.parse_args()
    try:
        catalog = load_json(args.catalog)
        errors = validate_catalog(catalog, load_json(args.snapshot), load_json(args.schema))
        if errors:
            raise ValueError("\n".join(errors))
        digest = hashlib.sha256(args.catalog.read_bytes()).hexdigest()
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: schema + B3 semantics + source comparison\nCounts: {catalog_counts(catalog)}\nSHA-256: {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
