import unittest

from datetime import datetime, timedelta, timezone

from analysis.temporal_snapshot_policy import (
    TemporalSnapshotPolicy,
    validate_snapshot_timestamp,
)


class TestTemporalSnapshotPolicy(unittest.TestCase):

    def setUp(self):
        self.now = datetime(
            2026, 11, 18, 15, 0,
            tzinfo=timezone.utc,
        )
        self.policy = TemporalSnapshotPolicy(
            maximum_age_seconds=60,
            future_tolerance_seconds=5,
        )

    def check(self, timestamp, expected, previous=None):
        result = validate_snapshot_timestamp(
            timestamp,
            reference_timestamp=self.now,
            policy=self.policy,
            previous_timestamp=previous,
        )
        self.assertEqual(result.reason, expected)

    def test_current(self):
        self.check(
            self.now.isoformat(),
            "TEMPORAL_ACCEPTED",
        )

    def test_stale(self):
        self.check(
            (self.now - timedelta(seconds=61)).isoformat(),
            "TEMPORAL_STALE_TIMESTAMP",
        )

    def test_future(self):
        self.check(
            (self.now + timedelta(seconds=6)).isoformat(),
            "TEMPORAL_FUTURE_TIMESTAMP",
        )

    def test_invalid(self):
        self.check(
            "INVALID_TIMESTAMP",
            "TEMPORAL_INVALID_TIMESTAMP",
        )

    def test_naive(self):
        self.check(
            "2026-11-18T15:00:00",
            "TEMPORAL_INVALID_TIMESTAMP",
        )

    def test_regressive(self):
        self.check(
            (self.now - timedelta(seconds=10)).isoformat(),
            "TEMPORAL_REGRESSIVE_TIMESTAMP",
            previous=self.now.isoformat(),
        )

    def test_repeated(self):
        timestamp = self.now.isoformat()
        self.check(
            timestamp,
            "TEMPORAL_ACCEPTED",
            previous=timestamp,
        )

    def test_future_within_tolerance(self):
        self.check(
            (self.now + timedelta(seconds=5)).isoformat(),
            "TEMPORAL_ACCEPTED",
        )

    def test_stale_boundary(self):
        self.check(
            (self.now - timedelta(seconds=60)).isoformat(),
            "TEMPORAL_ACCEPTED",
        )

    def test_invalid_policy(self):
        with self.assertRaises(ValueError):
            TemporalSnapshotPolicy(-1)

    def test_naive_reference(self):
        with self.assertRaises(ValueError):
            validate_snapshot_timestamp(
                self.now.isoformat(),
                reference_timestamp=datetime(2026, 11, 18),
                policy=self.policy,
            )


if __name__ == "__main__":
    unittest.main()