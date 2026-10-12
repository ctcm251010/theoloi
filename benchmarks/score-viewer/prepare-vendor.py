"""Fetch openly licensed benchmark tooling/fonts only; never fetch score content."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent


def get(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def main():
    vendor = ROOT / 'vendor'; vendor.mkdir(exist_ok=True)
    if (vendor / 'provenance.json').exists():
        raise SystemExit('Vendor already pinned; refusing to replace')
    version = json.loads(get('https://registry.npmjs.org/pdfjs-dist/latest'))['version']
    urls = {
        'pdf.mjs': f'https://unpkg.com/pdfjs-dist@{version}/build/pdf.mjs',
        'pdf.worker.mjs': f'https://unpkg.com/pdfjs-dist@{version}/build/pdf.worker.mjs',
        'PDFJS-LICENSE': f'https://unpkg.com/pdfjs-dist@{version}/LICENSE',
        'NotoSans-Regular.ttf': 'https://raw.githubusercontent.com/notofonts/noto-fonts/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf',
        'NOTO-LICENSE': 'https://raw.githubusercontent.com/notofonts/noto-fonts/main/LICENSE',
    }
    records = []
    for name, url in urls.items():
        data = get(url); (vendor / name).write_bytes(data)
        records.append({'file': name, 'url': url, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        print(name, len(data))
    (vendor / 'provenance.json').write_text(json.dumps({'pdfjsVersion': version, 'assets': records}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
