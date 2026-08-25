from core.analysis_context import AnalysisContext
from core.multi_timeframe_state import MultiTimeframeState
from models.candle import Candle
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from enums.trend import Trend


def _c(high, low):
    return Candle(low + (high - low) * 0.35, high, low, low + (high - low) * 0.65)


def _series(direction):
    if direction == Trend.UP:
        return [_c(101, 99), _c(103, 100), _c(105, 102), _c(107, 104), _c(109, 106)]
    if direction == Trend.DOWN:
        return [_c(109, 106), _c(107, 104), _c(105, 102), _c(103, 100), _c(101, 98)]
    return [_c(110, 100), _c(109, 101), _c(110, 100), _c(109, 101), _c(110, 100)]


def _context(m15, m5, m1):
    context = AnalysisContext()
    state = MultiTimeframeState()
    context.multi_timeframe = state
    for timeframe, trend in (("M15", m15), ("M5", m5), ("M1", m1)):
        market = state.get(timeframe)
        for candle in _series(trend):
            market.candles.add(candle)
        market.candles.add(_c(120, 80))
    return context


def test_requires_state():
    context = AnalysisContext()
    MultiTimeframeAnalysis().executar(context)
    assert context.multi_timeframe_analysis.valid is False


def test_all_up_is_buy():
    context = _context(Trend.UP, Trend.UP, Trend.UP)
    MultiTimeframeAnalysis().executar(context)
    result = context.multi_timeframe_analysis
    assert result.alignment == "BUY"
    assert result.bias == "BUY"
    assert result.aligned is True


def test_all_down_is_sell():
    context = _context(Trend.DOWN, Trend.DOWN, Trend.DOWN)
    MultiTimeframeAnalysis().executar(context)
    assert context.multi_timeframe_analysis.alignment == "SELL"


def test_m15_sideways_waits_context():
    context = _context(Trend.SIDEWAYS, Trend.UP, Trend.UP)
    MultiTimeframeAnalysis().executar(context)
    result = context.multi_timeframe_analysis
    assert result.alignment == "WAIT_CONTEXT"
    assert result.bias == "NONE"


def test_m5_opposite_is_structural_conflict():
    context = _context(Trend.UP, Trend.DOWN, Trend.UP)
    MultiTimeframeAnalysis().executar(context)
    result = context.multi_timeframe_analysis
    assert result.alignment == "CONFLICT_M5"
    assert result.conflict is True


def test_m5_sideways_waits_setup():
    context = _context(Trend.UP, Trend.SIDEWAYS, Trend.UP)
    MultiTimeframeAnalysis().executar(context)
    result = context.multi_timeframe_analysis
    assert result.alignment == "WAIT_M5"
    assert result.bias == "BUY"


def test_m1_sideways_waits_trigger():
    context = _context(Trend.UP, Trend.UP, Trend.SIDEWAYS)
    MultiTimeframeAnalysis().executar(context)
    result = context.multi_timeframe_analysis
    assert result.alignment == "WAIT_TRIGGER"
    assert result.bias == "BUY"


def test_m1_opposite_does_not_erase_higher_timeframe_bias():
    context = _context(Trend.UP, Trend.UP, Trend.DOWN)
    MultiTimeframeAnalysis().executar(context)
    result = context.multi_timeframe_analysis
    assert result.alignment == "CONFLICT_M1"
    assert result.bias == "BUY"
    assert result.conflict is True


def test_forming_candle_is_ignored():
    context = _context(Trend.UP, Trend.UP, Trend.UP)
    for timeframe in ("M15", "M5", "M1"):
        market = context.multi_timeframe.get(timeframe)
        market.candles.last().high = 1000
        market.candles.last().low = 1
    MultiTimeframeAnalysis().executar(context)
    assert context.multi_timeframe_analysis.alignment == "BUY"


def test_engine_remains_observational_about_decision():
    context = _context(Trend.UP, Trend.UP, Trend.UP)
    before = context.decision.direction
    MultiTimeframeAnalysis().executar(context)
    assert context.decision.direction == before
