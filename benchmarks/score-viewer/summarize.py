"""Analyze actual UI-exported evidence; never invent missing observations."""
import argparse
import json
import statistics
from pathlib import Path


def analyze(data):
    rows=[r for r in data['rows'] if r['phase'] in ('first','next','revisit')]
    result={'observations':len(rows),'environment':data['environment'],'groups':[]}
    for fmt in ('pdf','png','webp','avif','vector'):
        for condition in ('cold','warm'):
            group=[r for r in rows if r['format']==fmt and r['cache']==condition]
            entry={'format':fmt,'cache':condition,'phases':{}}
            for phase in ('first','next','revisit'):
                samples=[r for r in group if r['phase']==phase]
                if not samples: raise ValueError(f'Missing observations: {fmt}/{condition}/{phase}')
                entry['phases'][phase]={'n':len(samples)}
                for metric in ('ms','workMs','frameWaitMs','transferBytes','heapUsedBytes','estimatedActivePixelBytes'):
                    values=[r[metric] for r in samples if isinstance(r.get(metric),(int,float))]
                    entry['phases'][phase][metric]=({'median':statistics.median(values),'min':min(values),'max':max(values)} if values else None)
            entry['visibilityStates']=sorted(set(str(r.get('visibilityStart')) for r in group)|set(str(r.get('visibilityEnd')) for r in group))
            entry['resources']=[x for r in group for x in r['resources']]
            entry['appCacheHits']=sum(r['appCacheHit'] for r in group)
            result['groups'].append(entry)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=analyze(json.loads(args.input.read_text('utf-8')))
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(text,encoding='utf-8')
    else:print(text,end='')
