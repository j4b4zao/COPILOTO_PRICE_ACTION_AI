from analysis.price_action.extreme_scalping_dynamics import ExtremeScalpingDynamics


def test_extreme_scalping_rejects_high_precision_profile():
    result = ExtremeScalpingDynamics().analyze(
        risk_points=10,
        reward_points=4,
        expected_win_rate=0.72,
    )

    assert result.valid is True
    assert result.high_precision_required is True
    assert result.status == "EXTREME_SCALPING_UNSUITABLE"
    assert result.suitable_for_copiloto is False


def test_costs_raise_break_even_accuracy():
    engine = ExtremeScalpingDynamics()
    without_cost = engine.analyze(risk_points=10, reward_points=10)
    with_cost = engine.analyze(risk_points=10, reward_points=10, cost_points=1)

    assert with_cost.breakeven_win_rate > without_cost.breakeven_win_rate


def test_equal_reward_risk_can_be_acceptable_with_edge():
    result = ExtremeScalpingDynamics().analyze(
        risk_points=10,
        reward_points=10,
        expected_win_rate=0.60,
    )

    assert result.status == "SCALPING_MATH_ACCEPTABLE"
    assert result.expected_value_points > 0
    assert result.suitable_for_copiloto is True


def test_two_to_one_profile_is_preferred():
    result = ExtremeScalpingDynamics().analyze(
        risk_points=10,
        reward_points=20,
        expected_win_rate=0.50,
    )

    assert result.status == "FAVORABLE_REWARD_RISK_PROFILE"
    assert result.expected_value_points > 0
    assert result.suitable_for_copiloto is True


def test_cost_can_consume_tiny_scalp_reward():
    result = ExtremeScalpingDynamics().analyze(
        risk_points=5,
        reward_points=1,
        cost_points=1,
    )

    assert result.status == "EXTREME_SCALPING_UNSUITABLE"
    assert result.suitable_for_copiloto is False


def test_invalid_geometry_is_rejected():
    result = ExtremeScalpingDynamics().analyze(
        risk_points=0,
        reward_points=10,
    )

    assert result.valid is False
    assert "INVALID_RISK_REWARD_GEOMETRY" in result.reasons


def test_percentage_win_rate_is_normalized():
    result = ExtremeScalpingDynamics().analyze(
        risk_points=10,
        reward_points=20,
        expected_win_rate=50,
    )

    assert result.expected_win_rate == 0.5


def test_high_trade_frequency_is_only_diagnostic():
    result = ExtremeScalpingDynamics().analyze(
        risk_points=10,
        reward_points=20,
        expected_win_rate=0.55,
        trades_per_day=25,
    )

    assert "VERY_HIGH_TRADE_FREQUENCY" in result.reasons
    assert result.suitable_for_copiloto is True
