from core.analysis_context import AnalysisContext
from models.candle import Candle
from analysis.market_regime import MarketRegime
from enums.trend import Trend


def _c(high, low, open_=None, close=None):
    open_ = low + (high - low) * 0.35 if open_ is None else open_
    close = low + (high - low) * 0.65 if close is None else close
    return Candle(open_, high, low, close)


def _context(closed, current=None):
    context = AnalysisContext()
    for candle in closed:
        context.market.candles.add(candle)
    context.market.candles.add(current or _c(101, 99))
    return context


def test_rc2_9_version():
    assert MarketRegime.VERSION == "RC2.9-TRANSITION-STATE"


def test_persistent_uptrend_remains_trend_up():
    closed = [_c(101, 99), _c(103, 100), _c(105, 102), _c(107, 104), _c(109, 106)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.regime == "TREND_UP"
    assert context.regime.trend == Trend.UP


def test_persistent_downtrend_remains_trend_down():
    closed = [_c(109, 106), _c(107, 104), _c(105, 102), _c(103, 100), _c(101, 98)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.regime == "TREND_DOWN"
    assert context.regime.trend == Trend.DOWN


def test_high_overlap_persistent_range_remains_range():
    closed = [_c(110, 100), _c(111, 101), _c(110.5, 100.5), _c(111, 101), _c(110.5, 100.5)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.regime == "RANGE"
    assert context.regime.trend == Trend.SIDEWAYS


def test_mixed_direction_without_strong_range_is_transition():
    closed = [_c(102, 100), _c(105, 102), _c(103, 99), _c(106, 103), _c(104, 100)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.inertia == "TRANSITION"
    assert context.regime.regime == "TRANSITION"
    assert context.regime.trend == Trend.SIDEWAYS


def test_transition_with_directional_step_and_transition_bars():
    closed = [_c(102, 100), _c(105, 102), _c(106, 101), _c(107, 103), _c(108, 102)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert context.regime.inertia == "TRANSITION"
    assert context.regime.regime in {"TRANSITION", "TREND_UP"}


def test_transition_strength_and_confidence_are_bounded():
    closed = [_c(102, 100), _c(105, 102), _c(103, 99), _c(106, 103), _c(104, 100)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert 0.0 <= context.regime.strength <= 1.0
    assert 0.0 <= context.regime.confidence <= 1.0


def test_forming_candle_does_not_force_transition():
    closed = [_c(101, 99), _c(103, 100), _c(105, 102), _c(107, 104), _c(109, 106)]
    context = _context(closed, _c(200, 50))
    MarketRegime().executar(context)
    assert context.regime.regime == "TREND_UP"


def test_transition_reason_is_recorded():
    closed = [_c(102, 100), _c(105, 102), _c(103, 99), _c(106, 103), _c(104, 100)]
    context = _context(closed)
    MarketRegime().executar(context)
    assert any("TRANSITION" in reason for reason in context.regime.reasons)


def test_market_regime_still_does_not_touch_decision():
    closed = [_c(102, 100), _c(105, 102), _c(103, 99), _c(106, 103), _c(104, 100)]
    context = _context(closed)
    before = context.decision.direction
    MarketRegime().executar(context)
    assert context.decision.direction == before
