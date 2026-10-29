"""Pre-correction scenarios against unchanged INT-109; explicit classifications."""
from contextlib import closing
import sqlite3
import unittest
from unittest.mock import patch
from pathlib import Path
import test_f3_int109_offline_consumption_store as prior
from tools import f3_int109_offline_consumption_store as store


class BeforeContinuityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ConsumptionStoreTests.setUpClass()

    def setUp(self):
        self.h=prior.ConsumptionStoreTests()
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    def test_A_joint_rollback_accepts_again_architectural_limit(self):
        old=self.h.path.read_bytes()
        self.assertEqual(self.h.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.h.path.write_bytes(old)
        self.assertEqual(self.h.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')

    def test_B_lost_acknowledgment_fails_closed_architectural_limit(self):
        def stop(phase):
            if phase=='after_commit': raise store.SimulatedInterruption()
        with patch.object(store,'_checkpoint',side_effect=stop):
            self.assertEqual(self.h.consume().status,'COMMIT_OUTCOME_UNKNOWN')
        self.assertEqual(self.h.state()['consumed'],[self.h.pin])
        self.assertEqual(self.h.consume().status,'STATE_ANCHOR_MISMATCH')

    def test_C_process_restart_rolls_back_existing_protection(self):
        self.h.crash_child('after_write')
        self.assertEqual(store.verify_store(self.h.path,expected_state_digest=self.h.initial.state_digest),self.h.initial)

    def test_D_stale_anchor_rejected_existing_protection(self):
        self.h.consume()
        self.assertEqual(self.h.consume().status,'STATE_ANCHOR_MISMATCH')

    def test_E_same_database_competitor_blocked_existing_protection(self):
        observed=[]
        def compete(phase):
            if phase=='before_write': observed.append(self.h.consume().status)
        with patch.object(store,'_checkpoint',side_effect=compete):
            self.assertEqual(self.h.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(observed,['STORE_BUSY'])

    def test_E_cloned_databases_both_consume_external_fencing_required(self):
        other=self.h.path.with_name('clone.sqlite')
        other.write_bytes(self.h.path.read_bytes())
        args=dict(self.h.scope,expected_state_digest=self.h.initial.state_digest,
                  expected_digest=self.h.pin,batches=self.h.batches)
        self.assertEqual(self.h.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(store.consume_chain(other,self.h.segments,**args).status,'CONSUMED_FIXTURE_UNAUTHENTICATED')

    def test_F_history_divergence_rejected_existing_protection(self):
        state=self.h.state();state['next_revision']=2
        self.h.replace_state(state)
        self.assertEqual(self.h.consume().status,'STATE_ANCHOR_MISMATCH')

    def test_G_ignored_update_reports_success_real_defect(self):
        with closing(sqlite3.connect(self.h.path)) as conn, conn:
            conn.execute('CREATE TRIGGER discard BEFORE UPDATE ON state BEGIN SELECT RAISE(IGNORE); END')
        first=self.h.consume()
        self.assertEqual(first.status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.h.state()['consumed'],[])
        self.assertEqual(store.verify_store(self.h.path,expected_state_digest=first.state_digest).status,'STATE_ANCHOR_MISMATCH')
        self.assertEqual(self.h.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')

    def test_H_reverted_update_reports_success_real_defect(self):
        with closing(sqlite3.connect(self.h.path)) as conn, conn:
            conn.execute('CREATE TRIGGER undo AFTER UPDATE ON state BEGIN UPDATE state SET payload=OLD.payload WHERE id=1; END')
        self.assertEqual(self.h.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(self.h.state()['generation'],0)
        self.assertEqual(self.h.state()['consumed'],[])
        self.assertEqual(self.h.consume().status,'CONSUMED_FIXTURE_UNAUTHENTICATED')


if __name__=='__main__': unittest.main(verbosity=2)
