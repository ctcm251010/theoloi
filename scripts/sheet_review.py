"""Human musical identity decisions; no rights mutations, HTTP or media access."""
import copy
from datetime import datetime, timezone

from jsonschema import Draft202012Validator, FormatChecker
from catalog_lib import ROOT, load_json
from sheet_catalog import SCHEMA, digest_json, validate_sheet_catalog, mapping_report

REVIEW_SCHEMA=ROOT/'schemas/sheet-review.schema.json'
ZERO='0'*64


def _errors(value,kind):
    schema=load_json(REVIEW_SCHEMA)
    validator=Draft202012Validator({'$ref':'#/$defs/'+kind,'$defs':schema['$defs']},format_checker=FormatChecker())
    return [f'{list(e.absolute_path)}: {e.message}' for e in validator.iter_errors(value)]


def _revision(store):return digest_json({k:v for k,v in store.items() if k!='revision'})


def new_store():
    result={'schemaVersion':1,'reviewType':'musical-identity-only','events':[]}
    result['revision']=_revision(result);return result


def validate_store(store):
    errors=_errors(store,'store')
    if errors:return errors
    if store['revision']!=_revision(store):errors.append('Review store revision differs')
    previous=ZERO;unrejected=set()
    for n,event in enumerate(store['events'],1):
        if event['sequence']!=n or event['previousHash']!=previous:errors.append('Review event sequence/chain differs')
        if event['eventHash']!=digest_json({k:v for k,v in event.items() if k!='eventHash'}):errors.append('Review event hash differs')
        if event['songId'] is None and (event['decision']!='defer' or event['audioIdentitySha256'] is not None):errors.append('Null audio only valid for defer')
        if event['songId'] is not None and event['audioIdentitySha256'] is None:errors.append('Audio identity missing')
        pair=(event['sheetId'],event['songId'])
        if event['decision']=='approve':
            if any(s==pair[0] and a!=pair[1] for s,a in unrejected):errors.append('Song switch lacks explicit prior rejection')
            unrejected.add(pair)
        elif event['decision']=='reject':unrejected.discard(pair)
        previous=event['eventHash']
    return errors


def _context(catalog,audio):
    errors=validate_sheet_catalog(catalog,audio,load_json(SCHEMA))
    if errors:raise ValueError('; '.join(errors))
    songs={s['id']:s for s in audio['songs'].values()}
    if len(songs)!=len(audio['songs']):raise ValueError('Duplicate audio song ID')
    return songs


def source_identity_hash(row):
    return digest_json({k:v for k,v in row.items() if k not in ('usageRights','audioLinks','matchingStatus','reviewIssues')})


def latest_events(store):
    errors=validate_store(store)
    if errors:raise ValueError('; '.join(errors))
    latest={}
    for event in store['events']:latest[(event['sheetId'],event['songId'])]=event
    return latest


def apply_batch(store,batch,catalog,audio):
    songs=_context(catalog,audio);latest=latest_events(store)
    errors=_errors(batch,'batch')
    if errors:raise ValueError('; '.join(errors))
    if (batch['baseRevision']!=store['revision'] or batch['catalogSha256']!=digest_json(catalog)
        or batch['audioCatalogSha256']!=digest_json(audio)):
        raise ValueError('Stale batch revision/catalog pins; regenerate and review again')
    seen=set();result=copy.deepcopy(store);unrejected=set()
    for event in store['events']:
        pair=(event['sheetId'],event['songId'])
        if event['decision']=='approve':unrejected.add(pair)
        elif event['decision']=='reject':unrejected.discard(pair)
    for decision in batch['decisions']:
        sid,song=decision['sheetId'],decision['songId'];pair=(sid,song)
        if sid not in catalog['sheets'] or (song is not None and song not in songs):raise ValueError('Unknown source/audio song ID')
        if song is None and decision['decision']!='defer':raise ValueError('Only defer may omit an audio song ID')
        if pair in seen:raise ValueError('Duplicate source/audio decision in batch')
        seen.add(pair)
        if decision['decision']=='approve':
            if any(s==sid and a!=song for s,a in unrejected):
                raise ValueError('Source previously approved for another song; explicitly reject that pair first, even after defer')
            unrejected.add(pair)
        elif decision['decision']=='reject':unrejected.discard(pair)
        event=copy.deepcopy(decision)
        event.update(sequence=len(result['events'])+1,createdAt=datetime.now(timezone.utc).isoformat(),
                     catalogSha256=digest_json(catalog),audioCatalogSha256=digest_json(audio),
                     sourceIdentitySha256=source_identity_hash(catalog['sheets'][sid]),
                     audioIdentitySha256=digest_json(songs[song]) if song is not None else None,
                     previousHash=result['events'][-1]['eventHash'] if result['events'] else ZERO)
        event['eventHash']=digest_json(event);result['events'].append(event);latest[pair]=event
    result['revision']=_revision(result)
    return result


def _stale(event,catalog,songs):
    sid,song=event['sheetId'],event['songId']
    return (sid not in catalog['sheets'] or event['sourceIdentitySha256']!=source_identity_hash(catalog['sheets'][sid])
            or (song is not None and (song not in songs or event['audioIdentitySha256']!=digest_json(songs[song]))))


def export_verified(store,catalog,audio):
    songs=_context(catalog,audio);latest=latest_events(store);links=[];approved=set()
    for (sid,song),event in sorted(latest.items(),key=lambda x:(x[0][0],x[0][1] or '')):
        if event['decision']!='approve':continue
        if _stale(event,catalog,songs):raise ValueError(f'Stale approved identity: {sid}; re-review before export')
        if sid in approved:raise ValueError('Multiple active approved songs for one source')
        approved.add(sid)
        links.append({'sheetId':sid,'songId':song,'status':'verified','decisionEventHash':event['eventHash'],
                      'evidence':event['evidence'],'reviewer':event['reviewer'],'provenance':event['provenance'],
                      'reviewedAt':event['createdAt'],'usageRights':copy.deepcopy(catalog['sheets'][sid]['usageRights'])})
    result={'schemaVersion':1,'kind':'verified-identity-mapping','catalogSha256':digest_json(catalog),
            'audioCatalogSha256':digest_json(audio),'reviewRevision':store['revision'],'links':links}
    errors=_errors(result,'export')
    if errors:raise ValueError('; '.join(errors))
    return result


def review_queue(store,catalog,audio):
    songs=_context(catalog,audio);latest=latest_events(store)
    duplicates={sid for group in mapping_report(catalog,audio)['duplicateTitles'] for sid in group['sheetIds']}
    rows=[]
    for sid,row in catalog['sheets'].items():
        priority=('main-464' if row['sourceGroup']=='main' and row['sourceNumber']==464 else
                  'duplicate-title' if sid in duplicates else row['matchingStatus'])
        decisions=[{'songId':song,'decision':e['decision'],'stale':_stale(e,catalog,songs),'eventHash':e['eventHash']} for (s,song),e in latest.items() if s==sid]
        rows.append({'sheetId':sid,'sourceGroup':row['sourceGroup'],'sourceNumber':row['sourceNumber'],
                     'title':row['title'],'sourcePageUrl':row['sourcePageUrl'],'edition':row['edition'],
                     'matchingStatus':row['matchingStatus'],'priority':priority,'audioLinks':row['audioLinks'],
                     'reviewIssues':row['reviewIssues'],'usageRights':row['usageRights'],'decisions':decisions})
    order={'main-464':0,'duplicate-title':1,'conflict':2,'ambiguous':3,'unmatched':4,'candidate':5}
    rows.sort(key=lambda r:(order.get(r['priority'],6),r['sourceGroup'],r['sourceNumber'],r['sheetId']))
    return {'schemaVersion':1,'catalogSha256':digest_json(catalog),'audioCatalogSha256':digest_json(audio),
            'baseRevision':store['revision'],'rows':rows,'songs':[{'id':s['id'],'title':s['title'],'section':s['section'],'number':s['number']} for s in songs.values()]}
