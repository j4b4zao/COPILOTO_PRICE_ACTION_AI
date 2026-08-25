from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from models.book_diagnostics_result import BookDiagnosticsResult


def test_result_clear_resets_tight_range_state():
    result = BookDiagnosticsResult()
    result.tight_trading_range["state"] = "NO_TRADE_ZONE"
    result.tight_range_active = True
    result.no_trade_zone_watch = True
    result.range_quality_penalty = 35.0

    result.clear()

    assert result.tight_trading_range == {}
    assert result.tight_range_active is False
    assert result.no_trade_zone_watch is False
    assert result.range_breakout_confirmed is False
    assert result.range_breakout_direction == "NONE"
    assert result.directional_signal_range_conflict is False
    assert result.range_quality_penalty == 0.0


def test_tight_range_marks_directional_conflict_without_changing_bias():
    result = BookDiagnosticsResult()
    result.directional_bias = "BUY"
    result.quality_score = 82.0
    result.tight_trading_range.update({
        "valid": True,
        "state": "NO_TRADE_ZONE",
        "no_trade_zone": True,
        "breakout_confirmed": False,
        "breakout_direction": "NONE",
        "range_width_atr": 1.8,
        "overlap_ratio": 0.85,
        "barbwire": True,
    })

    BookDiagnosticsEngine._apply_tight_range_overlay(result)

    assert result.directional_bias == "BUY"
    assert result.quality_score == 82.0
    assert result.tight_range_active is True
    assert result.no_trade_zone_watch is True
    assert result.directional_signal_range_conflict is True
    assert result.range_quality_penalty == 35.0
    assert "DIRECTIONAL_SIGNAL_INSIDE_TIGHT_RANGE" in result.reasons


def test_confirmed_range_breakout_is_observed_separately():
    result = BookDiagnosticsResult()
    result.directional_bias = "BUY"
    result.tight_trading_range.update({
        "valid": True,
        "state": "TIGHT_RANGE_BREAKOUT_CONFIRMED",
        "no_trade_zone": False,
        "breakout_confirmed": True,
        "breakout_direction": "UP",
        "range_width_atr": 2.5,
        "overlap_ratio": 0.75,
        "barbwire": False,
    })

    BookDiagnosticsEngine._apply_tight_range_overlay(result)

    assert result.tight_range_active is False
    assert result.no_trade_zone_watch is False
    assert result.range_breakout_confirmed is True
    assert result.range_breakout_direction == "UP"
    assert result.directional_signal_range_conflict is False
    assert "TIGHT_RANGE_BREAKOUT_CONFIRMED_UP" in result.reasons


def test_invalid_tight_range_does_not_create_filter_state():
    result = BookDiagnosticsResult()
    result.directional_bias = "SELL"
    result.tight_trading_range.update({
        "valid": False,
        "state": "NO_TRADE_ZONE",
        "no_trade_zone": True,
        "breakout_confirmed": False,
        "range_width_atr": 1.0,
        "overlap_ratio": 1.0,
        "barbwire": True,
    })

    BookDiagnosticsEngine._apply_tight_range_overlay(result)

    assert result.tight_range_active is False
    assert result.no_trade_zone_watch is False
    assert result.directional_signal_range_conflict is False
    assert result.range_quality_penalty == 0.0


def test_range_penalty_is_diagnostic_only():
    result = BookDiagnosticsResult()
    result.directional_bias = "SELL"
    result.quality_score = 91.0
    result.confidence = 0.91
    result.tight_trading_range.update({
        "valid": True,
        "state": "TIGHT_TRADING_RANGE",
        "no_trade_zone": True,
        "breakout_confirmed": False,
        "range_width_atr": 2.4,
        "overlap_ratio": 0.72,
        "barbwire": False,
    })

    BookDiagnosticsEngine._apply_tight_range_overlay(result)

    assert result.range_quality_penalty == 15.0
    assert result.quality_score == 91.0
    assert result.confidence == 0.91
    assert result.passive_only is True
