"""Offline sheet metadata, conservative matching and validation. No HTTP or media IO."""
from collections import Counter, defaultdict
import copy
import hashlib
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker
from catalog_lib import ROOT, CATALOG as AUDIO_CATALOG, json_text, load_json

SNAPSHOT = ROOT / 'source/snapshots/bookvn-vi-2026-10-12.sheets.json'
CATALOG = ROOT / 'catalog/sheet-sources.vi.json'
SCHEMA = ROOT / 'schemas/sheet-catalog.schema.json'
PREFIX = re.compile(r'^\s*([1-9][0-9]*)\.\s*')


def digest_json(value):
    return hashlib.sha256(json_text(value).encode('utf-8')).hexdigest()


def normalize_title(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Title must be nonempty text')
    return ' '.join(unicodedata.normalize('NFC', value).split()).casefold()


def source_identity(url):
    if not isinstance(url, str):
        raise ValueError('Source page URL must be text')
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.netloc != 'bookvn.net' or parts.query or parts.fragment:
        raise ValueError('Expected canonical BookVN HTTPS page URL without credentials/query')
    for group, pattern in [('main',r'/newsong/newsong([1-9][0-9]*)/'),
                           ('appx',r'/newsong/newsong-appx([0-9]{3,})/'),
                           ('numbered-appendix',r'/newsong/newsong-appendix([1-9][0-9]*)/')]:
        match = re.fullmatch(pattern,parts.path)
        if match and int(match[1]) > 0:
            return group,int(match[1])
    raise ValueError('Unrecognized BookVN source namespace')


def match_audio(group, number, title, audio):
    section = 'main' if group == 'main' else 'appendix'
    rows = [s for s in audio['songs'].values() if s['section'] == section]
    exact = [s for s in rows if normalize_title(s['title']) == normalize_title(title)]
    issues = []
    links = []
    same_number = [s for s in rows if s['number'] == number] if group == 'main' else []
    preferred = [s for s in exact if s['number'] == number] if group == 'main' else exact
    if group == 'main' and same_number and not preferred:
        issues.append('number-title-disagree')
    candidates = preferred or exact or same_number
    for row in sorted(candidates,key=lambda s:s['id']):
        title_equal = row in exact
        evidence = []
        if title_equal: evidence.append('normalized-title-equal')
        if group == 'main':
            evidence.append('number-equal' if row['number'] == number else 'number-different')
            confidence = .98 if title_equal and row['number'] == number else (.80 if title_equal else .30)
            if row['number'] != number and 'number-title-disagree' not in issues:
                issues.append('number-title-disagree')
        else:
            confidence = .90
            evidence.append('appendix-number-not-a-join-key')
        links.append({'songId':row['id'],'confidence':confidence,'evidence':evidence,
                      'verificationStatus':'needs-review','verificationEvidence':None})
    status = 'unmatched' if not links else ('conflict' if issues else ('ambiguous' if len(links)>1 else 'candidate'))
    if len(links)>1: issues.append('multiple-audio-candidates')
    return status,links,issues


def build_sheet_catalog(snapshot,audio):
    if snapshot.get('schemaVersion') != 1 or snapshot.get('provider') != 'bookvn' or snapshot.get('locale') != 'vi':
        raise ValueError('Unsupported sheet snapshot')
    if snapshot.get('scope') != 'observed-category-pages-only' or not isinstance(snapshot.get('records'),list):
        raise ValueError('Snapshot must describe observed category records')
    notice = snapshot.get('notice',{})
    if not isinstance(notice.get('text'),str) or not notice['text'].strip() or notice.get('evidenceUrl') != 'https://bookvn.net/category/newsong/':
        raise ValueError('Missing observed usage notice')
    ids,urls,keys = set(),set(),set()
    sheets = {}
    for row in snapshot['records']:
        if not isinstance(row,dict) or set(row) != {'postId','pageUrl','rawTitle'}:
            raise ValueError('Malformed snapshot record')
        post_id = row['postId']
        if type(post_id) is not int or post_id < 1:
            raise ValueError('postId must be a positive integer')
        raw_title = row['rawTitle']
        normalize_title(raw_title)
        group,number = source_identity(row['pageUrl'])
        prefix = PREFIX.match(raw_title)
        display_number = int(prefix[1]) if prefix else None
        if group != 'appx' and display_number != number:
            raise ValueError('Display number disagrees with source slug')
        if post_id in ids or row['pageUrl'] in urls or (group,number) in keys:
            raise ValueError('Duplicate source ID, URL or namespace/number')
        ids.add(post_id); urls.add(row['pageUrl']); keys.add((group,number))
        title = raw_title[prefix.end():] if prefix else raw_title
        title = ' '.join(unicodedata.normalize('NFC',title).split())
        status,links,issues = match_audio(group,number,title,audio)
        sheet_id = f'bookvn:vi:post:{post_id}'
        sheets[sheet_id] = {'id':sheet_id,'provider':'bookvn','sourcePostId':post_id,'sourcePageUrl':row['pageUrl'],
                            'rawTitle':raw_title,'title':title,'normalizedTitle':normalize_title(title),
                            'sourceGroup':group,'sourceNumber':number,'displayNumber':display_number,'locale':'vi','edition':None,
                            'usageRights':{'status':'restricted','evidence':notice['text'],'evidenceUrl':notice['evidenceUrl'],
                                           'permissions':{'store':False,'convert':False,'serve':False,'upload':False}},
                            'observedContent':{'inspectionStatus':'not-observed','format':'unknown','renderer':None,
                                               'pages':[],'pdfStatus':'not-observed'},
                            'originalPdf':None,'audioLinks':links,'matchingStatus':status,'reviewIssues':issues}
    observed_ids = set()
    for obs in snapshot.get('observations',[]):
        sid = f"bookvn:vi:post:{obs.get('postId')}"
        if sid not in sheets or sid in observed_ids or sheets[sid]['sourcePageUrl'] != obs.get('pageUrl'):
            raise ValueError('Observation must reference one existing post and page')
        observed_ids.add(sid)
        if obs.get('format') != 'image-pages' or obs.get('renderer') != 'css-background-image' or obs.get('pdfStatus') != 'not-found-in-observed-dom':
            raise ValueError('Unsupported observation')
        if not obs.get('pages'): raise ValueError('Observed image pages cannot be empty')
        for n,page in enumerate(obs['pages'],1):
            if set(page) != {'pageNumber','sourceUrl','mediaType'} or type(page['pageNumber']) is not int or page['pageNumber'] != n:
                raise ValueError('Observed pages must be ordered and contiguous')
            url = urlsplit(page['sourceUrl'])
            if (url.scheme,url.netloc) != ('https','bookvn.net') or url.query or url.fragment or not re.fullmatch(r'/wp-content/uploads/[0-9]{4}/[0-9]{2}/[^/]+\.png',url.path) or page['mediaType'] != 'image/png':
                raise ValueError('Invalid observed image URL/type')
        sheets[sid]['observedContent'] = {'inspectionStatus':'observed','format':obs['format'],'renderer':obs['renderer'],
                                         'pages':copy.deepcopy(obs['pages']),'pdfStatus':obs['pdfStatus']}
    return {'schemaVersion':1,'collectionId':'watv-vi-newsong-sheets','locale':'vi',
            'sourceSnapshotSha256':digest_json(snapshot),'audioCatalogSha256':digest_json(audio),
            'observedDate':snapshot['observedDate'],'surveyScope':snapshot['scope'],
            'sheets':dict(sorted(sheets.items()))}


def validate_sheet_catalog(catalog,audio,schema,snapshot=None):
    errors = [f"schema {'.'.join(map(str,e.absolute_path))}: {e.message}" for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(catalog)]
    if errors: return errors
    audio_ids = {s['id'] for s in audio['songs'].values()}
    if catalog['audioCatalogSha256'] != digest_json(audio): errors.append('Audio catalog hash differs')
    seen = set()
    for sid,row in catalog['sheets'].items():
        if sid != row['id'] or not sid.startswith(row['provider']+':'+row['locale']+':'):
            errors.append(f'{sid}: source identity differs')
        if row['provider']=='bookvn':
            try:
                group,number=source_identity(row['sourcePageUrl'])
                if (group,number) != (row['sourceGroup'],row['sourceNumber']) or sid != f"bookvn:vi:post:{row['sourcePostId']}":
                    errors.append(f'{sid}: namespace/post/number differs')
            except ValueError as exc: errors.append(f'{sid}: {exc}')
        if row['normalizedTitle'] != normalize_title(row['title']): errors.append(f'{sid}: normalized title differs')
        identity=(row['provider'],row['locale'],row['sourceGroup'],row['sourceNumber'])
        if identity in seen: errors.append(f'{sid}: duplicate semantic source key')
        seen.add(identity)
        rights=row['usageRights']
        if rights['status'] != 'confirmed' and any(rights['permissions'].values()): errors.append(f'{sid}: unconfirmed permission')
        if rights['status']=='confirmed' and not (rights['evidence'] or '').strip(): errors.append(f'{sid}: confirmed rights need evidence')
        candidates=[]
        for link in row['audioLinks']:
            if link['songId'] not in audio_ids or link['songId'] in candidates: errors.append(f'{sid}: dangling/duplicate audio link')
            if link['verificationStatus']=='verified' and not (link['verificationEvidence'] or '').strip(): errors.append(f'{sid}: verified link needs evidence')
            candidates.append(link['songId'])
        if row['matchingStatus']=='unmatched' and candidates: errors.append(f'{sid}: unmatched row has candidates')
        if row['matchingStatus']=='candidate' and len(candidates)!=1: errors.append(f'{sid}: candidate needs one audio link')
        content=row['observedContent']
        if content['inspectionStatus']=='not-observed' and (content['pages'] or content['format']!='unknown' or content['pdfStatus']!='not-observed'):
            errors.append(f'{sid}: unobserved content claims inspected metadata')
        if [p['pageNumber'] for p in content['pages']] != list(range(1,len(content['pages'])+1)):
            errors.append(f'{sid}: unordered pages')
    if snapshot is not None:
        try:
            if catalog != build_sheet_catalog(snapshot,audio): errors.append('Catalog differs from retained snapshot and matching rules')
        except (ValueError,KeyError,TypeError) as exc: errors.append(f'Invalid source snapshot: {exc}')
    return errors


def mapping_report(catalog,audio):
    rows=list(catalog['sheets'].values()); by_title=defaultdict(list)
    for r in rows: by_title[r['normalizedTitle']].append(r['id'])
    numbers={r['sourceNumber'] for r in rows if r['sourceGroup']=='main'}
    linked={l['songId'] for r in rows for l in r['audioLinks']}
    counts={'sheets':len(rows),'byGroup':dict(sorted(Counter(r['sourceGroup'] for r in rows).items())),
            'byMatchingStatus':dict(sorted(Counter(r['matchingStatus'] for r in rows).items())),
            'links':sum(len(r['audioLinks']) for r in rows),'verifiedLinks':sum(l['verificationStatus']=='verified' for r in rows for l in r['audioLinks']),
            'observedSheets':sum(r['observedContent']['inspectionStatus']=='observed' for r in rows)}
    return {'schemaVersion':1,'catalogSha256':digest_json(catalog),'audioCatalogSha256':catalog['audioCatalogSha256'],
            'scope':catalog['surveyScope'],'counts':counts,
            'mainNumberGaps':[n for n in range(1,max(numbers,default=0)+1) if n not in numbers],
            'duplicateTitles':[{'normalizedTitle':title,'sheetIds':sorted(ids)} for title,ids in sorted(by_title.items()) if len(ids)>1],
            'unmatchedSheetIds':[r['id'] for r in rows if r['matchingStatus']=='unmatched'],
            'conflictSheetIds':[r['id'] for r in rows if r['matchingStatus']=='conflict'],
            'ambiguousSheetIds':[r['id'] for r in rows if r['matchingStatus']=='ambiguous'],
            'audioWithoutCandidate':[s['id'] for s in audio['songs'].values() if s['id'] not in linked],
            'mappings':[{'sheetId':r['id'],'sourcePageUrl':r['sourcePageUrl'],'sourceGroup':r['sourceGroup'],
                         'sourceNumber':r['sourceNumber'],'title':r['title'],'status':r['matchingStatus'],
                         'audioLinks':r['audioLinks'],'reviewIssues':r['reviewIssues']} for r in rows]}


def mapping_markdown(report):
    c=report['counts']
    lines=['# AudioTP — Đối chiếu bản nhạc với audio','',
           'Báo cáo sinh offline từ snapshot metadata đã quan sát. Không tải tài liệu; mọi link tự động đều cần review.',
           '',f"- Tổng nguồn: {c['sheets']}; nhóm: {c['byGroup']}.",
           f"- Kết quả: {c['byMatchingStatus']}; {c['links']} liên kết ứng viên; {c['verifiedLinks']} đã xác minh.",
           f"- Quan sát nội dung: {c['observedSheets']}; không ngoại suy số PDF/ảnh.",
           f"- Số bài chính vắng mặt: {report['mainNumberGaps']}.",
           f"- Nhóm title trùng: {len(report['duplicateTitles'])}; audio chưa có ứng viên: {len(report['audioWithoutCandidate'])}.",
           '', 'Confidence là điểm quy tắc, không phải xác suất hay bằng chứng cùng ấn bản.',
           '', '## Nguồn trùng title','']
    for d in report['duplicateTitles']: lines.append(f"- {d['normalizedTitle']}: {', '.join(d['sheetIds'])}")
    lines += ['', '## Toàn bộ mapping và mục cần review','',
              '| Nguồn | Nhóm:số | Title | Audio ứng viên (confidence) | Trạng thái |',
              '|---|---|---|---|---|']
    for row in report['mappings']:
        links=', '.join(f"{l['songId']} ({l['confidence']:.2f})" for l in row['audioLinks']) or '—'
        title=row['title'].replace('|','\\|').replace('\n',' ')
        lines.append(f"| [{row['sheetId']}]({row['sourcePageUrl']}) | {row['sourceGroup']}:{row['sourceNumber']} | {title} | {links} | {row['status']} / cần review |")
    lines += ['', '## Giới hạn','',
              '- Không tự ghép phụ lục theo số; trùng title không gộp nguồn.',
              '- Unmatched không có nghĩa thiếu file; chưa xác minh nội dung/ấn bản.',
              '- Rights BookVN restricted. Catalog và báo cáo không cấp quyền tải/chuyển đổi/phân phát.',
              '- Xem delivery/sheet-mapping.vi.json để lấy evidence và danh sách lỗi có cấu trúc.','']
    return '\n'.join(lines)
