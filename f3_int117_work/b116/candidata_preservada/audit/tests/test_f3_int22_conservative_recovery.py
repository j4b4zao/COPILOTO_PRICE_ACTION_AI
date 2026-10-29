"""F3-INT-22 regressions. Prior INT20/21 tests are not edited."""
from dataclasses import asdict, replace
import importlib.util
from pathlib import Path
import sys
import unittest

root = Path(__file__).resolve().parents[1]
if 'int21_support' not in sys.modules:
    spec = importlib.util.spec_from_file_location('int21_support', root / 'tools/f3_int21_adversarial_support.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
a = sys.modules['int21_support']
m = a.m


class ConservativeRepairs(unittest.TestCase):
    def setUp(self):
        self.h = a.Harness()

    def tearDown(self):
        self.h.check()

    def positive_parents(self):
        return tuple(e.evidence_id for e in self.h.r.active() if e.fact.obligation in m.BASE)

    def renew(self, negative=None, source='independent', include_negative=True):
        h = self.h
        self.assertTrue(h.reconcile())
        parents = self.positive_parents()
        if negative is not None and include_negative:
            parents += (negative.evidence_id,)
        j = h.empty(parents=parents, source=source)
        h.release(j, source=source)
        ticket = h.r.qualify(h.lease)
        self.assertIsNotNone(ticket)
        self.assertTrue(h.r.close(ticket))
        return j

    def conflict(self, kind):
        for negative_first in (False, True):
            h = a.Harness()
            self.h = h
            if negative_first:
                h.put(a.conflicting_fact(h, kind), source='second')
            h.base()
            if not negative_first:
                h.put(a.conflicting_fact(h, kind), source='second')
            ev = h.r.evaluate()
            self.assertTrue(ev['X'])
            self.assertFalse(ev[kind])
            self.assertFalse(h.reconcile())
            self.assertFalse(ev.eligible)
            self.assertEqual(h.s.phase, m.Phase.CONTESTED)

    def test_N01_F_conflict_both_arrival_orders(self):
        self.conflict('F')

    def test_N02_P_conflict_both_arrival_orders(self):
        self.conflict('P')

    def test_N03_H_conflict_both_arrival_orders(self):
        self.conflict('H')

    def test_N04_equivalent_independent_proofs_do_not_conflict(self):
        h = self.h
        h.base()
        for e in tuple(h.s.evidence):
            if e.fact.obligation in ('F', 'P', 'H'):
                h.put(e.fact, source='second')
        self.assertFalse(h.r.evaluate()['X'])
        self.assertTrue(h.finish())

    def test_N05_negative_and_incomplete_observations_are_material(self):
        for kind in ('J', 'L'):
            for variant in ('negative', 'incomplete', 'unsettled'):
                h = a.Harness()
                self.h = h
                h.base()
                old = h.eligible()
                prior = h.s.material_revision
                fact = a.conflicting_fact(h, kind)
                if variant != 'negative':
                    fact = h.fact(kind, 'JOB' if kind == 'J' else 'RESOURCES',
                                  'EMPTY' if kind == 'J' else 'RELEASED',
                                  complete=variant != 'incomplete', settled=variant != 'unsettled')
                negative = h.put(fact, source='second')
                self.assertGreater(h.s.material_revision, prior)
                self.assertIn(negative.evidence_id, h.s.negative_dependencies)
                self.assertFalse(h.r.evaluate()['J'])
                self.assertFalse(h.r.evaluate()['L'])
                self.assertFalse(h.r.close(old))
                self.assertFalse(a.resume_close(h))

    def test_N06_nonempty_can_recover_only_with_fresh_causal_J_and_L(self):
        h = self.h
        h.base()
        h.eligible()
        negative = h.put(a.conflicting_fact(h, 'J'), source='second')
        self.renew(negative)
        self.assertIn(negative, h.s.evidence)

    def test_N07_failed_cleanup_recovers_with_sticky_failure(self):
        h = self.h
        h.base()
        h.eligible()
        negative = h.put(a.conflicting_fact(h, 'L'), source='second')
        self.assertIn('CLEANUP_FAILED', h.s.failures)
        self.renew(negative)
        self.assertIn('CLEANUP_FAILED', h.s.failures)
        self.assertIn('CREATION_UNCERTAIN', h.s.failures)
        self.assertFalse(h.s.aggregate_success)

    def test_N08_revision_stamp_without_causal_bridge_is_insufficient(self):
        h = self.h
        h.base()
        h.eligible()
        negative = h.put(a.conflicting_fact(h, 'J'), source='second')
        self.assertTrue(h.reconcile())
        j = h.empty()  # New challenge, but source/clock unrelated to the negative fact.
        h.release(j)
        self.assertFalse(h.r.evaluate()['J'])
        self.assertFalse(h.r.evaluate()['L'])
        self.assertIsNone(h.r.qualify(h.lease))
        self.renew(negative)

    def test_N09_trusted_same_source_sequence_is_causal(self):
        h = self.h
        h.base()
        h.eligible()
        negative = h.put(a.conflicting_fact(h, 'J'))
        self.renew(negative, include_negative=False)

    def test_N10_unverified_cross_clock_bridge_blocks(self):
        h = self.h
        h.base()
        h.eligible()
        negative = h.put(a.conflicting_fact(h, 'J'), source='second')
        self.assertTrue(h.reconcile())
        e = h.mint(h.fact('J', 'JOB', 'EMPTY'),
                   parents=self.positive_parents() + (negative.evidence_id,), attest={'clock_bridge': False})
        self.assertEqual(h.add(e), 'INCOMPARABLE_CLOCKS')
        self.assertFalse(a.resume_close(h))

    def test_N11_repeated_negative_dependencies_are_not_dropped(self):
        h = self.h
        h.base()
        h.eligible()
        first = h.put(a.conflicting_fact(h, 'J'), source='second')
        last = h.put(a.conflicting_fact(h, 'L'), source='second')
        self.renew(last)  # Last source sequence causally covers first as well.
        self.assertIn(first.evidence_id, h.s.negative_dependencies)
        self.assertIn(last.evidence_id, h.s.negative_dependencies)

    def test_N12_changed_base_dependency_invalidates_both_observations(self):
        h = self.h
        h.base()
        old = h.eligible()
        before = h.s.material_revision
        h.put(h.fact('P', h.target.key, 'EXIT', processes=(h.target,)), source='second')
        self.assertGreater(h.s.material_revision, before)
        self.assertFalse(h.r.evaluate()['J'])
        self.assertFalse(h.r.evaluate()['L'])
        self.assertFalse(h.r.close(old))
        self.assertTrue(h.finish())

    def test_N13_conflicts_require_independent_explicit_resolution(self):
        for kind in ('F', 'P', 'H'):
            h = a.Harness()
            self.h = h
            h.base()
            bad = h.put(a.conflicting_fact(h, kind), source='second')
            self.assertTrue(h.r.evaluate()['X'])
            h.put(h.fact('RESOLVE', 'conflict', 'EXPLAINED', invalidates=(bad.evidence_id,),
                         explanation='Independent synthetic proof excludes the contrary claim.'))
            self.assertFalse(h.r.evaluate()['X'])
            self.assertTrue(h.finish())
            self.assertIn(bad, h.s.evidence)
            self.assertIn(bad.evidence_id, h.s.invalidated)

    def test_N14_unknown_verdict_never_becomes_ignored_positive(self):
        for kind, subject in (('F', 'SESSION'), ('C', 'attempt'), ('U', 'NO_COMMIT'),
                              ('P', 'process'), ('H', 'history'), ('J', 'JOB'), ('L', 'RESOURCES')):
            h = a.Harness()
            self.h = h
            h.base()
            h.eligible()
            e = h.mint(h.fact(kind, subject, 'UNKNOWN_VERDICT'))
            self.assertEqual(h.add(e), 'UNSUPPORTED_VERDICT')
            self.assertTrue(h.r.evaluate()['X'])
            self.assertFalse(a.resume_close(h))

    def test_N15_postclosure_negative_contests_without_reactivation(self):
        for kind in ('J', 'L'):
            h = a.Harness()
            self.h = h
            h.base()
            self.assertTrue(h.finish())
            closure = h.s.closure
            h.put(a.conflicting_fact(h, kind), source='second')
            self.assertEqual(h.s.closure, closure)
            self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
            self.assertFalse(h.s.conclusion_trusted)
            self.assertTrue(h.s.contestations)

    def test_N16_forging_new_ticket_cannot_requalify_stale_proofs(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        h.put(a.conflicting_fact(h, 'J'), source='second')
        forged = replace(ticket, revision=h.s.revision, evidence_digest=h.s.evidence_digest)
        self.assertFalse(h.r.close(forged))
        self.assertTrue(h.reconcile())
        self.assertIsNone(h.r.qualify(h.lease))

    def test_N17_duplicate_failure_is_idempotent_and_history_stays(self):
        h = self.h
        h.base()
        h.eligible()
        bad = h.put(a.conflicting_fact(h, 'L'), source='second')
        state = h.s.revision, h.s.material_revision, h.s.failures, h.s.negative_dependencies
        self.assertEqual(h.add(bad), 'DUPLICATE_NO_EFFECT')
        self.assertEqual(state, (h.s.revision, h.s.material_revision, h.s.failures, h.s.negative_dependencies))
        self.renew(bad)

    def test_N18_original_identity_outcome_deadline_and_authority_preserved(self):
        for outcome in ('FAILED', 'CANCELLED', 'TIMEOUT', 'COMPLETED'):
            h = a.Harness(outcome=outcome)
            self.h = h
            original = asdict(h.s.original)
            h.base()
            h.eligible()
            bad = h.put(a.conflicting_fact(h, 'L'), source='second')
            self.renew(bad)
            self.assertEqual(asdict(h.s.original), original)
            self.assertFalse(h.s.aggregate_success)
            for operation in ('ACCEPT', 'CREATE', 'RESUME', 'EXECUTE'):
                self.assertFalse(h.r.prohibit(operation, h.lease))

    def test_N19_replay_of_already_reconciled_negative_is_no_new_effect(self):
        h = self.h
        h.base()
        h.eligible()
        bad = h.put(a.conflicting_fact(h, 'J'), source='second')
        self.assertTrue(h.reconcile())
        j = h.empty(parents=self.positive_parents() + (bad.evidence_id,))
        h.release(j)
        ticket = h.r.qualify(h.lease)
        self.assertIsNotNone(ticket)
        self.assertEqual(h.add(bad), 'DUPLICATE_NO_EFFECT')
        self.assertTrue(h.r.close(ticket))

    def test_N20_semantic_incomplete_H_conflicts_with_positive_H(self):
        h = self.h
        h.base()
        h.put(h.fact('H', h.target.key, 'CONTAINED', processes=(h.target,), complete=False), source='second')
        self.assertTrue(h.r.evaluate()['X'])
        self.assertFalse(h.r.evaluate()['H'])
        self.assertFalse(h.reconcile())

    def test_N21_generation_cannot_erase_unresolved_F_P_H_conflicts(self):
        for kind in ('F', 'P', 'H'):
            h = a.Harness()
            self.h = h
            h.base()
            h.put(a.conflicting_fact(h, kind), source='second')
            self.assertTrue(h.r.evaluate()['X'])
            h.lease = h.r.acquire(2, 'replacement')
            h.base()
            self.assertTrue(h.r.evaluate()['X'])
            self.assertFalse(h.reconcile())

    def test_N22_generation_cannot_erase_negative_causal_obligation(self):
        h = self.h
        h.base()
        h.eligible()
        bad = h.put(a.conflicting_fact(h, 'J'), source='second')
        h.lease = h.r.acquire(2, 'replacement')
        h.base()
        self.assertTrue(h.reconcile())
        j = h.empty()
        h.release(j)
        self.assertFalse(h.r.evaluate()['J'])
        self.assertIsNone(h.r.qualify(h.lease))
        self.renew(bad)


if __name__ == '__main__':
    unittest.main(verbosity=2)