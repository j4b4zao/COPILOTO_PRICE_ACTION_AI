from analysis.book_depth_analysis import BookDepthAnalysis
from analysis.order_flow import OrderFlow
from analysis.price_action.price_action import PriceAction
from brain.context_engine import ContextEngine
from core.analysis_context import AnalysisContext
from enums.trend import Trend
from models.book_depth import BookDepthSnapshot


def _book():
    return BookDepthSnapshot.build(
        symbol="WINV26",
        timestamp="2026-08-23T10:00:00",
        bids=[(100.0, 100.0), (99.5, 60.0), (99.0, 40.0)],
        asks=[(100.5, 30.0), (101.0, 20.0), (101.5, 10.0)],
        source="TEST",
    )


def _order_flow_result(context, absorption, confidence=0.8):
    result = context.order_flow
    result.absorption = absorption
    result.exhaustion = "NONE"
    result.pattern_confidence = confidence
    return result


def test_order_flow_runs_before_price_action():
    assert OrderFlow.PRIORITY < PriceAction.PRIORITY


def test_book_depth_runs_after_price_action_before_context_engine():
    assert PriceAction.PRIORITY < BookDepthAnalysis.PRIORITY < ContextEngine.PRIORITY


def test_book_depth_uses_current_price_action_buy_bias():
    context = AnalysisContext()
    context.book_depth = _book()
    context.price_action.bias = "BUY"
    context.order_flow.pressure = "BUY"
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.price_action_alignment == "ALIGNED"


def test_book_depth_detects_current_price_action_conflict():
    context = AnalysisContext()
    context.book_depth = _book()
    context.price_action.bias = "SELL"
    context.order_flow.pressure = "BUY"
    BookDepthAnalysis().executar(context)
    assert context.book_depth_analysis.price_action_alignment == "CONFLICT"


def test_order_flow_uses_real_analysis_context_structure_up():
    context = AnalysisContext()
    context.structure.trend = Trend.UP
    result = _order_flow_result(context, "BUY_ABSORPTION")
    OrderFlow()._qualify_structure(context, result)
    assert result.structure_alignment == "ALIGNED"
    assert result.structural_pattern_confidence == 0.8


def test_order_flow_real_structure_down_conflicts_buy_pattern():
    context = AnalysisContext()
    context.structure.trend = Trend.DOWN
    result = _order_flow_result(context, "BUY_ABSORPTION")
    OrderFlow()._qualify_structure(context, result)
    assert result.structure_alignment == "CONFLICT"
    assert result.structural_pattern_confidence == 0.48


def test_order_flow_real_structure_down_aligns_sell_pattern():
    context = AnalysisContext()
    context.structure.trend = Trend.DOWN
    result = _order_flow_result(context, "SELL_ABSORPTION", confidence=0.75)
    OrderFlow()._qualify_structure(context, result)
    assert result.structure_alignment == "ALIGNED"
    assert result.structural_pattern_confidence == 0.75


def test_order_flow_sideways_structure_is_neutral():
    context = AnalysisContext()
    context.structure.trend = Trend.SIDEWAYS
    result = _order_flow_result(context, "BUY_ABSORPTION")
    OrderFlow()._qualify_structure(context, result)
    assert result.structure_alignment == "NEUTRAL"
    assert result.structural_pattern_confidence == 0.64


def test_order_flow_unknown_structure_is_unavailable():
    context = AnalysisContext()
    context.structure.trend = Trend.UNKNOWN
    result = _order_flow_result(context, "BUY_ABSORPTION")
    OrderFlow()._qualify_structure(context, result)
    assert result.structure_alignment == "UNAVAILABLE"
    assert result.structural_pattern_confidence == 0.0


def test_analysis_context_has_structure_not_legacy_market_structure():
    context = AnalysisContext()
    assert hasattr(context, "structure")
    assert not hasattr(context, "market_structure")
