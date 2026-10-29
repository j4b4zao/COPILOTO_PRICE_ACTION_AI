import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import test_f3_int109_offline_consumption_store as old
from tools import f3_int109_offline_consumption_store as store
from tools import f3_int110_offline_reconciliation as recon

class OfflineReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old.ConsumptionStoreTests.setUpClass()
        cls.source = old.ConsumptionStoreTests

    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'ledger.sqlite'
        self.scope=self.source.scope
        self.initial=store.create_store(self.path,**self.scope,minimum_revision=1)
        self.args=dict(self.scope,expected_chain_digest=self.source.pin,
                       before_state_digest=self.initial.state_digest)
        self.after=self.consume()
        self.args['after_state_digest']=self.after.state_digest

    def consume(self):
        return store.consume_chain(self.path,self.source.segments,
                                   expected_state_digest=self.initial.state_digest,
                                   expected_digest=self.source.pin,
                                   batches=self.source.batches,**self.scope)

    def inquiry(self,**kw):
        args=dict(self.args);args.update(kw)
        return recon.reconcile_consumption(self.path,**args)

    def test_committed_observed(self):
        r=self.inquiry();self.assertEqual(r.status,'COMMITTED_OBSERVED_UNAUTHENTICATED')
        self.assertEqual(r.digest,self.source.pin)
    def test_before_observed(self):
        self.path.unlink()
        self.initial=store.create_store(self.path,**self.scope,minimum_revision=1)
        self.assertEqual(self.inquiry().status,'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')
    def test_stale_after_pin(self):
        self.assertEqual(self.inquiry(after_state_digest='0'*64).status,'RECONCILIATION_UNRESOLVED')
    def test_wrong_chain_pin(self):
        self.assertEqual(self.inquiry(expected_chain_digest='0'*64).status,'RECONCILIATION_UNRESOLVED')
    def test_wrong_scope(self):
        self.assertEqual(self.inquiry(run_id='other').status,'STORE_SCOPE_MISMATCH')
    def test_equal_pins(self):
        self.assertEqual(self.inquiry(after_state_digest=self.initial.state_digest).status,'INVALID_RECONCILIATION_PIN')
    def test_invalid_pins(self):
        for k in ('before_state_digest','after_state_digest','expected_chain_digest'):
            with self.subTest(k=k):self.assertEqual(self.inquiry(**{k:'bad'}).status,'INVALID_RECONCILIATION_PIN')
    def test_missing_store(self):
        self.path.unlink();self.assertEqual(self.inquiry().status,'STORE_ERROR')
    def test_corrupt_store(self):
        self.path.write_bytes(b'garbage');self.assertIn(self.inquiry().status,('CORRUPT_STORE','STORE_ERROR'))
    def test_joint_rollback_limit(self):
        self.path.unlink();store.create_store(self.path,**self.scope,minimum_revision=1)
        # The old independently retained after pin rejects this rollback.
        self.assertEqual(self.inquiry(before_state_digest='0'*64).status,'RECONCILIATION_UNRESOLVED')
        # If an attacker also replaces the trusted pins, the old state is accepted.
        self.assertEqual(self.inquiry().status,'NOT_COMMITTED_OBSERVED_UNAUTHENTICATED')
    def test_no_operational_authorization(self):
        r=self.inquiry();self.assertFalse(recon.safe_to_promote(r))
        for key in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertFalse(getattr(r,key))

if __name__=='__main__':unittest.main()
