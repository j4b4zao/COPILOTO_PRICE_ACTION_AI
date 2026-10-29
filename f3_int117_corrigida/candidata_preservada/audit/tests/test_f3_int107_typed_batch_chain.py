import unittest
from dataclasses import replace
import test_f3_int105_typed_identity_envelope as prior
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry
from tools.f3_int107_typed_batch_chain import ChainBatch, build_typed_chain, safe_to_promote

class TypedBatchChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.TypedIdentityTests.setUpClass()
        cls.segment = prior.TypedIdentityTests.segment
    def call(self, **changes):
        args=dict(context="audit:fixture/A",purpose="evidence-review",run_id="run:1",
                  batches=(ChainBatch((TypedBatchEntry("audit","x"),),1),
                           ChainBatch((TypedBatchEntry("report","y"),),2)))
        args.update(changes)
        return build_typed_chain((self.segment,),**args)
    def test_success(self): self.assertEqual(self.call().status,"CHAIN_FIXTURE_UNAUTHENTICATED")
    def test_determinism(self): self.assertEqual(self.call(),self.call())
    def test_expected_digest(self): self.assertEqual(self.call(expected_digest=self.call().digest),self.call())
    def test_wrong_chain_digest(self): self.assertEqual(self.call(expected_digest="0"*64).status,"CHAIN_DIGEST_MISMATCH")
    def test_invalid_digest(self):
        for x in (True,"bad", "G"*64):
            with self.subTest(x=x): self.assertEqual(self.call(expected_digest=x).status,"INVALID_EXPECTED_DIGEST")
    def test_expected_batch_digests(self): self.assertEqual(self.call(expected_batch_digests=self.call().batch_digests),self.call())
    def test_tampered_expected_batch(self): self.assertEqual(self.call(expected_batch_digests=("0"*64,self.call().batch_digests[1])).status,"BATCH_DIGEST_MISMATCH")
    def test_invalid_expected_batch_digests(self):
        for x in ([],("0"*64,), (True,"0"*64),("G"*64,"0"*64)):
            with self.subTest(x=x): self.assertEqual(self.call(expected_batch_digests=x).status,"INVALID_EXPECTED_BATCH_DIGESTS")
    def test_order_swap(self):
        a=self.call().digest
        swapped=(ChainBatch((TypedBatchEntry("report","y"),),1),ChainBatch((TypedBatchEntry("audit","x"),),2))
        self.assertNotEqual(a,self.call(batches=swapped).digest)
    def test_revision_gap_allowed_and_bound(self):
        b=(ChainBatch((TypedBatchEntry("audit","x"),),1),ChainBatch((TypedBatchEntry("report","y"),),4))
        self.assertEqual(self.call(batches=b).status,"CHAIN_FIXTURE_UNAUTHENTICATED")
        self.assertNotEqual(self.call().digest,self.call(batches=b).digest)
    def test_revision_invalid(self):
        for x in (True,-1,"1",1.0):
            with self.subTest(x=x): self.assertEqual(self.call(batches=(ChainBatch((TypedBatchEntry("audit","x"),),x),)).status,"INVALID_REVISION_SEQUENCE")
    def test_revision_duplicate_or_descending(self):
        for x in (1,0):
            with self.subTest(x=x): self.assertEqual(self.call(batches=(ChainBatch((TypedBatchEntry("audit","x"),),1),ChainBatch((TypedBatchEntry("report","y"),),x))).status,"INVALID_REVISION_SEQUENCE")
    def test_invalid_batch_container(self):
        for x in ([],(),[ChainBatch((TypedBatchEntry("audit","x"),),1)],tuple(ChainBatch((TypedBatchEntry("audit",str(i)),),i) for i in range(17)),(1,)):
            with self.subTest(x=str(x)[:20]): self.assertEqual(self.call(batches=x).status,"INVALID_BATCHES")
    def test_invalid_child(self): self.assertEqual(self.call(batches=(ChainBatch((TypedBatchEntry("invalid","x"),),1),)).status,"BATCH_REJECTED:ENTRY_REJECTED:INVALID_KIND")
    def test_context_bound(self): self.assertNotEqual(self.call().digest,self.call(context="audit:fixture/B").digest)
    def test_run_bound(self): self.assertNotEqual(self.call().digest,self.call(run_id="run:2").digest)
    def test_reject_parent_tamper(self):
        result=build_typed_chain((replace(self.segment,expected_tip="0"*64),),context="audit:fixture/A",purpose="evidence-review",run_id="run:1",batches=(ChainBatch((TypedBatchEntry("audit","x"),),1),))
        self.assertTrue(result.status.startswith("BATCH_REJECTED:ENTRY_REJECTED:PARENT_REJECTED:"))
    def test_locks(self):
        for r in (self.call(),self.call(batches=())):
            self.assertEqual(r.f3,"OPEN");self.assertFalse(safe_to_promote(r))
            for k in ("orders_allowed","live_certified","flow_complete","f3_resolved","native_prototype_authorized","strict_deadline_guaranteed","authenticated_witness_verified"):
                self.assertIs(getattr(r,k),False)
if __name__=="__main__": unittest.main()
