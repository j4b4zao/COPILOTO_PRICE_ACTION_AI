from dataclasses import FrozenInstanceError

from analysis.analysis_pipeline import AnalysisPipeline
from core.analysis_context import AnalysisContext
from models.book_depth import BookDepthSnapshot, BookLevel


class HostileBookService:
    def __init__(self):
        self.mutable_bids = [
            BookLevel(price=100.0, quantity=100.0)
        ]

        self.mutable_asks = [
            BookLevel(price=101.0, quantity=20.0)
        ]

        self.state = BookDepthSnapshot(
            symbol="WINZ26",
            timestamp="2026-11-17T10:00:00",
            bids=self.mutable_bids,
            asks=self.mutable_asks,
            source="ADVERSARIAL",
            available=True,
        )

    def snapshot(self, symbol):
        return self.state


def test_rc910_normal_snapshot_is_immutable():
    snapshot = BookDepthSnapshot.build(
        symbol="WINZ26",
        timestamp="2026-11-17T10:00:00",
        bids=[(100.0, 100.0)],
        asks=[(101.0, 20.0)],
        source="TEST",
    )

    assert isinstance(snapshot.bids, tuple)
    assert isinstance(snapshot.asks, tuple)

    try:
        snapshot.available = False
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("RC910_FROZEN_CONTRACT_BROKEN")


def test_rc910_direct_constructor_accepts_mutable_levels():
    service = HostileBookService()

    assert isinstance(service.state.bids, list)
    assert isinstance(service.state.asks, list)


def test_rc910_hostile_service_mutates_official_book():
    service = HostileBookService()

    pipeline = AnalysisPipeline(
        book_depth_service=service
    )

    context = AnalysisContext()
    context.market.symbol = "WINZ26"

    pipeline.context = context
    pipeline._refresh_book_depth()

    assert context.book_available is True

    initial_imbalance = context.book_imbalance

    service.mutable_bids.clear()

    assert context.book_imbalance == initial_imbalance, (
        "RC910_VULNERABILIDADE_BOOK_MUTADO"
    )
