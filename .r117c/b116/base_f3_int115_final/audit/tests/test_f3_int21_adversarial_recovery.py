"""Adversarial F3-INT-21 expectations. Genuine contract failures remain failures."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

p = Path(__file__).resolve().parents[1] / 'tools/f3_int21_adversarial_support.py'
spec = importlib.util.spec_from_file_location('int21_support', p)
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)
m, Harness = a.m, a.Harness


class AdversarialAudit(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.check()

    def expectation(self, case, observed, expected, trace, scope='atomic_API'):
        a.observe(case, self.h, observed, expected, trace, scope)
        self.assertEqual(observed, expected, case)

    def test_A01_restart_during_collection(self):
        h = self.h
        h.r.start(h.lease)
        h.put(h.fact('F', 'SESSION', 'FENCED'))
        baseline = h.s.evidence
        h.r = m.Recovery(h.s, h.v)
        self.assertEqual(h.s.evidence, baseline)
        h.base(omit=('F',))
        self.assertTrue(h.finish())

    def test_A02_restart_after_qualification(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        h.r = m.Recovery(h.s, h.v)
        self.assertTrue(h.r.close(ticket))
        self.assertFalse(h.r.close(ticket))

    def test_A03_stale_generation_lease_and_new_id_replay(self):
        h = self.h
        h.base()
        old = h.s.evidence[0]
        old_lease = h.lease
        old_ticket = h.eligible()
        h.lease = h.r.acquire(2, 'second-worker')
        self.assertEqual(h.r.add(old, old_lease), 'STALE_LEASE')
        replay = replace(old, evidence_id='renamed-old', sequence=999)
        h.v.register_fixture(replay)
        self.assertEqual(h.add(replay), 'STALE_RECOVERY')
        self.assertFalse(h.r.close(old_ticket))
        self.assertFalse(h.r.evaluate()['F'])

    def test_A04_exact_replay_is_idempotent(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        revision = h.s.revision
        for e in h.s.evidence:
            self.assertEqual(h.add(e), 'DUPLICATE_NO_EFFECT')
        self.assertEqual(h.s.revision, revision)
        self.assertTrue(h.r.close(ticket))

    def test_A05_multiple_failed_attempts_can_close(self):
        h = Harness(attempts=('a', 'b'), known_processes=())
        self.h = h
        h.base(omit=('C',), processes=())
        for attempt in ('a', 'b'):
            h.put(h.fact('C', attempt, 'FAILED'))
        self.assertTrue(h.finish())

    def test_A06_partitioned_complete_inventories_are_reconciled(self):
        h = Harness(attempts=('a', 'b'), known_processes=())
        self.h = h
        # Immutable original inventory has two distinct processes, one per attempt.
        original = replace(h.original, known_processes=(h.target, h.child))
        h.original, h.baseline = original, a.normal(original)
        # Harness baseline uses asdict, not the normalized audit representation.
        from dataclasses import asdict
        h.baseline = asdict(original)
        h.s = m.Store(original, 'recovery', 'recovery-epoch')
        h.r = m.Recovery(h.s, h.v)
        h.lease = h.r.acquire(1, 'exclusive-1')
        h.base(omit=('C',), processes=(h.target, h.child))
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
        self.expectation('A06_PARTITION_AVAILABILITY', h.r.evaluate()['C'], True,
                         ['two attempts, two known processes', 'complete C(a)={target}, C(b)={child}',
                          'all exits and H provided', 'evaluate C'], 'conservative_availability_gap')

    def test_A07_incomplete_inventory_stays_blocked(self):
        h = Harness(attempts=('a', 'b'), known_processes=())
        self.h = h
        h.base(omit=('C',))
        h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,), complete=False))
        h.put(h.fact('C', 'b', 'FAILED'))
        self.assertFalse(h.r.evaluate()['C'])
        self.assertFalse(h.reconcile())

    def test_A08_C_and_U_conflicts_are_not_resolved_by_majority(self):
        for kind in ('C', 'U'):
            with self.subTest(kind=kind):
                h = Harness(commits=('commit',))
                h.base()
                if kind == 'C':
                    f = h.fact('C', 'attempt', 'FAILED')
                else:
                    f = h.fact('U', 'commit', 'NOT_APPLIED', processes=(h.target,), attempt_id='attempt')
                h.put(f, source='second')
                h.put(f, source='second')
                self.assertTrue(h.r.evaluate()['X'])
                self.assertFalse(a.resume_close(h))
                h.check()

    def negative_base_conflict(self, kind):
        h = self.h
        h.base()
        h.put(a.conflicting_fact(h, kind), source='second')
        observed = h.finish() if h.r.evaluate()['X'] is False else False
        self.expectation('CONFLICT_' + kind, observed, False,
                         ['base evidence complete', 'independent incompatible ' + kind,
                          'attempt new reconciliation/J/L and close'])

    def test_A09_conflicting_fencing_blocks_closure(self):
        self.negative_base_conflict('F')

    def test_A10_conflicting_exit_blocks_closure(self):
        self.negative_base_conflict('P')

    def test_A11_conflicting_history_blocks_closure(self):
        self.negative_base_conflict('H')

    def test_A12_nonempty_invalidates_previous_empty_and_cleanup(self):
        h = self.h
        h.base()
        h.eligible()
        h.put(a.conflicting_fact(h, 'J'), source='second')
        observed = a.resume_close(h)
        self.expectation('J_NONEMPTY_STALE_BARRIER', observed, False,
                         ['base -> reconcile -> J EMPTY -> L RELEASED -> eligible',
                          'J NONEMPTY', 'start -> reconcile -> qualify -> close without new EMPTY/L'])

    def test_A13_failed_cleanup_evidence_invalidates_previous_success(self):
        h = self.h
        h.base()
        h.eligible()
        h.put(a.conflicting_fact(h, 'L'), source='second')
        observed = a.resume_close(h)
        self.expectation('L_FAILED_STALE_BARRIER', observed, False,
                         ['base -> reconcile -> J EMPTY -> L RELEASED -> eligible',
                          'L FAILED', 'start -> reconcile -> qualify -> close without fresh J/L'])

    def test_A14_cleanup_failure_method_invalidates_ticket(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        h.r.cleanup_failed(h.lease)
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['J'])
        self.assertFalse(h.r.evaluate()['L'])
        self.assertIn('CLEANUP_FAILED', h.s.failures)
        self.assertTrue(h.finish())

    def test_A15_late_child_after_eligibility_aborts_commit(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        h.put(h.fact('C', 'attempt', 'CREATED', processes=(h.target, h.child)), source='second')
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['J'])
        self.assertTrue(h.r.evaluate()['X'])

    def test_A16_postclosure_contestation_is_external(self):
        h = self.h
        h.base()
        self.assertTrue(h.finish())
        ticket = h.s.closure
        h.put(a.conflicting_fact(h, 'J'), source='second')
        self.assertEqual(h.s.closure, ticket)
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertFalse(h.s.conclusion_trusted)
        self.assertTrue(h.s.contestations)

    def test_A17_terminal_outcomes_and_revocation_preserved(self):
        for outcome in ('FAILED', 'CANCELLED', 'TIMEOUT', 'COMPLETED'):
            with self.subTest(outcome=outcome):
                h = Harness(outcome=outcome)
                h.base()
                self.assertTrue(h.finish())
                self.assertEqual(h.s.original.outcome, outcome)
                self.assertTrue(h.s.original.revoked and h.s.original.admission_closed)
                self.assertFalse(h.s.aggregate_success)
                for operation in ('CREATE', 'RESUME', 'RUN', 'ACCEPT'):
                    self.assertFalse(h.r.prohibit(operation, h.lease))
                h.check()

    def test_A18_same_generation_competing_commits_are_single_winner_atomic(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        other = m.Recovery(h.s, h.v)
        outcomes = (other.close(ticket), h.r.close(ticket))
        self.assertEqual(sum(outcomes), 1)

    def test_A19_new_generation_fences_old_worker_atomic(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        other = m.Recovery(h.s, h.v)
        other.acquire(2, 'worker-two')
        self.assertFalse(h.r.close(ticket))
        self.assertEqual(h.s.phase, m.Phase.BLOCKED)

    def test_A20_interleaved_commits_have_one_winner(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        other = m.Recovery(h.s, h.v)
        outer, events = a.interleave_before_commit(h, ticket, lambda: other.close(ticket))
        self.expectation('INTRALINE_DOUBLE_COMMIT', int(outer) + int(events[1]), 1,
                         ['pause worker1 after checks, before closure assignment',
                          'worker2 closes same ticket', 'resume worker1', str(events)],
                         'non_atomic_line_schedule_boundary')

    def test_A21_interleaved_new_generation_aborts_old_commit(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        other = m.Recovery(h.s, h.v)
        def steal():
            other.acquire(2, 'worker-two')
            return 'generation=2 acquired'
        outer, events = a.interleave_before_commit(h, ticket, steal)
        self.expectation('INTRALINE_STALE_COMMIT', outer, False,
                         ['worker1 checks lease/generation1 then pauses', 'worker2 acquires generation2',
                          'worker1 stores generation1 ticket', str(events)],
                         'non_atomic_line_schedule_boundary')

    def test_A22_unverified_resolution_helper_cannot_clear_conflict(self):
        h = self.h
        h.base()
        bad = h.put(h.fact('C', 'attempt', 'FAILED'))
        self.assertTrue(h.r.evaluate()['X'])
        forged = h.mint(h.fact('RESOLVE', 'conflict', 'EXPLAINED', invalidates=(bad.evidence_id,),
                              explanation='Unverified helper input.'), source='second')
        h.v.receipts.pop(forged.fingerprint)
        h.r.resolve(forged)  # Public helper, no add/verify/lease/revision path.
        observed = h.finish()
        self.expectation('DIRECT_RESOLVE_BYPASS', observed, False,
                         ['conflicting C blocks', 'unregistered resolution passed directly to resolve',
                          'new J/L and close'], 'public_helper_trusted_caller_boundary')

    def test_A23_cloned_ledger_does_not_model_durable_exclusion(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        clone = deepcopy(h)
        h.r.acquire(2, 'authoritative-new-worker')
        # Characterization of the documented boundary, not a claim of persistence.
        self.assertTrue(clone.r.close(ticket))
        self.assertFalse(h.r.close(ticket))
        a.observe('CLONED_LEDGER_BOUNDARY', h, True, True,
                  ['clone eligible ledger', 'live ledger advances generation',
                   'isolated stale clone can close: no shared authority'], 'documented_non_durability')
        clone.check()

    def test_A24_source_withdrawal_before_commit_blocks(self):
        h = self.h
        h.base()
        ticket = h.eligible()
        h.v.sources['independent'] = replace(h.v.sources['independent'], available=False)
        self.assertFalse(h.r.close(ticket))
        self.assertFalse(h.r.evaluate()['J'])


if __name__ == '__main__':
    unittest.main(verbosity=2)