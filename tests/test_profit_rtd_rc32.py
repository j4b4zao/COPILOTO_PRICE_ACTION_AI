from types import SimpleNamespace

from market_data.order_flow_shadow_calibration import OrderFlowShadowCalibration


def ctx(*, alignment="NEUTRAL", recent_delta=0.0, dominance=0.0, imbalance=0.0, status="READY"):
    return SimpleNamespace(
        directional_alignment=alignment,
        recent_delta=recent_delta,
        delta_dominance=dominance,
        book_imbalance=imbalance,
        status=status,
    )


def test_shadow_detects_bullish_without_changing_official():
    result = OrderFlowShadowCalibration(delta_threshold=0.35, book_threshold=0.062149).evaluate(
        ctx(alignment="NEUTRAL", recent_delta=500.0, dominance=0.60, imbalance=0.08)
    )
    assert result.official_alignment == "NEUTRAL"
    assert result.shadow_alignment == "BULLISH_ALIGNED"
    assert result.changed is True
    assert result.observational_only is True
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False


def test_shadow_detects_bearish_and_divergent_from_signed_recent_delta():
    shadow = OrderFlowShadowCalibration(delta_threshold=0.35, book_threshold=0.062149)
    bearish = shadow.evaluate(ctx(recent_delta=-500.0, dominance=0.50, imbalance=-0.07))
    divergent = shadow.evaluate(ctx(recent_delta=500.0, dominance=0.50, imbalance=-0.07))
    assert bearish.shadow_alignment == "BEARISH_ALIGNED"
    assert divergent.shadow_alignment == "DIVERGENT"
    assert bearish.dominance == 0.50
    assert bearish.recent_delta == -500.0


def test_shadow_does_not_infer_direction_from_dominance_sign():
    shadow = OrderFlowShadowCalibration(delta_threshold=0.35, book_threshold=0.062149)
    result = shadow.evaluate(ctx(recent_delta=0.0, dominance=0.80, imbalance=-0.10))
    assert result.shadow_alignment == "NEUTRAL"


def test_shadow_keeps_neutral_when_source_not_ready():
    result = OrderFlowShadowCalibration().evaluate(
        ctx(alignment="NEUTRAL", recent_delta=500.0, dominance=0.80, imbalance=0.20, status="DEGRADED")
    )
    assert result.shadow_alignment == "NEUTRAL"


def test_threshold_validation_is_fail_safe():
    for delta, book in [(0, 0.05), (0.35, 0), (1.1, 0.05), (0.35, 1.1)]:
        try:
            OrderFlowShadowCalibration(delta_threshold=delta, book_threshold=book)
        except ValueError:
            pass
        else:
            raise AssertionError("threshold invalido deveria falhar")


if __name__ == "__main__":
    test_shadow_detects_bullish_without_changing_official()
    test_shadow_detects_bearish_and_divergent_from_signed_recent_delta()
    test_shadow_does_not_infer_direction_from_dominance_sign()
    test_shadow_keeps_neutral_when_source_not_ready()
    test_threshold_validation_is_fail_safe()
    print("PROFIT_RTD_RC35_DIRECTION=OK")
