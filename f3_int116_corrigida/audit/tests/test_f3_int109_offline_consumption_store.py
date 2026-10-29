import hashlib
import base64
import json
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import closing
import test_f3_int107_typed_batch_chain as prior
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry
from tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain
from tools import f3_int109_offline_consumption_store as store


class ConsumptionStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.TypedBatchChainTests.setUpClass()
        cls.segments = (prior.TypedBatchChainTests.segment,)
        cls.scope = dict(context='audit:A',purpose='review',run_id='run:1')
        cls.batches = (ChainBatch((TypedBatchEntry('audit','x'),),1),)
        cls.next_batches = (ChainBatch((TypedBatchEntry('audit','y'),),2),)
        cls.pin = build_typed_chain(cls.segments,**cls.scope,batches=cls.batches).digest
        cls.next_pin = build_typed_chain(cls.segments,**cls.scope,batches=cls.next_batches).digest

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'ledger.sqlite'
        self.initial = store.create_store(self.path,**self.scope,minimum_revision=1)
        self.assertEqual(self.initial.status,'STORE_FIXTURE_UNAUTHENTICATED')

    def consume(self, **changes):
        args = dict(self.scope,expected_state_digest=self.initial.state_digest,
                    expected_digest=self.pin,batches=self.batches)
        args.update(changes)
        return store.consume_chain(self.path,self.segments,**args)

    def state(self):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            return json.loads(conn.execute('SELECT payload FROM state').fetchone()[0])

    def replace_state(self, state, raw=None):
        data=store._encode(state) if raw is None else raw
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('UPDATE state SET payload=? WHERE id=1',(data,))
        return hashlib.sha256(store.DOMAIN+data).hexdigest()

    def test_create_and_reopen(self):
        self.assertEqual(store.verify_store(self.path,expected_state_digest=self.initial.state_digest),self.initial)

    def test_success_persists_consumption_and_floor(self):
        result=self.consume()
        self.assertEqual(result.status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.state()['consumed'],[self.pin])
        self.assertEqual(self.state()['next_revision'],2)
        self.assertEqual(self.state()['generation'],1)
        self.assertEqual(store.verify_store(self.path,expected_state_digest=result.state_digest).status,'STORE_FIXTURE_UNAUTHENTICATED')

    def test_next_chain_with_retained_new_anchor(self):
        first=self.consume()
        second=self.consume(expected_state_digest=first.state_digest,expected_digest=self.next_pin,batches=self.next_batches)
        self.assertEqual(second.status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.state()['next_revision'],3)
        self.assertEqual(self.state()['generation'],2)

    def test_restart_does_not_clear_history(self):
        result=self.consume()
        self.assertEqual(self.consume(expected_state_digest=result.state_digest).status,'STALE_CHAIN_REVISION')

    def test_stale_snapshot_cannot_consume_twice(self):
        self.assertEqual(self.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.consume().status,'STATE_ANCHOR_MISMATCH')

    def test_restored_old_database_rejected_by_retained_anchor(self):
        backup=self.path.read_bytes()
        result=self.consume()
        self.path.write_bytes(backup)
        self.assertEqual(self.consume(expected_state_digest=result.state_digest).status,'STATE_ANCHOR_MISMATCH')

    def test_joint_rollback_remains_explicit_limit(self):
        backup=self.path.read_bytes()
        self.consume()
        self.path.write_bytes(backup)
        self.assertEqual(store.verify_store(self.path,expected_state_digest=self.initial.state_digest).status,'STORE_FIXTURE_UNAUTHENTICATED')

    def test_existing_store_never_reinitialized(self):
        before=self.path.read_bytes()
        self.assertEqual(store.create_store(self.path,**self.scope,minimum_revision=0).status,'STORE_EXISTS')
        self.assertEqual(self.path.read_bytes(),before)

    def test_missing_store_never_created_by_consumption(self):
        self.path.unlink()
        self.assertEqual(self.consume().status,'STORE_ERROR')
        self.assertFalse(self.path.exists())

    def test_missing_parent_initialization_fails(self):
        result=store.create_store(self.path/'missing'/'db',**self.scope,minimum_revision=1)
        self.assertEqual(result.status,'STORE_ERROR')

    def test_invalid_initial_state(self):
        for change in (dict(minimum_revision=True),dict(minimum_revision=-1),dict(context=''),dict(run_id=[])):
            args=dict(self.scope,minimum_revision=1);args.update(change)
            with self.subTest(change=change):
                self.assertEqual(store.create_store(self.path,**args).status,'INVALID_INITIAL_STATE')

    def test_invalid_anchor(self):
        for anchor in (None,True,'bad','G'*64):
            with self.subTest(anchor=anchor):
                self.assertEqual(self.consume(expected_state_digest=anchor).status,'INVALID_STATE_ANCHOR')
                self.assertEqual(store.verify_store(self.path,expected_state_digest=anchor).status,'INVALID_STATE_ANCHOR')

    def test_scope_mismatch_is_rejected(self):
        self.assertEqual(self.consume(run_id='run:other').status,'STORE_SCOPE_MISMATCH')
        self.assertEqual(self.state()['generation'],0)

    def test_legacy_validation_failure_does_not_commit(self):
        self.assertEqual(self.consume(expected_digest='0'*64).status,'CHAIN_DIGEST_MISMATCH')
        self.assertEqual(store.verify_store(self.path,expected_state_digest=self.initial.state_digest),self.initial)

    def test_locked_competitor_cannot_admit(self):
        observed=[]
        def compete(phase):
            if phase=='before_write':
                observed.append(self.consume().status)
        with patch.object(store,'_checkpoint',side_effect=compete):
            self.assertEqual(self.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(observed,['STORE_BUSY'])
        self.assertEqual(self.consume().status,'STATE_ANCHOR_MISMATCH')

    def test_interruption_before_write_rolls_back(self):
        self.check_interruption('before_write')

    def test_interruption_after_write_rolls_back(self):
        self.check_interruption('after_write')

    def check_interruption(self, wanted):
        def interrupt(phase):
            if phase==wanted:
                raise store.SimulatedInterruption()
        with patch.object(store,'_checkpoint',side_effect=interrupt):
            self.assertEqual(self.consume().status,'INTERRUPTED_ROLLED_BACK')
        self.assertEqual(store.verify_store(self.path,expected_state_digest=self.initial.state_digest),self.initial)
        self.assertEqual(self.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')

    def test_lost_acknowledgment_after_commit_fails_closed(self):
        def interrupt(phase):
            if phase=='after_commit':
                raise store.SimulatedInterruption()
        with patch.object(store,'_checkpoint',side_effect=interrupt):
            result=self.consume()
        self.assertEqual(result.status,'COMMIT_OUTCOME_UNKNOWN')
        self.assertEqual(result.state_digest,'')
        self.assertEqual(self.state()['consumed'],[self.pin])
        self.assertEqual(self.consume().status,'STATE_ANCHOR_MISMATCH')

    def crash_child(self, phase):
        segment=self.segments[0]
        fixture=dict(blob=base64.b64encode(segment.records[0].blob).decode('ascii'),
                     sha=segment.records[0].sha256,
                     receipts=[(r.reference_id,r.classification) for r in segment.receipts],
                     references=segment.registry.reference_ids,namespace=segment.registry.namespace,
                     tip=segment.expected_tip,pin=self.pin)
        script='''import os,sys,json,base64
from tools import f3_int109_offline_consumption_store as store
from tools.f3_int98_policy_bundle_registry import PolicyBundleRecord,PolicyEvidenceRegistry,PolicyEvidenceReceipt
from tools.f3_int101_cross_batch_audit import AuditSegment
from tools.f3_int107_typed_batch_chain import ChainBatch
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry
f=json.loads(sys.stdin.read())
segment=AuditSegment((PolicyBundleRecord(base64.b64decode(f['blob']),f['sha']),),
                    tuple(PolicyEvidenceReceipt(*r) for r in f['receipts']),
                    PolicyEvidenceRegistry(tuple(f['references']),f['namespace']),f['tip'])
def stop(p):
    if p==sys.argv[3]: os._exit(73)
store._checkpoint=stop
store.consume_chain(sys.argv[1],(segment,),expected_state_digest=sys.argv[2],expected_digest=f['pin'],
                    batches=(ChainBatch((TypedBatchEntry('audit','x'),),1),),
                    context='audit:A',purpose='review',run_id='run:1')
os._exit(74)
'''
        result=subprocess.run([sys.executable,'-B','-c',script,str(self.path),self.initial.state_digest,phase],
                               input=json.dumps(fixture).encode('ascii'),
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        self.assertEqual(result.returncode,73,result.stderr.decode(errors='replace'))

    def test_process_death_after_write_recovers_old_state(self):
        self.crash_child('after_write')
        self.assertEqual(store.verify_store(self.path,expected_state_digest=self.initial.state_digest),self.initial)
        self.assertEqual(self.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')

    def test_process_death_after_commit_preserves_consumption(self):
        self.crash_child('after_commit')
        self.assertEqual(self.consume().status,'STATE_ANCHOR_MISMATCH')
        self.assertEqual(self.state()['consumed'],[self.pin])

    def test_unparseable_record_rejected(self):
        self.replace_state({},raw=b'{"broken":')
        self.assertEqual(self.consume().status,'CORRUPT_STORE')

    def test_deeply_nested_record_rejected(self):
        self.replace_state({},raw=b'['*2000+b'0'+b']'*2000)
        self.assertEqual(self.consume().status,'CORRUPT_STORE')

    def test_parseable_record_tamper_rejected_by_anchor(self):
        result=self.consume()
        state=self.state();state.update(generation=0,next_revision=1,consumed=[])
        self.replace_state(state)
        self.assertEqual(self.consume(expected_state_digest=result.state_digest).status,'STATE_ANCHOR_MISMATCH')

    def test_corrupt_database_rejected_without_reset(self):
        self.path.write_bytes(b'not a sqlite database')
        self.assertEqual(self.consume().status,'STORE_ERROR')
        self.assertEqual(self.path.read_bytes(),b'not a sqlite database')

    def test_invalid_schema_and_canonical_encoding(self):
        initial=self.state()
        variants=[dict(initial,generation=True),dict(initial,next_revision=True),
                  dict(initial,consumed=['bad']),dict(initial,extra=1),
                  dict(initial,version=2)]
        for state in variants:
            self.replace_state(state)
            self.assertEqual(self.consume().status,'CORRUPT_STORE')
        self.replace_state(initial,raw=json.dumps(initial,indent=2).encode('ascii'))
        self.assertEqual(self.consume().status,'CORRUPT_STORE')

    def test_empty_oversized_and_duplicate_rows_rejected(self):
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('UPDATE state SET payload=?',(b'x'*(store.MAX_BYTES+1),))
        self.assertEqual(self.consume().status,'CORRUPT_STORE')
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('DELETE FROM state')
        self.assertEqual(self.consume().status,'CORRUPT_STORE')
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('DROP TABLE state')
            conn.execute('CREATE TABLE state(id INTEGER,payload BLOB)')
            conn.executemany('INSERT INTO state VALUES(1,?)',[(b'{}',),(b'{}',)])
        self.assertEqual(self.consume().status,'CORRUPT_STORE')

    def test_revision_domain_exhaustion(self):
        state=self.state();state['next_revision']=2147483648
        anchor=self.replace_state(state)
        self.assertEqual(self.consume(expected_state_digest=anchor).status,'REVISION_DOMAIN_EXHAUSTED')

    def test_history_capacity_does_not_drop_entries(self):
        state=self.state()
        state.update(consumed=[format(i,'064x') for i in range(4096)],generation=4096)
        anchor=self.replace_state(state)
        self.assertEqual(self.consume(expected_state_digest=anchor).status,'HISTORY_CAPACITY_EXHAUSTED')
        self.assertEqual(len(self.state()['consumed']),4096)

    def test_locks_in_success_and_rejection(self):
        for result in (self.initial,self.consume(),self.consume(expected_state_digest=None)):
            self.assertEqual(result.f3,'OPEN');self.assertFalse(store.safe_to_promote(result))
            for key in ('orders_allowed','live_certified','flow_complete','f3_resolved',
                        'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(result,key),False)


if __name__=='__main__':
    unittest.main()
