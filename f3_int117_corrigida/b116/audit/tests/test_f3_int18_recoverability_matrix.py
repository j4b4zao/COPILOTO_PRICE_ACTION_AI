"""F3-INT-18: conservative simulated recoverability matrix; no external effects."""
import importlib.util
from pathlib import Path
import sys
import unittest

path = Path(__file__).resolve().parents[1] / 'tools' / 'f3_int09_architecture_c_model.py'
spec = importlib.util.spec_from_file_location('f3_int18_pure_model', path)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)

LOCKS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')

class RecoverabilityMatrixTests(unittest.TestCase):
    def setUp(self):
        self.identity = m.SessionIdentity('epoch', 'session', 1, 'nonce', 'job')
        self.process = m.ProcessIdentity('boot', 101, 'birth', 'ref')
        self.state = m.initialize(self.identity, budget=10)
        self.serial = 0

    def step(self, kind, *, now=None, qualified=True, domain=m.Domain.SIMULATED):
        self.serial += 1
        event = m.Event(f'int18-{self.serial}', kind, self.identity,
                        self.state.launch_attempt_id, self.process, qualified, domain)
        result = m.advance(self.state, event,
                           now=self.state.last_now if now is None else now)
        self.state = result.state
        self.assertEqual(m.invariants(self.state), ())
        self.assertTrue(all(getattr(self.state, flag) is False for flag in LOCKS))
        return result

    def pending(self):
        self.step(m.Kind.PREPARE_QUALIFIED)
        self.step(m.Kind.ACCEPT)
        self.serial += 1
        event = m.Event(f'int18-{self.serial}', m.Kind.LAUNCH_BEGIN, self.identity,
                        'attempt-1', self.process, True)
        self.state = m.advance(self.state, event, now=self.state.last_now).state
        self.assertEqual(m.invariants(self.state), ())

    def contained(self):
        self.pending()
        self.step(m.Kind.CREATE_RETURNED)
        self.step(m.Kind.CONTAINMENT_CONFIRMED)

    def assert_blocked(self):
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_SUCCEEDED)
        self.step(m.Kind.CLOSE)
        self.assertNotEqual(self.state.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertFalse(self.state.aggregate_success)

    def test_create_failure_can_close_with_fresh_evidence(self):
        self.pending()
        self.step(m.Kind.CREATE_FAILED)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_SUCCEEDED)
        self.step(m.Kind.CLOSE)
        self.assertEqual(self.state.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertEqual(self.state.functional_outcome, m.Outcome.FAILED)
        self.assertFalse(self.state.target_exit_observed)
        self.assertFalse(self.state.aggregate_success)

    def test_cancelled_created_session_can_close_after_all_evidence(self):
        self.contained()
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_SUCCEEDED)
        self.step(m.Kind.CLOSE)
        self.assertEqual(self.state.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertEqual(self.state.functional_outcome, m.Outcome.CANCELLED)
        self.assertFalse(self.state.aggregate_success)

    def test_uncertain_creation_resolved_late_does_not_requalify_evidence(self):
        self.pending()
        self.step(m.Kind.CREATION_UNCERTAIN)
        self.step(m.Kind.CREATE_RETURNED)
        self.step(m.Kind.CONTAINMENT_CONFIRMED)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.assertEqual(self.state.creation, m.Creation.RETURNED_CREATED)
        self.assertEqual(self.state.evidence, m.Evidence.INCOMPLETE)
        self.assert_blocked()

    def test_creator_exit_pending_then_failed_return_does_not_requalify(self):
        self.pending()
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.CREATE_FAILED)
        self.assertEqual(self.state.creation, m.Creation.RETURNED_FAILURE)
        self.assertEqual(self.state.evidence, m.Evidence.INCOMPLETE)
        self.assert_blocked()

    def test_uncertain_resume_resolved_not_applied_still_blocks_closure(self):
        self.contained()
        self.step(m.Kind.RESUME_COMMIT)
        self.step(m.Kind.RESUME_UNCERTAIN)
        self.step(m.Kind.RESUME_NOT_APPLIED)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.assertEqual(self.state.resume, m.Resume.NOT_APPLIED)
        self.assertEqual(self.state.evidence, m.Evidence.INCOMPLETE)
        self.assert_blocked()

    def test_late_resume_confirmed_after_cancel_allows_closure_not_success(self):
        self.contained()
        self.step(m.Kind.RESUME_COMMIT)
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.RESUME_CONFIRMED)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_SUCCEEDED)
        self.step(m.Kind.CLOSE)
        self.assertEqual(self.state.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertEqual(self.state.functional_outcome, m.Outcome.CANCELLED)
        self.assertFalse(self.state.aggregate_success)

    def test_witness_failure_is_sticky(self):
        self.contained()
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.WITNESS_FAILED)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.assertEqual(self.state.evidence, m.Evidence.INCOMPLETE)
        self.assert_blocked()

    def test_native_claim_rejection_is_sticky(self):
        self.contained()
        result = self.step(m.Kind.JOB_EMPTY, domain=m.Domain.NATIVE)
        self.assertIn('REJECTED_NATIVE_CLAIM', result.decisions)
        self.assertEqual(self.state.evidence, m.Evidence.REJECTED)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.assert_blocked()

    def test_supervisor_death_blocks_requalification(self):
        self.contained()
        self.step(m.Kind.SUPERVISOR_DIED)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.assertFalse(self.state.supervisor_alive)
        self.assert_blocked()

    def test_cleanup_failure_recovery_closes_with_sticky_failure(self):
        self.contained()
        self.step(m.Kind.CANCEL)
        self.step(m.Kind.TARGET_EXIT)
        self.step(m.Kind.AUXILIARY_EXIT)
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_FAILED)
        self.step(m.Kind.JOB_EMPTY)
        self.step(m.Kind.CLEANUP_SUCCEEDED)
        self.step(m.Kind.CLOSE)
        self.assertEqual(self.state.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertIn('CLEANUP_FAILED', self.state.failures)
        self.assertFalse(self.state.aggregate_success)

if __name__ == '__main__':
    unittest.main()
