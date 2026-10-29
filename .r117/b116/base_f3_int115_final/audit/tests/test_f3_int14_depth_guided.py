"""F3-INT-14: bounded depth-first exploration of pure simulated transitions only."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

SOURCE = Path(__file__).with_name('test_f3_int10_architecture_c_adversarial.py')
spec = importlib.util.spec_from_file_location('f3_int14_base', SOURCE)
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)
m = a.m
MAX_DEPTH = 7
MAX_EDGES = 30000
# Include all nine phase prefixes; use depth-first priority instead of broad BFS.
EVENTS = (m.Kind.TICK, m.Kind.CANCEL, m.Kind.CREATE_RETURNED,
          m.Kind.CREATION_UNCERTAIN, m.Kind.AUXILIARY_EXIT,
          m.Kind.TARGET_EXIT, m.Kind.RESUME_COMMIT,
          m.Kind.RESUME_CONFIRMED, m.Kind.WITNESS_FAILED,
          m.Kind.JOB_EMPTY, m.Kind.CLEANUP_SUCCEEDED, m.Kind.CLOSE)


def explore_deep():
    root = m.initialize(a.IDENTITY, budget=1)
    prefix = (m.Kind.PREPARE_QUALIFIED, m.Kind.ACCEPT, m.Kind.LAUNCH_BEGIN,
              m.Kind.CREATE_RETURNED, m.Kind.CONTAINMENT_CONFIRMED,
              m.Kind.RESUME_COMMIT, m.Kind.RESUME_CONFIRMED,
              m.Kind.TARGET_EXIT, m.Kind.FUNCTIONAL_COMPLETE,
              m.Kind.AUXILIARY_EXIT, m.Kind.JOB_EMPTY,
              m.Kind.CLEANUP_SUCCEEDED, m.Kind.CLOSE)
    seeds = [(root, ())]
    s = root
    for k in prefix:
        e = a.normal_event(s, k)
        s = m.advance(s, e, now=0).state
        seeds.append((s, tuple(x.value for x in prefix[:len(seeds)])))
    # Reverse for shallow preparation seed first; DFS dives before expanding siblings.
    stack = [(s, trace, 0) for s, trace in reversed(seeds)]
    seen = set()
    report = dict(attempted=0, accepted=0, rejected=0, no_effect=0,
                  exceptions=0, violations=0, rejection_violations=0,
                  depth_effective=0, states=0, counterexamples=[],
                  deadline_before=0, deadline_equal=0, deadline_after=0)
    while stack and report['attempted'] < MAX_EDGES:
        s, trace, depth = stack.pop()
        key = (a.operational_key(s), depth)
        if key in seen:
            continue
        seen.add(key)
        report['states'] += 1
        report['depth_effective'] = max(report['depth_effective'], depth)
        if depth >= MAX_DEPTH:
            continue
        candidates = []
        for kind in EVENTS:
            event = a.normal_event(s, kind)
            times = [s.last_now]
            if s.deadline is not None:
                from math import nextafter
                times += [t for t in (nextafter(s.deadline, -float('inf')),
                          s.deadline, nextafter(s.deadline, float('inf'))) if t >= s.last_now]
            for now in dict.fromkeys(times):
                candidates.append((event, now))
        # Add explicit native unsupported claim and stale session.
        e = a.normal_event(s, m.Kind.PREPARE_QUALIFIED)
        candidates.append((m.Event('native-'+str(depth), e.kind, e.identity,
                           e.launch_attempt_id, e.process, True, m.Domain.NATIVE), s.last_now))
        for event, now in candidates:
            if report['attempted'] >= MAX_EDGES:
                break
            report['attempted'] += 1
            if s.deadline is not None:
                from math import nextafter
                if now == nextafter(s.deadline, -float('inf')): report['deadline_before'] += 1
                if now == s.deadline: report['deadline_equal'] += 1
                if now == nextafter(s.deadline, float('inf')): report['deadline_after'] += 1
            try:
                t = m.advance(s, event, now=now)
            except Exception as exc:
                report['exceptions'] += 1
                report['counterexamples'].append([trace, event.kind.value, str(exc)])
                continue
            violations = a.safety_violations(s, t.state, event, t.decisions)
            rejection = a.rejection_violation(s, t)
            if violations or rejection:
                report['violations'] += bool(violations)
                report['rejection_violations'] += bool(rejection)
                if len(report['counterexamples']) < 5:
                    report['counterexamples'].append([trace, event.kind.value, now, violations, rejection])
            if any(code.startswith('REJECTED_') for code in t.decisions):
                report['rejected'] += 1
            elif any(code in ('DUPLICATE_NO_EFFECT','TERMINAL_NO_EFFECT','PARTIAL_EMPTY_OBSERVATION_ONLY') for code in t.decisions):
                report['no_effect'] += 1
            else:
                report['accepted'] += 1
            # Explore only meaningful non-rejected effects; push reversed to prioritize first branch.
            if not violations and not rejection and not any(code.startswith('REJECTED_') for code in t.decisions) and a.operational_key(s) != a.operational_key(t.state):
                stack.append((t.state, trace + (event.kind.value,), depth+1))
    report['stop_reason'] = 'EDGE_LIMIT' if report['attempted'] >= MAX_EDGES else 'EXHAUSTED'
    return report


class DepthGuidedAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = explore_deep()
        print('F3_INT14_REPORT='+json.dumps(cls.report, sort_keys=True), flush=True)

    def test_safety(self):
        self.assertEqual((self.report['violations'], self.report['exceptions']), (0,0), self.report['counterexamples'])

    def test_rejection_contract(self):
        self.assertEqual(self.report['rejection_violations'], 0, self.report['counterexamples'])

    def test_depth_and_accounting(self):
        r = self.report
        self.assertEqual(r['attempted'], r['accepted']+r['rejected']+r['no_effect']+r['exceptions'])
        self.assertGreaterEqual(r['depth_effective'], 5)
        self.assertTrue(all(r['deadline_'+k] > 0 for k in ('before','equal','after')))
