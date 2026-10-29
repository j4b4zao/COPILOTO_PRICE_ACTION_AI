import unittest
from dataclasses import replace
import test_f3_int105_typed_identity_envelope as prior
from tools.f3_int106_typed_batch_manifest import TypedBatchEntry, build_typed_batch, safe_to_promote

class TypedBatchManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.TypedIdentityTests.setUpClass()
        cls.segment = prior.TypedIdentityTests.segment

    def call(self, **changes):
        args=dict(context="audit:fixture/A",purpose="evidence-review",run_id="run:1",revision=1,
                  entries=(TypedBatchEntry("audit","receipt:1"),TypedBatchEntry("report","receipt:2")))
        args.update(changes)
        return build_typed_batch((self.segment,), **args)

    def test_success(self): self.assertEqual(self.call().status,"BATCH_FIXTURE_UNAUTHENTICATED")
    def test_deterministic(self): self.assertEqual(self.call(),self.call())
    def test_expected_match(self): self.assertEqual(self.call(expected_digest=self.call().digest),self.call())
    def test_expected_mismatch(self): self.assertEqual(self.call(expected_digest="0"*64).status,"BATCH_DIGEST_MISMATCH")
    def test_invalid_expected(self):
        for value in (True,42,"Z"*64,"bad"):
            with self.subTest(value=value): self.assertEqual(self.call(expected_digest=value).status,"INVALID_EXPECTED_DIGEST")
    def test_order_matters(self):
        a=(TypedBatchEntry("audit","receipt:1"),TypedBatchEntry("report","receipt:2"))
        self.assertNotEqual(self.call(entries=a).digest,self.call(entries=a[::-1]).digest)
    def test_type_matters(self): self.assertNotEqual(self.call().digest,self.call(entries=(TypedBatchEntry("replay","receipt:1"),TypedBatchEntry("report","receipt:2"))).digest)
    def test_scope_matters(self): self.assertNotEqual(self.call().digest,self.call(run_id="run:2").digest)
    def test_same_subject_different_type_allowed(self): self.assertEqual(self.call(entries=(TypedBatchEntry("audit","x"),TypedBatchEntry("report","x"))).status,"BATCH_FIXTURE_UNAUTHENTICATED")
    def test_duplicate_identity_rejected(self): self.assertEqual(self.call(entries=(TypedBatchEntry("audit","x"),TypedBatchEntry("audit","x"))).status,"DUPLICATE_TYPED_IDENTITY")
    def test_invalid_entries(self):
        for value in ([],(),[TypedBatchEntry("audit","x")],("audit",),tuple(TypedBatchEntry("audit",str(i)) for i in range(33)),True,None):
            with self.subTest(value=str(value)[:30]): self.assertEqual(self.call(entries=value).status,"INVALID_ENTRIES")
    def test_invalid_kind_and_unicode(self):
        self.assertEqual(self.call(entries=(TypedBatchEntry("wrong","x"),)).status,"ENTRY_REJECTED:INVALID_KIND")
        self.assertEqual(self.call(entries=(TypedBatchEntry("audit","e\u0301"),)).status,"ENTRY_REJECTED:INVALID_SUBJECT")
    def test_parent_tamper(self):
        result=build_typed_batch((replace(self.segment,expected_tip="0"*64),),context="audit:A",purpose="test",run_id="run",revision=0,entries=(TypedBatchEntry("audit","x"),))
        self.assertTrue(result.status.startswith("ENTRY_REJECTED:PARENT_REJECTED:"))
    def test_immutable(self):
        before=self.segment; entries=(TypedBatchEntry("audit","x"),)
        self.call(entries=entries);self.assertEqual(before,self.segment);self.assertEqual(entries,(TypedBatchEntry("audit","x"),))
    def test_locks(self):
        for result in (self.call(),self.call(entries=())):
            self.assertEqual(result.f3,"OPEN");self.assertFalse(safe_to_promote(result))
            for k in ("orders_allowed","live_certified","flow_complete","f3_resolved","native_prototype_authorized","strict_deadline_guaranteed","authenticated_witness_verified"):
                self.assertIs(getattr(result,k),False)

if __name__=="__main__": unittest.main()
