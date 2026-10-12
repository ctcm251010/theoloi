"""Build/validate the observed sheet catalog and audio mapping offline."""
import argparse
from pathlib import Path
import sys

from catalog_lib import ROOT, load_json
from sheet_catalog import AUDIO_CATALOG, CATALOG, SCHEMA, SNAPSHOT, build_sheet_catalog, mapping_report, mapping_markdown, validate_sheet_catalog
from sheet_paths import atomic_write, output_path, write_json


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('build','validate'):
        cmd=sub.add_parser(name)
        cmd.add_argument('--snapshot',type=Path,default=SNAPSHOT)
        cmd.add_argument('--audio-catalog',type=Path,default=AUDIO_CATALOG)
        cmd.add_argument('--schema',type=Path,default=SCHEMA)
        if name=='build':
            cmd.add_argument('--root',type=Path,default=ROOT)
            cmd.add_argument('--output',type=Path,default=CATALOG)
            cmd.add_argument('--report',type=Path,default=ROOT/'docs/sheet-mapping-report.md')
            cmd.add_argument('--mapping',type=Path,default=ROOT/'delivery/sheet-mapping.vi.json')
            cmd.add_argument('--dry-run',action='store_true')
        else: cmd.add_argument('--catalog',type=Path,default=CATALOG)
    args=parser.parse_args(argv)
    try:
        snapshot,audio,schema=load_json(args.snapshot),load_json(args.audio_catalog),load_json(args.schema)
        catalog=build_sheet_catalog(snapshot,audio) if args.command=='build' else load_json(args.catalog)
        errors=validate_sheet_catalog(catalog,audio,schema,snapshot)
        if errors: raise ValueError('\n'.join(errors))
        report=mapping_report(catalog,audio)
        if args.command=='build':
            paths=[output_path(args.output,args.root,'catalog','.json'),output_path(args.report,args.root,'docs','.md'),output_path(args.mapping,args.root,'delivery','.json')]
            protected={Path(p).resolve() for p in (args.snapshot,args.audio_catalog,args.schema)}
            if any(p.resolve() in protected for p in paths): raise ValueError('Output collides with input')
            if not args.dry_run:
                write_json(paths[0],catalog,args.root)
                atomic_write(paths[1],mapping_markdown(report).encode('utf-8'),args.root)
                write_json(paths[2],report,args.root)
        print(f"PASS: sheet catalog schema + semantics + source comparison\nCounts: {report['counts']}")
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'FAIL: {exc}',file=sys.stderr); return 1


if __name__=='__main__': sys.exit(main())
