from research.price_action.brooks.major_trend_reversal import (
    BrooksMajorTrendReversalResearch,
    MajorTrendReversalObservation,
)


def evaluate(**kwargs):
    return BrooksMajorTrendReversalResearch().evaluate(MajorTrendReversalObservation(**kwargs))


def test_uptrend_major_reversal_sell():
    r = evaluate(prior_trend="UP", reversal_candidate=True, reversal_direction="BEAR",
                 reversal_quality="STRONG", reversal_context="COUNTER_TREND",
                 structural_change=True, structural_change_direction="DOWN",
                 response_detected=True, candle_id="WIN|M5|1")
    assert r.matched and r.direction == "SELL" and r.sequence_complete


def test_downtrend_major_reversal_buy():
    r = evaluate(prior_trend="DOWN", reversal_candidate=True, reversal_direction="BULL",
                 reversal_quality="MODERATE", reversal_context="COUNTER_TREND",
                 structural_change=True, structural_change_direction="UP",
                 response_detected=True)
    assert r.matched and r.direction == "BUY"


def test_sideways_or_unknown_prior_trend_is_not_eligible():
    r = evaluate(prior_trend="SIDEWAYS", reversal_candidate=True)
    assert not r.matched and "PRIOR_TREND_NOT_ELIGIBLE" in r.reasons


def test_with_trend_reversal_bar_is_not_major_reversal_candidate():
    r = evaluate(prior_trend="UP", reversal_candidate=True, reversal_direction="BULL",
                 reversal_quality="STRONG", reversal_context="WITH_TREND",
                 structural_change=True, structural_change_direction="DOWN",
                 response_detected=True)
    assert not r.matched
    assert "REVERSAL_DIRECTION_NOT_COUNTER_TREND" in r.reasons


def test_weak_reversal_quality_is_rejected():
    r = evaluate(prior_trend="UP", reversal_candidate=True, reversal_direction="BEAR",
                 reversal_quality="WEAK", reversal_context="COUNTER_TREND",
                 structural_change=True, structural_change_direction="DOWN",
                 response_detected=True)
    assert not r.matched and "REVERSAL_QUALITY_NOT_ELIGIBLE" in r.reasons


def test_rejected_doji_quality_is_rejected():
    r = evaluate(prior_trend="DOWN", reversal_candidate=True, reversal_direction="BULL",
                 reversal_quality="REJECTED", reversal_context="COUNTER_TREND",
                 structural_change=True, structural_change_direction="UP",
                 response_detected=True)
    assert not r.matched and "REVERSAL_QUALITY_NOT_ELIGIBLE" in r.reasons


def test_no_structural_change_no_match():
    r = evaluate(prior_trend="UP", reversal_candidate=True, reversal_direction="BEAR",
                 reversal_quality="STRONG", reversal_context="COUNTER_TREND",
                 structural_change=False, structural_change_direction="NONE",
                 response_detected=True)
    assert not r.matched and "STRUCTURAL_CHANGE_NOT_CONFIRMED" in r.reasons


def test_structural_change_must_align_with_reversal():
    r = evaluate(prior_trend="UP", reversal_candidate=True, reversal_direction="BEAR",
                 reversal_quality="STRONG", reversal_context="COUNTER_TREND",
                 structural_change=True, structural_change_direction="UP",
                 response_detected=True)
    assert not r.matched and "STRUCTURAL_CHANGE_DIRECTION_NOT_ALIGNED" in r.reasons


def test_response_is_required():
    r = evaluate(prior_trend="UP", reversal_candidate=True, reversal_direction="BEAR",
                 reversal_quality="STRONG", reversal_context="COUNTER_TREND",
                 structural_change=True, structural_change_direction="DOWN",
                 response_detected=False)
    assert not r.matched and "REVERSAL_RESPONSE_NOT_CONFIRMED" in r.reasons


def test_structural_invalidation_blocks_match():
    r = evaluate(prior_trend="UP", reversal_candidate=True, reversal_direction="BEAR",
                 reversal_quality="STRONG", reversal_context="COUNTER_TREND",
                 structural_change=True, structural_change_direction="DOWN",
                 response_detected=True, structural_invalidation=True)
    assert r.invalidated and not r.matched


def test_safety_flags_are_all_off():
    r = evaluate(prior_trend="UP")
    assert r.research_only is True
    assert r.observational_only is True
    assert r.predictive_claim_allowed is False
    assert r.score_influence_allowed is False
    assert r.risk_influence_allowed is False
    assert r.decision_influence_allowed is False
    assert r.alert_influence_allowed is False
    assert r.order_execution_allowed is False
