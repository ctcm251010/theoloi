"""Create small self-authored PDF/image fixtures and an offline processing plan."""
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

import pymupdf

from catalog_lib import ROOT, load_json, json_text
from sheet_catalog import AUDIO_CATALOG, SCHEMA, digest_json, normalize_title, validate_sheet_catalog
from sheet_paths import output_path, write_json
from sheet_pipeline import validate_plan


def make_demo(root, directory, audio):
    folder=output_path(directory,root,'tmp/sheets-demo','')
    if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
        raise ValueError('Demo directory already contains files; refusing to overwrite')
    sid='local:vi:self-authored:1'
    title='AudioTP self-authored demonstration'
    rights={'status':'confirmed','evidence':'Self-authored synthetic geometric score created by make-sheet-demo.py',
            'evidenceUrl':None,'permissions':{'store':True,'convert':True,'serve':False,'upload':False}}
    row={'id':sid,'provider':'local','sourcePostId':None,'sourcePageUrl':None,'rawTitle':title,
         'title':title,'normalizedTitle':normalize_title(title),'sourceGroup':'local','sourceNumber':1,
         'displayNumber':None,'locale':'vi','edition':'demo-v1','usageRights':rights,
         'observedContent':{'inspectionStatus':'not-observed','format':'unknown','renderer':None,'pages':[],'pdfStatus':'not-observed'},
         'originalPdf':None,'audioLinks':[],'matchingStatus':'unmatched','reviewIssues':[]}
    catalog={'schemaVersion':1,'collectionId':'audiotp:vi:self-authored-demo','locale':'vi',
             'sourceSnapshotSha256':digest_json({'generator':'make-sheet-demo.py','version':1}),
             'audioCatalogSha256':digest_json(audio),'observedDate':datetime.now(timezone(timedelta(hours=7))).date().isoformat(),
             'surveyScope':'self-authored synthetic demo only','sheets':{sid:row}}
    images=['source/local-sheets/page-1.png','source/local-sheets/page-2.png']
    plan={'schemaVersion':1,'jobs':[
        {'sheetId':sid,'edition':'demo-v1','kind':'original-pdf','inputs':['source/local-sheets/original.pdf']},
        {'sheetId':sid,'edition':'demo-v1','kind':'image-derived-pdf','inputs':images},
        {'sheetId':sid,'edition':'demo-v1','kind':'image-pages','inputs':images}]}
    errors=validate_sheet_catalog(catalog,audio,load_json(SCHEMA))
    if errors:raise ValueError('; '.join(errors))
    validate_plan(plan,catalog,audio,folder)
    inputs=folder/'source/local-sheets';inputs.mkdir(parents=True,exist_ok=True)
    with pymupdf.open() as doc:
        for n,color in enumerate(((0.12,0.3,0.65),(0.15,0.5,0.28)),1):
            page=doc.new_page(width=300,height=420)
            page.draw_rect(pymupdf.Rect(20,20,280,68),color=color,fill=color)
            page.insert_text((30,43),'AudioTP Synthetic Sheet',fontsize=16,color=(1,1,1))
            page.insert_text((30,59),f'Self-authored test material - page {n}',fontsize=10,color=(1,1,1))
            page.insert_text((30,95),'Geometric marks for file verification only.',fontsize=10)
            for base in (140,220,300):
                for line in range(5):page.draw_line((30,base+line*7),(270,base+line*7),color=(0.3,0.3,0.3),width=0.5)
                for i in range(5):
                    x=50+i*40;y=base+7*((i+n)%5)
                    page.draw_circle((x,y),3,color=color,fill=color)
                    page.draw_line((x+3,y),(x+3,y-24),color=color,width=1)
            page.insert_text((30,385),'No BookVN content. Not a worship score.',fontsize=9)
            page.get_pixmap(dpi=144).save(inputs/f'page-{n}.png')
        doc.set_metadata({'title':title,'author':'AudioTP synthetic fixture generator'})
        doc.save(inputs/'original.pdf',garbage=4,deflate=True)
    write_json(folder/'catalog/sheet-demo.json',catalog,folder)
    write_json(folder/'catalog/sheet-file-plan.demo.json',plan,folder)
    return {'status':'PASS','demoRoot':str(folder),'catalog':str(folder/'catalog/sheet-demo.json'),
            'plan':str(folder/'catalog/sheet-file-plan.demo.json'),'jobs':3,'networkRequests':0}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--directory',default='tmp/sheets-demo/sample-01')
    parser.add_argument('--audio-catalog',type=Path,default=AUDIO_CATALOG)
    args=parser.parse_args(argv)
    try:
        print(json_text(make_demo(args.root,args.directory,load_json(args.audio_catalog))),end='');return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(f'FAIL: {exc}',file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())
