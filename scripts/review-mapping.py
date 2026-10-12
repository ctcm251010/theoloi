"""Local identity review overlay CLI. Default decisions/batch are dry-run."""
import argparse
import copy
import os
from pathlib import Path
import sys

from catalog_lib import ROOT,load_json,json_text
from sheet_catalog import CATALOG,AUDIO_CATALOG
from sheet_paths import plain_path,project_root,atomic_write,write_json
from sheet_pipeline import SheetLock
from sheet_review import new_store,validate_store,apply_batch,review_queue,export_verified


def review_output(value,root,area,suffix):
    path=plain_path(value,root);parts=path.relative_to(project_root(root)).parts
    if len(parts)!=2 or parts[0]!=area or not parts[1].startswith('sheet-') or path.suffix!=suffix:
        raise ValueError(f'Output must be {area}/sheet-*{suffix}')
    if path.exists() and path.stat().st_nlink!=1:raise ValueError('Hard-link aliases are not allowed')
    return path


def load_store(path):
    store=load_json(path) if path.exists() else new_store()
    errors=validate_store(store)
    if errors:raise ValueError('; '.join(errors))
    return store


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    for name in ('init','status','queue','decide','batch','export','html'):
        cmd=sub.add_parser(name)
        cmd.add_argument('--root',type=Path,default=ROOT)
        cmd.add_argument('--catalog',type=Path,default=CATALOG);cmd.add_argument('--audio-catalog',type=Path,default=AUDIO_CATALOG)
        cmd.add_argument('--store',default='reviews/sheet-mapping-decisions.vi.json')
        if name in ('queue','export','html'):cmd.add_argument('--output',default={'queue':'reviews/sheet-review-queue.vi.json','export':'delivery/sheet-verified-mapping.vi.json','html':'reviews/sheet-review.html'}[name])
        if name in ('decide','batch'):cmd.add_argument('--apply',action='store_true')
        if name=='batch':
            cmd.add_argument('--input',type=Path,required=True);cmd.add_argument('--confirm-count',type=int)
        if name=='decide':
            cmd.add_argument('--sheet',required=True);cmd.add_argument('--song')
            cmd.add_argument('--decision',choices=('approve','reject','defer'),required=True)
            cmd.add_argument('--evidence',required=True);cmd.add_argument('--reviewer',required=True);cmd.add_argument('--provenance',required=True)
            cmd.add_argument('--reviewed',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=project_root(args.root);store_path=review_output(args.store,root,'reviews','.json')
        protected={Path(args.catalog).resolve(),Path(args.audio_catalog).resolve(),store_path.resolve()}
        if hasattr(args,'input') and args.input.resolve()==store_path.resolve():raise ValueError('Batch input cannot be the decision store')
        catalog,audio=load_json(args.catalog),load_json(args.audio_catalog)
        if args.command in ('init','decide','batch') and (args.command=='init' or args.apply):
            lock=review_output('reviews/sheet-review.lock',root,'reviews','.lock')
            with SheetLock(lock):
                # Recheck aliases under the writer lock.
                review_output(store_path,root,'reviews','.json')
                store=load_store(store_path)
                if args.command=='init':
                    if store_path.exists():raise ValueError('Review store already exists; refusing to reset')
                    write_json(store_path,store,root);result={'status':'PASS','events':0,'revision':store['revision']}
                else:result=perform_decision(args,store,catalog,audio,store_path,root)
        else:
            store=load_store(store_path)
            if args.command in ('decide','batch'):result=perform_decision(args,store,catalog,audio,store_path,root)
            elif args.command=='status':
                queue=review_queue(store,catalog,audio);export=export_verified(store,catalog,audio)
                result={'status':'PASS','events':len(store['events']),'verified':len(export['links']),'sources':len(queue['rows']),'revision':store['revision']}
            else:
                area='delivery' if args.command=='export' else 'reviews';suffix='.html' if args.command=='html' else '.json'
                output=review_output(args.output,root,area,suffix)
                if output.resolve() in protected or (hasattr(args,'input') and output.resolve()==args.input.resolve()):raise ValueError('Output collides with input/store')
                if args.command=='export':data=export_verified(store,catalog,audio);write_json(output,data,root);count=len(data['links'])
                else:
                    data=review_queue(store,catalog,audio);count=len(data['rows'])
                    if args.command=='queue':write_json(output,data,root)
                    else:
                        from sheet_review_html import render_review_html
                        atomic_write(output,render_review_html(data).encode('utf-8'),root)
                result={'status':'PASS','output':str(output),'count':count,'revision':store['revision']}
        print(json_text(result),end='');return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'FAIL: {exc}',file=sys.stderr);return 1


def perform_decision(args,store,catalog,audio,store_path,root):
    if args.command=='batch':batch=load_json(args.input)
    else:
        from sheet_catalog import digest_json
        batch={'schemaVersion':1,'catalogSha256':digest_json(catalog),'audioCatalogSha256':digest_json(audio),'baseRevision':store['revision'],
               'decisions':[{'sheetId':args.sheet,'songId':args.song,'decision':args.decision,'evidence':args.evidence,
                             'reviewer':args.reviewer,'provenance':args.provenance,'reviewed':args.reviewed}]}
    new=apply_batch(store,batch,catalog,audio)
    if args.command=='batch' and args.apply and args.confirm_count!=len(batch['decisions']):raise ValueError('--confirm-count must equal the exact reviewed batch count')
    if args.apply:write_json(store_path,new,root)
    return {'status':'PASS','dryRun':not args.apply,'decisions':len(batch['decisions']),'eventsAfter':len(new['events']),
            'revision':new['revision'] if args.apply else store['revision']}


if __name__=='__main__':sys.exit(main())
