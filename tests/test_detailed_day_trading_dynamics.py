from types import SimpleNamespace

from analysis.price_action.detailed_day_trading_dynamics import DetailedDayTradingDynamics


def comp(direction, score=80, valid=True):
    return SimpleNamespace(direction=direction, quality_score=score, valid=valid)


def test_no_components():
    r = DetailedDayTradingDynamics().analyze([])
    assert not r.valid
    assert "NO_COMPONENTS" in r.reasons


def test_strong_buy_alignment():
    r = DetailedDayTradingDynamics().analyze([
        comp("BUY", 90), comp("BUY", 85), comp("BUY", 80), comp("BUY", 75)
    ])
    assert r.valid
    assert r.direction == "BUY"
    assert r.status == "DAY_TRADE_CONTEXT_STRONG_ALIGNMENT"
    assert r.strong_context


def test_mixed_context_tracks_conflict():
    r = DetailedDayTradingDynamics().analyze([
        comp("BUY", 90), comp("BUY", 80), comp("SELL", 75)
    ])
    assert r.direction == "BUY"
    assert r.conflict_risk
    assert r.conflicting_components == 1


def test_balanced_conflict_returns_none_direction():
    r = DetailedDayTradingDynamics().analyze([
        comp("BUY", 80), comp("SELL", 80)
    ])
    assert r.direction == "NONE"
    assert r.status == "DAY_TRADE_CONTEXT_CONFLICT"


def test_neutral_only_context():
    r = DetailedDayTradingDynamics().analyze([
        SimpleNamespace(direction="NONE", quality_score=80, valid=True),
        SimpleNamespace(direction="NONE", quality_score=70, valid=True),
    ])
    assert r.valid
    assert r.status == "DAY_TRADE_CONTEXT_NEUTRAL"


def test_invalid_component_has_zero_weight():
    r = DetailedDayTradingDynamics().analyze([
        comp("BUY", 90, True), comp("SELL", 100, False), comp("BUY", 80, True)
    ])
    assert r.direction == "BUY"
