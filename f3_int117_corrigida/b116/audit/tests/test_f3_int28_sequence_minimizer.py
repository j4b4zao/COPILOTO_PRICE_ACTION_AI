"""F3-INT-28: bounded deterministic replay and delta minimization, simulated only."""
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest

p = Path(__file__).resolve().parent / 'test_f3_int26_combined_faults.py'
spec = importlib.util.spec_from_file_location('int28_base', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)
m = base.m

ACTIONS = ('CREATE_A', 'CREATE_B', 'NEGATIVE_JOB', 'NEGATIVE_CLEANUP', 'NEW_GENERATION')


def replay(actions):
    h = base.CombinedFaults().h()
    ticket = None
    closure_accepted = False
    for action in actions:
        if action == 'CREATE_A':
            h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        elif action == 'CREATE_B':
            h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
        elif action == 'NEGATIVE_JOB':
            h.put(h.fact('J', 'JOB', 'NONEMPTY'))
        elif action == 'NEGATIVE_CLEANUP':
            h.put(h.fact('L', 'RESOURCES', 'FAILED'))
        elif action == 'NEW_GENERATION':
            h.lease = h.r.acquire(h.s.generation + 1, 'exclusive-' + str(h.s.generation + 1))
        elif action == 'QUALIFY':
            ticket = h.eligible()
        elif action == 'CLOSE':
            closure_accepted = bool(h.r.close(ticket))
        elif action == 'LATE_CONFLICT':
            h.put(h.fact('C', 'b', 'CREATED', processes=(h.target, h.child)))
        else:
            raise ValueError(action)
        h.check()
        assert h.s.original.revoked and h.s.original.admission_closed
        assert not h.s.aggregate_success
        assert not any(getattr(h.s, flag, False) for flag in m.FLAGS)
    return h, closure_accepted


def minimize(trace, predicate):
    """Deterministic 1-minimal deletion reduction; not globally shortest."""
    candidate = tuple(trace)
    if not predicate(candidate):
        raise ValueError('INPUT_DOES_NOT_REPRODUCE')
    changed = True
    while changed:
        changed = False
        for index in range(len(candidate)):
            smaller = candidate[:index] + candidate[index + 1:]
            if predicate(smaller):
                candidate = smaller
                changed = True
                break
    return candidate


class SequenceAndMinimizer(unittest.TestCase):
    def test_bounded_permutations_never_close_with_negative_j_or_l(self):
        # 5! = 120 bounded permutations; append qualification and close.
        for order in itertools.permutations(ACTIONS):
            with self.subTest(order=order):
                h, accepted = replay(order + ('QUALIFY', 'CLOSE'))
                self.assertFalse(accepted)
                self.assertNotEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)

    def test_stale_ticket_under_late_mutation(self):
        for fault in ('NEGATIVE_JOB', 'NEGATIVE_CLEANUP', 'NEW_GENERATION', 'LATE_CONFLICT'):
            with self.subTest(fault=fault):
                h, accepted = replay(('CREATE_A', 'CREATE_B', 'QUALIFY', fault, 'CLOSE'))
                self.assertFalse(accepted)
                self.assertNotEqual(h.s.phase, m.Phase.CLOSED_RECOVERED)

    def test_minimizer_removes_irrelevant_actions(self):
        # Synthetic oracle for reduction engine; does not claim a model bug.
        def predicate(seq):
            return 'NEGATIVE_JOB' in seq and 'CLOSE' in seq and seq.index('NEGATIVE_JOB') < seq.index('CLOSE')
        trace = ('CREATE_A', 'NEGATIVE_JOB', 'CREATE_B', 'NEW_GENERATION', 'CLOSE', 'CREATE_A')
        result = minimize(trace, predicate)
        self.assertEqual(result, ('NEGATIVE_JOB', 'CLOSE'))
        self.assertTrue(predicate(result))
        for i in range(len(result)):
            self.assertFalse(predicate(result[:i] + result[i+1:]))

    def test_minimizer_rejects_non_reproducer(self):
        with self.assertRaisesRegex(ValueError, 'INPUT_DOES_NOT_REPRODUCE'):
            minimize(('CREATE_A',), lambda s: 'NEGATIVE_JOB' in s)


if __name__ == '__main__':
    unittest.main()
