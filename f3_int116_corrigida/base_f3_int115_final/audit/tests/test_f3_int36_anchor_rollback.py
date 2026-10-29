import unittest
from tools.f3_int34_persistence_simulator import Authority, Record
from tools.f3_int36_anchor_rollback_simulator import Anchor, assess_copy, assess_pair, safe_to_promote


class AnchorRollbackTests(unittest.TestCase):
    def setUp(self):
        a = Authority()
        epoch = a.lease('worker')
        for event in ('FENCE', 'JOB_EMPTY', 'CLEANUP'):
            a.append('worker', epoch, event)
        self.records = a.snapshot()
        self.anchor = Anchor(2, self.records[1].checksum)

    def test_exact_anchor_is_not_authority(self):
        result = assess_copy(self.records[:2], self.anchor)
        self.assertEqual(result.status, 'MATCHES_ANCHOR')
        self.assertFalse(result.authoritative)
        self.assertFalse(result.closure_authorized)

    def test_rollback_or_missing_suffix(self):
        self.assertEqual(assess_copy(self.records[:1], self.anchor).status, 'ROLLBACK_OR_INCOMPLETE')

    def test_forged_anchor_conflict(self):
        self.assertEqual(assess_copy(self.records, Anchor(2, 'forged')).status, 'ANCHOR_CONFLICT')

    def test_unverified_suffix_is_not_authority(self):
        result = assess_copy(self.records, self.anchor)
        self.assertEqual(result.status, 'UNVERIFIED_SUFFIX')
        self.assertFalse(safe_to_promote(result))

    def test_pair_prefix_cannot_elect(self):
        status, a, b = assess_pair(self.records[:2], self.records, self.anchor)
        self.assertEqual(status, 'PREFIX_AFTER_ANCHOR_UNCERTAIN')
        self.assertFalse(a.authoritative or b.authoritative)

    def test_pair_divergent_suffix(self):
        other = Authority()
        epoch = other.lease('worker')
        for event in ('FENCE', 'JOB_EMPTY', 'OTHER'):
            other.append('worker', epoch, event)
        status, _, _ = assess_pair(self.records, other.snapshot(), self.anchor)
        self.assertEqual(status, 'DIVERGENT_AFTER_ANCHOR')

    def test_corrupted_record_rejected(self):
        broken = list(self.records)
        old = broken[2]
        broken[2] = Record(old.sequence, old.epoch, 'TAMPERED', old.previous, old.checksum)
        with self.assertRaises(ValueError):
            assess_copy(broken, self.anchor)

    def test_invalid_anchor_and_genesis(self):
        with self.assertRaises(ValueError):
            assess_copy(self.records, Anchor(True, 'GENESIS'))
        self.assertEqual(assess_copy(self.records, Anchor(0, 'GENESIS')).status, 'UNANCHORED_SUFFIX')
        self.assertFalse(safe_to_promote(self.records, Anchor(0, 'GENESIS')))


if __name__ == '__main__':
    unittest.main()
