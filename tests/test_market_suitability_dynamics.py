from dataclasses import dataclass

from analysis.price_action.market_suitability_dynamics import MarketSuitabilityDynamics


@dataclass
class Bar:
    open: float
    high: float
    low: float
    close: float
    volume: float = 1000.0


def _market(n=14, gap=False, volume=1000.0, width=10.0):
    bars = []
    price = 1000.0
    for i in range(n):
        o = price + (20.0 if gap and i % 3 == 0 and i else 0.0)
        c = o + (3.0 if i % 2 == 0 else -2.0)
        bars.append(Bar(o, max(o, c) + width / 2, min(o, c) - width / 2, c, volume))
        price = c
    bars.append(Bar(price, price + 1, price - 1, price, volume))  # current/open bar
    return bars


def test_insufficient_history():
    r = MarketSuitabilityDynamics().analyze(_market(5))
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons


def test_liquid_continuous_market_is_suitable():
    r = MarketSuitabilityDynamics().analyze(
        _market(width=12.0), symbol="WINV26", market_type="FUTURES", spread_ticks=1
    )
    assert r.valid is True
    assert r.status == "DAYTRADE_SUITABLE"
    assert r.daytrade_suitable is True


def test_missing_volume_creates_thin_market_risk():
    r = MarketSuitabilityDynamics().analyze(
        _market(volume=0.0), market_type="FUTURES", spread_ticks=1
    )
    assert r.thin_market_risk is True
    assert r.daytrade_suitable is False


def test_wide_spread_penalizes_market():
    r = MarketSuitabilityDynamics().analyze(
        _market(), market_type="STOCK", spread_ticks=5
    )
    assert r.spread_score == 0.0
    assert r.thin_market_risk is True


def test_irregular_gaps_are_flagged():
    r = MarketSuitabilityDynamics().analyze(
        _market(gap=True), market_type="STOCK", spread_ticks=1
    )
    assert r.irregular_flow_risk is True


def test_current_bar_is_excluded():
    bars = _market()
    a = MarketSuitabilityDynamics().analyze(bars, spread_ticks=1).to_dict()
    bars[-1] = Bar(1000, 100000, 1, 90000, 999999999)
    b = MarketSuitabilityDynamics().analyze(bars, spread_ticks=1).to_dict()
    assert a == b
