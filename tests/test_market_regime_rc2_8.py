from core.analysis_context import AnalysisContext
from models.candle import Candle
from analysis.market_regime import MarketRegime
from enums.trend import Trend


def _context(closed, current=None):
    context = AnalysisContext()
    for candle in closed:
        context.market.candles.add(candle)
    context.market.candles.add(current or Candle(100, 101, 99, 100))
    return context


def _c(high, low, open_=None, close=None):
    open_ = low + (high - low) * 0.35 if open_ is None else open_
    close = low + (high - low) * 0.65 if close is None else close
    return Candle(open_, high, low, close)


def test_requires_five_closed_candles_plus_current():
    context = _context([_c(101, 99)] * 4)
    MarketRegime().executar(context)
    assert context.regime.valid is False
    assert context.regime.regime == "UNKNOWN"


def test_strong_aggregate_uptrend_is_trend_up():
    closed = [_c(101, 99), _c(103, 100), _c(105, 102), _c(107, 104), _c(109, 106)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.regime == "TREND_UP"
    assert context.regime.trend == Trend.UP
    assert context.regime.up_steps == 4


def test_strong_aggregate_downtrend_is_trend_down():
    closed = [_c(109, 106), _c(107, 104), _c(105, 102), _c(103, 100), _c(101, 98)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.regime == "TREND_DOWN"
    assert context.regime.trend == Trend.DOWN
    assert context.regime.down_steps == 4


def test_last_two_bars_do_not_override_aggregate_range():
    closed = [
        _c(110, 100),
        _c(109, 101),
        _c(110, 100),
        _c(109, 101),
        _c(111, 102),
    ]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.regime == "RANGE"
    assert context.regime.trend == Trend.SIDEWAYS


def test_last_two_down_bars_do_not_override_aggregate_range():
    closed = [
        _c(110, 100),
        _c(111, 101),
        _c(110, 100),
        _c(111, 101),
        _c(109, 99),
    ]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.regime == "RANGE"


def test_high_overlap_is_range_evidence():
    closed = [_c(110, 100), _c(111, 101), _c(110.5, 100.5), _c(111, 101), _c(110.5, 100.5)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.bar_overlap_ratio >= 0.60
    assert context.regime.regime == "RANGE"


def test_current_forming_candle_is_ignored():
    closed = [_c(101, 99), _c(103, 100), _c(105, 102), _c(107, 104), _c(109, 106)]
    violent_current = _c(200, 50)
    context = _context(closed, violent_current)
    MarketRegime().executar(context)
    assert context.regime.regime == "TREND_UP"
    assert context.regime.up_steps == 4


def test_volatility_high_is_preserved():
    closed = [_c(101, 99), _c(102, 100), _c(103, 101), _c(110, 100), _c(112, 100)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.volatility == "HIGH"


def test_result_strength_and_confidence_are_bounded():
    closed = [_c(101, 99), _c(103, 100), _c(105, 102), _c(107, 104), _c(109, 106)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert 0.0 <= context.regime.strength <= 1.0
    assert 0.0 <= context.regime.confidence <= 1.0


def test_engine_remains_observational_about_decision():
    closed = [_c(101, 99), _c(103, 100), _c(105, 102), _c(107, 104), _c(109, 106)]
    context = _context(closed)
    before = context.decision.direction
    MarketRegime().executar(context)
    assert context.decision.direction == before
