"""F3-INT-23: documentary arbitration and verified conflict resolution, simulated."""
from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if 'int21_support' not in sys.modules:
    spec = importlib.util.spec_from_file_location('int21_support', ROOT / 'tools/f3_int21_adversarial_support.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
a = sys.modules['int21_support']
m = a.m


def interleave(h, code, text, callback):
    lines = Path(code.co_filename).read_text(encoding='utf-8').splitlines()
    line_number = next(i for i in range(code.co_firstlineno, len(lines) + 1) if lines[i - 1].strip() == text)
    events = []
    def tracer(frame, event, arg):
        if event == 'line' and frame.f_code is code and frame.f_lineno == line_number and not events:
            events.append('SCHEDULED')
            events.append(callback())
        return tracer
    if sys.gettrace() is not None:
        raise RuntimeError('Existing tracer')
    try:
        sys.settrace(tracer)
        result = h.r.close(h.ticket)
    finally:
        sys.settrace(None)
    if not events:
        raise AssertionError('Scheduler point not reached')
    h.check()
    return result, events


class CommitResolutionTests(unittest.TestCase):
    def setUp(self):
        self.h = a.Harness()

    def tearDown(self):
        self.h.check()

    def eligible(self):
        h = self.h
        h.base()
        h.ticket = h.eligible()
        self.assertIsNotNone(h.ticket)
        return h

    def conflict(self):
        h = self.h
        h.base()
        bad = h.put(h.fact('C', 'attempt', 'FAILED'), source='second')
        self.assertTrue(h.r.evaluate()['X'])
        return h, bad

    def resolution(self, h, bad, **changes):
        f = h.fact('RESOLVE', 'conflict', 'EXPLAINED', invalidates=(bad.evidence_id,),
                   explanation='Independent synthetic coverage explains the contrary record.')
        return h.mint(f, **changes)

    def test_S01_original_A20_schedule_has_single_winner(self):
        h = self.eligible()
        other = m.Recovery(h.s, h.v)
        outer, events = a.interleave_before_commit(h, h.ticket, lambda: other.close(h.ticket))
        self.assertEqual((outer, events[1]), (False, True))
        self.assertEqual(h.s.closure, h.ticket)

    def test_S02_original_A21_schedule_fences_old_commit(self):
        h = self.eligible()
        other = m.Recovery(h.s, h.v)
        result, _ = a.interleave_before_commit(h, h.ticket, lambda: other.acquire(2, 'new-owner'))
        self.assertFalse(result)
        self.assertIsNone(h.s.closure)
        self.assertEqual(h.s.generation, 2)
        self.assertEqual(h.s.phase, m.Phase.BLOCKED)

    def test_S03_rival_at_gate_decision_has_single_winner(self):
        h = self.eligible()
        other = m.Recovery(h.s, h.v)
        result, events = interleave(h, m.Store.__setattr__.__code__,
                                    "winner = gate.setdefault('decision', candidate)", lambda: other.close(h.ticket))
        self.assertEqual((result, events[1]), (False, True))

    def test_S04_generation_at_gate_decision_rejects_captured_old_gate(self):
        h = self.eligible()
        old_gate = h.s._commit_gate
        other = m.Recovery(h.s, h.v)
        result, _ = interleave(h, m.Store.__setattr__.__code__,
                               "winner = gate.setdefault('decision', candidate)", lambda: other.acquire(2, 'new-owner'))
        self.assertFalse(result)
        self.assertEqual(old_gate['decision'][0], 'FENCED')
        self.assertIsNone(h.s.closure)

    def test_S05_commit_linearized_before_generation_is_preserved_and_contested(self):
        h = self.eligible()
        other = m.Recovery(h.s, h.v)
        result, _ = interleave(h, m.Store.__setattr__.__code__,
                               'if winner is not candidate:', lambda: other.acquire(2, 'new-owner'))
        self.assertTrue(result)  # COMMIT won before the later generation transition.
        self.assertEqual(h.s.closure, h.ticket)
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertEqual(h.s.generation, 2)
        self.assertFalse(h.s.conclusion_trusted)
        self.assertTrue(h.s.contestations)

    def test_S06_material_negative_before_gate_aborts_close(self):
        h = self.eligible()
        result, _ = interleave(h, m.Store.__setattr__.__code__,
                               "winner = gate.setdefault('decision', candidate)",
                               lambda: h.put(a.conflicting_fact(h, 'J'), source='second'))
        self.assertFalse(result)
        self.assertFalse(h.r.evaluate()['J'])
        self.assertFalse(h.r.evaluate()['L'])

    def test_S07_negative_after_commit_decision_is_external_contestation(self):
        h = self.eligible()
        result, _ = interleave(h, m.Store.__setattr__.__code__,
                               'if winner is not candidate:',
                               lambda: h.put(a.conflicting_fact(h, 'L'), source='second'))
        self.assertTrue(result)
        self.assertEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)
        self.assertFalse(h.s.conclusion_trusted)
        self.assertIn('CLEANUP_FAILED', h.s.failures)

    def test_S08_duplicate_close_never_recommits(self):
        h = self.eligible()
        self.assertTrue(h.r.close(h.ticket))
        audit = h.s.audit.count('CLOSED_RECOVERED:SIMULATED_ONLY')
        for _ in range(3):
            self.assertFalse(m.Recovery(h.s, h.v).close(h.ticket))
        self.assertEqual(h.s.audit.count('CLOSED_RECOVERED:SIMULATED_ONLY'), audit)

    def test_S09_forged_ticket_fields_do_not_consume_valid_gate(self):
        h = self.eligible()
        for ticket in (replace(h.ticket, revision=0), replace(h.ticket, evidence_digest='wrong'),
                       replace(h.ticket, lease=replace(h.lease, token='other'))):
            self.assertFalse(h.r.close(ticket))
        self.assertTrue(h.r.close(h.ticket))

    def test_S10_closed_record_cannot_be_cleared_or_replaced(self):
        h = self.eligible()
        self.assertTrue(h.r.close(h.ticket))
        for value in (None, replace(h.ticket, revision=12345)):
            with self.assertRaises(m.CommitRejected):
                h.s.closure = value
        self.assertEqual(h.s.closure, h.ticket)

    def test_S11_restart_keeps_exclusive_gate(self):
        h = self.eligible()
        gate = h.s._commit_gate
        h.r = m.Recovery(h.s, h.v)
        self.assertIs(h.s._commit_gate, gate)
        self.assertTrue(h.r.close(h.ticket))
        self.assertFalse(m.Recovery(h.s, h.v).close(h.ticket))

    def test_S12_boolean_cannot_resolve_material_conflict(self):
        h, _ = self.conflict()
        invalidated = h.s.invalidated
        for value in (True, False, None, 'resolved'):
            self.assertEqual(h.r.resolve(value), 'RESOLUTION_NOT_ADMITTED')
        self.assertEqual(h.s.invalidated, invalidated)
        self.assertTrue(h.r.evaluate()['X'])
        self.assertFalse(h.finish())

    def test_S13_registered_but_unadmitted_resolution_is_insufficient(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad)
        self.assertEqual(h.r.resolve(e, h.lease), 'RESOLUTION_NOT_VERIFIED')
        self.assertTrue(h.r.evaluate()['X'])
        self.assertFalse(h.finish())

    def test_S14_unregistered_proof_cannot_resolve_with_explicit_lease(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad)
        h.v.receipts.pop(e.fingerprint)
        self.assertEqual(h.r.resolve(e, h.lease), 'RESOLUTION_NOT_VERIFIED')
        self.assertNotIn(bad.evidence_id, h.s.invalidated)

    def test_S15_valid_admission_independently_resolves_and_allows_fresh_close(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad)
        self.assertEqual(h.add(e), 'RESOLUTION_RECORDED')
        self.assertFalse(h.r.evaluate()['X'])
        self.assertIn(e.evidence_id, h.s.resolutions)
        self.assertIn(bad.evidence_id, h.s.invalidated)
        self.assertIn(bad, h.s.evidence)
        self.assertTrue(h.finish())

    def test_S16_same_failure_domain_cannot_remove_own_conflict(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad, source='second')
        self.assertEqual(h.add(e), 'RESOLUTION_NOT_INDEPENDENT')
        self.assertTrue(h.r.evaluate()['X'])
        self.assertNotIn(bad.evidence_id, h.s.invalidated)

    def test_S17_cache_and_self_asserted_independence_are_insufficient(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad, source='cache')
        self.assertEqual(h.add(e), 'RESOLUTION_INSUFFICIENT')
        self.assertTrue(h.r.evaluate()['X'])

    def test_S18_stale_lease_or_generation_cannot_apply_resolution(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad)
        old = h.lease
        h.lease = h.r.acquire(2, 'replacement')
        self.assertEqual(h.r.resolve(e, old), 'RESOLUTION_STALE_LEASE')
        self.assertEqual(h.add(e), 'STALE_RECOVERY')
        self.assertTrue(h.r.evaluate()['X'])

    def test_S19_incomplete_explanation_or_coverage_does_not_resolve(self):
        for variant in ('no-explanation', 'no-targets', 'incomplete', 'unsettled', 'no-interval'):
            h = a.Harness()
            self.h = h
            h.base()
            bad = h.put(h.fact('C', 'attempt', 'FAILED'), source='second')
            e = self.resolution(h, bad)
            if variant == 'no-explanation':
                e = replace(e, fact=replace(e.fact, explanation=''))
            elif variant == 'no-targets':
                e = replace(e, fact=replace(e.fact, invalidates=()))
            elif variant == 'incomplete':
                e = replace(e, fact=replace(e.fact, complete=False))
            elif variant == 'unsettled':
                e = replace(e, fact=replace(e.fact, settled=False))
            h.v.register_fixture(e, interval_covered=variant != 'no-interval')
            self.assertNotEqual(h.add(e), 'RESOLUTION_RECORDED')
            self.assertTrue(h.r.evaluate()['X'])
            self.assertNotIn(bad.evidence_id, h.s.invalidated)

    def test_S20_valid_resolution_replay_is_idempotent(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad)
        self.assertEqual(h.add(e), 'RESOLUTION_RECORDED')
        revision = h.s.revision
        self.assertEqual(h.add(e), 'DUPLICATE_NO_EFFECT')
        self.assertEqual(h.r.resolve(e, h.lease), 'RESOLUTION_ALREADY_RECORDED')
        self.assertEqual(h.s.revision, revision)

    def test_S21_resolution_receipt_revoked_before_apply_keeps_conflict(self):
        h, bad = self.conflict()
        e = self.resolution(h, bad)
        target_line = next(i for i, line in enumerate((ROOT / 'tools/f3_int20_evidence_recovery_model.py').read_text().splitlines(), 1)
                           if line.strip() == 'return self.resolve(e, lease)')
        fired = []
        def tracer(frame, event, arg):
            if event == 'line' and frame.f_code is m.Recovery.add.__code__ and frame.f_lineno == target_line and not fired:
                fired.append(True)
                h.v.receipts.pop(e.fingerprint)
            return tracer
        try:
            sys.settrace(tracer)
            result = h.add(e)
        finally:
            sys.settrace(None)
        self.assertEqual(result, 'RESOLUTION_NOT_VERIFIED')
        self.assertTrue(h.r.evaluate()['X'])
        self.assertNotIn(bad.evidence_id, h.s.invalidated)

    def test_S22_guard_rejection_helper_is_false_not_a_success(self):
        h, _ = self.conflict()
        self.assertIsNone(h.eligible())
        self.assertFalse(h.finish())
        self.assertTrue(h.r.evaluate()['X'])
        self.assertNotEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)

    def test_S23_positive_helper_still_requires_all_guards(self):
        h = self.h
        h.base(omit=('H',))
        self.assertFalse(h.finish())
        h.put(h.fact('H', h.target.key, 'CONTAINED', processes=(h.target,)))
        self.assertTrue(h.finish())

    def test_S24_original_outcomes_authority_history_and_deadline_are_immutable(self):
        for outcome in ('FAILED', 'CANCELLED', 'TIMEOUT', 'COMPLETED'):
            h = a.Harness(outcome=outcome)
            self.h = h
            original = asdict(h.s.original)
            h.base()
            h.ticket = h.eligible()
            other = m.Recovery(h.s, h.v)
            outer, events = a.interleave_before_commit(h, h.ticket, lambda: other.close(h.ticket))
            self.assertEqual(int(outer) + int(events[1]), 1)
            self.assertEqual(asdict(h.s.original), original)
            self.assertFalse(h.s.aggregate_success)
            self.assertTrue(all(getattr(h.s, f) is False for f in m.FLAGS))


if __name__ == '__main__':
    unittest.main(verbosity=2)