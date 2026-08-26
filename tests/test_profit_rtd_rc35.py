from types import SimpleNamespace

from market_data.order_flow_observational_context import OrderFlowObservationalContextBuilder


def delta(*, recent_delta, dominance):
    return SimpleNamespace(
        status="VALID",
        recent_delta=recent_delta,
        recent_total_aggression=1000.0,
        dominance=dominance,
        persistence=0.8,
        acceleration=0.0,
    )


def book(imbalance):
    return SimpleNamespace(status="VALID", imbalance=imbalance, spread=5.0, levels_bid=50, levels_ask=50)


def test_rc35_official_context_uses_recent_delta_sign_for_bearish():
    result = OrderFlowObservationalContextBuilder.build(
        delta_report=delta(recent_delta=-500.0, dominance=0.60),
        book_report=book(-0.20),
        symbol="WINV26",
    )
    assert result.directional_alignment == "BEARISH_ALIGNED"
    assert result.recent_delta == -500.0
    assert result.delta_dominance == 0.60
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False


def test_rc35_official_context_detects_divergence_when_signs_disagree():
    result = OrderFlowObservationalContextBuilder.build(
        delta_report=delta(recent_delta=-500.0, dominance=0.60),
        book_report=book(0.20),
        symbol="WINV26",
    )
    assert result.directional_alignment == "DIVERGENT"


def test_rc35_official_context_requires_delta_magnitude_threshold():
    result = OrderFlowObservationalContextBuilder.build(
        delta_report=delta(recent_delta=-500.0, dominance=0.05),
        book_report=book(-0.20),
        symbol="WINV26",
    )
    assert result.directional_alignment == "NEUTRAL"


if __name__ == "__main__":
    test_rc35_official_context_uses_recent_delta_sign_for_bearish()
    test_rc35_official_context_detects_divergence_when_signs_disagree()
    test_rc35_official_context_requires_delta_magnitude_threshold()
    print("PROFIT_RTD_RC35=OK")
