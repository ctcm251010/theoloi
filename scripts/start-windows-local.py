"""Open the real local AudioTP library and manage only a backend started here."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


@contextmanager
def single_launcher(root):
    import msvcrt
    directory=root/'logs/windows-local';directory.mkdir(parents=True,exist_ok=True)
    # The Windows byte lock is released on close/process exit; keep the file to avoid unlink races.
    with (directory/'launcher.lock').open('a+b') as handle:
        handle.seek(0)
        try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            yield False;return
        try:yield True
        finally:
            handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)


def find_release(root):
    directory=root/'release/windows'
    candidates=[p for p in directory.glob('LOCAL-*') if p.is_dir() and not p.is_symlink() and p.resolve().parent==directory.resolve()]
    if not candidates:raise ValueError('Chưa có EXE thư viện thật (LOCAL); không mở bản TEST thay thế.')
    folder=max(candidates,key=lambda p:p.stat().st_mtime_ns)
    report_file=folder/'build-report.json';exe=folder/'AudioTP.exe'
    if report_file.is_symlink() or exe.is_symlink():raise ValueError('Redirected local artifact')
    report=json.loads(report_file.read_text(encoding='utf-8'))
    base=report.get('apiBase','')
    match=re.fullmatch(r'http://127\.0\.0\.1:([0-9]{1,5})',base)
    if report.get('status')!='LOCAL_LIBRARY_NOT_FOR_DISTRIBUTION' or not match or not 1<=int(match[1])<=65535:
        raise ValueError('Invalid real local build/origin; refusing TEST or remote artifact')
    record=next((r for r in report.get('files',[]) if r.get('name')=='AudioTP.exe'),None)
    data=exe.read_bytes()
    if not record or record.get('bytes')!=len(data) or record.get('sha256')!=hashlib.sha256(data).hexdigest():
        raise ValueError('Local EXE integrity/hash mismatch; rebuild rather than bypass verification')
    return exe,base


def backend_ready(base):
    match=re.fullmatch(r'http://127\.0\.0\.1:([0-9]{1,5})',base)
    if not match or not 1<=int(match[1])<=65535:return False
    connection=http.client.HTTPConnection('127.0.0.1',int(match[1]),timeout=1)
    try:
        # Direct loopback HTTP: do not use proxy settings or follow redirects.
        connection.request('GET','/connection.json');response=connection.getresponse()
        if response.status!=200:return False
        config=json.loads(response.read(4096))
        if config.get('mode')!='local-files' or config.get('apiBase')!=base:return False
        connection.request('OPTIONS','/v1/local-session',headers={'Origin':'http://tauri.localhost','Access-Control-Request-Method':'POST'})
        response=connection.getresponse();response.read(4096)
        return response.status==204 and response.getheader('Access-Control-Allow-Origin')=='http://tauri.localhost'
    except (OSError,ValueError,http.client.HTTPException):return False
    finally:connection.close()


def port_in_use(port):
    with socket.socket() as connection:
        connection.settimeout(.5)
        return connection.connect_ex(('127.0.0.1',port))==0


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='verify local EXE/hash only, without starting processes or network')
    args=parser.parse_args(argv)
    exe,base=find_release(ROOT)
    print('AudioTP: thư viện thật trên máy, không phải TEST hoặc R2 live.',flush=True)
    if args.check:
        print(json.dumps({'status':'LOCAL_EXE_HASH_VERIFIED','exe':str(exe),'apiBase':base},ensure_ascii=False));return 0
    with single_launcher(ROOT) as acquired:
        if not acquired:
            print('AudioTP đang mở qua launcher này. Dùng cửa sổ hiện có.',flush=True);return 0
        return run_local(exe,base)


def run_local(exe,base):
    owned=None;log=None
    try:
        if not backend_ready(base):
            port=int(base.rsplit(':',1)[1])
            if port_in_use(port):raise RuntimeError(f'Cổng/port {port} đang được chương trình khác dùng; không tự dừng chương trình đó.')
            node=shutil.which('node')
            if not node:raise RuntimeError('Backend local cần Node.js; EXE online sau này sẽ không cần backend này.')
            logs=ROOT/'logs/windows-local';logs.mkdir(parents=True,exist_ok=True)
            filename=logs/(datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.log')
            log=filename.open('w',encoding='utf-8')
            owned=subprocess.Popen([node,str(ROOT/'workers/media-api/local-preview.mjs'),'--desktop','--port',str(port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            deadline=time.monotonic()+15
            while not backend_ready(base):
                if owned.poll() is not None or time.monotonic()>=deadline:raise RuntimeError('Không khởi động được backend local. Xem '+str(filename))
                time.sleep(.1)
        print('Đang mở AudioTP. Đóng app để dừng backend do launcher này mở.',flush=True)
        return subprocess.Popen([str(exe)],cwd=exe.parent).wait()
    finally:
        if owned is not None and owned.poll() is None:
            owned.terminate()
            try:owned.wait(timeout=5)
            except subprocess.TimeoutExpired:owned.kill();owned.wait(timeout=5)
        if log is not None:log.close()


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,RuntimeError) as error:
        print('AudioTP chưa mở được: '+str(error));raise SystemExit(1)
