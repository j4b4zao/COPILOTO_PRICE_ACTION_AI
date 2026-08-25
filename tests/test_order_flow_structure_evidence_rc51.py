from types import SimpleNamespace

from analysis.order_flow import OrderFlow
from models.order_flow_result import OrderFlowResult


def _result(absorption="NONE", exhaustion="NONE", confidence=0.8):
    result = OrderFlowResult()
    result.absorption = absorption
    result.exhaustion = exhaustion
    result.pattern_confidence = confidence
    return result


def _context(trend):
    return SimpleNamespace(market_structure=SimpleNamespace(trend=trend))


def test_buy_absorption_maps_to_buy_direction():
    result = _result(absorption="BUY_ABSORPTION")
    OrderFlow()._qualify_structure(_context("BULLISH"), result)
    assert result.pattern_direction == "BUY"


def test_sell_absorption_maps_to_sell_direction():
    result = _result(absorption="SELL_ABSORPTION")
    OrderFlow()._qualify_structure(_context("BEARISH"), result)
    assert result.pattern_direction == "SELL"


def test_sell_exhaustion_maps_to_buy_direction():
    result = _result(exhaustion="SELL_EXHAUSTION")
    OrderFlow()._qualify_structure(_context("BULLISH"), result)
    assert result.pattern_direction == "BUY"


def test_buy_exhaustion_maps_to_sell_direction():
    result = _result(exhaustion="BUY_EXHAUSTION")
    OrderFlow()._qualify_structure(_context("BEARISH"), result)
    assert result.pattern_direction == "SELL"


def test_aligned_structure_preserves_pattern_confidence():
    result = _result(absorption="BUY_ABSORPTION", confidence=0.8)
    OrderFlow()._qualify_structure(_context("TREND_UP"), result)
    assert result.structure_alignment == "ALIGNED"
    assert result.structural_pattern_confidence == 0.8


def test_conflicting_structure_reduces_confidence():
    result = _result(absorption="BUY_ABSORPTION", confidence=0.8)
    OrderFlow()._qualify_structure(_context("TREND_DOWN"), result)
    assert result.structure_alignment == "CONFLICT"
    assert result.structural_pattern_confidence == 0.48


def test_sideways_structure_is_neutral():
    result = _result(absorption="SELL_ABSORPTION", confidence=0.75)
    OrderFlow()._qualify_structure(_context("SIDEWAYS"), result)
    assert result.structure_alignment == "NEUTRAL"
    assert result.structural_pattern_confidence == 0.6


def test_missing_structure_is_unavailable():
    result = _result(absorption="BUY_ABSORPTION")
    context = SimpleNamespace(market_structure=None)
    OrderFlow()._qualify_structure(context, result)
    assert result.structure_alignment == "UNAVAILABLE"


def test_no_directional_pattern_is_neutral_and_zero_confidence():
    result = _result(confidence=0.9)
    OrderFlow()._qualify_structure(_context("BULLISH"), result)
    assert result.pattern_direction == "NONE"
    assert result.structure_alignment == "NEUTRAL"
    assert result.structural_pattern_confidence == 0.0


def test_clear_resets_structural_fields():
    result = _result(absorption="BUY_ABSORPTION")
    OrderFlow()._qualify_structure(_context("BULLISH"), result)
    result.clear()
    assert result.pattern_direction == "NONE"
    assert result.structure_alignment == "UNAVAILABLE"
    assert result.structural_pattern_confidence == 0.0
