"""Only mocked Worker-auth setup; never read secrets or execute Cloudflare CLI."""
import hashlib
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
        return m

    def test_default_is_dry_run_without_prompt_or_subprocess(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp))
            with patch.object(m.sys,'argv',['setup']),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass') as prompt,patch.object(m.subprocess,'run') as run:
                self.assertEqual(m.main(),0);prompt.assert_not_called();run.assert_not_called()

    def test_interactive_setup_sends_only_hash_and_signing_key_via_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp));code='synthetic-group-code-for-unit-tests-only'
            with patch.object(m.sys,'argv',['setup','--apply']),patch.object(m.sys.stdin,'isatty',return_value=True),patch.object(m.shutil,'which',return_value='node'),patch.object(m.getpass,'getpass',side_effect=[code,code]),patch.object(m.secrets,'token_hex',return_value='f'*64),patch.object(m.subprocess,'run') as run:
                self.assertEqual(m.main(),0);self.assertEqual(run.call_count,2)
                first,second=run.call_args_list
                self.assertEqual(first.args[0][-2:],['put','GROUP_CODE_SHA256']);self.assertEqual(first.kwargs['input'],hashlib.sha256(code.encode()).hexdigest()+'\n')
                self.assertEqual(second.args[0][-2:],['put','SIGNING_KEY']);self.assertEqual(second.kwargs['input'],'f'*64+'\n')
                for call in run.call_args_list:self.assertNotIn(code,' '.join(call.args[0]));self.assertNotIn('r2.env',' '.join(call.args[0]))

    def test_noninteractive_apply_is_blocked_before_secret_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=self.setup_module(Path(tmp))
            with patch.object(m.sys,'argv',['setup','--apply']),patch.object(m.shutil,'which',return_value='node'),patch.object(m.sys.stdin,'isatty',return_value=False),patch.object(m.getpass,'getpass') as prompt,patch.object(m.subprocess,'run') as run:
                with self.assertRaises(SystemExit):m.main()
                prompt.assert_not_called();run.assert_not_called()


if __name__=='__main__':unittest.main()
