from research.price_action.brooks.failed_breakout import (
    BrooksFailedBreakoutResearch,
    FailedBreakoutObservation,
)


def test_up_breakout_failure_maps_to_sell_response():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="UP",
        breakout_detected=True,
        failure_detected=True,
        failure_direction="DOWN",
        opposite_response_detected=True,
        candle_id="WIN|M5|1",
    ))
    assert result.matched is True
    assert result.sequence_complete is True
    assert result.direction == "SELL"
    assert result.reasons == ["FAILED_BREAKOUT_SEQUENCE_OBSERVED"]


def test_down_breakout_failure_maps_to_buy_response():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="DOWN",
        breakout_detected=True,
        failure_detected=True,
        failure_direction="UP",
        opposite_response_detected=True,
    ))
    assert result.matched is True
    assert result.direction == "BUY"


def test_breakout_is_required():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="UP",
        breakout_detected=False,
        failure_detected=True,
        failure_direction="DOWN",
        opposite_response_detected=True,
    ))
    assert result.matched is False
    assert "BREAKOUT_NOT_CONFIRMED" in result.reasons


def test_failure_is_required():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="UP",
        breakout_detected=True,
        failure_detected=False,
        failure_direction="DOWN",
        opposite_response_detected=True,
    ))
    assert result.matched is False
    assert "BREAKOUT_FAILURE_NOT_CONFIRMED" in result.reasons


def test_failure_direction_must_be_opposite_breakout():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="UP",
        breakout_detected=True,
        failure_detected=True,
        failure_direction="UP",
        opposite_response_detected=True,
    ))
    assert result.matched is False
    assert "FAILURE_DIRECTION_NOT_OPPOSITE_BREAKOUT" in result.reasons


def test_opposite_response_is_required_for_complete_sequence():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="DOWN",
        breakout_detected=True,
        failure_detected=True,
        failure_direction="UP",
        opposite_response_detected=False,
    ))
    assert result.matched is False
    assert "OPPOSITE_RESPONSE_NOT_CONFIRMED" in result.reasons


def test_structural_invalidation_blocks_match():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="UP",
        breakout_detected=True,
        failure_detected=True,
        failure_direction="DOWN",
        opposite_response_detected=True,
        structural_invalidation=True,
    ))
    assert result.matched is False
    assert result.invalidated is True
    assert result.reasons == ["FAILED_BREAKOUT_STRUCTURE_INVALIDATED"]


def test_invalid_direction_is_not_eligible():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation(
        breakout_direction="NONE",
        breakout_detected=True,
        failure_detected=True,
        failure_direction="DOWN",
        opposite_response_detected=True,
    ))
    assert result.matched is False
    assert result.direction == "NONE"
    assert result.reasons == ["BREAKOUT_DIRECTION_NOT_ELIGIBLE"]


def test_operational_influence_is_hard_disabled():
    result = BrooksFailedBreakoutResearch().evaluate(FailedBreakoutObservation())
    assert result.research_only is True
    assert result.observational_only is True
    assert result.predictive_claim_allowed is False
    assert result.score_influence_allowed is False
    assert result.risk_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.alert_influence_allowed is False
    assert result.order_execution_allowed is False
