"""B10 audit contract: synthetic S3 only; never load real secrets or call R2."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import sys
import threading
import unittest
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError, ParamValidationError
from botocore.stub import Stubber

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('b10_verifier',ROOT/'scripts/verify-r2.py')
b10=importlib.util.module_from_spec(spec);spec.loader.exec_module(b10)


def assets():
    return [{'assetId':'synthetic:1','objectKey':'audio/a.m4a','bytes':7,'sha256':'a'*64},
            {'assetId':'synthetic:2','objectKey':'audio/b.m4a','bytes':9,'sha256':'b'*64}]


def remote_error(status):
    return ClientError({'Error':{'Code':'Synthetic','Message':'untrusted secret-like text'},
                        'ResponseMetadata':{'HTTPStatusCode':status}},'Synthetic')


class Stop:
    def __init__(self):self.delays=[];self.stopped=False
    def is_set(self):return self.stopped
    def wait(self,delay):self.delays.append(delay);return self.stopped


class FakeS3:
    def __init__(self,items=None):
        items=items or assets();self.items={a['objectKey']:a for a in items}
        self.pages=[{'IsTruncated':False,'Contents':[{'Key':a['objectKey'],'Size':a['bytes'],'ETag':'"'+a['assetId']+'"'} for a in items]}]
        self.list_calls=[];self.head_calls=[];self.head_errors={};self.head_changes={};self.closed=False
        self.meta=type('Meta',(),{'events':type('Events',(),{'register':lambda *_:None})()})()
    def list_objects_v2(self,**params):
        self.list_calls.append(params)
        page=self.pages[len(self.list_calls)-1]
        if isinstance(page,Exception):raise page
        return page
    def head_object(self,**params):
        key=params['Key'];self.head_calls.append(key)
        if key in self.head_errors:raise self.head_errors[key]
        a=self.items[key]
        head={'ContentLength':a['bytes'],'Metadata':{'sha256':a['sha256'],'asset-id':a['assetId']},'ContentType':'audio/mp4','ETag':'"'+a['assetId']+'"'}
        head.update(self.head_changes.get(key,{}));return head
    def close(self):self.closed=True


def empty_report(n=2):
    return {'expectedObjectCount':n,'actualObjectCount':None,'inventoryComplete':False,'missingKeys':[],
            'extraKeys':[],'objects':[],'errors':[]}


class VerifyR2Tests(unittest.TestCase):
    def run_audit(self,client,items=None,stop=None):
        r=empty_report(len(items or assets()));stop=stop or Stop()
        try:b10.audit(client,{'bucket':'test'},items or assets(),2,stop,r)
        except Exception as exc:r['errors'].append(b10.safe_error(exc)[1])
        b10.finish_report(r,stop);return r

    def test_paginated_full_bucket_passes_and_hash_is_not_content_audit(self):
        client=FakeS3();contents=client.pages[0]['Contents']
        client.pages=[{'IsTruncated':True,'Contents':contents[:1],'NextContinuationToken':'opaque-1'},
                      {'IsTruncated':False,'Contents':contents[1:]}]
        r=self.run_audit(client)
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['listPages'],2)
        self.assertEqual(r['summary'],{'expected':2,'actual':2,'checked':2,'matched':2,'missing':0,'extra':0,'mismatched':0,'headErrors':0,'errors':0})
        self.assertEqual(client.list_calls,[{'Bucket':'test','MaxKeys':1000},{'Bucket':'test','MaxKeys':1000,'ContinuationToken':'opaque-1'}])

    def test_missing_extra_and_head_404_fail_with_precise_keys(self):
        client=FakeS3();client.pages[0]['Contents'][1]['Key']='unrelated/extra'
        client.head_errors['audio/b.m4a']=remote_error(404)
        r=self.run_audit(client)
        self.assertEqual(r['status'],'FAIL');self.assertEqual(r['missingKeys'],['audio/b.m4a'])
        self.assertEqual(r['extraKeys'],['unrelated/extra']);self.assertEqual(r['summary']['headErrors'],1)

    def test_wrong_metadata_type_size_and_etag_are_failures(self):
        for change,issue in [({'Metadata':{}},'metadata_sha256'),({'ContentLength':True},'size'),
                             ({'ContentType':'text/html'},'content_type'),({'ETag':'"changed"'},'list_head_etag')]:
            with self.subTest(issue=issue):
                c=FakeS3();c.head_changes['audio/a.m4a']=change;r=self.run_audit(c)
                self.assertEqual(r['status'],'FAIL');self.assertIn(issue,r['objects'][0]['issues'])

    def test_malformed_head_metadata_is_a_row_failure(self):
        c=FakeS3();c.head_changes['audio/a.m4a']={'Metadata':None}
        row=b10.head_check(c,'test',assets()[0],{'bytes':7,'etag':'"synthetic:1"'},Stop())
        self.assertEqual(row['status'],'FAIL');self.assertIn('invalid_head_response',row['issues'])

    def test_inventory_duplicate_and_bad_pagination_fail_closed(self):
        for mode in ('duplicate','no-token','repeat-token','bool-size','no-truncated','bad-contents','bad-page'):
            with self.subTest(mode=mode):
                c=FakeS3();page=c.pages[0]
                if mode=='duplicate':page['Contents'].append(copy.deepcopy(page['Contents'][0]))
                if mode=='no-token':page['IsTruncated']=True
                if mode=='repeat-token':c.pages=[dict(page,IsTruncated=True,NextContinuationToken='x'),{'IsTruncated':True,'Contents':[],'NextContinuationToken':'x'}]
                if mode=='bool-size':page['Contents'][0]['Size']=True
                if mode=='no-truncated':page.pop('IsTruncated')
                if mode=='bad-contents':page['Contents']=None
                if mode=='bad-page':c.pages=[None]
                r=self.run_audit(c);self.assertEqual(r['status'],'FAIL');self.assertFalse(r['inventoryComplete'])

    def test_duplicate_expected_identity_is_rejected_before_list(self):
        for field in ('assetId','objectKey'):
            items=assets();items[1][field]=items[0][field];c=FakeS3()
            with self.subTest(field=field),self.assertRaises(b10.UploadError):b10.audit(c,{'bucket':'test'},items,2,Stop(),empty_report())
            self.assertEqual(c.list_calls,[])

    def test_matching_malformed_etags_cannot_pass_inventory_or_head(self):
        for etag in (123,['x'],{'x':1},True,'',' '):
            with self.subTest(etag=etag):
                c=FakeS3();c.pages[0]['Contents'][0]['ETag']=etag;c.head_changes['audio/a.m4a']={'ETag':etag}
                self.assertEqual(self.run_audit(c)['status'],'FAIL')
                row=b10.head_check(c,'test',assets()[0],{'bytes':7,'etag':etag},Stop())
                self.assertEqual(row['status'],'FAIL');self.assertIn('list_head_etag',row['issues'])

    def test_permanent_403_does_not_retry_and_transients_are_bounded(self):
        for status,want_calls,want_delays in [(403,1,[]),(429,3,[2,4]),(503,3,[2,4])]:
            calls=[];stop=Stop()
            def fail(**_):calls.append(1);raise remote_error(status)
            with self.subTest(status=status),self.assertRaises(ClientError):b10.read_call(fail,stop)
            self.assertEqual(len(calls),want_calls);self.assertEqual(stop.delays,want_delays)
        calls=[]
        def recover(**_):
            calls.append(1)
            if len(calls)<3:raise remote_error(500)
            return {'ok':True}
        self.assertEqual(b10.read_call(recover,Stop()),{'ok':True})

    def test_head_403_is_not_missing_and_partial_interruption_fails(self):
        c=FakeS3();c.head_errors['audio/a.m4a']=remote_error(403);r=self.run_audit(c)
        self.assertEqual(r['status'],'FAIL');self.assertEqual(r['missingKeys'],[])
        self.assertIn('remote_http_403',r['objects'][0]['issues'])
        stop=Stop();stop.stopped=True;r=self.run_audit(FakeS3(),stop=stop)
        self.assertEqual(r['status'],'FAIL');self.assertIn('interrupted',r['errors'])

    def test_real_sdk_guard_blocks_every_operation_except_list_and_head_before_transport(self):
        client=boto3.client('s3',region_name='auto',endpoint_url='https://example.invalid',aws_access_key_id='synthetic',aws_secret_access_key='synthetic')
        client.meta.events.register('provide-client-params.s3',b10.read_only_guard)
        try:
            with patch.object(client._endpoint,'make_request',side_effect=AssertionError('Network forbidden')):
                for operation in client.meta.service_model.operation_names:
                    if operation not in ('ListObjectsV2','HeadObject'):
                        with self.subTest(operation=operation),self.assertRaises(b10.UploadError):client._make_api_call(operation,{})
                with Stubber(client) as stub:
                    stub.add_response('list_objects_v2',{'IsTruncated':False,'Contents':[]},{'Bucket':'test'})
                    self.assertEqual(client.list_objects_v2(Bucket='test')['Contents'],[])
                    stub.add_response('head_object',{'ContentLength':7},{'Bucket':'test','Key':'x'})
                    self.assertEqual(client.head_object(Bucket='test',Key='x')['ContentLength'],7)
        finally:client.close()

    def fake_main(self,client):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'config').mkdir();(root/'state').mkdir()
            state=root/'state/r2-transfers.sqlite';state.write_bytes(b'preserve-upload-state')
            (root/'config/r2.json').write_text(json.dumps({'accountId':'a'*32,'bucket':'test-bucket','endpoint':'https://'+'a'*32+'.r2.cloudflarestorage.com'}))
            console=io.StringIO()
            with patch.object(b10,'ROOT',root),patch.object(b10,'load_delivery',return_value={'assets':{a['assetId']:a for a in assets()}}),\
                 patch.object(b10,'read_secrets',return_value={'R2_ACCESS_KEY_ID':'TESTKEY123','R2_SECRET_ACCESS_KEY':'TESTSECRET456'}),\
                 patch.object(b10,'create_client',return_value=client),patch.object(b10.signal,'signal'),contextlib.redirect_stdout(console):
                code=b10.main(['--workers','2'])
            report=json.loads(next((root/'logs/r2-verification').rglob('report.json')).read_text(encoding='utf-8'))
            self.assertEqual(state.read_bytes(),b'preserve-upload-state')
            self.assertFalse((root/'.secrets').exists());self.assertTrue(client.closed)
            self.assertNotIn('TESTKEY123',json.dumps(report));self.assertNotIn('TESTSECRET456',json.dumps(report))
            self.assertNotIn('TESTKEY123',console.getvalue());return code,report

    def test_mock_main_report_exit_and_redaction_without_credentials_or_state_writes(self):
        code,r=self.fake_main(FakeS3());self.assertEqual(code,0);self.assertEqual(r['status'],'PASS')
        self.assertFalse(r['contentSha256Verified']);self.assertFalse(r['stateUsedForRemoteVerdict'])
        c=FakeS3();c.pages[0]['Contents'].append({'Key':'TESTSECRET456/extra','Size':0,'ETag':'x'})
        code,r=self.fake_main(c);self.assertEqual(code,1);self.assertEqual(r['extraKeys'],['[REDACTED]/extra'])

    def test_cleanup_failure_still_saves_fail_report(self):
        c=FakeS3()
        def fail_close():c.closed=True;raise RuntimeError('untrusted secret-like text')
        c.close=fail_close
        code,r=self.fake_main(c);self.assertEqual(code,1);self.assertEqual(r['status'],'FAIL')
        self.assertIn('client_cleanup_error',r['errors'])


if __name__=='__main__':unittest.main()
