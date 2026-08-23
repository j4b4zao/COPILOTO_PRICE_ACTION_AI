from types import SimpleNamespace

from analysis.book_depth_analysis import BookDepthAnalysis
from models.book_depth import BookDepthSnapshot
from models.book_depth_analysis_result import BookDepthAnalysisResult


def _context(bids, asks, pa_bias="BUY", of_pressure="BUY"):
    book = BookDepthSnapshot.build(
        symbol="WINV26",
        timestamp="2026-08-23T10:00:00",
        bids=bids,
        asks=asks,
        source="TEST",
    )
    return SimpleNamespace(
        book_depth=book,
        book_depth_analysis=BookDepthAnalysisResult(),
        price_action=SimpleNamespace(bias=pa_bias),
        order_flow=SimpleNamespace(pressure=of_pressure),
    )


def test_unavailable_book_skips():
    context = SimpleNamespace(
        book_depth=BookDepthSnapshot.unavailable("WINV26"),
        book_depth_analysis=BookDepthAnalysisResult(),
        price_action=SimpleNamespace(bias="BUY"),
        order_flow=SimpleNamespace(pressure="BUY"),
    )
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.pressure == "UNAVAILABLE"


def test_bid_dominant_book_aligns_with_buy():
    context = _context([(100, 100), (99, 80)], [(101, 20), (102, 20)])
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.pressure == "BID_DOMINANT"
    assert context.book_depth_analysis.price_action_alignment == "ALIGNED"


def test_ask_dominant_book_aligns_with_sell():
    context = _context([(100, 20), (99, 20)], [(101, 100), (102, 80)], "SELL", "SELL")
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.pressure == "ASK_DOMINANT"
    assert context.book_depth_analysis.price_action_alignment == "ALIGNED"


def test_book_conflict_with_price_action():
    context = _context([(100, 100), (99, 80)], [(101, 20), (102, 20)], "SELL", "BUY")
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.price_action_alignment == "CONFLICT"


def test_order_flow_duplicate_risk_when_same_direction():
    context = _context([(100, 100), (99, 80)], [(101, 20), (102, 20)], "BUY", "BUY")
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.duplicate_evidence_risk is True


def test_no_duplicate_risk_when_order_flow_differs():
    context = _context([(100, 100), (99, 80)], [(101, 20), (102, 20)], "BUY", "SELL")
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.duplicate_evidence_risk is False


def test_balanced_book_is_neutral():
    context = _context([(100, 50), (99, 50)], [(101, 50), (102, 50)])
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.pressure == "BALANCED"
    assert context.book_depth_analysis.price_action_alignment == "NEUTRAL"


def test_spread_ratio_is_positive():
    context = _context([(100, 60)], [(101, 40)])
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.spread == 1.0
    assert context.book_depth_analysis.spread_ratio > 0


def test_concentration_metrics_are_clamped():
    context = _context(
        [(100, 60), (99, 30), (98, 10), (97, 1)],
        [(101, 20), (102, 20), (103, 20), (104, 40)],
    )
    BookDepthAnalysis().executar(context)
    result = context.book_depth_analysis
    assert 0.0 <= result.top_bid_concentration <= 1.0
    assert 0.0 <= result.top_ask_concentration <= 1.0


def test_clear_resets_result():
    result = BookDepthAnalysisResult(pressure="BID_DOMINANT", imbalance=0.7, confidence=0.8)
    result.clear()
    assert result.pressure == "UNAVAILABLE"
    assert result.imbalance == 0.0
    assert result.confidence == 0.0
    assert result.passive_only is True
