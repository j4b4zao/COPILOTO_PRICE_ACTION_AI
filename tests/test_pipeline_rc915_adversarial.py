"""RC9.15-A6.6: testes adversariais de integracao temporal."""

from datetime import datetime, timedelta, timezone

import pytest

from analysis.analysis_pipeline import AnalysisPipeline
from analysis.temporal_snapshot_policy import TemporalSnapshotPolicy
from external_context.external_market_state import ExternalMarketState
from models.book_depth import BookDepthSnapshot


NOW = datetime(2026, 11, 18, 15, 0, tzinfo=timezone.utc)

POLICY = TemporalSnapshotPolicy(
    maximum_age_seconds=60,
    future_tolerance_seconds=5,
)


class ExternalService:
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def snapshot(self):
        return ExternalMarketState(
            valid=True,
            timestamp=self.timestamp,
        )


class BookService:
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def snapshot(self, symbol):
        return BookDepthSnapshot.build(
            symbol=symbol,
            timestamp=self.timestamp,
            bids=((100.0, 10, 1),),
            asks=((101.0, 10, 1),),
            source="RC915_ADVERSARIAL",
        )


def iso(offset=0):
    return (NOW + timedelta(seconds=offset)).isoformat()


def make_pipeline(
    external_timestamp=None,
    book_timestamp=None,
    external_policy=POLICY,
    book_policy=POLICY,
    clock=None,
):
    external = ExternalService(
        external_timestamp if external_timestamp is not None
        else iso()
    )

    book = BookService(
        book_timestamp if book_timestamp is not None
        else iso()
    )

    pipeline = AnalysisPipeline(
        external_context_service=external,
        book_depth_service=book,
        temporal_external_policy=external_policy,
        temporal_book_policy=book_policy,
        temporal_reference_provider=(
            clock if clock is not None else lambda: NOW
        ),
    )

    pipeline.context.market.symbol = "WINZ26"

    return pipeline, external, book


def refresh(pipeline):
    pipeline._refresh_external_context()
    pipeline._refresh_book_depth()

    return (
        pipeline.context.external_market.valid,
        pipeline.context.book_depth.available,
    )


def test_current_snapshots_accepted():
    pipeline, _, _ = make_pipeline()

    assert refresh(pipeline) == (True, True)


@pytest.mark.parametrize(
    "timestamp",
    [
        iso(-61),
        iso(6),
        "INVALID_TIMESTAMP",
        "2026-11-18T15:00:00",
    ],
)
def test_external_invalid_temporal_snapshot_rejected(timestamp):
    pipeline, _, _ = make_pipeline(
        external_timestamp=timestamp,
    )

    external_valid, book_available = refresh(pipeline)

    assert external_valid is False
    assert book_available is True


@pytest.mark.parametrize(
    "timestamp",
    [
        iso(-61),
        iso(6),
        "INVALID_TIMESTAMP",
        "2026-11-18T15:00:00",
    ],
)
def test_book_invalid_temporal_snapshot_rejected(timestamp):
    pipeline, _, _ = make_pipeline(
        book_timestamp=timestamp,
    )

    external_valid, book_available = refresh(pipeline)

    assert external_valid is True
    assert book_available is False


def test_regressive_timestamps_rejected():
    pipeline, external, book = make_pipeline()

    assert refresh(pipeline) == (True, True)

    external.timestamp = iso(-10)
    book.timestamp = iso(-10)

    assert refresh(pipeline) == (False, False)


def test_repeated_timestamps_accepted():
    pipeline, _, _ = make_pipeline()

    assert refresh(pipeline) == (True, True)
    assert refresh(pipeline) == (True, True)


def test_recovery_after_rejection():
    pipeline, external, book = make_pipeline(
        external_timestamp=iso(-61),
        book_timestamp=iso(-61),
    )

    assert refresh(pipeline) == (False, False)

    external.timestamp = iso()
    book.timestamp = iso()

    assert refresh(pipeline) == (True, True)


def test_external_and_book_independent():
    pipeline, external, book = make_pipeline()

    assert refresh(pipeline) == (True, True)

    external.timestamp = iso(-61)

    assert refresh(pipeline) == (False, True)

    external.timestamp = iso()
    book.timestamp = iso(-61)

    assert refresh(pipeline) == (True, False)


def test_disabled_policies_preserve_legacy_behavior():
    pipeline, _, _ = make_pipeline(
        external_timestamp="INVALID_TIMESTAMP",
        book_timestamp="INVALID_TIMESTAMP",
        external_policy=None,
        book_policy=None,
    )

    assert refresh(pipeline) == (True, True)


def test_reference_clock_failure_rejects_both():
    def failing_clock():
        raise RuntimeError("CLOCK_FAILURE")

    pipeline, _, _ = make_pipeline(
        clock=failing_clock,
    )

    assert refresh(pipeline) == (False, False)


def test_invalid_reference_clock_rejects_both():
    pipeline, _, _ = make_pipeline(
        clock=lambda: None,
    )

    assert refresh(pipeline) == (False, False)


def test_future_tolerance_boundary():
    pipeline, _, _ = make_pipeline(
        external_timestamp=iso(5),
        book_timestamp=iso(5),
    )

    assert refresh(pipeline) == (True, True)


def test_staleness_boundary():
    pipeline, _, _ = make_pipeline(
        external_timestamp=iso(-60),
        book_timestamp=iso(-60),
    )

    assert refresh(pipeline) == (True, True)
