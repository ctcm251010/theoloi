"""Generate Windows client metadata; never fetch, synthesize or change audio."""
import argparse
import hashlib
import json
from pathlib import Path

from catalog_lib import ROOT, load_json, json_text
from windows_catalog import project_catalog, project_quick_play


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    catalog_path = ROOT / 'catalog/catalog.vi.json'
    manifest_path = ROOT / 'delivery/manifest.vi.json'
    if hashlib.sha256(catalog_path.read_bytes()).hexdigest() != 'e449b3a25ed49c6879bf06c72219863857632491f4a2ca424c2bc692e45ca8d4':
        raise ValueError('Reviewed catalog baseline differs')
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != 'b54965fd3c612439ba2ef503bd502abbab11fadcd6b1e16857c2ef0403051a4c':
        raise ValueError('Reviewed manifest baseline differs')
    catalog, manifest = load_json(catalog_path), load_json(manifest_path)
    data = project_catalog(catalog, manifest)
    snapshot_path = ROOT / 'source/snapshots/watv-vi-2026-10-10.audio.json'
    if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != 'febb88a7aa08ada4bac3abb78176112ce3a35c42673f100771dfb15ecfe8ac97':
        raise ValueError('Reviewed source snapshot baseline differs')
    quick = project_quick_play(catalog, manifest, load_json(snapshot_path))
    web = ROOT / 'apps/windows/web'
    web.mkdir(parents=True, exist_ok=True)
    (web / 'catalog.client.json').write_text(json_text(data), encoding='utf-8')
    (web / 'quick-play.json').write_text(json_text(quick), encoding='utf-8')
    print('PASS: projected 485 guide / 485 instrumental / 13 silent; silent-library shortcut + 2 unavailable prayer items. No audio file/network/state changes.')


if __name__ == '__main__': main()
