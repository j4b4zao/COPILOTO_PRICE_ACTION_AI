import unittest
from dataclasses import replace
import test_f3_int104_domain_scoped_commitment as prior
from tools.f3_int105_typed_identity_envelope import typed_envelope, safe_to_promote

class TypedIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.ScopedCommitmentTests.setUpClass()
        cls.segment = prior.ScopedCommitmentTests.segment

    def call(self, **changes):
        kw=dict(context="audit:fixture/A",purpose="evidence-review",run_id="run:1",revision=1,
                kind="audit",subject="receipt:1")
        kw.update(changes)
        return typed_envelope((self.segment,), **kw)

    def test_success(self): self.assertEqual(self.call().status,"TYPED_FIXTURE_UNAUTHENTICATED")
    def test_determinism(self): self.assertEqual(self.call(),self.call())
    def test_kind_separation(self): self.assertNotEqual(self.call().digest,self.call(kind="report").digest)
    def test_subject_separation(self): self.assertNotEqual(self.call().digest,self.call(subject="receipt:2").digest)
    def test_context_separation(self): self.assertNotEqual(self.call().digest,self.call(context="audit:fixture/B").digest)
    def test_role_swap_separation(self): self.assertNotEqual(self.call(purpose="audit",subject="receipt").digest,self.call(purpose="receipt",subject="audit").digest)
    def test_replay_rejected(self): self.assertEqual(self.call(kind="replay",expected_digest=self.call().digest).status,"TYPED_DIGEST_MISMATCH")
    def test_expected_match(self): self.assertEqual(self.call(expected_digest=self.call().digest),self.call())
    def test_invalid_expected(self):
        for x in (True,42,"Z"*64,"no"):
            with self.subTest(x=x): self.assertEqual(self.call(expected_digest=x).status,"INVALID_EXPECTED_DIGEST")
    def test_invalid_kind(self):
        for x in ("AUDIT","unknown","",True,None,1,"a\u200bud it"):
            with self.subTest(x=x): self.assertEqual(self.call(kind=x).status,"INVALID_KIND")
    def test_invalid_subject(self):
        for x in ("", "é", "e\u0301", "abc\u200b", "x y", "x\ny", "a"*129, True, None, 3):
            with self.subTest(x=x): self.assertEqual(self.call(subject=x).status,"INVALID_SUBJECT")
    def test_parent_rejected(self): self.assertTrue(self.call(context="é").status.startswith("PARENT_REJECTED:"))
    def test_parent_tamper(self):
        r=typed_envelope((replace(self.segment,expected_tip="0"*64),),context="audit:A",purpose="test",run_id="run",revision=0,kind="audit",subject="receipt")
        self.assertTrue(r.status.startswith("PARENT_REJECTED:"))
    def test_immutable_input(self):
        before=self.segment; self.call(); self.assertEqual(before,self.segment)
    def test_locks(self):
        for r in (self.call(),self.call(kind="bad")):
            self.assertEqual(r.f3,"OPEN");self.assertFalse(safe_to_promote(r))
            for k in ("orders_allowed","live_certified","flow_complete","f3_resolved","native_prototype_authorized","strict_deadline_guaranteed","authenticated_witness_verified"):
                self.assertIs(getattr(r,k),False)

if __name__=="__main__": unittest.main()
