"""F3-INT-17: isolated, simulated recovery/closure barrier regression.

No Windows API, subprocess, Excel, RTD/DDE, operational project or native claims.
"""
import importlib.util
from pathlib import Path
import sys
import unittest

path = Path(__file__).resolve().parents[1] / 'tools' / 'f3_int09_architecture_c_model.py'
spec = importlib.util.spec_from_file_location('f3_int17_pure_model', path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class RecoveryClosureTests(unittest.TestCase):
    def setUp(self):
        self.ident = m.SessionIdentity('epoch', 'session', 1, 'nonce', 'job')
        self.proc = m.ProcessIdentity('boot', 101, 'birth', 'ref')
        self.s = m.initialize(self.ident, budget=10)
        self.n = 0

    def step(self, kind, *, qualified=True, process=None, attempt=None, now=None):
        self.n += 1
        e = m.Event('event-%d' % self.n, kind, self.ident,
                    self.s.launch_attempt_id if attempt is None else attempt,
                    self.proc if process is None else process, qualified)
        t = m.advance(self.s, e, now=self.s.last_now if now is None else now)
        self.s = t.state
        self.assertEqual(m.invariants(self.s), ())
        for flag in ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
                     'native_prototype_authorized', 'strict_deadline_guaranteed',
                     'authenticated_witness_verified'):
            self.assertIs(getattr(self.s, flag), False)
        return t

    def pending(self):
        self.step(m.Kind.PREPARE_QUALIFIED)
        self.step(m.Kind.ACCEPT)
        self.step(m.Kind.LAUNCH_BEGIN, attempt='attempt')

    def contained(self):
        self.pending()
        self.step(m.Kind.CREATE_RETURNED)
        self.step(m.Kind.CONTAINMENT_CONFIRMED)

    def assert_not_closed(self):
        self.step(m.Kind.CLOSE)
        self.assertNotEqual(self.s.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertFalse(self.s.aggregate_success)

    def test_creator_exit_is_not_creation_resolution(self):
        self.pending()
        self.step(m.Kind.AUXILIARY_EXIT)
        self.assertEqual(self.s.creation, m.Creation.UNCERTAIN)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()

    def test_late_created_target_requires_independent_exit_and_containment(self):
        self.pending()
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.CREATE_RETURNED)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()
        self.step(m.Kind.CONTAINMENT_CONFIRMED)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        # Earlier creator exit while creation was pending poisoned the evidence.
        self.assertFalse(self.s.job_empty_qualified)
        self.assertEqual(self.s.evidence, m.Evidence.INCOMPLETE)
        self.assert_not_closed()

    def test_target_exit_alone_is_not_session_closure(self):
        self.contained()
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()

    def test_job_empty_before_creator_exit_does_not_latch(self):
        self.pending()
        self.step(m.Kind.CREATE_FAILED)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()
        self.step(m.Kind.JOB_EMPTY)
        self.assertTrue(self.s.job_empty_qualified)

    def test_pending_resume_not_settled_by_exits_or_empty(self):
        self.contained()
        self.step(m.Kind.RESUME_COMMIT)
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()

    def test_uncertain_resume_blocks_even_after_both_exits(self):
        self.contained()
        self.step(m.Kind.RESUME_COMMIT)
        self.step(m.Kind.RESUME_UNCERTAIN)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()

    def test_supervisor_death_does_not_imply_recovered_closure(self):
        self.pending()
        self.step(m.Kind.SUPERVISOR_DIED)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.CREATE_FAILED)
        self.step(m.Kind.JOB_EMPTY)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()

    def test_witness_failure_not_repaired_by_later_exit_and_cleanup(self):
        self.contained()
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.WITNESS_FAILED)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_SUCCEEDED)
        self.assertFalse(self.s.job_empty_qualified)
        self.assert_not_closed()

    def test_cleanup_failure_never_becomes_functional_success(self):
        self.contained()
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_FAILED)
        self.assert_not_closed()
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_SUCCEEDED)
        self.step(m.Kind.CLOSE)
        self.assertEqual(self.s.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertIn('CLEANUP_FAILED', self.s.failures)
        self.assertFalse(self.s.aggregate_success)


if __name__ == '__main__':
    unittest.main()
