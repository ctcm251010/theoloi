"""Offline supplementary prayer preparation; default dry-run, --write creates JSON."""
import argparse

from catalog_lib import ROOT
from prayer_assets import prepare, write_prepared
from r2_pipeline import safe_error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write only separate prayer manifest and quick-audio projection")
    args = parser.parse_args(argv)
    try:
        manifest, quick = prepare(ROOT)
        if args.write:
            write_prepared(ROOT, manifest, quick)
        print(("Written" if args.write else "Dry-run") + " prayer-assets=" + str(len(manifest["assets"])) + " revision=" + quick["revision"])
        return 0
    except Exception as exc:
        print("ERROR " + safe_error(exc)[1])
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
