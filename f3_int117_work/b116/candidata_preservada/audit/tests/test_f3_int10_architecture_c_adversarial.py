"""Bounded adversarial audit of the pure F3-INT-09 model.

Only this test module is executed. The existing test suite is never imported.
BFS: at most 3 extra events per reachable seed, 12000 candidate edges,
12000 distinct states, and 8 seconds total emergency wall-clock allowance.
No-op/rejected edges are checked but not expanded. Receipt order is canonicalized
for deduplication because advance uses receipts only for event-ID lookup.
The strict rejected-state contract includes audit metadata; autonomous timeout is
reported separately and is not attributed to the rejected message.
"""
from collections import deque
from dataclasses import fields, replace
import importlib.util
import json
from math import nextafter
from pathlib import Path
import sys
from time import monotonic
import unittest


MODEL_PATH = Path(__file__).resolve().parents[1] / 'tools' / 'f3_int09_architecture_c_model.py'
SPEC = importlib.util.spec_from_file_location('f3_int10_audited_model', MODEL_PATH)
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)

MAX_DEPTH = 3
MAX_STATES = 12000
MAX_TRANSITIONS = 12000
MAX_SECONDS = 8.0
MAX_MINIMIZER_CALLS = 200
IDENTITY = m.SessionIdentity('epoch-1', 'session-1', 1, 'nonce-1', 'job-1')
PROCESS = m.ProcessIdentity('boot-1', 101, 'birth-1', 'reference-1')
FLAGS = ('orders_allowed', 'live_certified', 'flow_complete', 'f3_resolved',
         'native_prototype_authorized', 'strict_deadline_guaranteed',
         'authenticated_witness_verified')


def operational_key(s):
    return tuple(getattr(s, f.name) for f in fields(s) if f.name not in ('receipts', 'last_now'))


def state_key(s):
    return replace(s, receipts=tuple(sorted(s.receipts, key=lambda e: e.event_id)))


def normal_event(s, kind):
    occurrence = sum(e.kind == kind for e in s.receipts)
    return m.Event(kind.value + ':normal:' + str(occurrence), kind, IDENTITY,
                   'attempt-1' if kind == m.Kind.LAUNCH_BEGIN else s.launch_attempt_id,
                   PROCESS, True)


def candidates(s):
    # Fixed order, one normal form of every implemented event plus adversarial forms.
    events = [normal_event(s, kind) for kind in m.Kind]
    resume = normal_event(s, m.Kind.RESUME_COMMIT)
    events.extend((
        replace(resume, event_id='stale-generation', identity=replace(IDENTITY, generation=0)),
        replace(resume, event_id='stale-epoch', identity=replace(IDENTITY, supervisor_epoch='old')),
        replace(resume, event_id='wrong-process', process=replace(PROCESS, birth_token='other')),
        replace(normal_event(s, m.Kind.CREATE_RETURNED), event_id='wrong-attempt', launch_attempt_id='other'),
        replace(normal_event(s, m.Kind.CREATE_RETURNED), event_id='missing-process', process=None),
        replace(normal_event(s, m.Kind.JOB_EMPTY), event_id='unqualified-empty', qualified=False),
        replace(normal_event(s, m.Kind.PREPARE_QUALIFIED), event_id='native-claim', domain=m.Domain.NATIVE),
    ))
    if s.receipts:
        events.append(s.receipts[-1])
        events.append(replace(s.receipts[-1], kind=(m.Kind.CANCEL if s.receipts[-1].kind != m.Kind.CANCEL else m.Kind.TICK)))
    times = [s.last_now]
    if s.deadline is not None:
        times.extend(t for t in (nextafter(s.deadline, -float('inf')), s.deadline,
                                nextafter(s.deadline, float('inf'))) if t >= s.last_now)
    for event in events:
        for now in dict.fromkeys(times):
            yield event, now


def safety_violations(before, after, event, decisions):
    problems = list(m.invariants(after))
    if any(getattr(after, name) is not False for name in FLAGS) or after.evidence_domain != m.Domain.SIMULATED:
        problems.append('UNSAFE_NATIVE_OR_OPERATIONAL_CLAIM')
    if after.launch_count > 1 or after.resume_count > 1:
        problems.append('MULTIPLE_CREATION_OR_RESUME')
    if before.revoked and (not after.revoked or after.resume_count != before.resume_count):
        problems.append('REVOCATION_BROKEN')
    if not before.supervisor_alive and after.supervisor_alive:
        problems.append('AUTHORITY_RESURRECTED')
    if before.admission_closed and not after.admission_closed:
        problems.append('ADMISSION_REOPENED')
    if before.functional_outcome in (m.Outcome.CANCELLED, m.Outcome.TIMEOUT, m.Outcome.FAILED):
        if after.functional_outcome != before.functional_outcome:
            problems.append('TERMINAL_OUTCOME_CHANGED')
    if after.phase == m.Phase.RUNNING:
        if (after.revoked or not after.supervisor_alive or after.resume != m.Resume.CONFIRMED
                or not after.membership_qualified or not after.suspension_qualified):
            problems.append('UNSAFE_RUNNING')
    if after.phase == m.Phase.CLOSED_CONFIRMED:
        if (after.creation in (m.Creation.PENDING, m.Creation.UNCERTAIN)
                or after.resume in (m.Resume.IN_FLIGHT, m.Resume.UNCERTAIN)
                or not after.auxiliary_exit_observed
                or (after.target is not None and (not after.target_exit_observed
                    or not after.membership_qualified or not after.suspension_qualified))
                or not after.job_empty_qualified or after.cleanup != m.Cleanup.SUCCEEDED):
            problems.append('UNSAFE_CLOSURE')
    if after.target is None and after.target_exit_observed:
        problems.append('INVENTED_EXIT')
    if 'RESUME_COMMIT_RECORDED' in decisions:
        if (before.revoked or not before.supervisor_alive or before.phase != m.Phase.CONTAINED_SUSPENDED
                or before.resume_count != 0 or event.identity != before.identity
                or after.last_now >= before.deadline):
            problems.append('UNSAFE_RESUME_COMMIT')
    return tuple(dict.fromkeys(problems))


def rejection_violation(before, transition):
    """Validate explicit reject effects, separating clock, audit and fail-safe."""
    codes = transition.decisions
    if not any(code.startswith('REJECTED_') for code in codes):
        return None
    after = transition.state
    # The clock advances independently; its deadline transition must survive.
    timed_out = 'TIMEOUT_DECIDED' in codes
    base = before
    if timed_out:
        base = m._stop(base, after.last_now, 'TIMEOUT', m.Outcome.TIMEOUT)
    base = replace(base, last_now=after.last_now)
    changed = [f.name for f in fields(base) if getattr(base, f.name) != getattr(after, f.name)]
    if 'CONSERVATIVE_STOP_REQUIRED' in codes:
        if not after.revoked or not after.admission_closed or after.evidence != m.Evidence.REJECTED:
            return 'REJECTED_STOP_NOT_CONSERVATIVE'
        if after.functional_outcome == m.Outcome.COMPLETED and before.functional_outcome != m.Outcome.COMPLETED:
            return 'REJECTED_STOP_PROMOTED_SUCCESS'
        return None
    if 'AUDIT_RECORDED' in codes:
        if changed != ['receipts']:
            return 'REJECTED_AUDIT_MUTATES_OPERATIONAL_STATE'
        return None
    if changed:
        return 'REJECTED_PURE_MUTATES_STATE'
    return None


def describe(trace):
    return [dict(kind=e.kind.value, event_id=e.event_id, now=now,
                 generation=e.identity.generation, epoch=e.identity.supervisor_epoch,
                 attempt=e.launch_attempt_id, qualified=e.qualified, domain=e.domain.value,
                 process=None if e.process is None else dict(pid=e.process.pid, birth=e.process.birth_token))
            for e, now in trace]


def explore():
    started = monotonic()
    report = dict(max_extra_depth=MAX_DEPTH, max_states=MAX_STATES,
                  max_transitions=MAX_TRANSITIONS, max_seconds=MAX_SECONDS,
                  attempted=0, accepted=0, rejected=0, no_effect=0, exceptions=0,
                  rejected_unchanged=0, rejected_with_independent_timeout=0,
                  seed_model_calls=0, minimizer_calls=0,
                  expanded_paths=0, depth_effective=0, absolute_depth_effective=0,
                  boundary_attempts=dict(before=0, equal=0, after=0),
                  safety_violation_occurrences=0, rejection_violation_occurrences=0)
    findings = {}
    reached = set()
    considered_paths = set()
    phases = set()
    seeds = []
    initial = m.initialize(IDENTITY, budget=1.0)
    seeds.append((initial, ()))
    # Reachable prefixes cover preparation through full closure; no forged states.
    prefix = (m.Kind.PREPARE_QUALIFIED, m.Kind.ACCEPT, m.Kind.LAUNCH_BEGIN,
              m.Kind.CREATE_RETURNED, m.Kind.CONTAINMENT_CONFIRMED, m.Kind.RESUME_COMMIT,
              m.Kind.RESUME_CONFIRMED, m.Kind.TARGET_EXIT, m.Kind.FUNCTIONAL_COMPLETE,
              m.Kind.AUXILIARY_EXIT, m.Kind.JOB_EMPTY, m.Kind.CLEANUP_SUCCEEDED, m.Kind.CLOSE)
    s, trace = initial, ()
    for kind in prefix:
        e = normal_event(s, kind)
        t = m.advance(s, e, now=0.0)
        report['seed_model_calls'] += 1
        if safety_violations(s, t.state, e, t.decisions):
            raise AssertionError('INVALID_REACHABLE_SEED')
        trace += ((e, 0.0),)
        s = t.state
        seeds.append((s, trace))
    queue = deque()
    queued = set()
    for s, trace in seeds:
        key = state_key(s)
        reached.add(key)
        phases.add(s.phase.value)
        considered_paths.add(trace)
        if key not in queued:
            queued.add(key)
            queue.append((s, trace, 0))

    def record(code, trace, detail):
        previous = findings.get(code)
        if previous is None or len(trace) < len(previous[0]):
            findings[code] = (trace, detail)

    stop = 'DEPTH_EXHAUSTED'
    while queue:
        if report['attempted'] >= MAX_TRANSITIONS:
            stop = 'TRANSITION_LIMIT'
            break
        if len(reached) >= MAX_STATES:
            stop = 'STATE_LIMIT'
            break
        if monotonic() - started >= MAX_SECONDS:
            stop = 'DURATION_LIMIT'
            break
        s, trace, depth = queue.popleft()
        if depth >= MAX_DEPTH:
            continue
        report['expanded_paths'] += 1
        for event, now in candidates(s):
            if report['attempted'] >= MAX_TRANSITIONS or len(reached) >= MAX_STATES or monotonic() - started >= MAX_SECONDS:
                break
            path = trace + ((event, now),)
            considered_paths.add(path)
            report['attempted'] += 1
            report['depth_effective'] = max(report['depth_effective'], depth + 1)
            report['absolute_depth_effective'] = max(report['absolute_depth_effective'], len(path))
            if s.deadline is not None:
                for label, boundary in (('before', nextafter(s.deadline, -float('inf'))),
                                        ('equal', s.deadline), ('after', nextafter(s.deadline, float('inf')))):
                    if now == boundary:
                        report['boundary_attempts'][label] += 1
            try:
                t = m.advance(s, event, now=now)
            except Exception as error:
                report['exceptions'] += 1
                report['safety_violation_occurrences'] += 1
                record('MODEL_EXCEPTION:' + type(error).__name__ + ':' + str(error), path, 'advance raised')
                continue
            problems = safety_violations(s, t.state, event, t.decisions)
            for code in problems:
                report['safety_violation_occurrences'] += 1
                record('SAFETY:' + code, path, list(t.decisions))
            rejected = any(c.startswith('REJECTED_') for c in t.decisions)
            no_effect = any(c in ('DUPLICATE_NO_EFFECT', 'TERMINAL_NO_EFFECT', 'PARTIAL_EMPTY_OBSERVATION_ONLY') for c in t.decisions)
            if rejected:
                report['rejected'] += 1
                if t.state == s:
                    report['rejected_unchanged'] += 1
                if 'TIMEOUT_DECIDED' in t.decisions:
                    report['rejected_with_independent_timeout'] += 1
            elif no_effect:
                report['no_effect'] += 1
            else:
                report['accepted'] += 1
            issue = rejection_violation(s, t)
            if issue:
                report['rejection_violation_occurrences'] += 1
                changed = [f.name for f in fields(s) if getattr(s, f.name) != getattr(t.state, f.name)]
                record(issue, path, dict(decisions=list(t.decisions), changed=changed))
            key = state_key(t.state)
            reached.add(key)
            phases.add(t.state.phase.value)
            # Rejected/no-op branches are inspected but not extended. This is an
            # explicit scope reduction, not a claim of exhaustive model checking.
            if not problems and not rejected and not no_effect and operational_key(s) != operational_key(t.state) and key not in queued:
                queued.add(key)
                queue.append((t.state, path, depth + 1))

    # Deletion minimization preserves the exact violation signature and timestamps.
    # A one-event counterexample is globally minimal (the initial state is valid).
    for code in list(findings):
        trace, detail = findings[code]
        changed = True
        while changed and len(trace) > 1 and report['minimizer_calls'] < MAX_MINIMIZER_CALLS and monotonic() - started < MAX_SECONDS:
            changed = False
            for index in range(len(trace)):
                candidate = trace[:index] + trace[index+1:]
                current = initial
                observed = None
                for e, now in candidate:
                    if report['minimizer_calls'] >= MAX_MINIMIZER_CALLS or monotonic() - started >= MAX_SECONDS:
                        break
                    report['minimizer_calls'] += 1
                    try:
                        t = m.advance(current, e, now=now)
                    except Exception as error:
                        observed = 'MODEL_EXCEPTION:' + type(error).__name__ + ':' + str(error)
                        break
                    issues = ['SAFETY:' + p for p in safety_violations(current, t.state, e, t.decisions)]
                    rejection = rejection_violation(current, t)
                    if rejection:
                        issues.append(rejection)
                    if code in issues:
                        observed = code
                        break
                    current = t.state
                if observed == code:
                    trace = candidate
                    changed = True
                    break
        findings[code] = (trace, detail)
    report.update(stop_reason=stop, seeds=len(seeds), distinct_states=len(reached),
                  distinct_candidate_paths=len(considered_paths), queued_states=len(queued),
                  phases_reached=sorted(phases), elapsed_seconds=round(monotonic()-started, 6),
                  total_model_calls=report['seed_model_calls']+report['attempted']+report['minimizer_calls'],
                  counterexamples=[dict(violation=code, length=len(trace),
                    minimality='global: one event' if len(trace) == 1 else 'shortest observed, bounded deletion minimization',
                    trace=describe(trace), detail=detail) for code, (trace, detail) in sorted(findings.items())])
    return report


class ArchitectureCAdversarialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = explore()  # one exploration, not one unittest per edge
        print('F3_INT10_REPORT=' + json.dumps(cls.report, sort_keys=True), flush=True)

    def test_metrics_are_disjoint_and_bounded(self):
        r = self.report
        self.assertEqual(r['attempted'], r['accepted'] + r['rejected'] + r['no_effect'] + r['exceptions'])
        self.assertLessEqual(r['attempted'], MAX_TRANSITIONS)
        self.assertLessEqual(r['distinct_states'], MAX_STATES)
        self.assertLessEqual(r['depth_effective'], MAX_DEPTH)
        self.assertTrue(all(r['boundary_attempts'][name] > 0 for name in ('before', 'equal', 'after')))

    def test_model_safety_invariants(self):
        self.assertEqual(self.report['safety_violation_occurrences'], 0,
                         json.dumps(self.report['counterexamples'], sort_keys=True))

    def test_rejected_events_obey_classified_effect_contract(self):
        # Pure rejection, audit receipt, conservative stop, and independent timeout.
        self.assertEqual(self.report['rejection_violation_occurrences'], 0,
                         json.dumps(self.report['counterexamples'], sort_keys=True))

    def test_unchanged_rejection_is_not_a_failure(self):
        s = m.initialize(IDENTITY, budget=1)
        t = m.Transition(s, ('REJECTED_TRANSITION',))
        self.assertIsNone(rejection_violation(s, t))
