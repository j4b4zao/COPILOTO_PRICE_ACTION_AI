from analysis.price_action.trading_guidelines_dynamics import TradingGuidelinesDynamics


def test_strong_discipline_context():
    r = TradingGuidelinesDynamics().analyze(
        direction="BUY",
        context_clear=True,
        setup_confirmed=True,
        reward_risk=2.0,
        conflict_present=False,
        trades_today=2,
        max_preferred_trades=5,
        chase_risk=False,
    )
    assert r.status == "GUIDELINES_STRONG_DISCIPLINE"
    assert not r.guideline_veto
    assert r.discipline_score == 100.0


def test_conflict_creates_veto():
    r = TradingGuidelinesDynamics().analyze(
        direction="SELL",
        context_clear=True,
        setup_confirmed=True,
        reward_risk=2.0,
        conflict_present=True,
    )
    assert r.status == "GUIDELINE_VETO"
    assert r.guideline_veto


def test_chasing_creates_veto():
    r = TradingGuidelinesDynamics().analyze(
        direction="BUY",
        context_clear=True,
        setup_confirmed=True,
        reward_risk=1.5,
        chase_risk=True,
    )
    assert r.status == "GUIDELINE_VETO"
    assert r.chase_risk


def test_bad_reward_risk_below_point_seven_five_is_hard_veto():
    r = TradingGuidelinesDynamics().analyze(
        direction="BUY",
        context_clear=True,
        setup_confirmed=True,
        reward_risk=0.5,
    )
    assert r.guideline_veto
    assert "REWARD_RISK_BELOW_1R" in r.reasons


def test_overtrading_creates_caution():
    r = TradingGuidelinesDynamics().analyze(
        direction="SELL",
        context_clear=True,
        setup_confirmed=True,
        reward_risk=1.5,
        trades_today=7,
        max_preferred_trades=5,
    )
    assert r.status == "GUIDELINE_CAUTION"
    assert r.overtrading_risk


def test_unclear_and_unconfirmed_context_creates_soft_veto():
    r = TradingGuidelinesDynamics().analyze(
        direction="BUY",
        context_clear=False,
        setup_confirmed=False,
        reward_risk=2.0,
    )
    assert r.status == "GUIDELINE_CAUTION"
    assert r.guideline_veto


def test_invalid_direction_is_normalized_to_none():
    r = TradingGuidelinesDynamics().analyze(
        direction="SIDEWAYS",
        context_clear=True,
        setup_confirmed=True,
        reward_risk=1.5,
    )
    assert r.direction == "NONE"
    assert r.valid
