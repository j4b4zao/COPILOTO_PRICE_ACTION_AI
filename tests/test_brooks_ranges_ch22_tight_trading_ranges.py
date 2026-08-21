from dataclasses import dataclass

from analysis.price_action.tight_trading_range_dynamics import TightTradingRangeDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def test_tight_range_becomes_no_trade_zone():
    bars = []
    prices = [100.0, 100.2, 100.0, 100.15, 100.0, 100.18, 100.02, 100.16, 100.01, 100.14, 100.03]
    for i, p in enumerate(prices):
        o = 100.08 if i % 2 == 0 else 100.12
        bars.append(C(o, max(o, p) + 0.08, min(o, p) - 0.08, p))
    bars.append(C(100.1, 100.2, 100.0, 100.1))  # current/forming

    r = TightTradingRangeDynamics().analyze(bars)
    assert r.valid is True
    assert r.no_trade_zone is True
    assert r.state in ("NO_TRADE_ZONE", "TIGHT_TRADING_RANGE")


def test_confirmed_breakout_releases_no_trade_zone():
    base = [
        C(100.05, 100.20, 99.95, 100.10),
        C(100.10, 100.22, 99.98, 100.02),
        C(100.02, 100.18, 99.94, 100.12),
        C(100.12, 100.24, 100.00, 100.04),
        C(100.04, 100.21, 99.96, 100.14),
        C(100.14, 100.23, 100.01, 100.06),
        C(100.06, 100.20, 99.97, 100.13),
        C(100.13, 100.25, 100.00, 100.05),
    ]
    bars = base + [
        C(100.05, 100.65, 100.04, 100.58),
        C(100.58, 100.82, 100.50, 100.76),
        C(100.76, 100.80, 100.65, 100.72),  # current/forming
    ]

    r = TightTradingRangeDynamics().analyze(bars)
    assert r.breakout_attempt is True
    assert r.breakout_confirmed is True
    assert r.breakout_direction == "UP"
    assert r.no_trade_zone is False


def test_current_candle_cannot_create_breakout():
    closed = [C(100.05, 100.2, 99.95, 100.1) for _ in range(10)]
    current = C(100.1, 101.0, 100.05, 100.9)
    r = TightTradingRangeDynamics().analyze(closed + [current])
    assert r.breakout_confirmed is False


def test_insufficient_history():
    bars = [C(100, 101, 99, 100) for _ in range(6)]
    r = TightTradingRangeDynamics().analyze(bars)
    assert r.valid is False
    assert "INSUFFICIENT_HISTORY" in r.reasons
