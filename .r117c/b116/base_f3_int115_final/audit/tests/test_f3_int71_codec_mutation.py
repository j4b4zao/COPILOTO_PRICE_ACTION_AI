import unittest
from test_f3_int53_interleaving import recovery
from tools.f3_int54_schedule_divergence_simulator import request
from tools.f3_int68_crash_witness_simulator import find_crash_witness
from tools.f3_int69_crash_minimizer_simulator import minimize_crash_witness
from tools.f3_int70_crash_witness_codec import encode_witness
from tools.f3_int71_codec_mutation_simulator import audit_mutations, corpus, safe_to_promote


class MutationCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        requests=(request('a',**recovery(6)),request('b',**recovery(5)))
        cls.blob=encode_witness(minimize_crash_witness(find_crash_witness(requests).witness).witness)
    def test_full_corpus(self):
        r=audit_mutations(self.blob); self.assertTrue(r.complete); self.assertEqual(r.failures,())
        self.assertEqual(r.status,'CODEC_MUTATION_CORPUS_FIXTURE_UNAUTHENTICATED')
        self.assertEqual(sum(actual for _,_,actual in r.observations),2)
        self.assertGreaterEqual(r.checked,40)
    def test_bound_is_not_full_coverage(self):
        r=audit_mutations(self.blob,max_cases=1); self.assertFalse(r.complete)
        self.assertEqual(r.status,'CODEC_MUTATION_LIMIT_REACHED'); self.assertEqual(r.checked,1)
    def test_labels_unique_and_deterministic(self):
        cases=corpus(self.blob); self.assertEqual(len({c[0] for c in cases}),len(cases)); self.assertEqual(cases,corpus(self.blob))
    def test_bad_baseline(self): self.assertEqual(audit_mutations(b'{}').status,'INVALID_MUTATION_BASELINE')
    def test_bad_bound(self):
        for bound in (False,0,129): self.assertEqual(audit_mutations(self.blob,max_cases=bound).status,'INVALID_MUTATION_BOUND')
    def test_flags(self):
        r=audit_mutations(self.blob); self.assertEqual(r.f3,'OPEN'); self.assertFalse(safe_to_promote(r))
        for k in ('orders_allowed','live_certified','flow_complete','f3_resolved','native_prototype_authorized','strict_deadline_guaranteed','authenticated_witness_verified'):
            self.assertIs(getattr(r,k),False)
