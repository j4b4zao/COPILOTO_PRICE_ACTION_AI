from dataclasses import dataclass

from analysis.price_action.trading_range_playbook_dynamics import TradingRangePlaybookDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def _range_bars():
    data = [
        (100, 104, 98, 102), (102, 106, 100, 104), (104, 108, 101, 103),
        (103, 105, 99, 100), (100, 103, 96, 98), (98, 101, 95, 99),
        (99, 104, 97, 103), (103, 107, 101, 105), (105, 109, 102, 104),
        (104, 106, 100, 101), (101, 104, 97, 99), (99, 102, 95, 98),
        (98, 103, 96, 101), (101, 105, 99, 103), (103, 107, 101, 104),
        (104, 106, 100, 101), (101, 103, 97, 99), (99, 102, 95, 98),
        (98, 101, 96, 100),
    ]
    return [C(*x) for x in data]


def test_detects_range_and_classifies_zone():
    bars = _range_bars()
    result = TradingRangePlaybookDynamics().analyze(bars)
    assert result.valid is True
    assert result.zone in {"LOW", "MIDDLE", "HIGH"}
    assert result.range_high > result.range_low


def test_middle_is_avoided():
    bars = _range_bars()
    bars[-2] = C(101, 104, 99, 102)
    result = TradingRangePlaybookDynamics().analyze(bars)
    if result.zone == "MIDDLE":
        assert result.avoid_middle is True
        assert result.setup_direction == "NONE"


def test_current_candle_is_excluded():
    bars = _range_bars()
    baseline = TradingRangePlaybookDynamics().analyze(bars)
    bars[-1] = C(100, 140, 60, 130)
    changed = TradingRangePlaybookDynamics().analyze(bars)
    assert changed.range_low == baseline.range_low
    assert changed.range_high == baseline.range_high


def test_insufficient_history():
    result = TradingRangePlaybookDynamics().analyze(_range_bars()[:8])
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
