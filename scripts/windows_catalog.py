"""Build a source-free client metadata projection. No media/state/network access."""
import math
import unicodedata


def project_catalog(catalog, manifest):
    tracks = []
    used = set()
    assets = manifest['assets']

    def add(logical_id, mode, section, number, title, category, asset_id):
        if asset_id in used:
            raise ValueError('Duplicate catalog asset identity')
        asset = assets.get(asset_id)
        if not isinstance(asset, dict) or asset.get('assetId') != asset_id:
            raise ValueError('Missing or invalid manifest asset identity')
        if asset.get('logicalId') != logical_id or asset.get('variant') != mode:
            raise ValueError('Manifest logical identity/variant mismatch')
        kind = 'meditation' if mode == 'silent' else 'song'
        if asset.get('kind') != kind:
            raise ValueError('Manifest kind mismatch')
        if mode != 'silent' and (asset.get('section'), asset.get('number')) != (section, number):
            raise ValueError('Manifest section/number mismatch')
        duration = asset.get('durationSeconds')
        if isinstance(duration, bool) or not isinstance(duration, (float, int)) or not math.isfinite(duration) or duration <= 0:
            raise ValueError('Invalid measured duration')
        if type(number) is not int or number <= 0 or not title or not category:
            raise ValueError('Invalid client metadata')
        used.add(asset_id)
        tracks.append(dict(id=asset_id, logicalId=logical_id, mode=mode, section=section,
                           number=number, title=title, category=category, durationSeconds=duration))

    for song in catalog['songs'].values():
        for mode in ('guide', 'instrumental'):
            add(song['id'], mode, song['section'], song['number'], song['title'], song['category'], song['variants'][mode]['assetId'])
    for item in catalog['meditations'].values():
        add(item['id'], 'silent', None, item['sourceDisplayNumber'], item['title'], item['category'], item['asset']['assetId'])
    if used != set(assets):
        raise ValueError('Unexpected assets in manifest')
    if [sum(t['mode'] == mode for t in tracks) for mode in ('guide', 'instrumental', 'silent')] != [485,485,13]:
        raise ValueError('Reviewed catalog counts differ')
    tracks.sort(key=lambda t: (('guide','instrumental','silent').index(t['mode']), t['section'] == 'appendix', t['number'], t['id']))
    return {'schemaVersion': 1, 'revision': manifest['revision'], 'tracks': tracks}


def project_quick_play(catalog, manifest, snapshot):
    """User-requested silent library shortcut, distinct from WATV's pinned rule.

    Explicit source audio IDs determine sequence; never infer identity from index,
    title or hymn number. Prayer imports still require a separate reviewed source.
    """
    client = project_catalog(catalog, manifest)
    silent = {t['id']: t for t in client['tracks'] if t['mode'] == 'silent'}
    rows = snapshot.get('lists', {}).get('silentSongList')
    if not isinstance(rows, list) or len(rows) != len(silent):
        raise ValueError('Incomplete silent source sequence')
    ids = []
    def normalized(value):
        return ' '.join(unicodedata.normalize('NFC', str(value)).split()).casefold()
    for row in rows:
        audio_id = row.get('newsongAudioId') if isinstance(row, dict) else None
        asset_id = f'watv:vi:silent:{audio_id}'
        track = silent.get(asset_id)
        if not track or asset_id in ids or row.get('newsongDispNo') != track['number'] or normalized(row.get('title')) != normalized(track['title']):
            raise ValueError('Silent source identity mismatch')
        source = catalog['meditations'][track['logicalId']]['asset']['source']
        if str(audio_id) != source['audioId'] or row.get('songUrl') != source['hlsUrl']:
            raise ValueError('Silent source URL/ID mismatch')
        ids.append(asset_id)
    if set(ids) != set(silent):
        raise ValueError('Silent source membership mismatch')
    return [
        {'id':'quick:meditation', 'title':'Nhạc ngẫm nghĩ', 'behavior':'silent-library',
         'available':True, 'reason':'Phát từ bài đầu của danh sách Ngẫm nghĩ.',
         'firstAssetId':ids[0], 'assetIds':ids, 'sourceStatus':'verified', 'rightsStatus':'approved',
         'provenance':{'sequence':'source/snapshots/watv-vi-2026-10-10.audio.json#lists.silentSongList',
                       'identity':'newsongAudioId + manifest assetId',
                       'rights':'User confirmed rights to existing 983 assets; requested silent-library shortcut.'}},
        {'id':'quick:our-wish-meditation', 'title':'Cầu nguyện chúng con mong muốn',
         'behavior':'asset-playlist', 'available':False,
         'reason':'Chưa có audio được nhập và xác minh trong thư viện.', 'assetIds':[],
         'sourceStatus':'observed-not-imported', 'rightsStatus':'unknown'},
        {'id':'quick:unison-prayer', 'title':'Nhạc không lời cầu nguyện thống thanh',
         'behavior':'asset-playlist', 'available':False,
         'reason':'Có thể bổ sung khi có nguồn audio và quyền sử dụng phù hợp.', 'assetIds':[],
         'sourceStatus':'not-imported', 'rightsStatus':'unknown'}
    ]
