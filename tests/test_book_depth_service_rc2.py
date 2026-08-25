from models.book_depth import BookDepthProvider, BookDepthSnapshot
from market.book_depth_service import BookDepthCollector, BookDepthService
from core.analysis_context import AnalysisContext


class Provider(BookDepthProvider):
    SOURCE = "TEST"

    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error

    def snapshot(self, symbol):
        if self.error:
            raise self.error
        return self.value


def _snapshot(symbol="WINV26"):
    return BookDepthSnapshot.build(
        symbol=symbol,
        timestamp="2026-08-23T10:00:00",
        bids=[(100.0, 120, 3), (99.5, 80, 2), (99.0, 50, 1)],
        asks=[(100.5, 70, 2), (101.0, 50, 1), (101.5, 30, 1)],
        source="TEST",
    )


def test_collector_returns_valid_snapshot():
    result = BookDepthCollector(Provider(_snapshot())).collect("WINV26")
    assert result.available is True
    assert result.symbol == "WINV26"


def test_collector_limits_levels():
    result = BookDepthCollector(Provider(_snapshot()), levels=2).collect("WINV26")
    assert len(result.bids) == 2
    assert len(result.asks) == 2


def test_empty_symbol_is_unavailable():
    result = BookDepthCollector(Provider(_snapshot())).collect("")
    assert result.available is False
    assert result.source == "BOOK_SYMBOL_UNAVAILABLE"


def test_provider_error_is_fail_safe():
    result = BookDepthCollector(Provider(error=RuntimeError("offline"))).collect("WINV26")
    assert result.available is False
    assert result.source == "TEST:PROVIDER_ERROR"


def test_invalid_provider_payload_is_fail_safe():
    result = BookDepthCollector(Provider({"bids": []})).collect("WINV26")
    assert result.available is False
    assert result.source == "TEST:INVALID_SNAPSHOT"


def test_symbol_mismatch_is_rejected():
    result = BookDepthCollector(Provider(_snapshot("WDOU26"))).collect("WINV26")
    assert result.available is False
    assert result.source == "TEST:SYMBOL_MISMATCH"


def test_service_refresh_writes_analysis_context():
    context = AnalysisContext()
    context.market.symbol = "WINV26"
    result = BookDepthService(Provider(_snapshot())).refresh(context)
    assert context.book_depth is result
    assert context.book_available is True
    assert context.book_liquidity_pressure == "BID_DOMINANT"


def test_clear_results_preserves_book_snapshot():
    context = AnalysisContext()
    context.book_depth = _snapshot()
    before = context.book_depth
    context.clear_results()
    assert context.book_depth is before


def test_reset_clears_book_snapshot():
    context = AnalysisContext()
    context.book_depth = _snapshot()
    context.reset()
    assert context.book_available is False
    assert context.book_liquidity_pressure == "UNAVAILABLE"


def test_book_properties_expose_read_only_metrics():
    context = AnalysisContext()
    context.book_depth = _snapshot()
    assert context.book_imbalance == context.book_depth.imbalance
    assert context.book_depth.best_bid == 100.0
    assert context.book_depth.best_ask == 100.5
