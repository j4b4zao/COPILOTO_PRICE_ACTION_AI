import unittest
from datetime import datetime, timedelta, timezone

from analysis.research.intermarket_context_observer import (
    IntermarketContextObserver,
    IntermarketPoint,
)


class IntermarketContextObserverTests(unittest.TestCase):
    def test_ready_requires_every_asset_fresh_and_aligned(self):
        now = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)
        result = IntermarketContextObserver.audit_readiness(
            (
                IntermarketPoint("equity", now, 100.0),
                IntermarketPoint("usdbrl", now - timedelta(seconds=2), 5.4),
                IntermarketPoint("rates", now - timedelta(seconds=5), 12.0),
            ),
            required_assets=("EQUITY", "USDBRL", "RATES"),
            reference_timestamp=now,
            maximum_staleness_seconds=5,
        )
        self.assertEqual(result.status, "DATA_READY")
        self.assertEqual(result.maximum_observed_skew_seconds, 5.0)
        self.assertFalse(result.score_influence_allowed)
        self.assertFalse(result.order_execution_allowed)

    def test_missing_or_stale_is_not_coerced_to_neutral(self):
        now = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)
        result = IntermarketContextObserver.audit_readiness(
            (IntermarketPoint("equity", now - timedelta(seconds=11), 100.0),),
            required_assets=("EQUITY", "USDBRL"),
            reference_timestamp=now,
            maximum_staleness_seconds=10,
        )
        self.assertEqual(result.status, "DATA_NOT_READY")
        self.assertEqual(result.missing_assets, ("USDBRL",))
        self.assertEqual(result.stale_assets, ("EQUITY",))

    def test_future_timestamp_is_stale_and_inputs_are_validated(self):
        now = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)
        result = IntermarketContextObserver.audit_readiness(
            (IntermarketPoint("equity", now + timedelta(seconds=1), 100.0),),
            required_assets=("EQUITY",),
            reference_timestamp=now,
            maximum_staleness_seconds=10,
        )
        self.assertEqual(result.status, "DATA_NOT_READY")
        with self.assertRaises(ValueError):
            IntermarketPoint("equity", datetime(2026, 9, 4), 100.0)


if __name__ == "__main__":
    unittest.main()
