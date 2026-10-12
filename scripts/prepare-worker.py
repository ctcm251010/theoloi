"""Export the reviewed asset allowlist for Worker; no media/secret/network access."""
import hashlib
import json
from pathlib import Path
from windows_catalog import project_catalog

ROOT = Path(__file__).resolve().parents[1]


def main():
    inputs = [('catalog/catalog.vi.json','e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4'),
              ('delivery/manifest.vi.json','b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c')]
    values = []
    for name, expected in inputs:
        raw = (ROOT / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Unreviewed catalog/manifest baseline')
        values.append(json.loads(raw))
    catalog, manifest = values
    client = project_catalog(catalog, manifest)
    allowed = {aid:{key:entry[key] for key in ('assetId','objectKey','bytes','sha256')}
               for aid,entry in manifest['assets'].items()}
    folder = ROOT / 'workers/media-api/generated'
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in [('catalog.json', client), ('assets.json', allowed)]:
        (folder / name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    print('PASS: exported 983 exact IDs/object keys; source catalog and manifest unchanged.')


if __name__ == '__main__': main()
