from dataclasses import dataclass

from research.price_action.brooks.wedge_three_pushes import (
    BrooksThreePushesDetector,
    BrooksWedgeThreePushesResearch,
    WedgeThreePushesObservation,
)


@dataclass
class C:
    high: float
    low: float


def up_candles(last_push=12.0):
    # ultimo item e candle ainda aberto e deve ser ignorado
    return [
        C(9.0, 5.0), C(10.0, 5.2), C(9.4, 5.1),
        C(11.0, 5.3), C(10.2, 5.2), C(last_push, 5.4),
        C(10.8, 5.3), C(99.0, 1.0),
    ]


def down_candles(last_push=3.0):
    return [
        C(15.0, 7.0), C(14.8, 6.0), C(15.1, 6.6),
        C(14.7, 5.0), C(15.0, 5.8), C(14.6, last_push),
        C(14.9, 4.8), C(99.0, -99.0),
    ]


def evaluate(**kwargs):
    return BrooksWedgeThreePushesResearch().evaluate(WedgeThreePushesObservation(**kwargs))


def test_detects_three_up_pushes_from_closed_candles():
    r = BrooksThreePushesDetector.analyze(up_candles())
    assert r.detected and r.push_direction == "UP"
    assert r.push_indices == (1, 3, 5)
    assert r.push_prices == (10.0, 11.0, 12.0)


def test_detects_three_down_pushes_from_closed_candles():
    r = BrooksThreePushesDetector.analyze(down_candles())
    assert r.detected and r.push_direction == "DOWN"
    assert r.push_indices == (1, 3, 5)
    assert r.push_prices == (6.0, 5.0, 3.0)


def test_requires_three_local_pushes():
    candles = [C(9, 5), C(10, 5), C(9, 5), C(11, 5), C(10, 5), C(10.5, 5), C(10, 5), C(99, 1)]
    r = BrooksThreePushesDetector.analyze(candles)
    assert not r.detected


def test_non_monotonic_three_highs_are_not_up_pushes():
    candles = up_candles(last_push=10.5)
    r = BrooksThreePushesDetector.analyze(candles)
    assert not (r.detected and r.push_direction == "UP")


def test_open_candle_is_not_used_as_a_push():
    candles = [C(9, 5), C(10, 5), C(9, 5), C(11, 5), C(10, 5), C(10.5, 5), C(10, 5), C(13, 5)]
    r = BrooksThreePushesDetector.analyze(candles)
    assert not r.detected


def test_narrowing_is_diagnostic_not_mandatory():
    r = BrooksThreePushesDetector.analyze(up_candles(last_push=11.5))
    assert r.detected and r.narrowing is True
    r2 = BrooksThreePushesDetector.analyze(up_candles(last_push=13.0))
    assert r2.detected and r2.narrowing is False


def test_up_pushes_plus_sell_reversal_matches():
    r = evaluate(three_pushes_detected=True, push_direction="UP",
                 reversal_candidate=True, reversal_direction="BEAR",
                 reversal_quality="STRONG", structural_change=True,
                 structural_change_direction="DOWN", response_detected=True)
    assert r.matched and r.direction == "SELL" and r.sequence_complete


def test_down_pushes_plus_buy_reversal_matches():
    r = evaluate(three_pushes_detected=True, push_direction="DOWN",
                 reversal_candidate=True, reversal_direction="BULL",
                 reversal_quality="MODERATE", structural_change=True,
                 structural_change_direction="UP", response_detected=True)
    assert r.matched and r.direction == "BUY"


def test_weak_reversal_does_not_match():
    r = evaluate(three_pushes_detected=True, push_direction="UP",
                 reversal_candidate=True, reversal_direction="SELL",
                 reversal_quality="WEAK", structural_change=True,
                 structural_change_direction="DOWN", response_detected=True)
    assert not r.matched and "REVERSAL_QUALITY_NOT_ELIGIBLE" in r.reasons


def test_structural_change_is_required():
    r = evaluate(three_pushes_detected=True, push_direction="UP",
                 reversal_candidate=True, reversal_direction="SELL",
                 reversal_quality="STRONG", structural_change=False,
                 structural_change_direction="NONE", response_detected=True)
    assert not r.matched and "STRUCTURAL_CHANGE_NOT_CONFIRMED" in r.reasons


def test_response_is_required():
    r = evaluate(three_pushes_detected=True, push_direction="UP",
                 reversal_candidate=True, reversal_direction="SELL",
                 reversal_quality="STRONG", structural_change=True,
                 structural_change_direction="DOWN", response_detected=False)
    assert not r.matched and "REVERSAL_RESPONSE_NOT_CONFIRMED" in r.reasons


def test_structural_invalidation_blocks_setup():
    r = evaluate(three_pushes_detected=True, push_direction="UP",
                 reversal_candidate=True, reversal_direction="SELL",
                 reversal_quality="STRONG", structural_change=True,
                 structural_change_direction="DOWN", response_detected=True,
                 structural_invalidation=True)
    assert r.invalidated and not r.matched


def test_safety_flags_remain_off():
    r = evaluate(push_direction="UP")
    assert r.research_only is True and r.observational_only is True
    assert r.predictive_claim_allowed is False
    assert r.score_influence_allowed is False
    assert r.risk_influence_allowed is False
    assert r.decision_influence_allowed is False
    assert r.alert_influence_allowed is False
    assert r.order_execution_allowed is False
