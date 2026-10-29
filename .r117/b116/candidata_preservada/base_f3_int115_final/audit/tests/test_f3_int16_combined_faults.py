"""F3-INT-16: isolated simulated fault-order regression, no native side effects."""
import importlib.util
from itertools import permutations
from pathlib import Path
import sys
import unittest

P = Path(__file__).resolve().parents[1] / 'tools' / 'f3_int09_architecture_c_model.py'
spec = importlib.util.spec_from_file_location('f3_int16_pure_model', P)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
I = m.SessionIdentity('epoch-16', 'session-16', 1, 'nonce-16', 'job-16')
P_ID = m.ProcessIdentity('boot-16', 116, 'birth-16', 'ref-16')
FLAGS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')

class CombinedFaultTests(unittest.TestCase):
    def run_trace(self, prefix, faults, *, deadline=False):
        s = m.initialize(I, budget=1)
        seq = 0
        for kind in tuple(prefix) + tuple(faults):
            seq += 1
            now = s.deadline if deadline and kind == m.Kind.TICK and s.deadline is not None else s.last_now
            e = m.Event('f16-'+str(seq), kind, I,
                        'attempt-16' if kind == m.Kind.LAUNCH_BEGIN else s.launch_attempt_id,
                        P_ID, True)
            before = s
            t = m.advance(s, e, now=now)
            s = t.state
            self.assertEqual(m.invariants(s), (), (kind, t.decisions))
            self.assertTrue(all(getattr(s, flag) is False for flag in FLAGS))
            self.assertLessEqual(s.launch_count, 1)
            self.assertLessEqual(s.resume_count, 1)
            if before.revoked:
                self.assertTrue(s.revoked)
                self.assertEqual(s.resume_count, before.resume_count)
            if before.functional_outcome in (m.Outcome.FAILED, m.Outcome.CANCELLED, m.Outcome.TIMEOUT):
                self.assertEqual(s.functional_outcome, before.functional_outcome)
            if s.phase == m.Phase.CLOSED_CONFIRMED:
                self.assertNotIn(s.creation, (m.Creation.PENDING, m.Creation.UNCERTAIN))
                self.assertNotIn(s.resume, (m.Resume.IN_FLIGHT, m.Resume.UNCERTAIN))
        return s

    PREPARED = (m.Kind.PREPARE_QUALIFIED, m.Kind.ACCEPT)
    PENDING = PREPARED + (m.Kind.LAUNCH_BEGIN,)
    CONTAINED = PENDING + (m.Kind.CREATE_RETURNED, m.Kind.CONTAINMENT_CONFIRMED)
    RESUMING = CONTAINED + (m.Kind.RESUME_COMMIT,)

    def test_pending_creation_supervisor_death_and_auxiliary_exit_orders(self):
        for order in permutations((m.Kind.SUPERVISOR_DIED, m.Kind.AUXILIARY_EXIT, m.Kind.CREATE_RETURNED)):
            with self.subTest(order=order):
                s = self.run_trace(self.PENDING, order + (m.Kind.RESUME_COMMIT, m.Kind.JOB_EMPTY, m.Kind.CLOSE))
                self.assertTrue(s.revoked)
                self.assertEqual(s.resume_count, 0)
                self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_uncertain_creation_and_late_return_orders(self):
        for order in permutations((m.Kind.CREATION_UNCERTAIN, m.Kind.CREATE_RETURNED, m.Kind.AUXILIARY_EXIT)):
            with self.subTest(order=order):
                s = self.run_trace(self.PENDING, order + (m.Kind.RESUME_COMMIT, m.Kind.CLOSE))
                self.assertEqual(s.resume_count, 0)
                self.assertTrue(s.revoked or s.creation == m.Creation.RETURNED_CREATED)
                self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_inflight_resume_supervisor_loss_cancel_late_confirmation(self):
        for order in permutations((m.Kind.SUPERVISOR_DIED, m.Kind.CANCEL, m.Kind.RESUME_CONFIRMED)):
            with self.subTest(order=order):
                s = self.run_trace(self.RESUMING, order + (m.Kind.RESUME_COMMIT, m.Kind.CLOSE))
                self.assertTrue(s.revoked)
                self.assertEqual(s.resume_count, 1)
                self.assertNotEqual(s.phase, m.Phase.RUNNING)
                self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_timeout_and_late_resume_confirmation(self):
        for order in permutations((m.Kind.TICK, m.Kind.RESUME_CONFIRMED, m.Kind.CANCEL)):
            with self.subTest(order=order):
                s = self.run_trace(self.RESUMING, order + (m.Kind.RESUME_COMMIT,), deadline=True)
                self.assertTrue(s.revoked)
                self.assertEqual(s.resume_count, 1)
                self.assertNotEqual(s.phase, m.Phase.RUNNING)
                self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_witness_failure_and_cleanup_failure_orders(self):
        for order in permutations((m.Kind.WITNESS_FAILED, m.Kind.CLEANUP_FAILED, m.Kind.JOB_EMPTY)):
            with self.subTest(order=order):
                s = self.run_trace(self.CONTAINED, (m.Kind.CANCEL, m.Kind.TARGET_EXIT,
                                   m.Kind.AUXILIARY_EXIT) + order + (m.Kind.CLEANUP_SUCCEEDED, m.Kind.CLOSE))
                self.assertTrue(s.revoked)
                self.assertFalse(s.aggregate_success)
                self.assertIn('WITNESS_FAILED', s.failures)

    def test_no_invented_exit_from_creator_failure(self):
        for order in permutations((m.Kind.CREATE_FAILED, m.Kind.AUXILIARY_EXIT, m.Kind.JOB_EMPTY)):
            with self.subTest(order=order):
                s = self.run_trace(self.PENDING, order + (m.Kind.CLEANUP_SUCCEEDED, m.Kind.CLOSE))
                self.assertFalse(s.target_exit_observed)
                self.assertFalse(s.aggregate_success)

    def test_simultaneous_faults_never_authorize_operations(self):
        faults = (m.Kind.SUPERVISOR_DIED, m.Kind.CREATION_UNCERTAIN,
                  m.Kind.AUXILIARY_EXIT, m.Kind.WITNESS_FAILED, m.Kind.CLEANUP_FAILED)
        for order in permutations(faults):
            with self.subTest(order=order):
                s = self.run_trace(self.PENDING, order + (m.Kind.RESUME_COMMIT, m.Kind.CLOSE))
                self.assertTrue(s.revoked)
                self.assertEqual(s.resume_count, 0)
                self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

if __name__ == '__main__':
    unittest.main()
