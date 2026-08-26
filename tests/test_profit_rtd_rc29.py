from types import SimpleNamespace

from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder


def _delta(status="VALID", dominance=0.4, persistence=0.5, recent_delta=120.0, aggression=500.0):
    return SimpleNamespace(
        status=status,
        recent_delta=recent_delta,
        recent_total_aggression=aggression,
        dominance=dominance,
        persistence=persistence,
        acceleration=0.1,
    )


def _book(status="VALID", imbalance=0.25, spread=15.0):
    return SimpleNamespace(
        status=status,
        imbalance=imbalance,
        spread=spread,
        levels_bid=50,
        levels_ask=50,
    )


def test_rc29_bullish_alignment_is_observational_only():
    ctx = OrderFlowObservationalContextBuilder.build(
        delta_report=_delta(dominance=0.4),
        book_report=_book(imbalance=0.25),
        symbol="WINV26",
    )
    assert ctx.status == "READY"
    assert ctx.directional_alignment == "BULLISH_ALIGNED"
    assert ctx.confidence > 0
    assert ctx.observational_only is True
    assert ctx.score_influence_allowed is False
    assert ctx.decision_influence_allowed is False
    assert ctx.order_execution_allowed is False


def test_rc29_bearish_alignment():
    ctx = OrderFlowObservationalContextBuilder.build(
        delta_report=_delta(dominance=-0.5),
        book_report=_book(imbalance=-0.30),
        symbol="WINV26",
    )
    assert ctx.status == "READY"
    assert ctx.directional_alignment == "BEARISH_ALIGNED"


def test_rc29_divergence_is_explicit():
    ctx = OrderFlowObservationalContextBuilder.build(
        delta_report=_delta(dominance=0.5),
        book_report=_book(imbalance=-0.30),
        symbol="WINV26",
    )
    assert ctx.status == "READY"
    assert ctx.directional_alignment == "DIVERGENT"
    assert "DELTA_BOOK_DIVERGENCE" in ctx.reasons


def test_rc29_degraded_source_cannot_be_ready():
    ctx = OrderFlowObservationalContextBuilder.build(
        delta_report=_delta(status="DEGRADED"),
        book_report=_book(status="VALID"),
        symbol="WINV26",
    )
    assert ctx.status == "DEGRADED"
    assert ctx.confidence == 0.0
    assert "DELTA_DEGRADED" in ctx.reasons
    assert ctx.score_influence_allowed is False
    assert ctx.decision_influence_allowed is False
    assert ctx.order_execution_allowed is False
