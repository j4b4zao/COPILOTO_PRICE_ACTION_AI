"""Read-only split-brain and rollback tests; no real persistence."""
import unittest
from tools.f3_int34_persistence_simulator import Authority, Record
from tools.f3_int35_reconciliation_simulator import reconcile, safe_to_promote


class ReconciliationAdversarial(unittest.TestCase):
    def setUp(self):
        self.a = Authority()
        self.epoch = self.a.lease('w')
        self.a.append('w', self.epoch, 'first')
        self.first = self.a.snapshot()
        self.a.append('w', self.epoch, 'second')
        self.full = self.a.snapshot()

    def test_identical_snapshots_not_authoritative(self):
        result = reconcile(self.full, self.full)
        self.assertEqual(result.status, 'IDENTICAL_UNVERIFIED')
        self.assertFalse(result.authoritative)
        self.assertFalse(result.closure_authorized)
        self.assertFalse(safe_to_promote(result))

    def test_prefix_snapshot_cannot_prove_rollback_or_commit(self):
        result = reconcile(self.first, self.full)
        self.assertEqual(result.status, 'PREFIX_UNCERTAIN')
        self.assertEqual(result.common_length, 1)
        self.assertFalse(result.authoritative)

    def test_valid_divergent_histories_are_rejected(self):
        b = Authority()
        e = b.lease('w')
        b.append('w', e, 'first')
        b.append('w', e, 'different-second')
        result = reconcile(self.full, b.snapshot())
        self.assertEqual(result.status, 'DIVERGENT')
        self.assertFalse(result.closure_authorized)

    def test_corrupted_copy_fails_closed(self):
        bad = (Record(1, 1, 'forged', 'GENESIS', 'fake'),)
        with self.assertRaises(ValueError):
            reconcile(self.full, bad)

    def test_anchor_missing_in_short_copy_blocks_reconciliation(self):
        anchor = (2, self.full[1].checksum)
        result = reconcile(self.first, self.full, anchor)
        self.assertEqual(result.status, 'ANCHOR_MISSING_FROM_COPY')
        self.assertFalse(result.authoritative)
        self.assertEqual(reconcile(self.full, self.full, (2, 'wrong')).status, 'ANCHOR_NOT_FOUND')

    def test_even_matching_anchor_does_not_promote_snapshot(self):
        result = reconcile(self.full, self.full, (2, self.full[1].checksum))
        self.assertEqual(result.status, 'IDENTICAL_UNVERIFIED')
        self.assertFalse(safe_to_promote(result))


if __name__ == '__main__':
    unittest.main()
