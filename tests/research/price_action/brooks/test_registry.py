from enums.trend import Trend
from research.price_action.brooks.breakout_pullback import (
    BreakoutPullbackObservation,
)
from research.price_action.brooks.registry import (
    BrooksResearchRegistry,
    BrooksResearchSuite,
)
from research.price_action.brooks.stop_target_rules import StopTargetObservation


EXPECTED_NAMES = {
    "BROOKS_BREAKOUT_PULLBACK_V1",
    "BROOKS_TREND_PULLBACK_V1",
    "BROOKS_FAILED_BREAKOUT_V1",
    "BROOKS_MAJOR_TREND_REVERSAL_V1",
    "BROOKS_WEDGE_THREE_PUSHES_V1",
    "BROOKS_TRADING_RANGE_REVERSAL_V1",
    "BROOKS_STOP_TARGET_RULES_V1",
}


def test_registry_contains_all_formalized_families():
    assert set(BrooksResearchRegistry.names()) == EXPECTED_NAMES


def test_registry_has_six_setups_and_one_management_rule():
    entries = BrooksResearchRegistry.entries()
    assert sum(x.category == "SETUP" for x in entries) == 6
    assert sum(x.category == "MANAGEMENT" for x in entries) == 1


def test_registry_entries_are_research_only_and_safe():
    for entry in BrooksResearchRegistry.entries():
        assert entry.research_only is True
        assert entry.observational_only is True
        assert entry.predictive_claim_allowed is False
        assert entry.score_influence_allowed is False
        assert entry.risk_influence_allowed is False
        assert entry.decision_influence_allowed is False
        assert entry.alert_influence_allowed is False
        assert entry.order_execution_allowed is False


def test_registry_lookup_is_case_insensitive():
    entry = BrooksResearchRegistry.get("brooks_breakout_pullback_v1")
    assert entry is not None
    assert entry.name == "BROOKS_BREAKOUT_PULLBACK_V1"


def test_registry_unknown_lookup_returns_none():
    assert BrooksResearchRegistry.get("BROOKS_UNKNOWN") is None


def test_suite_dispatches_breakout_pullback():
    obs = BreakoutPullbackObservation(
        trend=Trend.UP,
        breakout_direction="BUY",
        breakout_detected=True,
        pullback_detected=True,
        rejection_detected=True,
        resumption_detected=True,
        candle_id="WINV26|M1|2026-09-05T10:00:00",
    )
    result = BrooksResearchSuite().run({"BROOKS_BREAKOUT_PULLBACK_V1": obs})
    classified = result.results["BROOKS_BREAKOUT_PULLBACK_V1"]
    assert classified.matched is True
    assert classified.direction == "BUY"


def test_suite_dispatches_management_rules():
    obs = StopTargetObservation(
        direction="BUY",
        entry_price=100.0,
        initial_stop=95.0,
        current_stop=95.0,
        proposed_stop=97.0,
        stop_geometry_valid=True,
        stop_loosened=False,
        structural_advance_confirmed=True,
        stop_improved=True,
        target_price=110.0,
        target_valid=True,
        reward_risk=2.0,
        partial_profit_zone=True,
    )
    result = BrooksResearchSuite().run({"BROOKS_STOP_TARGET_RULES_V1": obs})
    classified = result.results["BROOKS_STOP_TARGET_RULES_V1"]
    assert classified.protective_stop_valid is True
    assert classified.trailing_advance_supported is True
    assert classified.target_valid is True
    assert classified.rr_observed == 2.0


def test_suite_records_unknown_setup_without_executing_it():
    result = BrooksResearchSuite().run({"UNKNOWN": object()})
    assert result.results == {}
    assert result.unknown_setups == ["UNKNOWN"]


def test_suite_empty_input_is_safe():
    result = BrooksResearchSuite().run({})
    assert result.results == {}
    assert result.unknown_setups == []


def test_suite_global_flags_are_all_non_operational():
    result = BrooksResearchSuite().run({})
    assert result.research_only is True
    assert result.observational_only is True
    assert result.predictive_claim_allowed is False
    assert result.score_influence_allowed is False
    assert result.risk_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.alert_influence_allowed is False
    assert result.order_execution_allowed is False


def test_suite_can_run_multiple_registered_observations_together():
    breakout = BreakoutPullbackObservation(
        trend=Trend.DOWN,
        breakout_direction="SELL",
        breakout_detected=True,
        pullback_detected=True,
        rejection_detected=True,
        resumption_detected=True,
    )
    management = StopTargetObservation(
        direction="SELL",
        entry_price=100.0,
        initial_stop=105.0,
        current_stop=105.0,
        proposed_stop=103.0,
        stop_geometry_valid=True,
        structural_advance_confirmed=True,
        stop_improved=True,
        target_price=90.0,
        target_valid=True,
        reward_risk=2.0,
    )
    result = BrooksResearchSuite().run(
        {
            "BROOKS_BREAKOUT_PULLBACK_V1": breakout,
            "BROOKS_STOP_TARGET_RULES_V1": management,
        }
    )
    assert set(result.results) == {
        "BROOKS_BREAKOUT_PULLBACK_V1",
        "BROOKS_STOP_TARGET_RULES_V1",
    }


def test_registry_names_are_unique():
    names = BrooksResearchRegistry.names()
    assert len(names) == len(set(names))
