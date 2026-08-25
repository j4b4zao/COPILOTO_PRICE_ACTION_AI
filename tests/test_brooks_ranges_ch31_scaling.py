from analysis.price_action.scaling_trade_dynamics import ScalingTradeDynamics


def test_scale_in_allowed_with_structure_and_risk_controlled():
    engine = ScalingTradeDynamics()
    result = engine.analyze(
        direction="BUY",
        entries=[(100.0, 1.0)],
        stop_price=95.0,
        current_price=104.0,
        action="SCALE_IN",
        action_price=102.0,
        action_size=0.5,
        structure_confirmed=True,
    )
    assert result.valid is True
    assert result.state == "SCALE_IN_ALLOWED"
    assert result.favorable_scale_in is True


def test_scale_in_blocked_when_averaging_down_without_structure():
    engine = ScalingTradeDynamics()
    result = engine.analyze(
        direction="BUY",
        entries=[(100.0, 1.0)],
        stop_price=95.0,
        current_price=98.0,
        action="SCALE_IN",
        action_price=97.0,
        action_size=0.5,
        structure_confirmed=False,
    )
    assert result.state == "SCALE_IN_BLOCKED_AVERAGING_DOWN"
    assert result.averaging_down_risk is True


def test_scale_out_near_target():
    engine = ScalingTradeDynamics()
    result = engine.analyze(
        direction="BUY",
        entries=[(100.0, 1.0)],
        stop_price=95.0,
        current_price=109.0,
        action="SCALE_OUT",
        target_near=True,
    )
    assert result.state == "SCALE_OUT_APPROPRIATE"
    assert result.scale_out_appropriate is True


def test_scale_out_on_deterioration():
    engine = ScalingTradeDynamics()
    result = engine.analyze(
        direction="SELL",
        entries=[(100.0, 1.0)],
        stop_price=105.0,
        current_price=94.0,
        action="SCALE_OUT",
        deterioration=True,
    )
    assert result.scale_out_appropriate is True


def test_invalid_direction():
    engine = ScalingTradeDynamics()
    result = engine.analyze(
        direction="NONE",
        entries=[(100.0, 1.0)],
        stop_price=95.0,
        current_price=101.0,
        action="HOLD",
    )
    assert result.valid is False
    assert result.reason == "INVALID_DIRECTION"
