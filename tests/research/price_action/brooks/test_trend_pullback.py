from enums.trend import Trend
from research.price_action.brooks.trend_pullback import (
    BrooksTrendPullbackResearch,
    TrendPullbackObservation,
)


def test_buy_trend_pullback_matches_early_countertrend_pullback_with_resumption():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.UP,
            pullback_detected=True,
            pullback_direction="SELL",
            pullback_stage="MOVING_AVERAGE_TOUCH",
            pullback_stage_index=3,
            continuation_bias=True,
            resumption_detected=True,
            candle_id="WINV26|M1|BUY",
        )
    )

    assert result.matched is True
    assert result.direction == "BUY"
    assert result.sequence_complete is True
    assert result.invalidated is False
    assert result.reasons == ["TREND_PULLBACK_SEQUENCE_OBSERVED"]


def test_sell_trend_pullback_matches_early_countertrend_pullback_with_resumption():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.DOWN,
            pullback_detected=True,
            pullback_direction="BUY",
            pullback_stage="MINOR_TRENDLINE_BREAK",
            pullback_stage_index=2,
            continuation_bias=True,
            resumption_detected=True,
        )
    )

    assert result.matched is True
    assert result.direction == "SELL"


def test_sideways_context_is_not_eligible():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.SIDEWAYS,
            pullback_detected=True,
            pullback_direction="SELL",
            pullback_stage_index=1,
            continuation_bias=True,
            resumption_detected=True,
        )
    )

    assert result.matched is False
    assert result.context_valid is False
    assert "TREND_CONTEXT_NOT_ELIGIBLE" in result.reasons


def test_pullback_must_be_countertrend():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.UP,
            pullback_detected=True,
            pullback_direction="BUY",
            pullback_stage_index=1,
            continuation_bias=True,
            resumption_detected=True,
        )
    )

    assert result.matched is False
    assert "PULLBACK_DIRECTION_NOT_COUNTER_TREND" in result.reasons


def test_mature_pullback_does_not_match_early_continuation_hypothesis():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.UP,
            pullback_detected=True,
            pullback_direction="SELL",
            pullback_stage="MAJOR_TRENDLINE_BREAK",
            pullback_stage_index=6,
            continuation_bias=False,
            resumption_detected=True,
        )
    )

    assert result.matched is False
    assert "PULLBACK_STAGE_NOT_EARLY" in result.reasons
    assert "CONTINUATION_BIAS_NOT_PRESENT" in result.reasons


def test_reversal_risk_invalidates_hypothesis():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.DOWN,
            pullback_detected=True,
            pullback_direction="BUY",
            pullback_stage_index=2,
            continuation_bias=True,
            reversal_risk=True,
            resumption_detected=True,
        )
    )

    assert result.matched is False
    assert result.invalidated is True
    assert result.reasons == ["PULLBACK_MATURITY_REVERSAL_RISK"]


def test_trading_range_transition_invalidates_hypothesis():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.UP,
            pullback_detected=True,
            pullback_direction="SELL",
            pullback_stage_index=3,
            continuation_bias=True,
            trading_range_transition=True,
            resumption_detected=True,
        )
    )

    assert result.matched is False
    assert result.invalidated is True
    assert result.reasons == ["TRADING_RANGE_TRANSITION"]


def test_operational_influence_is_hard_disabled():
    result = BrooksTrendPullbackResearch().evaluate(
        TrendPullbackObservation(
            trend=Trend.UP,
        )
    )

    assert result.research_only is True
    assert result.observational_only is True
    assert result.predictive_claim_allowed is False
    assert result.score_influence_allowed is False
    assert result.risk_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.alert_influence_allowed is False
    assert result.order_execution_allowed is False
