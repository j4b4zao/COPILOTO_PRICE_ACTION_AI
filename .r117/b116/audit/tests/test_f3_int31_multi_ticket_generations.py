"""F3-INT-31: bounded multi-ticket and cross-generation adversarial replay, simulation only."""
import importlib.util
import itertools
from pathlib import Path
import sys
import unittest

p = Path(__file__).with_name('test_f3_int28_sequence_minimizer.py')
spec = importlib.util.spec_from_file_location('int31_replay', p)
base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)


def replay_tickets(actions):
    """Keep each ticket separately; closing an older ticket must never inherit newer proof."""
    h = base.base.CombinedFaults().h()
    tickets = []
    outcomes = []
    for action in actions:
        if action == 'CREATE_A':
            h.put(h.fact('C', 'a', 'CREATED', processes=(h.target,)))
        elif action == 'CREATE_B':
            h.put(h.fact('C', 'b', 'CREATED', processes=(h.child,)))
        elif action == 'QUALIFY':
            tickets.append(h.eligible())
        elif action == 'NEW_GENERATION':
            h.lease = h.r.acquire(h.s.generation + 1, 'exclusive-' + str(h.s.generation + 1))
        elif action == 'NEGATIVE_JOB':
            h.put(h.fact('J', 'JOB', 'NONEMPTY'))
        elif action == 'NEGATIVE_CLEANUP':
            h.put(h.fact('L', 'RESOURCES', 'FAILED'))
        elif action == 'LATE_CONFLICT':
            h.put(h.fact('C', 'b', 'CREATED', processes=(h.target, h.child)))
        elif action.startswith('CLOSE_'):
            index = int(action.split('_')[1])
            outcomes.append(bool(h.r.close(tickets[index])))
        else:
            raise ValueError(action)
        h.check()
        assert h.s.original.revoked and h.s.original.admission_closed
        assert not h.s.aggregate_success
        assert not any(getattr(h.s, flag, False) for flag in base.m.FLAGS)
    return h, tickets, outcomes


class MultiTicketGenerations(unittest.TestCase):
    def test_two_tickets_cross_generation_with_both_close_orders(self):
        for fault in ('NEW_GENERATION', 'NEGATIVE_JOB', 'NEGATIVE_CLEANUP', 'LATE_CONFLICT'):
            for order in ((0, 1), (1, 0)):
                with self.subTest(fault=fault, order=order):
                    trace = ('CREATE_A', 'CREATE_B', 'QUALIFY', fault, 'QUALIFY') + tuple('CLOSE_' + str(i) for i in order)
                    h, tickets, outcomes = replay_tickets(trace)
                    self.assertEqual(len(tickets), 2)
                    if fault in ('NEGATIVE_JOB', 'NEGATIVE_CLEANUP'):
                        # A new qualification creates fresh J/L evidence; only the new ticket may close.
                        self.assertEqual(outcomes, [False, True] if order == (0, 1) else [True, False])
                    else:
                        self.assertEqual(outcomes, [False, False])
                        self.assertNotEqual(h.s.phase, base.m.Phase.CLOSED_RECOVERED)

    def test_multiple_mutations_between_two_tickets(self):
        faults = ('NEW_GENERATION', 'NEGATIVE_JOB', 'NEGATIVE_CLEANUP', 'LATE_CONFLICT')
        for first, second in itertools.permutations(faults, 2):
            trace = ('CREATE_A', 'CREATE_B', 'QUALIFY', first, second, 'QUALIFY', 'CLOSE_0', 'CLOSE_1')
            h, _, outcomes = replay_tickets(trace)
            if set((first, second)) == {'NEGATIVE_JOB', 'NEGATIVE_CLEANUP'}:
                self.assertEqual(outcomes, [False, True], (first, second))
            else:
                self.assertEqual(outcomes, [False, False], (first, second))
                self.assertNotEqual(h.s.phase, base.m.Phase.CLOSED_RECOVERED)

    def test_three_tickets_with_repeated_generation_changes(self):
        for order in itertools.permutations((0, 1, 2)):
            trace = ('CREATE_A', 'CREATE_B', 'QUALIFY', 'NEW_GENERATION', 'QUALIFY',
                     'NEW_GENERATION', 'QUALIFY') + tuple('CLOSE_' + str(i) for i in order)
            h, tickets, outcomes = replay_tickets(trace)
            self.assertEqual(len(tickets), 3)
            self.assertEqual(outcomes, [False] * 3)
            self.assertNotEqual(h.s.phase, base.m.Phase.CLOSED_RECOVERED)

    def test_no_cross_ticket_proof_laundering_after_conflict(self):
        for order in itertools.permutations(('QUALIFY', 'LATE_CONFLICT', 'NEGATIVE_JOB')):
            # A negative condition before or after qualification must not be cleared by a second ticket.
            trace = ('CREATE_A', 'CREATE_B') + order + ('QUALIFY', 'CLOSE_0', 'CLOSE_1')
            h, _, outcomes = replay_tickets(trace)
            self.assertEqual(outcomes, [False, False], order)
            self.assertNotEqual(h.s.phase, base.m.Phase.CLOSED_RECOVERED)

if __name__ == '__main__':
    unittest.main()
