from contextlib import closing
import base64
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
import test_f3_int109_offline_consumption_store as prior_tests
from tools import f3_int109_offline_consumption_store as old
from tools import f3_int110_confirmed_consumption as fixed


class ConfirmedConsumptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior_tests.ConsumptionStoreTests.setUpClass()

    def setUp(self):
        self.h = prior_tests.ConsumptionStoreTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def call(self, **changes):
        args = dict(self.h.scope, expected_state_digest=self.h.initial.state_digest,
                    expected_digest=self.h.pin, batches=self.h.batches)
        args.update(changes)
        return fixed.consume_chain_confirmed(self.h.path, self.h.segments, **args)

    def sql(self, command):
        with closing(sqlite3.connect(self.h.path)) as conn, conn:
            conn.execute(command)

    def assert_initial_state(self):
        self.assertEqual(old.verify_store(self.h.path,expected_state_digest=self.h.initial.state_digest),self.h.initial)

    def test_success_matches_legacy_result_exactly(self):
        copy=self.h.path.with_name('comparison.sqlite')
        copy.write_bytes(self.h.path.read_bytes())
        args=dict(self.h.scope,expected_state_digest=self.h.initial.state_digest,
                  expected_digest=self.h.pin,batches=self.h.batches)
        legacy=old.consume_chain(copy,self.h.segments,**args)
        result=self.call()
        self.assertEqual(result,legacy)
        self.assertEqual(old.verify_store(self.h.path,expected_state_digest=result.state_digest).status,'STORE_FIXTURE_UNAUTHENTICATED')

    def test_ignored_update_rejected(self):
        self.sql('CREATE TRIGGER discard BEFORE UPDATE ON state BEGIN SELECT RAISE(IGNORE); END')
        result=self.call()
        self.assertEqual(result.status,'STATE_WRITE_NOT_CONFIRMED')
        self.assertEqual(result.digest,'');self.assertEqual(result.state_digest,'')
        self.assert_initial_state()

    def test_reverted_update_rejected_even_with_rowcount_one(self):
        self.sql('CREATE TRIGGER undo AFTER UPDATE ON state BEGIN UPDATE state SET payload=OLD.payload WHERE id=1; END')
        self.assertEqual(self.call().status,'STATE_WRITE_NOT_CONFIRMED')
        self.assert_initial_state()

    def test_valid_but_wrong_floor_readback_rejected(self):
        state=self.h.state()
        state.update(generation=1,consumed=[self.h.pin],next_revision=1)
        raw=old._encode(state).hex()
        self.sql("CREATE TRIGGER wrong_floor AFTER UPDATE ON state BEGIN UPDATE state SET payload=X'"+raw+"' WHERE id=1; END")
        self.assertEqual(self.call().status,'STATE_WRITE_NOT_CONFIRMED')
        self.assert_initial_state()

    def test_corrupt_readback_rolls_back(self):
        self.sql("CREATE TRIGGER break_record AFTER UPDATE ON state BEGIN UPDATE state SET payload=X'7b' WHERE id=1; END")
        self.assertEqual(self.call().status,'CORRUPT_STORE')
        self.assert_initial_state()

    def test_benign_trigger_allowed(self):
        self.sql('CREATE TABLE audit_log(message TEXT)')
        self.sql("CREATE TRIGGER log_update AFTER UPDATE ON state BEGIN INSERT INTO audit_log VALUES('consumed'); END")
        self.assertEqual(self.call().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        with closing(sqlite3.connect(self.h.path)) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM audit_log').fetchone()[0],1)

    def test_failed_confirmation_rolls_back_trigger_side_effects(self):
        self.sql('CREATE TABLE audit_log(message TEXT)')
        self.sql("CREATE TRIGGER discard BEFORE UPDATE ON state BEGIN INSERT INTO audit_log VALUES('attempt'); SELECT RAISE(IGNORE); END")
        self.assertEqual(self.call().status,'STATE_WRITE_NOT_CONFIRMED')
        with closing(sqlite3.connect(self.h.path)) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM audit_log').fetchone()[0],0)
        self.assert_initial_state()

    def test_clean_retry_after_removing_bad_trigger(self):
        self.sql('CREATE TRIGGER discard BEFORE UPDATE ON state BEGIN SELECT RAISE(IGNORE); END')
        self.assertEqual(self.call().status,'STATE_WRITE_NOT_CONFIRMED')
        self.sql('DROP TRIGGER discard')
        self.assertEqual(self.call().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.h.state()['generation'],1)

    def test_normal_continuity_advances_floor(self):
        first=self.call()
        second=self.call(expected_state_digest=first.state_digest,expected_digest=self.h.next_pin,batches=self.h.next_batches)
        self.assertEqual(second.status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.h.state()['next_revision'],3)

    def test_stale_anchor_rejected(self):
        self.call()
        self.assertEqual(self.call().status,'STATE_ANCHOR_MISMATCH')

    def test_competing_connection_is_rejected(self):
        observed=[]
        def compete(phase):
            if phase=='before_write': observed.append(self.call().status)
        with patch.object(fixed,'_checkpoint',side_effect=compete):
            self.assertEqual(self.call().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(observed,['STORE_BUSY'])

    def test_lost_ack_is_still_unknown_and_never_reconsumed(self):
        def stop(phase):
            if phase=='after_commit': raise old.SimulatedInterruption()
        with patch.object(fixed,'_checkpoint',side_effect=stop):
            self.assertEqual(self.call().status,'COMMIT_OUTCOME_UNKNOWN')
        self.assertEqual(self.call().status,'STATE_ANCHOR_MISMATCH')
        self.assertEqual(self.h.state()['generation'],1)

    def test_interruption_before_and_after_write_rolls_back(self):
        for wanted in ('before_write','after_write'):
            def stop(phase):
                if phase==wanted: raise old.SimulatedInterruption()
            with self.subTest(phase=wanted),patch.object(fixed,'_checkpoint',side_effect=stop):
                self.assertEqual(self.call().status,'INTERRUPTED_ROLLED_BACK')
            self.assert_initial_state()

    def crash_child(self, phase):
        segment=self.h.segments[0]
        fixture=dict(blob=base64.b64encode(segment.records[0].blob).decode('ascii'),sha=segment.records[0].sha256,
                     receipts=[(r.reference_id,r.classification) for r in segment.receipts],
                     references=segment.registry.reference_ids,namespace=segment.registry.namespace,
                     tip=segment.expected_tip,pin=self.h.pin)
        script='''import os,sys,json,base64
from tools import f3_int110_confirmed_consumption as fixed
from tools.f3_int98_policy_bundle_registry import PolicyBundleRecord,PolicyEvidenceRegistry,PolicyEvidenceReceipt
from tools.f3_int101_cross_batch_audit import AuditSegment
from tools.f3_int107_typed_batch_chain import ChainBatch
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry
f=json.loads(sys.stdin.read())
segment=AuditSegment((PolicyBundleRecord(base64.b64decode(f['blob']),f['sha']),),tuple(PolicyEvidenceReceipt(*r) for r in f['receipts']),PolicyEvidenceRegistry(tuple(f['references']),f['namespace']),f['tip'])
def stop(p):
    if p==sys.argv[3]: os._exit(73)
fixed._checkpoint=stop
fixed.consume_chain_confirmed(sys.argv[1],(segment,),expected_state_digest=sys.argv[2],expected_digest=f['pin'],batches=(ChainBatch((TypedBatchEntry('audit','x'),),1),),context='audit:A',purpose='review',run_id='run:1')
os._exit(74)
'''
        child=subprocess.run([sys.executable,'-B','-c',script,str(self.h.path),self.h.initial.state_digest,phase],
                             input=json.dumps(fixture).encode('ascii'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
        self.assertEqual(child.returncode,73,child.stderr.decode(errors='replace'))

    def test_process_restart_before_commit_recovers(self):
        self.crash_child('after_write')
        self.assert_initial_state()
        self.assertEqual(self.call().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')

    def test_process_restart_after_commit_preserves_consumption(self):
        self.crash_child('after_commit')
        self.assertEqual(self.call().status,'STATE_ANCHOR_MISMATCH')
        self.assertEqual(self.h.state()['consumed'],[self.h.pin])

    def test_joint_rollback_remains_a_limit(self):
        backup=self.h.path.read_bytes()
        self.call()
        self.h.path.write_bytes(backup)
        self.assertEqual(self.call().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')

    def test_divergent_history_is_rejected(self):
        state=self.h.state();state['next_revision']=2
        self.h.replace_state(state)
        self.assertEqual(self.call().status,'STATE_ANCHOR_MISMATCH')

    def test_invalid_inputs_do_not_change_store(self):
        for change,status in ((dict(expected_state_digest=None),'INVALID_STATE_ANCHOR'),
                              (dict(batches=()),'INVALID_BATCHES'),
                              (dict(expected_digest='0'*64),'CHAIN_DIGEST_MISMATCH')):
            with self.subTest(status=status): self.assertEqual(self.call(**change).status,status)
            self.assert_initial_state()

    def test_locks_on_success_and_rejection(self):
        for result in (self.call(),self.call(expected_state_digest=None)):
            self.assertEqual(result.f3,'OPEN');self.assertFalse(fixed.safe_to_promote(result))
            for key in ('orders_allowed','live_certified','flow_complete','f3_resolved',
                        'native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(result,key),False)


if __name__=='__main__': unittest.main()
