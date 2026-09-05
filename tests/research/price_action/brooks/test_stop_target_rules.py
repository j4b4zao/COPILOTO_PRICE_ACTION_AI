from research.price_action.brooks.stop_target_rules import (
    BrooksStopTargetRulesResearch,
    StopTargetObservation,
)


def evaluate(**kwargs):
    base = dict(
        direction="BUY",
        entry_price=100.0,
        initial_stop=95.0,
        current_stop=95.0,
        proposed_stop=97.0,
        stop_geometry_valid=True,
        stop_loosened=False,
        structural_advance_confirmed=True,
        stop_improved=True,
        protected_r=0.4,
        target_price=110.0,
        target_valid=True,
        target_source="STRUCTURAL",
        reward_risk=2.0,
        partial_profit_zone=False,
        target_zone=False,
        target_reached=False,
        target_overshot=False,
        heavy_profit_taking=False,
        correction_risk=False,
        reversal_risk=False,
        candle_id="WINV26|M5|1",
    )
    base.update(kwargs)
    return BrooksStopTargetRulesResearch().evaluate(StopTargetObservation(**base))


def test_buy_valid_stop_and_target_context():
    result = evaluate()
    assert result.valid_context is True
    assert result.protective_stop_valid is True
    assert result.never_loosen_rule_respected is True
    assert result.trailing_advance_supported is True
    assert result.target_valid is True
    assert result.rr_observed == 2.0


def test_sell_valid_stop_and_target_context():
    result = evaluate(
        direction="SELL",
        entry_price=100.0,
        initial_stop=105.0,
        current_stop=105.0,
        proposed_stop=103.0,
        target_price=90.0,
    )
    assert result.protective_stop_valid is True
    assert result.trailing_advance_supported is True
    assert result.target_valid is True


def test_invalid_direction_rejected():
    result = evaluate(direction="NONE")
    assert result.valid_context is False
    assert "INVALID_DIRECTION" in result.reasons


def test_invalid_entry_rejected():
    result = evaluate(entry_price=0.0)
    assert result.valid_context is False
    assert "INVALID_ENTRY_PRICE" in result.reasons


def test_buy_stop_wrong_side_rejected():
    result = evaluate(initial_stop=101.0)
    assert result.protective_stop_valid is False


def test_sell_stop_wrong_side_rejected():
    result = evaluate(direction="SELL", initial_stop=99.0, target_price=90.0)
    assert result.protective_stop_valid is False


def test_stop_loosen_rule_is_rejected():
    result = evaluate(stop_loosened=True)
    assert result.never_loosen_rule_respected is False
    assert result.trailing_advance_supported is False
    assert "STOP_LOOSENING_REJECTED" in result.reasons


def test_trailing_requires_structural_advance():
    result = evaluate(structural_advance_confirmed=False, stop_improved=True)
    assert result.trailing_advance_supported is False
    assert "TRAILING_ADVANCE_WITHOUT_STRUCTURE_REJECTED" in result.reasons


def test_no_stop_improvement_means_no_trailing_advance():
    result = evaluate(stop_improved=False)
    assert result.trailing_advance_supported is False


def test_buy_target_wrong_side_rejected():
    result = evaluate(target_price=99.0)
    assert result.target_valid is False


def test_sell_target_wrong_side_rejected():
    result = evaluate(direction="SELL", initial_stop=105.0, target_price=101.0)
    assert result.target_valid is False


def test_partial_profit_zone_recorded_observationally():
    result = evaluate(partial_profit_zone=True)
    assert result.partial_profit_observed is True
    assert "PARTIAL_PROFIT_ZONE_OBSERVED" in result.reasons


def test_target_reached_recorded_observationally():
    result = evaluate(target_reached=True)
    assert result.target_reached_observed is True


def test_profit_taking_pressure_from_heavy_profit_taking():
    result = evaluate(heavy_profit_taking=True)
    assert result.profit_taking_pressure_observed is True


def test_profit_taking_pressure_from_correction_risk():
    result = evaluate(correction_risk=True)
    assert result.profit_taking_pressure_observed is True


def test_profit_taking_pressure_from_reversal_risk():
    result = evaluate(reversal_risk=True)
    assert result.profit_taking_pressure_observed is True


def test_invalid_target_blocks_profit_taking_flags():
    result = evaluate(target_valid=False, partial_profit_zone=True, target_reached=True, heavy_profit_taking=True)
    assert result.target_valid is False
    assert result.partial_profit_observed is False
    assert result.target_reached_observed is False
    assert result.profit_taking_pressure_observed is False


def test_safety_flags_are_all_off():
    result = evaluate()
    assert result.research_only is True
    assert result.observational_only is True
    assert result.predictive_claim_allowed is False
    assert result.score_influence_allowed is False
    assert result.risk_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.alert_influence_allowed is False
    assert result.order_execution_allowed is False
