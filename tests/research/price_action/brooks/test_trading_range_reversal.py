from research.price_action.brooks.trading_range_reversal import (
    BrooksTradingRangeReversalResearch,
    TradingRangeReversalObservation,
)


def evaluate(**kwargs):
    return BrooksTradingRangeReversalResearch().evaluate(
        TradingRangeReversalObservation(**kwargs)
    )


def test_low_edge_h2_buy_reversal_matches():
    r = evaluate(
        range_valid=True,
        zone="LOW",
        setup_direction="BUY",
        h2_near_low=True,
        reversal_candidate=True,
        reversal_direction="BULL",
        reversal_quality="STRONG",
        response_detected=True,
        candle_id="WIN|M5|1",
    )
    assert r.matched and r.direction == "BUY" and r.sequence_complete


def test_high_edge_l2_sell_reversal_matches():
    r = evaluate(
        range_valid=True,
        zone="HIGH",
        setup_direction="SELL",
        l2_near_high=True,
        reversal_candidate=True,
        reversal_direction="BEAR",
        reversal_quality="MODERATE",
        response_detected=True,
    )
    assert r.matched and r.direction == "SELL"


def test_failed_breakout_risk_can_supply_edge_signal():
    r = evaluate(
        range_valid=True,
        zone="LOW",
        setup_direction="NONE",
        failed_breakout_risk=True,
        reversal_candidate=True,
        reversal_direction="BUY",
        reversal_quality="STRONG",
        response_detected=True,
    )
    assert r.matched and r.direction == "BUY"


def test_range_must_be_confirmed():
    r = evaluate(range_valid=False, zone="LOW")
    assert not r.matched and "TRADING_RANGE_NOT_CONFIRMED" in r.reasons


def test_middle_zone_is_not_eligible():
    r = evaluate(range_valid=True, zone="MIDDLE")
    assert not r.matched and "RANGE_EDGE_NOT_ELIGIBLE" in r.reasons


def test_low_edge_requires_h2_or_failed_breakout_risk():
    r = evaluate(
        range_valid=True,
        zone="LOW",
        setup_direction="BUY",
        reversal_candidate=True,
        reversal_direction="BUY",
        reversal_quality="STRONG",
        response_detected=True,
    )
    assert not r.matched
    assert "RANGE_EDGE_REVERSAL_SIGNAL_NOT_CONFIRMED" in r.reasons


def test_high_edge_requires_l2_or_failed_breakout_risk():
    r = evaluate(
        range_valid=True,
        zone="HIGH",
        setup_direction="SELL",
        reversal_candidate=True,
        reversal_direction="SELL",
        reversal_quality="STRONG",
        response_detected=True,
    )
    assert not r.matched
    assert "RANGE_EDGE_REVERSAL_SIGNAL_NOT_CONFIRMED" in r.reasons


def test_playbook_direction_cannot_conflict():
    r = evaluate(
        range_valid=True,
        zone="LOW",
        setup_direction="SELL",
        h2_near_low=True,
        reversal_candidate=True,
        reversal_direction="BUY",
        reversal_quality="STRONG",
        response_detected=True,
    )
    assert not r.matched and "PLAYBOOK_DIRECTION_NOT_ALIGNED" in r.reasons


def test_reversal_direction_must_point_into_range():
    r = evaluate(
        range_valid=True,
        zone="HIGH",
        l2_near_high=True,
        reversal_candidate=True,
        reversal_direction="BUY",
        reversal_quality="STRONG",
        response_detected=True,
    )
    assert not r.matched and "REVERSAL_DIRECTION_NOT_INTO_RANGE" in r.reasons


def test_weak_reversal_quality_is_rejected():
    r = evaluate(
        range_valid=True,
        zone="LOW",
        h2_near_low=True,
        reversal_candidate=True,
        reversal_direction="BUY",
        reversal_quality="WEAK",
        response_detected=True,
    )
    assert not r.matched and "REVERSAL_QUALITY_NOT_ELIGIBLE" in r.reasons


def test_response_is_required():
    r = evaluate(
        range_valid=True,
        zone="LOW",
        h2_near_low=True,
        reversal_candidate=True,
        reversal_direction="BUY",
        reversal_quality="STRONG",
        response_detected=False,
    )
    assert not r.matched and "REVERSAL_RESPONSE_NOT_CONFIRMED" in r.reasons


def test_range_invalidation_blocks_match():
    r = evaluate(
        range_valid=True,
        zone="HIGH",
        l2_near_high=True,
        reversal_candidate=True,
        reversal_direction="SELL",
        reversal_quality="STRONG",
        response_detected=True,
        range_invalidated=True,
    )
    assert r.invalidated and not r.matched


def test_safety_flags_remain_off():
    r = evaluate()
    assert r.research_only is True
    assert r.observational_only is True
    assert r.predictive_claim_allowed is False
    assert r.score_influence_allowed is False
    assert r.risk_influence_allowed is False
    assert r.decision_influence_allowed is False
    assert r.alert_influence_allowed is False
    assert r.order_execution_allowed is False
