"""Deterministic Architecture C scenarios. Pure data only, no external effects."""
import importlib.util
from dataclasses import FrozenInstanceError, replace
from itertools import permutations
from pathlib import Path
import sys
import unittest


# Load exactly the new pure model, avoiding package discovery/integration imports.
_model_path = Path(__file__).resolve().parents[1] / 'tools' / 'f3_int09_architecture_c_model.py'
_spec = importlib.util.spec_from_file_location('f3_int09_pure_model', _model_path)
m = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = m
_spec.loader.exec_module(m)


class ArchitectureCModelTests(unittest.TestCase):
    def setUp(self):
        self.identity = m.SessionIdentity('epoch-1', 'session-1', 1, 'nonce-1', 'job-1')
        self.process = m.ProcessIdentity('boot-1', 101, 'birth-1', 'reference-1')
        self.serial = 0

    def initial(self, budget=10):
        s = m.initialize(self.identity, budget=budget)
        self.check(s)
        return s

    def check(self, s):
        self.assertEqual(m.invariants(s), ())
        self.assertEqual(s.evidence_domain, m.Domain.SIMULATED)
        for name in ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
                     'native_prototype_authorized', 'strict_deadline_guaranteed',
                     'authenticated_witness_verified'):
            self.assertIs(getattr(s, name), False)
        self.assertLessEqual(s.launch_count, 1)
        self.assertLessEqual(s.resume_count, 1)

    def event(self, s, kind, **kwargs):
        self.serial += 1
        args = dict(event_id='event-' + str(self.serial), kind=kind, identity=self.identity,
                    launch_attempt_id=s.launch_attempt_id, process=self.process,
                    qualified=True)
        args.update(kwargs)
        return m.Event(**args)

    def step(self, s, kind, *, now=None, **kwargs):
        event = self.event(s, kind, **kwargs)
        t = m.advance(s, event, now=s.last_now + .1 if now is None else now)
        self.check(t.state)
        if s.revoked:
            self.assertEqual(t.state.resume_count, s.resume_count)
        return t

    def armed(self):
        return self.step(self.initial(), m.Kind.PREPARE_QUALIFIED, now=.5).state

    def accepted(self):
        return self.step(self.armed(), m.Kind.ACCEPT, now=1).state

    def pending(self):
        return self.step(self.accepted(), m.Kind.LAUNCH_BEGIN, launch_attempt_id='attempt-1').state

    def contained(self):
        s = self.step(self.pending(), m.Kind.CREATE_RETURNED).state
        return self.step(s, m.Kind.CONTAINMENT_CONFIRMED).state

    def running(self):
        s = self.step(self.contained(), m.Kind.RESUME_COMMIT).state
        return self.step(s, m.Kind.RESUME_CONFIRMED).state

    def stopped_with_exits(self):
        s = self.step(self.running(), m.Kind.TARGET_EXIT).state
        s = self.step(s, m.Kind.FUNCTIONAL_COMPLETE).state
        return self.step(s, m.Kind.AUXILIARY_EXIT).state

    def test_preparation_does_not_start_session_budget(self):
        s = self.armed()
        self.assertIsNone(s.accepted_at)
        self.assertIsNone(s.deadline)
        s = self.step(s, m.Kind.ACCEPT, now=100).state
        self.assertEqual((s.accepted_at, s.deadline), (100, 110))

    def test_accept_requires_qualified_preparation(self):
        t = self.step(self.initial(), m.Kind.ACCEPT)
        self.assertIn('REJECTED_TRANSITION', t.decisions)
        self.assertIsNone(t.state.accepted_at)
        t = self.step(self.initial(), m.Kind.PREPARE_QUALIFIED, qualified=False)
        self.assertEqual(t.state.phase, m.Phase.EVIDENCE_INCOMPLETE)
        self.assertIsNone(t.state.accepted_at)

    def test_only_one_creation_attempt(self):
        s = self.pending()
        t = self.step(s, m.Kind.LAUNCH_BEGIN, launch_attempt_id='attempt-2')
        self.assertIn('REJECTED_TRANSITION', t.decisions)
        self.assertEqual(t.state.launch_attempt_id, 'attempt-1')
        self.assertEqual(t.state.launch_count, 1)

    def test_exact_deadline_revokes_pending_launch(self):
        s = self.pending()
        t = self.step(s, m.Kind.TICK, now=s.deadline)
        self.assertEqual(t.state.functional_outcome, m.Outcome.TIMEOUT)
        self.assertEqual(t.state.phase, m.Phase.STOP_REQUESTED)
        self.assertIn('TIMEOUT_DECIDED', t.decisions)
        self.assertEqual(t.state.decision_at, s.deadline)
        self.assertEqual(t.state.stop_requested_at, s.deadline)
        self.assertEqual(t.state.creation, m.Creation.PENDING)

    def test_resume_commit_at_exact_deadline_is_rejected(self):
        s = self.contained()
        t = self.step(s, m.Kind.RESUME_COMMIT, now=s.deadline)
        self.assertEqual(t.state.resume_count, 0)
        self.assertTrue(t.state.revoked)
        self.assertNotIn('RESUME_COMMIT_RECORDED', t.decisions)

    def test_cancel_before_resume_blocks_new_commit(self):
        s = self.step(self.contained(), m.Kind.CANCEL).state
        s = self.step(s, m.Kind.RESUME_COMMIT).state
        self.assertEqual(s.functional_outcome, m.Outcome.CANCELLED)
        self.assertEqual(s.resume, m.Resume.NOT_COMMITTED)
        self.assertEqual(s.resume_count, 0)

    def test_late_creation_is_recovery_only(self):
        s = self.pending()
        s = self.step(s, m.Kind.TICK, now=s.deadline).state
        t = self.step(s, m.Kind.CREATE_RETURNED)
        self.assertIn('LATE_CREATION_RECOVERY_ONLY', t.decisions)
        s = self.step(t.state, m.Kind.CONTAINMENT_CONFIRMED).state
        s = self.step(s, m.Kind.RESUME_COMMIT).state
        self.assertEqual(s.functional_outcome, m.Outcome.TIMEOUT)
        self.assertEqual(s.resume_count, 0)
        self.assertEqual(s.target, self.process)

    def test_resume_effect_after_cancel_is_recorded_without_running(self):
        s = self.step(self.contained(), m.Kind.RESUME_COMMIT).state
        s = self.step(s, m.Kind.CANCEL).state
        t = self.step(s, m.Kind.RESUME_CONFIRMED)
        self.assertIn('LATE_RESUME_EFFECT_STOP_REQUIRED', t.decisions)
        self.assertEqual(t.state.resume, m.Resume.CONFIRMED)
        self.assertEqual(t.state.phase, m.Phase.STOP_REQUESTED)
        self.assertEqual(t.state.functional_outcome, m.Outcome.CANCELLED)

    def test_uncertain_resume_blocks_closure(self):
        s = self.step(self.contained(), m.Kind.RESUME_COMMIT).state
        s = self.step(s, m.Kind.RESUME_UNCERTAIN).state
        s = self.step(s, m.Kind.TARGET_EXIT).state
        s = self.step(s, m.Kind.AUXILIARY_EXIT).state
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertEqual(s.resume, m.Resume.UNCERTAIN)

    def test_explicit_not_applied_resolves_resume_but_not_evidence_failure(self):
        s = self.step(self.contained(), m.Kind.RESUME_COMMIT).state
        s = self.step(s, m.Kind.RESUME_UNCERTAIN).state
        s = self.step(s, m.Kind.RESUME_NOT_APPLIED).state
        self.assertEqual(s.resume, m.Resume.NOT_APPLIED)
        self.assertEqual(s.evidence, m.Evidence.INCOMPLETE)
        self.assertEqual(s.functional_outcome, m.Outcome.FAILED)

    def test_duplicate_does_not_repeat_effect(self):
        s = self.contained()
        event = self.event(s, m.Kind.RESUME_COMMIT)
        first = m.advance(s, event, now=2)
        self.check(first.state)
        duplicate = m.advance(first.state, event, now=2.1)
        self.check(duplicate.state)
        self.assertIn('DUPLICATE_NO_EFFECT', duplicate.decisions)
        self.assertEqual(duplicate.state.resume_count, 1)

    def test_conflicting_event_id_is_rejected(self):
        s = self.accepted()
        event = self.event(s, m.Kind.TICK)
        s = m.advance(s, event, now=2).state
        t = m.advance(s, replace(event, kind=m.Kind.CANCEL), now=3)
        self.check(t.state)
        self.assertIn('REJECTED_EVENT_ID_REUSE', t.decisions)
        self.assertFalse(t.state.revoked)

    def test_stale_generation_epoch_and_nonce_cannot_resume(self):
        for change in (dict(generation=0), dict(supervisor_epoch='epoch-old'), dict(nonce='old')):
            with self.subTest(change=change):
                s = self.contained()
                t = self.step(s, m.Kind.RESUME_COMMIT, identity=replace(self.identity, **change))
                self.assertIn('REJECTED_SESSION_IDENTITY', t.decisions)
                self.assertEqual(t.state.resume_count, 0)

    def test_stale_message_does_not_suppress_local_timeout(self):
        s = self.pending()
        t = self.step(s, m.Kind.TICK, now=s.deadline, identity=replace(self.identity, generation=0))
        self.assertEqual(t.state.functional_outcome, m.Outcome.TIMEOUT)
        self.assertIn('REJECTED_SESSION_IDENTITY', t.decisions)

    def test_wrong_attempt_is_rejected(self):
        s = self.pending()
        t = self.step(s, m.Kind.CREATE_RETURNED, launch_attempt_id='other-attempt')
        self.assertIn('REJECTED_ATTEMPT_ID', t.decisions)
        self.assertIsNone(t.state.target)
        self.assertEqual(t.state.creation, m.Creation.PENDING)

    def test_wrong_process_identity_revokes(self):
        s = self.contained()
        t = self.step(s, m.Kind.RESUME_COMMIT, process=replace(self.process, birth_token='different'))
        self.assertEqual(t.state.evidence, m.Evidence.REJECTED)
        self.assertTrue(t.state.revoked)
        self.assertEqual(t.state.resume_count, 0)

    def test_association_failure_never_allows_resume(self):
        s = self.step(self.pending(), m.Kind.CREATE_RETURNED).state
        s = self.step(s, m.Kind.ASSOCIATION_FAILED).state
        s = self.step(s, m.Kind.RESUME_COMMIT).state
        self.assertEqual(s.evidence, m.Evidence.REJECTED)
        self.assertEqual(s.resume_count, 0)
        self.assertEqual(s.functional_outcome, m.Outcome.FAILED)

    def test_supervisor_death_preserves_creation_uncertainty(self):
        s = self.step(self.pending(), m.Kind.SUPERVISOR_DIED).state
        self.assertFalse(s.supervisor_alive)
        self.assertEqual(s.creation, m.Creation.UNCERTAIN)
        t = self.step(s, m.Kind.CREATE_RETURNED)
        self.assertIn('LATE_CREATION_RECOVERY_ONLY', t.decisions)
        s = self.step(t.state, m.Kind.CONTAINMENT_CONFIRMED).state
        s = self.step(s, m.Kind.RESUME_COMMIT).state
        self.assertEqual(s.resume_count, 0)

    def test_supervisor_death_makes_resume_uncertain(self):
        s = self.step(self.contained(), m.Kind.RESUME_COMMIT).state
        s = self.step(s, m.Kind.SUPERVISOR_DIED).state
        self.assertEqual(s.resume, m.Resume.UNCERTAIN)
        self.assertEqual(s.phase, m.Phase.EVIDENCE_INCOMPLETE)
        self.assertTrue(s.revoked)

    def test_creator_exit_does_not_settle_pending_creation(self):
        s = self.step(self.pending(), m.Kind.AUXILIARY_EXIT).state
        self.assertEqual(s.creation, m.Creation.UNCERTAIN)
        s = self.step(s, m.Kind.JOB_EMPTY).state
        self.assertFalse(s.job_empty_qualified)
        s = self.step(s, m.Kind.CLOSE).state
        self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_job_empty_while_creator_pending_is_partial(self):
        s = self.step(self.pending(), m.Kind.CANCEL).state
        t = self.step(s, m.Kind.JOB_EMPTY)
        self.assertIn('PARTIAL_EMPTY_OBSERVATION_ONLY', t.decisions)
        self.assertFalse(t.state.job_empty_qualified)

    def test_missing_exits_empty_or_cleanup_blocks_close(self):
        for missing in ('auxiliary', 'target', 'empty', 'cleanup'):
            with self.subTest(missing=missing):
                s = self.step(self.running(), m.Kind.CANCEL).state
                if missing != 'target':
                    s = self.step(s, m.Kind.TARGET_EXIT).state
                if missing != 'auxiliary':
                    s = self.step(s, m.Kind.AUXILIARY_EXIT).state
                if missing != 'empty':
                    s = self.step(s, m.Kind.JOB_EMPTY).state
                if missing != 'cleanup':
                    s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
                s = self.step(s, m.Kind.CLOSE).state
                self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_witness_failure_blocks_confirmation(self):
        s = self.step(self.stopped_with_exits(), m.Kind.WITNESS_FAILED).state
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertFalse(s.job_empty_qualified)
        self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_rejection_contract_pure_audit_and_conservative(self):
        s = self.initial()
        t = self.step(s, m.Kind.ACCEPT)
        self.assertIn('REJECTED_TRANSITION', t.decisions)
        self.assertIn('AUDIT_RECORDED', t.decisions)
        self.assertEqual(t.state.phase, s.phase)
        self.assertEqual(t.state.receipts, s.receipts + (t.state.receipts[-1],))
        duplicate = m.advance(t.state, t.state.receipts[-1], now=t.state.last_now)
        self.assertIn('DUPLICATE_NO_EFFECT', duplicate.decisions)
        self.assertEqual(duplicate.state, t.state)
        native = self.step(self.initial(), m.Kind.PREPARE_QUALIFIED, domain=m.Domain.NATIVE)
        self.assertIn('REJECTED_NATIVE_CLAIM', native.decisions)
        self.assertIn('CONSERVATIVE_STOP_REQUIRED', native.decisions)
        self.assertTrue(native.state.revoked)
        self.assertEqual(native.state.evidence, m.Evidence.REJECTED)

    def test_rejection_does_not_suppress_independent_timeout(self):
        s = self.pending()
        t = self.step(s, m.Kind.RESUME_COMMIT, now=s.deadline,
                      identity=replace(self.identity, generation=0))
        self.assertIn('TIMEOUT_DECIDED', t.decisions)
        self.assertIn('REJECTED_SESSION_IDENTITY', t.decisions)
        self.assertEqual(t.state.functional_outcome, m.Outcome.TIMEOUT)
        self.assertTrue(t.state.revoked)

    def test_native_evidence_is_rejected_and_never_promoted(self):
        t = self.step(self.initial(), m.Kind.PREPARE_QUALIFIED, domain=m.Domain.NATIVE)
        self.assertIn('REJECTED_NATIVE_CLAIM', t.decisions)
        self.assertEqual(t.state.evidence_domain, m.Domain.SIMULATED)
        self.assertEqual(t.state.evidence, m.Evidence.REJECTED)
        self.assertNotEqual(t.state.phase, m.Phase.ARMED)

    def test_functional_success_requires_full_closure_for_aggregate(self):
        s = self.stopped_with_exits()
        self.assertFalse(s.aggregate_success)
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertEqual(s.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertTrue(s.aggregate_success)
        self.assertGreater(s.closed_at, s.stop_requested_at)

    def test_timeout_can_close_without_becoming_success(self):
        s = self.running()
        s = self.step(s, m.Kind.TICK, now=s.deadline).state
        s = self.step(s, m.Kind.TARGET_EXIT).state
        s = self.step(s, m.Kind.AUXILIARY_EXIT).state
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertEqual(s.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertEqual(s.functional_outcome, m.Outcome.TIMEOUT)
        self.assertFalse(s.aggregate_success)
        self.assertGreater(s.closed_at, s.deadline)

    def test_creation_failure_is_not_an_observed_target_exit(self):
        s = self.step(self.pending(), m.Kind.CREATE_FAILED).state
        s = self.step(s, m.Kind.AUXILIARY_EXIT).state
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertEqual(s.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertIsNone(s.target)
        self.assertFalse(s.target_exit_observed)
        self.assertEqual(s.functional_outcome, m.Outcome.FAILED)

    def test_cleanup_failure_is_sticky_after_recovery(self):
        s = self.step(self.stopped_with_exits(), m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_FAILED).state
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertEqual(s.phase, m.Phase.CLOSED_CONFIRMED)
        self.assertIn('CLEANUP_FAILED', s.failures)
        self.assertFalse(s.aggregate_success)

    def test_events_in_different_orders_preserve_invariants(self):
        for order in permutations((m.Kind.CANCEL, m.Kind.CREATE_RETURNED, m.Kind.AUXILIARY_EXIT)):
            with self.subTest(order=order):
                s = self.pending()
                for kind in order:
                    s = self.step(s, kind).state
                    self.assertEqual(s.resume_count, 0)
                s = self.step(s, m.Kind.CLOSE).state
                self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)

    def test_cancel_and_commit_orders_have_different_safe_results(self):
        for order in permutations((m.Kind.CANCEL, m.Kind.RESUME_COMMIT)):
            with self.subTest(order=order):
                s = self.contained()
                for kind in order:
                    s = self.step(s, kind).state
                self.assertTrue(s.revoked)
                self.assertEqual(s.resume_count, int(order[0] == m.Kind.RESUME_COMMIT))
                self.assertNotEqual(s.phase, m.Phase.RUNNING)

    def test_prohibited_transitions_do_not_skip_preparation_or_containment(self):
        for kind in (m.Kind.ACCEPT, m.Kind.LAUNCH_BEGIN, m.Kind.CLOSE):
            with self.subTest(kind=kind):
                t = self.step(self.initial(), kind, launch_attempt_id='attempt-1')
                self.assertEqual(t.state.phase, m.Phase.PREPARING)
                self.assertIn('REJECTED_TRANSITION', t.decisions)
        s = self.step(self.pending(), m.Kind.CREATE_RETURNED).state
        t = self.step(s, m.Kind.RESUME_COMMIT)
        self.assertEqual(t.state.resume_count, 0)

    def test_dead_target_cannot_be_resumed(self):
        s = self.step(self.contained(), m.Kind.TARGET_EXIT).state
        t = self.step(s, m.Kind.RESUME_COMMIT)
        self.assertIn('REJECTED_TRANSITION', t.decisions)
        self.assertEqual(t.state.resume_count, 0)

    def test_repeated_containment_does_not_regress_running_phase(self):
        s = self.running()
        t = self.step(s, m.Kind.CONTAINMENT_CONFIRMED)
        self.assertEqual(t.state.phase, m.Phase.RUNNING)
        self.assertIn('REJECTED_TRANSITION', t.decisions)

    def test_no_new_launch_after_auxiliary_exit(self):
        s = self.step(self.accepted(), m.Kind.AUXILIARY_EXIT).state
        t = self.step(s, m.Kind.LAUNCH_BEGIN, launch_attempt_id='attempt-1')
        self.assertEqual(t.state.launch_count, 0)

    def test_transition_is_pure_and_deterministic(self):
        s = self.armed()
        event = self.event(s, m.Kind.ACCEPT)
        first = m.advance(s, event, now=1)
        second = m.advance(s, event, now=1)
        self.check(first.state)
        self.check(second.state)
        self.assertEqual(first, second)
        self.assertIsNone(s.accepted_at)
        with self.assertRaises(FrozenInstanceError):
            first.state.revoked = True

    def test_clock_reversal_nonfinite_and_boolean_times_are_rejected(self):
        s = self.armed()
        for now in (-1, 0, float('nan'), float('inf'), True):
            with self.subTest(now=now):
                with self.assertRaises(ValueError):
                    m.advance(s, self.event(s, m.Kind.TICK), now=now)

    def test_invalid_identity_and_budget_are_rejected(self):
        for generation in (-1, True):
            with self.assertRaises(ValueError):
                replace(self.identity, generation=generation)
        for budget in (0, -1, True, float('inf'), float('nan')):
            with self.assertRaises(ValueError):
                self.initial(budget)

    def test_invalid_forged_state_is_rejected(self):
        s = replace(self.pending(), phase=m.Phase.CLOSED_CONFIRMED)
        self.assertIn('PREMATURE_CLOSURE', m.invariants(s))
        with self.assertRaises(ValueError):
            m.advance(s, self.event(s, m.Kind.TICK), now=2)

    def test_deadline_overflow_rejected_without_acceptance(self):
        s = m.initialize(self.identity, budget=1e308)
        s = self.step(s, m.Kind.PREPARE_QUALIFIED, now=1e308).state
        t = self.step(s, m.Kind.ACCEPT, now=1e308)
        self.assertIn('REJECTED_DEADLINE_OVERFLOW', t.decisions)
        self.assertIsNone(t.state.deadline)


    def test_late_target_after_creator_exit_requires_new_exit_evidence(self):
        s = self.step(self.pending(), m.Kind.AUXILIARY_EXIT).state
        self.assertEqual(s.creation, m.Creation.UNCERTAIN)
        self.assertNotEqual(s.phase, m.Phase.EXIT_OBSERVED)
        s = self.step(s, m.Kind.CREATE_RETURNED).state
        self.assertEqual(s.target, self.process)
        self.assertFalse(s.target_exit_observed)
        self.assertNotEqual(s.phase, m.Phase.EXIT_OBSERVED)
        s = self.step(s, m.Kind.JOB_EMPTY).state
        self.assertFalse(s.job_empty_qualified)
        self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)


    def test_unverified_target_containment_blocks_closure(self):
        s = self.step(self.pending(), m.Kind.CREATE_RETURNED).state
        s = self.step(s, m.Kind.CANCEL).state
        s = self.step(s, m.Kind.TARGET_EXIT).state
        s = self.step(s, m.Kind.AUXILIARY_EXIT).state
        s = self.step(s, m.Kind.JOB_EMPTY).state
        s = self.step(s, m.Kind.CLEANUP_SUCCEEDED).state
        s = self.step(s, m.Kind.CLOSE).state
        self.assertFalse(s.membership_qualified)
        self.assertFalse(s.job_empty_qualified)
        self.assertNotEqual(s.phase, m.Phase.CLOSED_CONFIRMED)
