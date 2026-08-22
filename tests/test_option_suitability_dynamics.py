from analysis.price_action.option_suitability_dynamics import OptionSuitabilityDynamics


def test_higher_timeframe_swing_option_vehicle_can_be_suitable():
    r = OptionSuitabilityDynamics().analyze(
        timeframe="D1",
        holding_horizon="SWING",
        bid=9.90,
        ask=10.00,
        liquidity_score=85,
        overnight_exposure=True,
    )
    assert r.valid
    assert r.status == "OPTIONS_HIGHER_TIMEFRAME_SUITABLE"
    assert r.option_vehicle_suitable
    assert r.higher_timeframe_context


def test_wide_spread_creates_caution():
    r = OptionSuitabilityDynamics().analyze(
        timeframe="D1",
        holding_horizon="SWING",
        bid=9.00,
        ask=10.00,
        liquidity_score=90,
    )
    assert r.status == "OPTIONS_WIDE_SPREAD_CAUTION"
    assert r.wide_spread_risk


def test_low_liquidity_creates_caution():
    r = OptionSuitabilityDynamics().analyze(
        timeframe="D1",
        holding_horizon="SWING",
        bid=9.95,
        ask=10.00,
        liquidity_score=30,
    )
    assert r.status == "OPTIONS_LOW_LIQUIDITY_CAUTION"
    assert r.low_liquidity_risk


def test_intraday_scalping_with_friction_is_poor_fit():
    r = OptionSuitabilityDynamics().analyze(
        timeframe="M5",
        holding_horizon="SCALP",
        bid=9.80,
        ask=10.00,
        liquidity_score=45,
    )
    assert r.status == "OPTIONS_POOR_FOR_INTRADAY_SCALPING"
    assert r.intraday_option_scalping_risk


def test_underlying_price_action_remains_primary():
    r = OptionSuitabilityDynamics().analyze(
        timeframe="M15",
        holding_horizon="INTRADAY",
        bid=9.98,
        ask=10.00,
        liquidity_score=90,
    )
    assert "UNDERLYING_PRICE_ACTION_REMAINS_PRIMARY" in r.reasons


def test_invalid_bid_ask_is_rejected():
    r = OptionSuitabilityDynamics().analyze(
        timeframe="D1",
        holding_horizon="SWING",
        bid=10.0,
        ask=9.0,
        liquidity_score=90,
    )
    assert not r.valid
    assert r.status == "OPTION_CONTEXT_INVALID"
