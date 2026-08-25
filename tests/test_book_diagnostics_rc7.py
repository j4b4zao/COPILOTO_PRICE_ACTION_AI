from models.book_diagnostics_result import BookDiagnosticsResult
from analysis.book_diagnostics_engine import BookDiagnosticsEngine


def test_rc7_clean_directional_context():
    result = BookDiagnosticsResult()
    result.directional_bias = "BUY"
    result.alignment = "FULL_ALIGNMENT"
    result.aligned_diagnostics = 3
    result.quality_score = 82.0

    BookDiagnosticsEngine._build_rc7_synthesis(result)

    assert result.trend_control["state"] == "STRONG_CONTROL"
    assert result.trend_control["direction"] == "BUY"
    assert result.reversal_pressure["state"] == "NONE"
    assert result.market_environment["state"] == "NORMAL_OR_OTHER"
    assert result.synthesis_state == "CLEAN_DIRECTIONAL_CONTEXT"
    assert result.synthesis_direction == "BUY"
    assert result.caution_count == 0
    assert result.synthesis_score == 82.0


def test_rc7_tight_range_degrades_environment_only_observationally():
    result = BookDiagnosticsResult()
    result.directional_bias = "SELL"
    result.alignment = "FULL_ALIGNMENT"
    result.aligned_diagnostics = 3
    result.quality_score = 90.0
    result.tight_range_active = True
    result.no_trade_zone_watch = True
    result.directional_signal_range_conflict = True
    result.range_quality_penalty = 30.0

    BookDiagnosticsEngine._build_rc7_synthesis(result)

    assert result.market_environment["state"] == "TIGHT_RANGE_NO_TRADE_WATCH"
    assert result.market_environment["favorability"] == 70.0
    assert result.synthesis_state == "DIRECTIONAL_EDGE_IN_POOR_ENVIRONMENT"
    assert result.synthesis_direction == "SELL"
    assert result.synthesis_score < result.quality_score
    assert result.quality_score == 90.0
    assert result.passive_only is True


def test_rc7_reversal_confluence_creates_trend_reversal_tension():
    result = BookDiagnosticsResult()
    result.directional_bias = "BUY"
    result.alignment = "ALIGNED"
    result.aligned_diagnostics = 2
    result.quality_score = 78.0

    result.reversal_watch = True
    result.reversal_confirmed = True
    result.reversal_direction = "SELL"
    result.reversal_quality_score = 90.0
    result.trend_reversal_divergence = True

    result.wedge_watch = True
    result.wedge_confirmed = True
    result.wedge_direction = "SELL"
    result.wedge_quality_score = 85.0
    result.mtr_wedge_confluence = True

    BookDiagnosticsEngine._build_rc7_synthesis(result)

    assert result.reversal_pressure["state"] == "CONFIRMED_CONFLUENCE"
    assert result.reversal_pressure["direction"] == "SELL"
    assert result.synthesis_state == "TREND_REVERSAL_TENSION"
    assert result.synthesis_direction == "BUY"
    assert result.caution_count >= 1


def test_rc7_reversal_conflict_stays_non_directional_inside_pressure_block():
    result = BookDiagnosticsResult()
    result.directional_bias = "BUY"
    result.alignment = "ALIGNED"
    result.quality_score = 70.0

    result.reversal_watch = True
    result.reversal_direction = "SELL"
    result.reversal_quality_score = 70.0
    result.wedge_watch = True
    result.wedge_direction = "BUY"
    result.wedge_quality_score = 60.0
    result.mtr_wedge_conflict = True

    BookDiagnosticsEngine._build_rc7_synthesis(result)

    assert result.reversal_pressure["state"] == "CONFLICTED_PRESSURE"
    assert result.reversal_pressure["direction"] == "NONE"
    assert result.caution_count >= 1
    assert result.synthesis_state == "DIRECTIONAL_CONTEXT_WITH_CAUTION"


def test_rc7_reset_clears_synthesis_blocks():
    result = BookDiagnosticsResult()
    result.trend_control["state"] = "CONTROL"
    result.reversal_pressure["state"] = "WATCH"
    result.market_environment["state"] = "TIGHT_RANGE"
    result.synthesis_state = "DIRECTIONAL_CONTEXT_WITH_CAUTION"
    result.synthesis_direction = "BUY"
    result.synthesis_score = 55.0
    result.caution_count = 3

    result.clear()

    assert result.trend_control == {}
    assert result.reversal_pressure == {}
    assert result.market_environment == {}
    assert result.synthesis_state == "NEUTRAL"
    assert result.synthesis_direction == "NONE"
    assert result.synthesis_score == 0.0
    assert result.caution_count == 0
