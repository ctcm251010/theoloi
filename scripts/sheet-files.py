"""Offline sheet files: process authorized local inputs, resume, status, verify. No downloads."""
import argparse
from pathlib import Path
import sys

from catalog_lib import ROOT,load_json,json_text
from sheet_catalog import CATALOG,AUDIO_CATALOG,SCHEMA,validate_sheet_catalog
from sheet_media import inspect_file
from sheet_paths import output_path,relative_input,write_json
from sheet_pipeline import process_plan,read_status,validate_manifest,build_manifest,manifest_file_summary


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('process','status','verify','inspect','init-manifest'):
        cmd=sub.add_parser(name)
        cmd.add_argument('--root',type=Path,default=ROOT)
        if name in ('process','verify','init-manifest'):
            cmd.add_argument('--catalog',type=Path,default=CATALOG)
            cmd.add_argument('--audio-catalog',type=Path,default=AUDIO_CATALOG)
            cmd.add_argument('--manifest',type=Path,default=Path('delivery/sheet-manifest.vi.json'))
        if name in ('process','status'):
            cmd.add_argument('--state',type=Path,default=Path('state/sheet-transfers.sqlite'))
        if name=='process':
            cmd.add_argument('--plan',type=Path,required=True)
            cmd.add_argument('--dry-run',action='store_true')
            cmd.add_argument('--retry-failed',action='store_true')
        if name=='inspect':cmd.add_argument('--input',type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.command=='status':
            result=read_status(output_path(args.state,args.root,'state','.sqlite'))
        elif args.command=='inspect':
            result=inspect_file(relative_input(args.input.as_posix(),args.root))
        else:
            catalog,audio=load_json(args.catalog),load_json(args.audio_catalog)
            errors=validate_sheet_catalog(catalog,audio,load_json(SCHEMA))
            if errors:raise ValueError('\n'.join(errors))
            target=output_path(args.manifest,args.root,'delivery','.json')
            if args.command=='process':
                result=process_plan(load_json(args.plan),catalog,audio,args.root,args.state,target,args.dry_run,args.retry_failed,
                                    progress=lambda n,total,jid,status:print(f'[{n}/{total}] {status}: {jid}'))
            elif args.command=='verify':
                manifest=load_json(target)
                errors=validate_manifest(manifest,catalog,audio,args.root)
                if errors:raise ValueError('\n'.join(errors))
                result={'status':'PASS','manifest':str(target),'assets':len(manifest['assets']),**manifest_file_summary(manifest)}
            else:
                if target.exists() and load_json(target).get('assets'):
                    raise ValueError('Refusing to replace an existing nonempty sheet manifest')
                result=build_manifest(catalog,audio,{})
                errors=validate_manifest(result,catalog,audio,args.root)
                if errors:raise ValueError('\n'.join(errors))
                write_json(target,result,args.root)
                result={'status':'PASS','manifest':str(target),'available':0,'noFile':len(catalog['sheets'])}
        print(json_text(result),end='')
        return 1 if result.get('counts',{}).get('failed',0) else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'FAIL: {exc}',file=sys.stderr);return 1
    except KeyboardInterrupt:
        print('Stopped. State and completed artifacts retained; rerun the same process command to resume.',file=sys.stderr)
        return 130


if __name__=='__main__':sys.exit(main())
