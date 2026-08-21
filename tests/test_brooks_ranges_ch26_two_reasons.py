from analysis.price_action.two_reason_trade_dynamics import TwoReasonTradeDynamics


def test_two_independent_reasons_confirm_trade_context():
    result = TwoReasonTradeDynamics().analyze(
        direction="BUY",
        reasons=["H2", "SUPPORT"],
        market_trend="UP",
    )
    assert result.valid is True
    assert result.two_reason_rule_met is True
    assert result.independent_reason_count == 2
    assert result.setup_state == "TWO_REASONS_CONFIRMED"


def test_same_category_does_not_count_twice():
    result = TwoReasonTradeDynamics().analyze(
        direction="BUY",
        reasons=["H1", "H2"],
        market_trend="UP",
    )
    assert result.reason_count == 2
    assert result.independent_reason_count == 1
    assert result.two_reason_rule_met is False
    assert result.setup_state == "ONE_REASON_ONLY"


def test_steep_countertrend_is_blocked_without_structural_reversal():
    result = TwoReasonTradeDynamics().analyze(
        direction="BUY",
        reasons=["H2", "DOUBLE_BOTTOM"],
        market_trend="DOWN",
        steep_trend=True,
        trendline_break=False,
        reversal_confirmation=False,
    )
    assert result.countertrend_blocked is True
    assert result.two_reason_rule_met is False
    assert result.setup_state == "COUNTERTREND_BLOCKED"


def test_countertrend_allowed_after_break_and_confirmation():
    result = TwoReasonTradeDynamics().analyze(
        direction="BUY",
        reasons=["TRENDLINE_BREAK", "DOUBLE_BOTTOM", "FOLLOW_THROUGH"],
        market_trend="DOWN",
        steep_trend=True,
        trendline_break=True,
        reversal_confirmation=True,
    )
    assert result.countertrend_blocked is False
    assert result.two_reason_rule_met is True
    assert result.independent_reason_count >= 2


def test_invalid_direction_is_rejected():
    result = TwoReasonTradeDynamics().analyze(
        direction="NONE",
        reasons=["BOS", "SUPPORT"],
    )
    assert result.valid is False
    assert result.reason == "INVALID_DIRECTION"
