"""F3-INT-34 simulated crash/replay/fencing tests; no disk or native APIs."""
import unittest
from dataclasses import replace
from tools.f3_int34_persistence_simulator import (
    Authority, SimulatedCrash, StaleAuthority, replay, safe_to_claim_native)


class SimulatedPersistence(unittest.TestCase):
    def test_before_append_crash_leaves_no_record(self):
        a = Authority()
        epoch = a.lease('worker-a')
        with self.assertRaises(SimulatedCrash):
            a.append('worker-a', epoch, 'qualification', 'before_append')
        self.assertEqual(a.snapshot(), ())
        self.assertEqual(replay(a.snapshot()), 'GENESIS')

    def test_after_append_crash_requires_replay_not_guessing(self):
        a = Authority()
        epoch = a.lease('worker-a')
        with self.assertRaises(SimulatedCrash):
            a.append('worker-a', epoch, 'qualification', 'after_append')
        self.assertEqual(len(a.snapshot()), 1)
        self.assertEqual(replay(a.snapshot()), a.snapshot()[-1].checksum)

    def test_lease_rotation_fences_stale_writer(self):
        a = Authority()
        first = a.lease('worker-a')
        a.append('worker-a', first, 'qualification')
        second = a.lease('worker-b')
        with self.assertRaises(StaleAuthority):
            a.append('worker-a', first, 'closure')
        a.append('worker-b', second, 'new-evidence')
        self.assertEqual(len(a.snapshot()), 2)
        replay(a.snapshot())

    def test_snapshot_is_not_an_authority_and_tamper_rejected(self):
        a = Authority()
        epoch = a.lease('worker-a')
        a.append('worker-a', epoch, 'qualification')
        snapshot = a.snapshot()
        with self.assertRaises(ValueError):
            replay((replace(snapshot[0], event='forged'),))
        self.assertEqual(replay(snapshot), snapshot[0].checksum)
        self.assertFalse(hasattr(snapshot, 'append'))

    def test_reorder_duplicate_and_missing_record_rejected(self):
        a = Authority()
        epoch = a.lease('worker-a')
        a.append('worker-a', epoch, 'first')
        a.append('worker-a', epoch, 'second')
        records = a.snapshot()
        for bad in ((records[1], records[0]), (records[0], records[0]), (records[1],)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                replay(bad)

    def test_simulated_authority_never_certifies_native_or_orders(self):
        a = Authority()
        epoch = a.lease('worker-a')
        a.append('worker-a', epoch, 'CLOSED_RECOVERED_SIMULATED')
        self.assertFalse(safe_to_claim_native(a))
        self.assertFalse(hasattr(a, 'orders_allowed'))


if __name__ == '__main__':
    unittest.main()
