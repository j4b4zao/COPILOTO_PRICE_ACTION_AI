from dataclasses import dataclass

from analysis.price_action.double_flag_dynamics import DoubleFlagDynamics


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float


def c(close, high=None, low=None, open_=None):
    high = close + 0.6 if high is None else high
    low = close - 0.6 if low is None else low
    open_ = close + 0.2 if open_ is None else open_
    return Candle(open=open_, high=high, low=low, close=close)


def test_double_top_bear_flag_confirmed():
    closed = [
        c(110), c(108), c(106), c(104), c(102), c(100), c(98), c(96),
        c(98, high=98.7),
        c(100, high=100.6, low=97.5),       # first top
        c(97, high=98.8, low=96.4),
        c(98, high=99.0, low=96.8),
        c(99.8, high=100.4, low=97.2),      # second top
        c(97, high=98.2, low=96.2),
        c(95, high=97.0, low=94.4),         # breaks neckline -> resumes downtrend
        c(93, high=95.4, low=92.4),
    ]
    candles = closed + [c(92)]  # current/forming

    result = DoubleFlagDynamics().analyze(candles)

    assert result.valid is True
    assert result.direction == "DOWN"
    assert result.pattern == "DOUBLE_TOP_BEAR_FLAG"
    assert result.state == "DOUBLE_FLAG_CONFIRMED"
    assert result.resumed_trend is True
    assert result.continuation_bias is True
    assert result.quality_score >= 80.0


def test_double_bottom_bull_flag_confirmed():
    closed = [
        c(90), c(92), c(94), c(96), c(98), c(100), c(102), c(104),
        c(102, low=101.3),
        c(100, high=102.5, low=99.4),        # first bottom
        c(103, high=103.6, low=101.2),
        c(102, high=103.2, low=101.0),
        c(100.2, high=102.8, low=99.6),      # second bottom
        c(103, high=103.8, low=101.8),
        c(105, high=105.6, low=103.0),       # breaks neckline -> resumes uptrend
        c(107, high=107.6, low=104.8),
    ]
    candles = closed + [c(108)]

    result = DoubleFlagDynamics().analyze(candles)

    assert result.valid is True
    assert result.direction == "UP"
    assert result.pattern == "DOUBLE_BOTTOM_BULL_FLAG"
    assert result.state == "DOUBLE_FLAG_CONFIRMED"
    assert result.resumed_trend is True
    assert result.continuation_bias is True


def test_pattern_can_remain_candidate_before_breakout():
    closed = [
        c(110), c(108), c(106), c(104), c(102), c(100), c(98), c(96),
        c(98, high=98.7),
        c(100, high=100.6, low=97.5),
        c(97, high=98.8, low=96.4),
        c(98, high=99.0, low=96.8),
        c(99.8, high=100.4, low=97.2),
        c(98, high=99.0, low=97.1),
        c(97.5, high=98.5, low=96.7),
    ]
    candles = closed + [c(97)]

    result = DoubleFlagDynamics().analyze(candles)

    assert result.pattern == "DOUBLE_TOP_BEAR_FLAG"
    assert result.state == "DOUBLE_FLAG_CANDIDATE"
    assert result.resumed_trend is False
    assert result.continuation_bias is False


def test_current_candle_cannot_confirm_pattern():
    closed = [
        c(110), c(108), c(106), c(104), c(102), c(100), c(98), c(96),
        c(98, high=98.7),
        c(100, high=100.6, low=97.5),
        c(97, high=98.8, low=96.4),
        c(98, high=99.0, low=96.8),
        c(99.8, high=100.4, low=97.2),
        c(98, high=99.0, low=97.1),
        c(97.5, high=98.5, low=96.7),
    ]
    # This forming bar would confirm if it were incorrectly included.
    candles = closed + [c(94.0, high=97.0, low=93.5)]

    result = DoubleFlagDynamics().analyze(candles)

    assert result.state == "DOUBLE_FLAG_CANDIDATE"
    assert result.resumed_trend is False


def test_insufficient_history_is_rejected():
    candles = [c(100), c(99), c(98), c(97), c(96)]

    result = DoubleFlagDynamics().analyze(candles)

    assert result.valid is False
    assert "INSUFFICIENT_HISTORY" in result.reasons
