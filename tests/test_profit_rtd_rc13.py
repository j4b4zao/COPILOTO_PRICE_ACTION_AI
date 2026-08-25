"""Offline gate do Profit RTD RC13: avaliador de aceitação de sessão."""

from market_data.profit_rtd_validation_acceptance import (
    ProfitRTDValidationAcceptanceEvaluator,
    ProfitRTDValidationAcceptancePolicy,
)
from market_data.profit_rtd_validation_recorder import ProfitRTDValidationSnapshot


def snapshot(**overrides):
    data = dict(
        total_cycles=500,
        state_updates=100,
        baseline_resets=1,
        total_new_trades=500,
        total_source_units=500,
        contiguous_cycles=495,
        no_new_trade_cycles=395,
        continuity_loss_cycles=5,
        symbol_reset_cycles=0,
        last_symbol="WINV26",
        last_continuity="CONTIGUOUS",
        last_new_trade_count=1,
        last_state_updated=True,
        update_rate=0.20,
        continuity_rate=0.99,
        observational_only=True,
        score_influence_allowed=False,
        decision_influence_allowed=False,
        order_execution_allowed=False,
    )
    data.update(overrides)
    return ProfitRTDValidationSnapshot(**data)


def test_rc13_passes_good_observational_session():
    result = ProfitRTDValidationAcceptanceEvaluator().evaluate(snapshot())
    assert result.verdict == "PASS"
    assert result.reasons == ("ACCEPTANCE_CRITERIA_MET",)
    assert result.observational_only is True
    assert result.score_influence_allowed is False
    assert result.decision_influence_allowed is False
    assert result.order_execution_allowed is False


def test_rc13_reviews_short_or_thin_session():
    result = ProfitRTDValidationAcceptanceEvaluator().evaluate(
        snapshot(
            total_cycles=100,
            total_new_trades=20,
            contiguous_cycles=100,
            continuity_loss_cycles=0,
            update_rate=0.005,
            continuity_rate=1.0,
        )
    )
    assert result.verdict == "REVIEW"
    assert "INSUFFICIENT_CYCLES" in result.reasons
    assert "INSUFFICIENT_NEW_TRADES" in result.reasons
    assert "UPDATE_RATE_LOW" in result.reasons


def test_rc13_fails_excessive_continuity_loss():
    result = ProfitRTDValidationAcceptanceEvaluator().evaluate(
        snapshot(
            total_cycles=500,
            continuity_loss_cycles=20,
            contiguous_cycles=480,
            continuity_rate=0.96,
        )
    )
    assert result.verdict == "FAIL"
    assert result.continuity_loss_rate == 0.04
    assert "CONTINUITY_LOSS_RATE_HIGH" in result.reasons


def test_rc13_fails_if_operational_capability_is_enabled():
    result = ProfitRTDValidationAcceptanceEvaluator().evaluate(
        snapshot(score_influence_allowed=True)
    )
    assert result.verdict == "FAIL"
    assert "SCORE_INFLUENCE_ENABLED" in result.reasons


def test_rc13_policy_is_configurable_and_validated():
    policy = ProfitRTDValidationAcceptancePolicy(
        min_cycles=10,
        min_new_trades=1,
        min_continuity_rate=0.50,
        max_continuity_loss_rate=0.50,
        min_update_rate=0.0,
    )
    result = ProfitRTDValidationAcceptanceEvaluator(policy).evaluate(
        snapshot(
            total_cycles=10,
            total_new_trades=1,
            continuity_loss_cycles=0,
            contiguous_cycles=10,
            update_rate=0.0,
            continuity_rate=1.0,
        )
    )
    assert result.verdict == "PASS"

    try:
        ProfitRTDValidationAcceptancePolicy(min_cycles=0)
    except ValueError:
        pass
    else:
        raise AssertionError("min_cycles=0 deveria ser rejeitado")


def main():
    test_rc13_passes_good_observational_session()
    test_rc13_reviews_short_or_thin_session()
    test_rc13_fails_excessive_continuity_loss()
    test_rc13_fails_if_operational_capability_is_enabled()
    test_rc13_policy_is_configurable_and_validated()
    print("Profit RTD RC13: OK")


if __name__ == "__main__":
    main()
