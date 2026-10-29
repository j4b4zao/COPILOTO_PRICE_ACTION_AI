"""F3-INT-15: bounded, deterministic phase/event coverage audit; simulated only."""
import importlib.util
import json
from collections import Counter
from pathlib import Path
import sys
import unittest

P = Path(__file__).with_name('test_f3_int10_architecture_c_adversarial.py')
spec = importlib.util.spec_from_file_location('f3_int15_base', P)
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)
m = a.m
PREFIX = (m.Kind.PREPARE_QUALIFIED, m.Kind.ACCEPT, m.Kind.LAUNCH_BEGIN,
          m.Kind.CREATE_RETURNED, m.Kind.CONTAINMENT_CONFIRMED,
          m.Kind.RESUME_COMMIT, m.Kind.RESUME_CONFIRMED, m.Kind.TARGET_EXIT,
          m.Kind.FUNCTIONAL_COMPLETE, m.Kind.AUXILIARY_EXIT,
          m.Kind.JOB_EMPTY, m.Kind.CLEANUP_SUCCEEDED, m.Kind.CLOSE)


def audit():
    state = m.initialize(a.IDENTITY, budget=1)
    seeds = [state]
    for kind in PREFIX:
        event = a.normal_event(state, kind)
        state = m.advance(state, event, now=0).state
        seeds.append(state)
    from dataclasses import replace
    native = replace(a.normal_event(seeds[0], m.Kind.PREPARE_QUALIFIED), domain=m.Domain.NATIVE)
    seeds.append(m.advance(seeds[0], native, now=0).state)
    counters = Counter()
    kinds = set()
    phases = set()
    decisions = set()
    pairs = set()
    failures = []
    for state in seeds:
        for kind in m.Kind:
            for variant in ('normal', 'stale', 'native', 'unqualified'):
                event = a.normal_event(state, kind)
                if variant == 'stale':
                    from dataclasses import replace
                    event = replace(event, identity=replace(a.IDENTITY, generation=0))
                elif variant == 'native':
                    from dataclasses import replace
                    event = replace(event, domain=m.Domain.NATIVE)
                elif variant == 'unqualified':
                    from dataclasses import replace
                    event = replace(event, qualified=False)
                times = [state.last_now]
                if state.deadline is not None:
                    from math import nextafter
                    times += [v for v in (nextafter(state.deadline, -float('inf')),
                              state.deadline, nextafter(state.deadline, float('inf')))
                              if v >= state.last_now]
                for now in dict.fromkeys(times):
                    counters['attempted'] += 1
                    try:
                        transition = m.advance(state, event, now=now)
                        issues = a.safety_violations(state, transition.state, event, transition.decisions)
                        reject = a.rejection_violation(state, transition)
                        if issues or reject:
                            failures.append((state.phase.value, kind.value, variant, now, issues, reject))
                        kinds.add(kind.value)
                        phases.add(state.phase.value)
                        decisions.update(transition.decisions)
                        pairs.add((state.phase.value, kind.value))
                        counters['rejected'] += any(c.startswith('REJECTED_') for c in transition.decisions)
                        counters['timeouts'] += 'TIMEOUT_DECIDED' in transition.decisions
                    except Exception as exc:
                        failures.append((state.phase.value, kind.value, variant, now, type(exc).__name__, str(exc)))
    return dict(attempted=counters['attempted'], rejected=counters['rejected'],
                independent_timeouts=counters['timeouts'], phases=sorted(phases),
                event_kinds=sorted(kinds), decision_codes=sorted(decisions),
                phase_kind_pairs=len(pairs), theoretical_phase_kind_pairs=len(m.Phase)*len(m.Kind),
                failures=failures[:10], failure_count=len(failures),
                scope='reachable canonical prefix states; four event variants; deadline boundaries; NOT exhaustive')


class TransitionCoverageAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit()
        print('F3_INT15_REPORT=' + json.dumps(cls.report, sort_keys=True), flush=True)

    def test_no_checked_safety_or_contract_violations(self):
        self.assertEqual(self.report['failure_count'], 0, self.report['failures'])

    def test_all_kinds_and_phases_sampled(self):
        self.assertEqual(set(self.report['event_kinds']), {k.value for k in m.Kind})
        self.assertEqual(set(self.report['phases']), {p.value for p in m.Phase})
        self.assertEqual(self.report['phase_kind_pairs'], self.report['theoretical_phase_kind_pairs'])

    def test_deadline_and_rejection_variants_exercised(self):
        self.assertGreater(self.report['independent_timeouts'], 0)
        self.assertGreater(self.report['rejected'], 0)
        self.assertIn('CONSERVATIVE_STOP_REQUIRED', self.report['decision_codes'])
        self.assertIn('AUDIT_RECORDED', self.report['decision_codes'])
