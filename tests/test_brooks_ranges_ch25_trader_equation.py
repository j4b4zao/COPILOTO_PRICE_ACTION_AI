from analysis.price_action.trader_equation_dynamics import TraderEquationDynamics


def test_good_setup_with_equal_reward_and_risk_is_positive():
    result = TraderEquationDynamics().analyze(
        entry_price=100.0,
        stop_price=90.0,
        target_price=110.0,
        probability_success=0.60,
    )

    assert result.valid is True
    assert result.direction == "BUY"
    assert result.reward_risk == 1.0
    assert result.expected_value_points == 2.0
    assert result.expectancy_r == 0.2
    assert result.favorable is True


def test_low_probability_large_reward_can_still_be_positive():
    result = TraderEquationDynamics().analyze(
        entry_price=100.0,
        stop_price=90.0,
        target_price=160.0,
        probability_success=0.30,
    )

    assert result.reward_risk == 6.0
    assert result.expected_value_points == 11.0
    assert result.expectancy_r == 1.1
    assert result.equation_state == "STRONGLY_FAVORABLE"
    assert result.favorable is True


def test_fifty_fifty_equal_reward_and_risk_is_breakeven():
    result = TraderEquationDynamics().analyze(
        entry_price=100.0,
        stop_price=90.0,
        target_price=110.0,
        probability_success=0.50,
    )

    assert result.expected_value_points == 0.0
    assert result.expectancy_r == 0.0
    assert result.equation_state == "BREAKEVEN"
    assert result.favorable is False


def test_high_probability_can_still_be_unfavorable_when_reward_is_too_small():
    result = TraderEquationDynamics().analyze(
        entry_price=100.0,
        stop_price=90.0,
        target_price=105.0,
        probability_success=0.60,
    )

    assert result.reward_risk == 0.5
    assert result.expected_value_points == -1.0
    assert result.expectancy_r == -0.1
    assert result.equation_state == "UNFAVORABLE"
    assert result.favorable is False
    assert "REWARD_SMALLER_THAN_RISK_REQUIRES_HIGH_WIN_RATE" in result.reasons


def test_sell_geometry_is_supported():
    result = TraderEquationDynamics().analyze(
        entry_price=100.0,
        stop_price=110.0,
        target_price=80.0,
        probability_success=0.60,
    )

    assert result.valid is True
    assert result.direction == "SELL"
    assert result.reward_risk == 2.0
    assert result.favorable is True


def test_probability_defaults_follow_setup_quality():
    good = TraderEquationDynamics().analyze(100, 90, 110, setup_quality="GOOD")
    uncertain = TraderEquationDynamics().analyze(100, 90, 110, setup_quality="UNCERTAIN")
    speculative = TraderEquationDynamics().analyze(100, 90, 130, setup_quality="SPECULATIVE")

    assert good.probability_success == 0.60
    assert uncertain.probability_success == 0.50
    assert speculative.probability_success == 0.40


def test_invalid_trade_geometry_is_rejected():
    result = TraderEquationDynamics().analyze(
        entry_price=100.0,
        stop_price=105.0,
        target_price=110.0,
        probability_success=0.60,
        direction="BUY",
    )

    assert result.valid is False
    assert result.equation_state == "INVALID"
    assert result.reason == "INVALID_TRADE_GEOMETRY"


def test_layer_never_uses_current_candle():
    result = TraderEquationDynamics().analyze(100, 90, 120, probability_success=0.60)
    assert result.current_candle_used is False
