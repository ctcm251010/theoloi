"""Read-only Windows preflight by default; --build produces an API-configured release."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess

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
    parser.add_argument('--check',action='store_true',help='preflight only (the default)')
    parser.add_argument('--build',action='store_true',help='user-run: install locked npm dependencies and build release')
    parser.add_argument('--api-base',help='actual deployed HTTPS API origin, required for --build')
    parser.add_argument('--installer',action='store_true',help='also create NSIS installer after successful EXE build')
    args=parser.parse_args(argv)
    report,tools,npm_cli=preflight()
    print(json.dumps(report,indent=2))
    if not args.build: return 2 if report['missing'] else 0
    try: origin=api_origin(args.api_base or '')
    except ValueError as error: parser.error(str(error))
    if report['missing']: return 2
    with exclusive_build():
        return build_release(origin,args.installer,tools,npm_cli)


def build_release(origin,installer,tools,npm_cli):
    config_path=APP / 'src-tauri/tauri.conf.json'
    original=config_path.read_bytes()
    config=json.loads(original)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backups=APP/'build-backups';backups.mkdir(exist_ok=True)
    (backups/(stamp+'.tauri.json')).write_bytes(original)
    stage=APP / 'web-release' / stamp
    stage.mkdir(parents=True,exist_ok=False)
    files=['index.html','styles.css','app.mjs','catalog.mjs','player.mjs','storage.mjs','ui-core.mjs','api-client.mjs','catalog.client.json','quick-play.json','favicon.svg']
    for name in files: shutil.copyfile(APP / 'web' / name, stage / name)
    (stage/'connection.json').write_text(json.dumps(dict(mode='remote',apiBase=origin,version='0.2.0',buildNumber=stamp)),encoding='utf-8')
    config['build']['frontendDist']='../web-release/'+stamp
    config['app']['security']['csp']=f"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; media-src 'self' {origin}; connect-src 'self' {origin} ipc: http://ipc.localhost; object-src 'none'; frame-src 'none'; base-uri 'self'"
    child_env=os.environ.copy()
    child_env['PATH']=str(Path(tools['cargo']).parent)+os.pathsep+child_env.get('PATH','')
    child_env['CARGO_ENCODED_RUSTFLAGS']='--remap-path-prefix='+str(ROOT)+'=audiotp'
    command=[tools['node'],str(npm_cli)]
    try:
        config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
        for arguments in (['ci','--ignore-scripts'],['test'],['run','build']):
            subprocess.run(command+arguments,cwd=APP,env=child_env,check=True)
        if installer: subprocess.run(command+['run','installer'],cwd=APP,env=child_env,check=True)
        binary=APP/'src-tauri/target/release/AudioTP.exe'
        if not binary.is_file(): raise ValueError('Expected AudioTP.exe was not produced')
        artifacts=[binary]
        if installer:
            installers=list((APP/'src-tauri/target/release/bundle/nsis').glob('*.exe'))
            if not installers: raise ValueError('NSIS installer was not produced')
            artifacts.extend(installers)
        inspected=[]
        for artifact in artifacts:
            data=artifact.read_bytes()
            for marker in (str(ROOT).encode(),str(ROOT).encode('utf-16-le'),b'R2_SECRET_ACCESS_KEY',b'AWS_SECRET_ACCESS_KEY'):
                if marker in data: raise ValueError('Release contains a prohibited developer path/credential marker')
            inspected.append((artifact.name,data))
        guide=(ROOT/'docs/windows-user-guide.vi.md').read_bytes()
        release=ROOT/'release/windows'/('0.2.0-'+stamp)
        release.mkdir(parents=True,exist_ok=False)
        sums=[]
        for name,data in inspected:
            (release/name).write_bytes(data)
            sums.append(hashlib.sha256(data).hexdigest()+'  '+name)
        (release/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
        (release/'HUONG-DAN.md').write_bytes(guide)
        print('BUILT, NOT YET LIVE-E2E VERIFIED:',release)
        return 0
    finally:
        config_path.write_bytes(original)


if __name__=='__main__': raise SystemExit(main())
