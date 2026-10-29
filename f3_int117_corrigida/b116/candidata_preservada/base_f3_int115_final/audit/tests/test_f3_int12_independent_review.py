"""F3-INT-12 independent contract regression: pure Python only."""
import importlib.util
from dataclasses import replace
from pathlib import Path
import sys
import unittest

P = Path(__file__).resolve().parents[1] / 'tools' / 'f3_int09_architecture_c_model.py'
spec = importlib.util.spec_from_file_location('f3_int12_model', P)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

class IndependentReview(unittest.TestCase):
    def setUp(self):
        self.identity = m.SessionIdentity('epoch', 'session', 1, 'nonce', 'job')
        self.process = m.ProcessIdentity('boot', 100, 'birth', 'reference')
        self.seq = 0

    def event(self, s, kind, **changes):
        self.seq += 1
        d = dict(event_id=f'e{self.seq}', kind=kind, identity=self.identity,
                 launch_attempt_id=s.launch_attempt_id, process=self.process, qualified=True)
        d.update(changes)
        return m.Event(**d)

    def step(self, s, kind, now=None, **changes):
        t = m.advance(s, self.event(s, kind, **changes), now=s.last_now if now is None else now)
        self.assertEqual(m.invariants(t.state), ())
        return t

    def pending(self):
        s = m.initialize(self.identity, budget=2)
        s = self.step(s, m.Kind.PREPARE_QUALIFIED).state
        s = self.step(s, m.Kind.ACCEPT).state
        return self.step(s, m.Kind.LAUNCH_BEGIN, launch_attempt_id='attempt').state

    def test_rejection_is_explicitly_audit_only(self):
        s = m.initialize(self.identity, budget=2)
        t = self.step(s, m.Kind.ACCEPT)
        self.assertEqual(t.decisions, ('AUDIT_RECORDED', 'REJECTED_TRANSITION'))
        self.assertEqual(replace(t.state, receipts=s.receipts), s)

    def test_native_rejection_stops_conservatively(self):
        s = m.initialize(self.identity, budget=2)
        t = self.step(s, m.Kind.PREPARE_QUALIFIED, domain=m.Domain.NATIVE)
        self.assertIn('CONSERVATIVE_STOP_REQUIRED', t.decisions)
        self.assertTrue(t.state.revoked)
        self.assertEqual(t.state.evidence, m.Evidence.REJECTED)
        self.assertEqual(t.state.evidence_domain, m.Domain.SIMULATED)

    def test_stale_identity_at_deadline_preserves_timeout(self):
        s = self.pending()
        t = self.step(s, m.Kind.RESUME_COMMIT, now=s.deadline,
                      identity=replace(self.identity, generation=0))
        self.assertIn('TIMEOUT_DECIDED', t.decisions)
        self.assertIn('REJECTED_SESSION_IDENTITY', t.decisions)
        self.assertEqual(t.state.functional_outcome, m.Outcome.TIMEOUT)
        self.assertEqual(t.state.resume_count, 0)

    def test_duplicate_at_deadline_does_not_suppress_timeout(self):
        s = self.pending()
        e = s.receipts[-1]
        t = m.advance(s, e, now=s.deadline)
        self.assertIn('DUPLICATE_NO_EFFECT', t.decisions)
        self.assertIn('TIMEOUT_DECIDED', t.decisions)
        self.assertEqual(t.state.functional_outcome, m.Outcome.TIMEOUT)

    def test_native_claim_after_timeout_cannot_promote_success(self):
        s = self.pending()
        t = self.step(s, m.Kind.CREATE_RETURNED, now=s.deadline, domain=m.Domain.NATIVE)
        self.assertIn('TIMEOUT_DECIDED', t.decisions)
        self.assertIn('CONSERVATIVE_STOP_REQUIRED', t.decisions)
        self.assertEqual(t.state.functional_outcome, m.Outcome.TIMEOUT)
        self.assertEqual(t.state.creation, m.Creation.PENDING)

    def test_rejected_wrong_attempt_only_audit(self):
        s = self.pending()
        t = self.step(s, m.Kind.CREATE_RETURNED, launch_attempt_id='other')
        self.assertIn('AUDIT_RECORDED', t.decisions)
        self.assertIn('REJECTED_ATTEMPT_ID', t.decisions)
        self.assertEqual(replace(t.state, receipts=s.receipts), s)

    def test_terminal_closed_does_not_accept_new_event(self):
        s = self.pending()
        s = self.step(s, m.Kind.CREATE_FAILED).state
        s = self.step(s, m.Kind.AUXILIARY_EXIT).state
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertEqual(s.phase, m.Phase.CLOSED_CONFIRMED)
        t = self.step(s, m.Kind.CANCEL, now=s.last_now+1)
        self.assertEqual(t.decisions, ('TERMINAL_NO_EFFECT',))
        self.assertEqual(t.state.phase, m.Phase.CLOSED_CONFIRMED)

if __name__ == '__main__':
    unittest.main()
