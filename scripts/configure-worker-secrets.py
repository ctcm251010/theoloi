"""USER-RUN ONLY: configure Worker auth secrets without reading R2 credentials."""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='user-run interactive Cloudflare mutation after deployment approval')
    args=parser.parse_args()
    cli=ROOT/'workers/media-api/node_modules/wrangler/bin/wrangler.js'
    node=shutil.which('node')
    if not node or not cli.is_file(): parser.error('Install locked Worker npm dependencies first')
    if not args.apply:
        print('DRY RUN: would set GROUP_CODE_SHA256 and SIGNING_KEY. No secrets read or Cloudflare request made.')
        return 0
    if not sys.stdin.isatty(): parser.error('--apply requires your own interactive terminal')
    code=getpass.getpass('Group access code (32+ characters; keep it in your password manager): ')
    confirm=getpass.getpass('Repeat group access code: ')
    if code!=confirm or len(code)<32 or len(code)>256: parser.error('Codes must match and contain 32..256 characters')
    values={'GROUP_CODE_SHA256':hashlib.sha256(code.encode()).hexdigest(),'SIGNING_KEY':secrets.token_hex(32)}
    code=confirm=''
    env=os.environ.copy();env['WRANGLER_SEND_METRICS']='false';env['WRANGLER_LOG_PATH']=str(ROOT/'tmp/wrangler-logs')
    for name,value in values.items():
        subprocess.run([node,str(cli),'secret','put',name],input=value+'\n',text=True,cwd=ROOT/'workers/media-api',env=env,check=True)
    print('Configured auth secrets. Rotating SIGNING_KEY invalidates all existing sessions/tickets. R2 credentials were not used.')
    return 0


if __name__=='__main__': raise SystemExit(main())
