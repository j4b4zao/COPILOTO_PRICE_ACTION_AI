import unittest
from dataclasses import replace
import test_f3_int103_context_bound_transcript as prior_tests
from tools.f3_int104_domain_scoped_commitment import scope_transcript, safe_to_promote

class ScopedCommitmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior_tests.ContextBoundTests.setUpClass()
        cls.segment=prior_tests.ContextBoundTests.segment

    def scope(self, **overrides):
        params=dict(context='audit:fixture/A',purpose='evidence-review',run_id='run:1',revision=1)
        params.update(overrides)
        return scope_transcript((self.segment,),**params)

    def test_success(self):
        r=self.scope();self.assertEqual(r.status,'SCOPED_FIXTURE_UNAUTHENTICATED');self.assertEqual(len(r.digest),64)
    def test_determinism(self): self.assertEqual(self.scope(),self.scope())
    def test_purpose_separation(self): self.assertNotEqual(self.scope().digest,self.scope(purpose='reporting').digest)
    def test_run_separation(self): self.assertNotEqual(self.scope().digest,self.scope(run_id='run:2').digest)
    def test_revision_separation(self): self.assertNotEqual(self.scope().digest,self.scope(revision=2).digest)
    def test_context_separation(self): self.assertNotEqual(self.scope().digest,self.scope(context='audit:fixture/B').digest)
    def test_cross_scope_replay(self): self.assertEqual(self.scope(purpose='reporting',expected_digest=self.scope().digest).status,'SCOPED_DIGEST_MISMATCH')
    def test_expected_match(self): self.assertEqual(self.scope(expected_digest=self.scope().digest),self.scope())
    def test_expected_invalid(self):
        for value in (False,42,'xyz','Z'*64):
            with self.subTest(value=value):self.assertEqual(self.scope(expected_digest=value).status,'INVALID_EXPECTED_DIGEST')
    def test_purpose_invalid(self):
        for value in ('','a b','é','a\nb','a'*129,True,1,None):
            with self.subTest(value=value):self.assertEqual(self.scope(purpose=value).status,'INVALID_PURPOSE')
    def test_run_invalid(self):
        for value in ('','a b','é','a\nb','a'*129,True,1,None):
            with self.subTest(value=value):self.assertEqual(self.scope(run_id=value).status,'INVALID_RUN_ID')
    def test_revision_invalid(self):
        for value in (-1,True,False,1.0,'1',None,2147483648):
            with self.subTest(value=value):self.assertEqual(self.scope(revision=value).status,'INVALID_REVISION')
    def test_parent_invalid(self):self.assertTrue(self.scope(context='é').status.startswith('PARENT_REJECTED:'))
    def test_parent_tamper(self):
        result=scope_transcript((replace(self.segment,expected_tip='0'*64),),context='audit:A',purpose='test',run_id='run',revision=0)
        self.assertTrue(result.status.startswith('PARENT_REJECTED:'))
    def test_immutable_input(self):
        old=self.segment;self.scope();self.assertEqual(old,self.segment)
    def test_fail_closed_flags(self):
        for r in (self.scope(),self.scope(purpose='')):
            self.assertEqual(r.f3,'OPEN');self.assertFalse(safe_to_promote(r))
            for key in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
                self.assertIs(getattr(r,key),False)

if __name__=='__main__':unittest.main()
