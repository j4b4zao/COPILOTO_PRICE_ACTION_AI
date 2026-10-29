import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import test_f3_int109_offline_consumption_store as old
from tools import f3_int109_offline_consumption_store as store
from tools import f3_int111_adversarial_reconciliation as audit

class AdversarialReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old.ConsumptionStoreTests.setUpClass()
        cls.fixture=old.ConsumptionStoreTests

    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state.sqlite'
        self.scope=self.fixture.scope
        initial=store.create_store(self.path,**self.scope,minimum_revision=1)
        self.before=initial.state_digest
        self.after=store.consume_chain(self.path,self.fixture.segments,
            expected_state_digest=self.before,expected_digest=self.fixture.pin,
            batches=self.fixture.batches,**self.scope).state_digest
        self.kw=dict(before_state_digest=self.before,after_state_digest=self.after,
            expected_chain_digest=self.fixture.pin,**self.scope)

    def check(self, **overrides):
        kw=dict(self.kw,independent_pins_attested=True,stable_snapshot_attested=True)
        kw.update(overrides)
        return audit.assess_reconciliation(self.path,**kw)

    def test_observation_remains_unauthenticated(self):
        result=self.check()
        self.assertEqual(result.status,'OBSERVATION_ONLY_UNAUTHENTICATED')
        self.assertEqual(result.observed_status,'COMMITTED_OBSERVED_UNAUTHENTICATED')

    def test_no_independent_pins(self):
        self.assertEqual(self.check(independent_pins_attested=False).status,'PIN_INDEPENDENCE_UNPROVEN')

    def test_no_stable_snapshot(self):
        self.assertEqual(self.check(stable_snapshot_attested=False).status,'SNAPSHOT_STABILITY_UNPROVEN')

    def test_nonboolean_attestation(self):
        for value in (1, None, 'true'):
            with self.subTest(value=value):
                self.assertEqual(self.check(independent_pins_attested=value).status,'INVALID_AUDIT_CLAIM')

    def test_invalid_pin(self):
        self.assertEqual(self.check(after_state_digest='bad').status,'INVALID_AUDIT_PIN')

    def test_joint_rollback_with_replaced_pins_is_undetectable(self):
        self.path.unlink()
        store.create_store(self.path,**self.scope,minimum_revision=1)
        result=self.check()
        self.assertEqual(result.observed_status,'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')
        self.assertEqual(result.status,'OBSERVATION_ONLY_UNAUTHENTICATED')
        self.assertEqual(self.check(independent_pins_attested=False).status,'PIN_INDEPENDENCE_UNPROVEN')

    def test_old_pin_with_rolled_back_store_unresolved(self):
        self.path.unlink()
        store.create_store(self.path,**self.scope,minimum_revision=1)
        self.assertEqual(self.check(before_state_digest='0'*64).status,'FAIL_CLOSED')

    def test_missing_store_fails_closed(self):
        self.path.unlink()
        self.assertEqual(self.check().status,'FAIL_CLOSED')

    def test_corrupt_store_fails_closed(self):
        self.path.write_bytes(b'not sqlite')
        self.assertEqual(self.check().status,'FAIL_CLOSED')

    def test_wrong_scope_fails_closed(self):
        self.assertEqual(self.check(run_id='other').status,'FAIL_CLOSED')

    def test_concurrent_change_at_observation_is_unresolved(self):
        with patch('tools.f3_int111_adversarial_reconciliation.reconcile_consumption') as mock:
            from tools.f3_int110_offline_reconciliation import ReconciliationResult
            mock.return_value=ReconciliationResult('RECONCILIATION_UNRESOLVED')
            self.assertEqual(self.check().status,'FAIL_CLOSED')

    def test_no_authority_on_all_paths(self):
        for result in (self.check(),self.check(independent_pins_attested=False),
                       self.check(after_state_digest='bad'),self.check(run_id='other')):
            for name in ('orders_allowed','live_certified','flow_complete','f3_resolved',
                         'native_prototype_authorized','strict_deadline_guaranteed',
                         'authenticated_witness_verified'):
                self.assertIs(getattr(result,name),False)
            self.assertFalse(audit.safe_to_promote(result))

if __name__=='__main__':unittest.main()
