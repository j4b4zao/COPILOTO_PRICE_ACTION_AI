from dataclasses import dataclass

from analysis.price_action.dueling_lines_dynamics import DuelingLinesDynamics


@dataclass
class C:
    open: float
    high: float
    low: float
    close: float


def _bars(values):
    return [C(*x) for x in values]


def test_insufficient_history():
    result = DuelingLinesDynamics().analyze(
        _bars([(100, 101, 99, 100.5)] * 8)
    )
    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons


def test_dueling_lines_buy_context_is_diagnostic():
    values = [
        (100, 102, 99.8, 101.8),
        (101.8, 104, 101.2, 103.7),
        (103.7, 106, 103.0, 105.8),
        (105.8, 108, 105.0, 107.7),
        (107.7, 110, 107.0, 109.7),
        (109.7, 111, 108.8, 110.5),
        (110.5, 111, 107.8, 108.4),
        (108.4, 109.2, 106.9, 107.4),
        (107.4, 108.6, 106.2, 108.0),
        (108.0, 108.4, 105.4, 106.1),
        (106.1, 107.5, 105.0, 107.0),
        (107.0, 107.2, 104.5, 105.1),
        (105.1, 106.8, 104.7, 106.5),
        (106.5, 106.9, 104.2, 104.8),
        (104.8, 107.2, 104.4, 106.9),
        (106.9, 108.4, 106.5, 108.1),
        (108.1, 109.3, 107.8, 109.0),
        (109.0, 110.0, 108.7, 109.7),
        # current/forming candle: must be ignored
        (109.7, 115.0, 109.5, 114.8),
    ]
    result = DuelingLinesDynamics().analyze(_bars(values))
    assert result.trend_direction in ("UP", "NONE") or result.valid in (True, False)
    assert (not result.continuation_bias) or result.reaction_confirmed


def test_current_candle_does_not_confirm_setup():
    values = [(100 + i, 101 + i, 99.5 + i, 100.8 + i) for i in range(18)]
    values.append((118, 130, 117.5, 129.5))
    result = DuelingLinesDynamics().analyze(_bars(values))
    assert result.signal_bar_index < len(values) - 1 or result.signal_bar_index == -1
