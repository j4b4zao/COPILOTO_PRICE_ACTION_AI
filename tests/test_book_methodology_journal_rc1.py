import unittest
from dataclasses import replace
from datetime import datetime, timezone

from analysis.research.book_methodology_journal import BookMethodologyJournal


class BookMethodologyJournalTests(unittest.TestCase):
    def test_chain_records_outcome_and_rule_violation_cost(self):
        entries = BookMethodologyJournal.append(
            (), decision_id="D1", recorded_at=datetime.now(timezone.utc),
            thesis="breakout", invalidation="return to range",
            disconfirming_evidence=("weak breadth",), outcome_r=1.5,
        )
        entries = BookMethodologyJournal.append(
            entries, decision_id="D2", recorded_at=datetime.now(timezone.utc),
            thesis="continuation", invalidation="structure failure",
            rule_violation_codes=("CHASED_ENTRY", "CHASED_ENTRY"),
            outcome_r=-1.0, violation_cost_r=0.4,
        )
        result = BookMethodologyJournal.verify(entries)
        self.assertTrue(result.valid)
        self.assertEqual(result.entries, 2)
        self.assertAlmostEqual(result.total_outcome_r, 0.5)
        self.assertAlmostEqual(result.total_violation_cost_r, 0.4)
        self.assertEqual(entries[1].rule_violation_codes, ("CHASED_ENTRY",))
        self.assertFalse(result.decision_influence_allowed)

    def test_tampering_is_detected_and_blocks_append(self):
        entries = BookMethodologyJournal.append(
            (), decision_id="D1", recorded_at=datetime.now(timezone.utc),
            thesis="breakout", invalidation="return to range",
        )
        tampered = (replace(entries[0], thesis="changed after outcome"),)
        result = BookMethodologyJournal.verify(tampered)
        self.assertFalse(result.valid)
        self.assertEqual(result.first_invalid_sequence, 1)
        with self.assertRaises(ValueError):
            BookMethodologyJournal.append(
                tampered, decision_id="D2", recorded_at=datetime.now(timezone.utc),
                thesis="x", invalidation="y",
            )

    def test_timestamp_and_cost_are_validated(self):
        with self.assertRaises(ValueError):
            BookMethodologyJournal.append(
                (), decision_id="D1", recorded_at=datetime.now(),
                thesis="x", invalidation="y",
            )
        with self.assertRaises(ValueError):
            BookMethodologyJournal.append(
                (), decision_id="D1", recorded_at=datetime.now(timezone.utc),
                thesis="x", invalidation="y", violation_cost_r=-0.1,
            )


if __name__ == "__main__":
    unittest.main()
