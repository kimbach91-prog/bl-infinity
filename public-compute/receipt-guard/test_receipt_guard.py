"""Public synthetic tests; no real account, node, credential or queue data."""
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from receipt_guard import Binding, ClaimConflict, ClaimJournal, reconcile, digest

B = Binding('test-job', 'test-node', 'test-mode', 'a'*64)
Q = 'b'*64
R = 'c'*64
EMPTY = hashlib.sha256(b'').hexdigest()

def row(**changes):
    value = dict(B.normalized(), receipt_id='test-receipt', state='SUCCEEDED', exit_code='0', timed_out='FALSE', stdout_sha256=R, stderr_sha256=EMPTY, stdout_bytes='3', stderr_bytes='0')
    value.update(changes)
    return value

class ReconciliationTests(unittest.TestCase):
    def test_01_completed(self):
        self.assertEqual(reconcile(B,[row()],complete=True).state,'DO_NOT_REPLAY_COMPLETED')
    def test_02_delivery_dedup(self):
        a=reconcile(B,[row(finished='one'),row(finished='two')],complete=True)
        self.assertEqual((a.state,a.unique_receipts,a.delivery_rows),('DO_NOT_REPLAY_COMPLETED',1,2))
    def test_03_execution_not_delivery(self):
        self.assertEqual(reconcile(B,[row(),row(receipt_id='other')],complete=True).state,'HOLD_MULTIPLE_EXECUTIONS')
    def test_04_conflicting_receipt(self):
        self.assertEqual(reconcile(B,[row(),row(stdout_sha256='d'*64)],complete=True).state,'HOLD_RECEIPT_ID_COLLISION')
    def test_05_missing_not_permission(self):
        self.assertEqual(reconcile(B,[],complete=True).state,'HOLD_NO_RECEIPT')
    def test_06_incomplete_not_permission(self):
        self.assertEqual(reconcile(B,[row()],complete=False).state,'HOLD_INCOMPLETE_SOURCE')
    def test_07_binding_fields(self):
        for k in B.normalized():
            with self.subTest(field=k):
                self.assertEqual(reconcile(B,[row(**{k:'wrong'})],complete=True).state,'HOLD_BINDING_CONFLICT')
    def test_08_failed_receipt(self):
        for changes in ({'state':'FAILED'},{'exit_code':1},{'timed_out':True}):
            with self.subTest(changes=changes):
                self.assertEqual(reconcile(B,[row(**changes)],complete=True).state,'HOLD_NON_SUCCESS_RECEIPT')
    def test_09_strict_boolean(self):
        self.assertEqual(reconcile(B,[row(timed_out='false')],complete=True).state,'HOLD_INVALID_SOURCE')
    def test_10_strict_integer(self):
        for value in (True,-1,'1.0',' 1','01'):
            with self.subTest(value=value):
                self.assertEqual(reconcile(B,[row(stdout_bytes=value)],complete=True).state,'HOLD_INVALID_SOURCE')
    def test_11_missing_field(self):
        a=row();del a['stdout_sha256']
        self.assertEqual(reconcile(B,[a],complete=True).state,'HOLD_INVALID_SOURCE')
    def test_12_digest_validation(self):
        for value in ('A'*64,'a'*63,'a'*64+'\n',None):
            with self.subTest(value=value):
                self.assertEqual(reconcile(B,[row(stdout_sha256=value)],complete=True).state,'HOLD_INVALID_SOURCE')
    def test_13_done_normalization(self):
        self.assertEqual(reconcile(B,[row(),row(state='DONE')],complete=True).unique_receipts,1)
    def test_14_order_invariant(self):
        a=row();b=row(receipt_id='second')
        self.assertEqual(reconcile(B,[a,b],complete=True),reconcile(B,[b,a],complete=True))
    def test_15_no_raw_queue_authority(self):
        self.assertEqual(reconcile(B,[row(queue_state='REJECTED')],complete=True).state,'DO_NOT_REPLAY_COMPLETED')
    def test_16_invalid_binding(self):
        self.assertEqual(reconcile(dataclasses.replace(B,job_id=''),[row()],complete=True).state,'HOLD_INVALID_SOURCE')
    def test_17_non_mapping(self):
        self.assertEqual(reconcile(B,[None],complete=True).state,'HOLD_INVALID_SOURCE')

class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'claims.sqlite';self.j=ClaimJournal(self.path)
    def tearDown(self):
        self.j.close();self.tmp.cleanup()
    def test_18_first_claim_only(self):
        self.assertIsNotNone(self.j.claim(B,Q));self.assertIsNone(self.j.claim(B,Q))
    def test_19_request_conflict(self):
        self.j.claim(B,Q)
        with self.assertRaises(ClaimConflict):self.j.claim(B,'e'*64)
    def test_20_binding_conflict(self):
        self.j.claim(B,Q)
        with self.assertRaises(ClaimConflict):self.j.claim(dataclasses.replace(B,mode='other'),Q)
    def test_21_completion(self):
        n=self.j.claim(B,Q);self.j.finish(B,n,R);self.j.finish(B,n,R)
        self.assertEqual(self.j.state(B),'COMPLETED');self.assertIsNone(self.j.claim(B,Q))
    def test_22_wrong_nonce(self):
        self.j.claim(B,Q)
        with self.assertRaises(ClaimConflict):self.j.finish(B,'wrong',R)
    def test_23_conflicting_result(self):
        n=self.j.claim(B,Q);self.j.finish(B,n,R)
        with self.assertRaises(ClaimConflict):self.j.finish(B,n,'e'*64)
    def test_24_reopen(self):
        self.j.claim(B,Q);self.j.close();self.j=ClaimJournal(self.path)
        self.assertIsNone(self.j.claim(B,Q));self.assertEqual(self.j.state(B),'CLAIMED')
    def test_25_concurrent_claims(self):
        def claim(_):
            j=ClaimJournal(self.path)
            try:return j.claim(B,Q)
            finally:j.close()
        with ThreadPoolExecutor(max_workers=8) as pool:values=list(pool.map(claim,range(24)))
        self.assertEqual(sum(x is not None for x in values),1)
    def test_26_child_crash_after_effect(self):
        effect=Path(self.tmp.name)/'effect.txt'
        script="from receipt_guard import *;from pathlib import Path;import os,sys;b=Binding('test-job','test-node','test-mode','a'*64);j=ClaimJournal(sys.argv[1]);n=j.claim(b,'b'*64);assert n;Path(sys.argv[2]).write_text('one');os._exit(23)"
        r=subprocess.run([sys.executable,'-c',script,str(self.path),str(effect)],cwd=Path(__file__).parent,timeout=15,capture_output=True)
        self.assertEqual(r.returncode,23);self.assertEqual(effect.read_text(),'one');self.assertIsNone(self.j.claim(B,Q));self.assertEqual(self.j.state(B),'CLAIMED')
    def test_27_finish_without_claim(self):
        with self.assertRaises(ClaimConflict):self.j.finish(B,'none',R)
    def test_28_job_isolation(self):
        self.j.claim(B,Q);other=dataclasses.replace(B,job_id='other');self.assertIsNotNone(self.j.claim(other,Q))
    def test_29_wrong_state_binding(self):
        self.j.claim(B,Q)
        with self.assertRaises(ClaimConflict):self.j.state(dataclasses.replace(B,mode='other'))
    def test_30_bad_db_fails_closed(self):
        bad=Path(self.tmp.name)/'bad.sqlite';bad.write_bytes(b'not a database')
        with self.assertRaises(Exception):ClaimJournal(bad)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'schema':'public-receipt-guard-tests/1','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'scope':'public synthetic; not production target fencing'},sort_keys=True))
    raise SystemExit(0 if result.wasSuccessful() else 1)
