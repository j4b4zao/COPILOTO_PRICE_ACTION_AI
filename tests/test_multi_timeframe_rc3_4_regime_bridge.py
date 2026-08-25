from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from core.analysis_context import AnalysisContext


def _result_with_bias(context, bias="BUY", alignment="BUY", confidence=1.0):
    result = context.multi_timeframe_analysis
    result.bias = bias
    result.alignment = alignment
    result.aligned = alignment in {"BUY", "SELL"}
    result.conflict = False
    result.confidence = confidence
    return result


def test_buy_bias_matches_trend_up_regime():
    context = AnalysisContext()
    context.regime.regime = "TREND_UP"
    result = _result_with_bias(context, "BUY", "BUY", 1.0)
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert result.regime_context == "TREND_UP"
    assert result.regime_compatible is True
    assert result.alignment == "BUY"


def test_sell_bias_matches_trend_down_regime():
    context = AnalysisContext()
    context.regime.regime = "TREND_DOWN"
    result = _result_with_bias(context, "SELL", "SELL", 1.0)
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert result.regime_compatible is True
    assert result.alignment == "SELL"


def test_buy_bias_conflicts_with_trend_down_regime():
    context = AnalysisContext()
    context.regime.regime = "TREND_DOWN"
    result = _result_with_bias(context, "BUY", "BUY", 1.0)
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert result.regime_compatible is False
    assert result.alignment == "CONFLICT_REGIME"
    assert result.conflict is True
    assert result.confidence <= 0.15


def test_sell_bias_conflicts_with_trend_up_regime():
    context = AnalysisContext()
    context.regime.regime = "TREND_UP"
    result = _result_with_bias(context, "SELL", "SELL", 1.0)
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert result.regime_compatible is False
    assert result.alignment == "CONFLICT_REGIME"


def test_range_regime_turns_directional_bias_into_wait():
    context = AnalysisContext()
    context.regime.regime = "RANGE"
    result = _result_with_bias(context, "BUY", "BUY", 1.0)
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert result.alignment == "WAIT_REGIME"
    assert result.aligned is False
    assert result.conflict is False
    assert result.confidence <= 0.40


def test_transition_regime_turns_directional_bias_into_wait():
    context = AnalysisContext()
    context.regime.regime = "TRANSITION"
    result = _result_with_bias(context, "SELL", "SELL", 1.0)
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert result.alignment == "WAIT_REGIME"
    assert result.regime_compatible is False


def test_unknown_regime_is_not_considered_compatible():
    context = AnalysisContext()
    context.regime.regime = "UNKNOWN"
    result = _result_with_bias(context, "BUY", "WAIT_M5", 0.50)
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert result.regime_context == "UNKNOWN"
    assert result.regime_compatible is False
    assert result.alignment == "WAIT_M5"


def test_no_bias_is_compatible_with_range_or_transition():
    for regime in ("RANGE", "TRANSITION"):
        context = AnalysisContext()
        context.regime.regime = regime
        result = _result_with_bias(context, "NONE", "WAIT_CONTEXT", 0.35)
        MultiTimeframeAnalysis._apply_regime_context(context, result)
        assert result.regime_compatible is True
        assert result.alignment == "WAIT_CONTEXT"


def test_clear_resets_regime_bridge_metadata():
    context = AnalysisContext()
    result = context.multi_timeframe_analysis
    result.regime_context = "TREND_UP"
    result.regime_compatible = True
    result.clear()
    assert result.regime_context == "UNKNOWN"
    assert result.regime_compatible is False


def test_regime_bridge_does_not_touch_decision():
    context = AnalysisContext()
    context.regime.regime = "TREND_DOWN"
    result = _result_with_bias(context, "BUY", "BUY", 1.0)
    before = context.decision.direction
    MultiTimeframeAnalysis._apply_regime_context(context, result)
    assert context.decision.direction == before
