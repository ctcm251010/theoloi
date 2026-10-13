"""USER-RUN ONLY: configure Worker auth secrets without reading R2 credentials."""
import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import secrets
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply',action='store_true',help='user-run interactive Cloudflare mutation after deployment approval')
    parser.add_argument('--account-id',help='explicit Cloudflare account ID; required with --apply')
    args=parser.parse_args()
    cli=ROOT/'workers/media-api/node_modules/wrangler/bin/wrangler.js'
    node=shutil.which('node')
    if not node or not cli.is_file(): parser.error('Install locked Worker npm dependencies first')
    if not args.apply:
        print('DRY RUN: would set GROUP_CODE_SHA256 and SIGNING_KEY. No secrets read or Cloudflare request made.')
        return 0
    if not sys.stdin.isatty(): parser.error('--apply requires your own interactive terminal')
    if not args.account_id or not re.fullmatch(r'[0-9a-f]{32}',args.account_id):
        parser.error('--apply requires an explicit 32-character lowercase hex --account-id')
    try:
        config=json.loads((ROOT/'workers/media-api/wrangler.jsonc').read_text(encoding='utf-8'))
        if config.get('account_id') not in (None,args.account_id):
            parser.error('Wrangler config account_id conflicts with --account-id. No secrets changed.')
    except (OSError,ValueError,AttributeError):
        parser.error('Could not validate Worker config account_id. Keep this config in strict JSON format.')
    env=os.environ.copy();env['WRANGLER_SEND_METRICS']='false';env['WRANGLER_LOG_PATH']=str(ROOT/'tmp/wrangler-logs')
    env['CLOUDFLARE_ACCOUNT_ID']=args.account_id
    try:
        identity=subprocess.run([node,str(cli),'whoami','--json'],cwd=ROOT/'workers/media-api',env=env,capture_output=True,text=True,encoding='utf-8',timeout=30)
        info=json.loads(identity.stdout)
        accounts=info.get('accounts',[])
        if identity.returncode or info.get('loggedIn') is not True or not any(isinstance(a,dict) and a.get('id')==args.account_id for a in accounts):
            parser.error('Wrangler does not have access to the requested account. No secrets changed.')
    except (OSError,subprocess.SubprocessError,ValueError,TypeError,AttributeError):
        parser.error('Could not verify Wrangler account access. No secrets changed; refresh login and retry.')
    code=getpass.getpass('Group access code (32+ characters; keep it in your password manager): ')
    confirm=getpass.getpass('Repeat group access code: ')
    if code!=confirm or len(code)<32 or len(code)>256: parser.error('Codes must match and contain 32..256 characters')
    values={'GROUP_CODE_SHA256':hashlib.sha256(code.encode()).hexdigest(),'SIGNING_KEY':secrets.token_hex(32)}
    code=confirm=''
    for name,value in values.items():
        subprocess.run([node,str(cli),'secret','put',name],input=value+'\n',text=True,cwd=ROOT/'workers/media-api',env=env,check=True)
    print('Configured auth secrets. Rotating SIGNING_KEY invalidates all existing sessions/tickets. R2 credentials were not used.')
    return 0


if __name__=='__main__': raise SystemExit(main())
