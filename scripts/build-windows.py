"""Read-only Windows preflight by default; --build produces an API-configured release."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'apps/windows'


def api_origin(value):
    from urllib.parse import urlsplit
    url = urlsplit(value)
    if any(ch.isspace() or ord(ch)<32 for ch in value) or url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('','/') or (url.port is not None and not 1<=url.port<=65535):
        raise ValueError('A deployed HTTPS API origin is required, without credentials/path/query')
    host=url.hostname.encode('idna').decode('ascii').lower()
    if not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in host.split('.')):
        raise ValueError('Invalid API hostname')
    return 'https://'+host+((':'+str(url.port)) if url.port is not None else '')


def test_origin(value):
    from urllib.parse import urlsplit
    url=urlsplit(value)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or not url.port or not 1<=url.port<=65535 or url.username or url.password or url.query or url.fragment or url.path not in ('','/') or any(ch.isspace() for ch in value):
        raise ValueError('Test fixtures require an explicit http://127.0.0.1:PORT origin')
    return 'http://127.0.0.1:'+str(url.port)


def preflight():
    tools = {name:shutil.which(name) for name in ('node','cargo','rustc','rustup')}
    for name in ('cargo','rustc','rustup'):
        candidate = Path.home() / '.cargo/bin' / (name + '.exe')
        if not tools[name] and candidate.is_file(): tools[name] = str(candidate)
    versions = {}
    for name, executable in tools.items():
        if executable:
            result = subprocess.run([executable,'--version'],capture_output=True,text=True,timeout=15)
            if result.returncode: tools[name] = None
            else: versions[name] = result.stdout.strip()
    base = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)'))
    locator = base / 'Microsoft Visual Studio/Installer/vswhere.exe'
    msvc = False
    if locator.is_file():
        result = subprocess.run([str(locator),'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],capture_output=True,text=True,timeout=15)
        if result.returncode == 0 and result.stdout.strip():
            msvc = any(Path(result.stdout.strip()).glob('VC/Tools/MSVC/*/bin/Hostx64/x64/cl.exe'))
    sdk = any((base / 'Windows Kits/10/Include').glob('*/ucrt/stdio.h'))
    webview = any((base / 'Microsoft/EdgeWebView/Application').glob('*/msedgewebview2.exe'))
    npm_cli = Path(tools['node']).parent / 'node_modules/npm/bin/npm-cli.js' if tools['node'] else None
    tauri = APP / 'node_modules/@tauri-apps/cli/tauri.js'
    if tools['node']:
        for name, script in [('npm',npm_cli),('tauri',tauri)]:
            if script and script.is_file():
                result=subprocess.run([tools['node'],str(script),'--version'],capture_output=True,text=True,timeout=15)
                if result.returncode==0: versions[name]=result.stdout.strip()
    missing = [name for name in ('node','cargo','rustc') if not tools[name]]
    if not npm_cli or not npm_cli.is_file(): missing.append('npm CLI')
    if not msvc: missing.append('MSVC x64 C++ Build Tools')
    if not sdk: missing.append('Windows SDK/UCRT')
    if not webview: missing.append('WebView2 runtime')
    if os.name != 'nt': missing.append('Windows build host')
    return dict(status='BLOCKED' if missing else 'READY',versions=versions,missing=missing,msvc=msvc,windowsSdk=sdk,webview2=webview,tauriInstalled=tauri.is_file()),tools,npm_cli


@contextmanager
def exclusive_build():
    if not APP.resolve().is_relative_to(ROOT.resolve()): raise ValueError('Build directory outside workspace')
    lock=APP/'build.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        os.write(fd,str(os.getpid()).encode())
        yield
    finally:
        os.close(fd)
        lock.unlink()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group()
    action.add_argument('--check',action='store_true',help='read-only preflight (default)')
    action.add_argument('--prepare',action='store_true',help='stage reviewed frontend/config only; no compiler/network')
    action.add_argument('--build',action='store_true',help='install locked npm dependencies and compile native app')
    parser.add_argument('--api-base',help='actual HTTPS API origin, required for release')
    parser.add_argument('--debug',action='store_true',help='native debug; without API, catalog-only and no network playback')
    parser.add_argument('--installer',action='store_true',help='create NSIS installer with release build')
    parser.add_argument('--test-fixtures',action='store_true',help='isolated TEST app with self-authored catalog and loopback mock; never distribute as production')
    args=parser.parse_args(argv)
    if args.debug and args.installer: parser.error('Debug builds cannot produce a distribution installer')
    if (args.debug or args.installer or args.api_base or args.test_fixtures) and not (args.build or args.prepare): parser.error('Build options require --build or --prepare')
    origin=None
    if args.build or args.prepare:
        try: origin=(test_origin if args.test_fixtures else api_origin)(args.api_base) if args.api_base else None
        except ValueError as error: parser.error(str(error))
        if not origin and not args.debug: parser.error('A deployed HTTPS API origin is required for release')
        if args.test_fixtures and not origin: parser.error('Test fixtures require a loopback mock API origin')
    if args.prepare:
        with exclusive_build(): stage,override,version=prepare_stage(origin,debug=args.debug,test_fixtures=args.test_fixtures)
        print(json.dumps(dict(status='PREPARED_NOT_COMPILED',stage=str(stage),override=str(override),version=version,debug=args.debug)))
        return 0
    report,tools,npm_cli=preflight()
    print(json.dumps(report,indent=2),flush=True)
    if not args.build: return 2 if report['missing'] else 0
    if report['missing']: return 2
    with exclusive_build():
        return build_release(origin,args.installer,tools,npm_cli,debug=args.debug,test_fixtures=args.test_fixtures)


def prepare_stage(origin,debug=False,test_fixtures=False):
    if origin is not None: origin=(test_origin if test_fixtures else api_origin)(origin)
    if test_fixtures and not origin: raise ValueError('Test fixture origin required')
    if not origin and not debug: raise ValueError('Release requires an HTTPS origin')
    config_path=APP / 'src-tauri/tauri.conf.json'
    original=config_path.read_bytes()
    config=json.loads(original)
    version=config.get('version')
    if not isinstance(version,str) or not re.fullmatch(r'\d+\.\d+\.\d+',version): raise ValueError('Invalid application version')
    web=(APP/'web').resolve()
    files=['index.html','styles.css','app.mjs','catalog.mjs','player.mjs','storage.mjs','ui-core.mjs','api-client.mjs','favicon.svg']
    if not test_fixtures: files+=['catalog.client.json','quick-play.json']
    for name in files:
        source=APP/'web'/name
        if source.is_symlink() or not source.resolve().is_relative_to(web): raise ValueError('Frontend source symlink/outside web directory')
        if not source.is_file(): raise ValueError('Missing frontend input: '+name+'; run prepare-windows.py with authorized inputs')
    fixture=json.loads((APP/'test-fixtures.json').read_text(encoding='utf-8')) if test_fixtures else None
    catalog=fixture['catalog'] if fixture else json.loads((web/'catalog.client.json').read_text(encoding='utf-8-sig'))
    if test_fixtures and any(not row['id'].startswith('test:') or not row['title'].startswith('TEST') for row in catalog['tracks']): raise ValueError('Unlabelled test fixture')
    fields={'id','logicalId','mode','section','number','title','category','durationSeconds'}
    if not isinstance(catalog,dict) or set(catalog)!={'schemaVersion','revision','tracks'} or catalog['schemaVersion']!=1 or not isinstance(catalog['revision'],str) or not catalog['revision'] or not isinstance(catalog['tracks'],list) or not catalog['tracks']: raise ValueError('Invalid public catalog')
    ids=set()
    for row in catalog['tracks']:
        if not isinstance(row,dict) or set(row)!=fields or not all(isinstance(row[k],str) and row[k].strip() for k in ('id','logicalId','title','category')) or row['id'] in ids or row['mode'] not in ('guide','instrumental','silent') or type(row['number']) is not int or row['number']<=0 or type(row['durationSeconds']) not in (int,float) or not math.isfinite(row['durationSeconds']) or row['durationSeconds']<=0 or (row['section'] is not None if row['mode']=='silent' else row['section'] not in ('main','appendix')): raise ValueError('Invalid public catalog track')
        ids.add(row['id'])
    quick=fixture['quick'] if fixture else json.loads((web/'quick-play.json').read_text(encoding='utf-8-sig'))
    if not isinstance(quick,list) or any(not isinstance(card,dict) for card in quick): raise ValueError('Invalid quick metadata')
    allowed={'id','title','behavior','available','reason','assetIds','firstAssetId','sourceStatus','rightsStatus'}
    quick=[{key:value for key,value in card.items() if key in allowed} for card in quick]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backups=APP/'build-backups';backups.mkdir(exist_ok=True)
    (backups/(stamp+'.tauri.json')).write_bytes(original)
    stage=APP / 'web-release' / stamp
    stage.mkdir(parents=True,exist_ok=False)
    for name in files: shutil.copyfile(APP / 'web' / name, stage / name)
    (stage/'catalog.client.json').write_text(json.dumps(catalog,ensure_ascii=False),encoding='utf-8')
    (stage/'quick-play.json').write_text(json.dumps(quick,ensure_ascii=False),encoding='utf-8')
    (stage/'connection.json').write_text(json.dumps(dict(mode='test-fixtures' if test_fixtures else 'remote' if origin else 'catalog-only',apiBase=origin or '',version=version,buildNumber=stamp)),encoding='utf-8')
    remote=(' '+origin) if origin else ''
    csp=f"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; media-src 'self'{remote}; connect-src 'self'{remote} ipc: http://ipc.localhost; object-src 'none'; frame-src 'none'; base-uri 'self'; form-action 'none'"
    override=backups/(stamp+'.override.json')
    settings={'build':{'frontendDist':'../web-release/'+stamp,'devUrl':None},'app':{'security':{'csp':csp,'devCsp':csp,'capabilities':[]}},'bundle':{'resources':[],'externalBin':[]}}
    if test_fixtures: settings.update(identifier='org.audiotp.acceptance',productName='AudioTP Test')
    override.write_text(json.dumps(settings,indent=2),encoding='utf-8')
    return stage,override,version


def inspect_artifact(artifact,started):
    data=artifact.read_bytes()
    for marker in (str(ROOT).encode(),str(ROOT).encode('utf-16-le'),b'R2_SECRET_ACCESS_KEY',b'AWS_SECRET_ACCESS_KEY',b'WATV_NEWSONG'):
        if marker in data: raise ValueError('Release contains a prohibited developer path/credential/source marker')
    pe=int.from_bytes(data[60:64],'little') if len(data)>=64 else len(data)
    if data[:2]!=b'MZ' or data[pe:pe+4]!=b'PE\0\0': raise ValueError('Expected a Windows PE executable')
    if artifact.stat().st_mtime<started: raise ValueError('Refusing stale artifact from an earlier build')
    return data


def build_release(origin,installer,tools,npm_cli,debug=False,test_fixtures=False):
    stage,override,version=prepare_stage(origin,debug=debug,test_fixtures=test_fixtures)
    stamp=stage.name
    child_env=os.environ.copy()
    child_env.pop('TAURI_CONFIG',None)
    child_env['PATH']=str(Path(tools['cargo']).parent)+os.pathsep+child_env.get('PATH','')
    child_env['CARGO_ENCODED_RUSTFLAGS']='--remap-path-prefix='+str(ROOT)+'=audiotp'
    child_env['CARGO_TARGET_DIR']=str(APP/'src-tauri/target')
    command=[tools['node'],str(npm_cli)]
    for arguments in (['ci','--ignore-scripts'],['test']):
        print('STEP:', ' '.join(arguments),flush=True)
        subprocess.run(command+arguments,cwd=APP,env=child_env,check=True)
    arguments=['build','--config',str(override),'--ci']+(['--debug','--no-bundle'] if debug else ['--bundles','nsis'] if installer else ['--no-bundle'])+['--','--locked']
    started=time.time()
    print('STEP: native '+('debug' if debug else 'release')+' build',flush=True)
    subprocess.run([tools['node'],str(APP/'node_modules/@tauri-apps/cli/tauri.js')]+arguments,cwd=APP,env=child_env,check=True)
    profile='debug' if debug else 'release'
    binary=APP/f'src-tauri/target/{profile}/AudioTP.exe'
    if not binary.is_file(): raise ValueError('Expected AudioTP.exe was not produced')
    inspected=[(binary.name,inspect_artifact(binary,started))]
    if debug:
        print('DEBUG BUILT, NOT A DISTRIBUTION:',binary,flush=True)
        return 0
    if installer:
        installers=list((APP/'src-tauri/target/release/bundle/nsis').glob('*.exe'))
        installers=[p for p in installers if p.stat().st_mtime>=started]
        if len(installers)!=1: raise ValueError('Expected exactly one fresh NSIS installer')
        inspected.extend((p.name,inspect_artifact(p,started)) for p in installers)
    guide=(ROOT/'docs/windows-user-guide.vi.md').read_bytes()
    if test_fixtures:
        guide=('''# AudioTP TEST — chỉ dùng nghiệm thu

Đây là bản kiểm thử với 4 track `test:*`, dùng 3 WAV tự tạo (12 giây). Không chứa nhạc WATV, không kết nối R2 và không dùng để phân phối thư viện thật. Identifier riêng: org.audiotp.acceptance.

Trên máy phát triển, chạy `node apps/windows/native-mock.mjs --port 8870`. Trong app mở Cài đặt → Kết nối thư viện, dùng mã công khai `public-self-authored-native-test-code`. Mã này chỉ dùng cho fixture, không phải credential production. Mock chỉ bind 127.0.0.1; phiên mất khi dừng mock.

Ứng dụng EXE cần WebView2, không cần Node/Python hay workspace để khởi động. Backend TEST riêng cần Node và repo để phục vụ fixture. Đây không phải nghiệm thu máy sạch hoặc API/R2 live. Đóng mock sau khi thử.

Hai mục cầu nguyện chưa khả dụng; Nghe nhanh dùng âm mẫu có nhãn TEST. Bản production chỉ build sau khi có endpoint HTTPS thật và hoàn tất phê duyệt/nghiệm thu Phase01. Không gửi installer TEST như bản thư viện thật.
''').encode('utf-8')
    release=ROOT/'release/windows'/(('TEST-' if test_fixtures else '')+version+'-'+stamp)
    release.mkdir(parents=True,exist_ok=False)
    sums=[]
    for name,data in inspected:
        (release/name).write_bytes(data)
        sums.append(hashlib.sha256(data).hexdigest()+'  '+name)
    (release/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
    (release/'HUONG-DAN.md').write_bytes(guide)
    (release/'build-report.json').write_text(json.dumps(dict(status='TEST_ONLY_NOT_FOR_DISTRIBUTION' if test_fixtures else 'BUILT_NOT_ACCEPTED',version=version,buildNumber=stamp,apiBase=origin,installer=installer,files=[dict(name=n,bytes=len(d),sha256=hashlib.sha256(d).hexdigest()) for n,d in inspected]),indent=2),encoding='utf-8')
    print('BUILT, NOT YET NATIVE/LIVE-E2E ACCEPTED:',release,flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
