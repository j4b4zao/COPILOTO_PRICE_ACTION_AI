"""Controlled offline tests for BROOKS_BREAKOUT_PULLBACK_V1."""

from enums.trend import Trend
from research.price_action.brooks.breakout_pullback import (
    BreakoutPullbackObservation,
    BrooksBreakoutPullbackResearch,
)


def _engine():
    return BrooksBreakoutPullbackResearch()


def test_buy_sequence_matches_only_as_research_observation():
    result = _engine().evaluate(
        BreakoutPullbackObservation(
            trend=Trend.UP,
            breakout_direction="UP",
            breakout_detected=True,
            pullback_detected=True,
            rejection_detected=True,
            resumption_detected=True,
            structural_level_lost=False,
            candle_id="WINV26|M1|2026-09-04T10:15:00",
        )
    )

    assert result.matched is True
    assert result.direction == "BUY"
    assert result.context_valid is True
    assert result.sequence_complete is True
    assert result.invalidated is False
    assert result.candle_id == "WINV26|M1|2026-09-04T10:15:00"
    assert "BREAKOUT_PULLBACK_SEQUENCE_OBSERVED" in result.reasons

    assert result.research_only is True
    assert result.observational_only is True
    assert result.predictive_claim_allowed is False
    assert result.score_influence_allowed is False
    assert result.risk_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.alert_influence_allowed is False
    assert result.order_execution_allowed is False


def test_sell_sequence_matches_when_breakout_is_aligned_with_downtrend():
    result = _engine().evaluate(
        BreakoutPullbackObservation(
            trend=Trend.DOWN,
            breakout_direction="SELL",
            breakout_detected=True,
            pullback_detected=True,
            rejection_detected=True,
            resumption_detected=True,
        )
    )

    assert result.matched is True
    assert result.direction == "SELL"
    assert result.sequence_complete is True


def test_sideways_market_is_not_eligible():
    result = _engine().evaluate(
        BreakoutPullbackObservation(
            trend=Trend.SIDEWAYS,
            breakout_direction="BUY",
            breakout_detected=True,
            pullback_detected=True,
            rejection_detected=True,
            resumption_detected=True,
        )
    )

    assert result.matched is False
    assert result.context_valid is False
    assert result.direction == "NONE"
    assert "TREND_CONTEXT_NOT_ELIGIBLE" in result.reasons


def test_breakout_must_align_with_trend():
    result = _engine().evaluate(
        BreakoutPullbackObservation(
            trend=Trend.UP,
            breakout_direction="SELL",
            breakout_detected=True,
            pullback_detected=True,
            rejection_detected=True,
            resumption_detected=True,
        )
    )

    assert result.matched is False
    assert result.context_valid is False
    assert "BREAKOUT_DIRECTION_NOT_ALIGNED_WITH_TREND" in result.reasons


def test_structural_loss_invalidates_candidate_before_match():
    result = _engine().evaluate(
        BreakoutPullbackObservation(
            trend=Trend.DOWN,
            breakout_direction="DOWN",
            breakout_detected=True,
            pullback_detected=True,
            rejection_detected=True,
            resumption_detected=True,
            structural_level_lost=True,
        )
    )

    assert result.matched is False
    assert result.context_valid is True
    assert result.direction == "SELL"
    assert result.invalidated is True
    assert "BREAKOUT_STRUCTURE_INVALIDATED" in result.reasons


def test_incomplete_sequence_remains_observational_non_match():
    result = _engine().evaluate(
        BreakoutPullbackObservation(
            trend=Trend.UP,
            breakout_direction="BUY",
            breakout_detected=True,
            pullback_detected=True,
            rejection_detected=False,
            resumption_detected=False,
        )
    )

    assert result.matched is False
    assert result.context_valid is True
    assert result.sequence_complete is False
    assert "REJECTION_NOT_CONFIRMED" in result.reasons
    assert "RESUMPTION_NOT_CONFIRMED" in result.reasons

    assert result.score_influence_allowed is False
    assert result.risk_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.alert_influence_allowed is False
    assert result.order_execution_allowed is False
