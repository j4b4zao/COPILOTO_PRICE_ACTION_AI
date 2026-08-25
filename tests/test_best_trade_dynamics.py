from analysis.price_action.best_trade_dynamics import BestTradeDynamics


def test_no_clear_direction_returns_no_trade():
    r = BestTradeDynamics().analyze(["BUY", "SELL"])
    assert r.status == "NO_TRADE_CONTEXT"
    assert r.direction == "NONE"


def test_a_plus_requires_clean_confirmed_structured_context():
    r = BestTradeDynamics().analyze(
        ["BUY", "BUY", "BUY"],
        setup_quality=95,
        context_quality=95,
        risk_reward=2.2,
        confirmation_present=True,
        structure_present=True,
        higher_timeframe_direction="BUY",
    )
    assert r.status == "BEST_TRADE_A_PLUS"
    assert r.direction == "BUY"
    assert r.beginner_friendly


def test_high_quality_trade_can_exist_without_higher_timeframe_alignment():
    r = BestTradeDynamics().analyze(
        ["SELL", "SELL", "SELL"],
        setup_quality=90,
        context_quality=85,
        risk_reward=2.0,
        confirmation_present=True,
        structure_present=True,
        higher_timeframe_direction="NONE",
    )
    assert r.status in {"HIGH_QUALITY_TRADE", "BEST_TRADE_A_PLUS"}
    assert r.direction == "SELL"


def test_conflicting_diagnostics_are_penalized():
    r = BestTradeDynamics().analyze(
        ["BUY", "BUY", "BUY", "SELL", "SELL"],
        setup_quality=90,
        context_quality=90,
        risk_reward=2.0,
        confirmation_present=True,
        structure_present=True,
        higher_timeframe_direction="BUY",
    )
    assert r.status == "CONFLICTED_TRADE"
    assert r.conflicting_signals == 2
    assert not r.beginner_friendly


def test_poor_risk_reward_prevents_beginner_friendly_classification():
    r = BestTradeDynamics().analyze(
        ["BUY", "BUY", "BUY"],
        setup_quality=90,
        context_quality=90,
        risk_reward=0.8,
        confirmation_present=True,
        structure_present=True,
        higher_timeframe_direction="BUY",
    )
    assert not r.beginner_friendly
    assert "POOR_RISK_REWARD" in r.reasons


def test_dict_and_object_like_diagnostics_are_supported():
    class D:
        direction = "SELL"

    r = BestTradeDynamics().analyze(
        [{"bias": "SELL"}, D(), {"signal": "SELL"}],
        setup_quality=80,
        context_quality=80,
        risk_reward=1.8,
        confirmation_present=True,
        structure_present=True,
    )
    assert r.direction == "SELL"
    assert r.aligned_signals == 3
