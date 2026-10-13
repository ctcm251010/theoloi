"""Only mocked Worker-auth setup; never read secrets or execute Cloudflare CLI."""
import hashlib
import json
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

FILE=Path(__file__).resolve().parents[1]/'scripts/configure-worker-secrets.py'


def module():
    spec=importlib.util.spec_from_file_location('worker_secret_setup',FILE)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class WorkerSecretSetupTests(unittest.TestCase):
    def setup_module(self,root):
        m=module();m.ROOT=root
        target=root/'workers/media-api/node_modules/wrangler/bin/wrangler.js'
        target.parent.mkdir(parents=True);target.write_text('synthetic cli, never executed')
        (root/'workers/media-api/wrangler.jsonc').write_text(json.dumps({'name':'audiotp-media-api'}))
        return m

    def test_default_is_dry_run_without_prompt_or_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp))
            with patch.object(m.sys,'argv',['setup']),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass') as prompt,patch.object(m.subprocess,'run') as run:
                self.assertEqual(m.main(),0);prompt.assert_not_called();run.assert_not_called()

    def test_interactive_setup_sends_only_hash_and_signing_key_via_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp));code='synthetic-group-code-for-unit-tests-only'
            account='a'*32
            identity=m.subprocess.CompletedProcess([],0,stdout=json.dumps({'loggedIn':True,'accounts':[{'id':account}]}),stderr='')
            with patch.object(m.sys,'argv',['setup','--apply','--account-id',account]),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass',side_effect=[code,code]),patch.object(m.secrets,'token_hex',return_value='f'*64),patch.object(m.subprocess,'run',side_effect=[identity,None,None]) as run:
                self.assertEqual(m.main(),0);self.assertEqual(run.call_count,3)
                preflight,first,second=run.call_args_list
                self.assertEqual(preflight.args[0][-2:],['whoami','--json'])
                self.assertEqual(first.args[0][-2:],['put','GROUP_CODE_SHA256']);self.assertEqual(first.kwargs['input'],hashlib.sha256(code.encode()).hexdigest()+'\n')
                self.assertEqual(second.args[0][-2:],['put','SIGNING_KEY']);self.assertEqual(second.kwargs['input'],'f'*64+'\n')
                for call in run.call_args_list:
                    self.assertNotIn(code,' '.join(call.args[0]));self.assertNotIn('r2.env',' '.join(call.args[0]))
                    self.assertEqual(call.kwargs['env']['CLOUDFLARE_ACCOUNT_ID'],account)

    def test_apply_requires_explicit_account_before_prompt_or_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp))
            with patch.object(m.sys,'argv',['setup','--apply']),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass') as prompt,patch.object(m.subprocess,'run') as run:
                with self.assertRaises(SystemExit):m.main()
                prompt.assert_not_called();run.assert_not_called()

    def test_wrong_account_or_failed_identity_never_prompts_or_writes(self):
        for result in ({'loggedIn':True,'accounts':[{'id':'b'*32}]},{'loggedIn':False,'accounts':[]},None):
            with self.subTest(result=result),tempfile.TemporaryDirectory() as tmp:
                m=self.setup_module(Path(tmp))
                response=m.subprocess.CompletedProcess([],1 if result is None else 0,stdout=json.dumps(result),stderr='private diagnostic must not be printed')
                with patch.object(m.sys,'argv',['setup','--apply','--account-id','a'*32]),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass') as prompt,patch.object(m.subprocess,'run',return_value=response) as run:
                    with self.assertRaises(SystemExit):m.main()
                    prompt.assert_not_called();self.assertEqual(run.call_count,1)

    def test_config_account_cannot_override_explicit_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp))
            (m.ROOT/'workers/media-api/wrangler.jsonc').write_text(json.dumps({'account_id':'b'*32}))
            with patch.object(m.sys,'argv',['setup','--apply','--account-id','a'*32]),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass') as prompt,patch.object(m.subprocess,'run') as run:
                with self.assertRaises(SystemExit):m.main()
                prompt.assert_not_called();run.assert_not_called()

    def test_noninteractive_apply_is_blocked_before_secret_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp))
            with patch.object(m.sys,'argv',['setup','--apply']),patch.object(m.shutil,'which',return_value='node'),patch.object(m.sys.stdin,'isatty',return_value=False),patch.object(m.getpass,'getpass') as prompt,patch.object(m.subprocess,'run') as run:
                with self.assertRaises(SystemExit):m.main()
                prompt.assert_not_called();run.assert_not_called()

    def test_code_only_update_accepts_short_code_without_rotating_signing_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp));code='4826';account='a'*32
            identity=m.subprocess.CompletedProcess([],0,stdout=json.dumps({'loggedIn':True,'accounts':[{'id':account}]}),stderr='')
            with patch.object(m.sys,'argv',['setup','--apply','--code-only','--account-id',account]),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass',side_effect=[code,code]),patch.object(m.secrets,'token_hex') as generate,patch.object(m.subprocess,'run',side_effect=[identity,None]) as run:
                self.assertEqual(m.main(),0);self.assertEqual(run.call_count,2);generate.assert_not_called()
                write=run.call_args_list[1]
                self.assertEqual(write.args[0][-3:],['secret','put','GROUP_CODE_SHA256'])
                self.assertEqual(write.kwargs['input'],hashlib.sha256(code.encode()).hexdigest()+'\n')
                self.assertNotIn(code,' '.join(write.args[0]))
                self.assertEqual(write.kwargs['env']['CLOUDFLARE_ACCOUNT_ID'],account)

    def test_invalid_code_or_confirmation_never_writes_secrets(self):
        for code,confirm in [('123','123'),('x'*257,'x'*257),('ab\nc','ab\nc'),('4826','4827')]:
            with self.subTest(length=len(code)),tempfile.TemporaryDirectory() as tmp:
                m=self.setup_module(Path(tmp));account='a'*32
                identity=m.subprocess.CompletedProcess([],0,stdout=json.dumps({'loggedIn':True,'accounts':[{'id':account}]}),stderr='')
                with patch.object(m.sys,'argv',['setup','--apply','--code-only','--account-id',account]),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass',side_effect=[code,confirm]),patch.object(m.subprocess,'run',return_value=identity) as run:
                    with self.assertRaises(SystemExit):m.main()
                    self.assertEqual(run.call_count,1)


if __name__=='__main__':unittest.main()
