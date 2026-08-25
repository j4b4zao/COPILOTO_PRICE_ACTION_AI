from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from models.book_diagnostics_result import BookDiagnosticsResult


def _base_buy_context(result):
    result.always_in.update({
        "direction": "BUY",
        "quality_score": 82.0,
    })
    result.trend_strength.update({
        "brooks_trend_strength_direction": "BUY",
        "brooks_trend_strength_score": 88.0,
    })
    result.breakout_strength.update({
        "valid": True,
        "direction": "BUY",
        "score": 84.0,
    })


def test_result_clear_resets_mtr_observation():
    result = BookDiagnosticsResult()
    result.major_trend_reversal["state"] = "MTR_CONFIRMED"
    result.reversal_watch = True
    result.reversal_confirmed = True
    result.reversal_direction = "SELL"
    result.reversal_quality_score = 90.0
    result.trend_reversal_divergence = True

    result.clear()

    assert result.major_trend_reversal == {}
    assert result.reversal_watch is False
    assert result.reversal_confirmed is False
    assert result.reversal_direction == "NONE"
    assert result.reversal_quality_score == 0.0
    assert result.trend_reversal_divergence is False
    assert result.passive_only is True


def test_mtr_watch_can_diverge_from_strong_trend_without_changing_bias():
    result = BookDiagnosticsResult()
    _base_buy_context(result)
    result.major_trend_reversal.update({
        "valid": True,
        "state": "MTR_EXTREME_TEST",
        "reversal_direction": "SELL",
        "quality_score": 60.0,
        "structural_break": True,
        "follow_through": False,
    })

    BookDiagnosticsEngine._synthesize(result)

    assert result.directional_bias == "BUY"
    assert result.alignment == "FULL_ALIGNMENT"
    assert result.reversal_watch is True
    assert result.reversal_confirmed is False
    assert result.reversal_direction == "SELL"
    assert result.trend_reversal_divergence is True
    assert "MTR_WATCH_OPPOSES_DIRECTIONAL_BIAS" in result.reasons


def test_confirmed_mtr_is_observed_but_does_not_replace_directional_bias():
    result = BookDiagnosticsResult()
    _base_buy_context(result)
    result.major_trend_reversal.update({
        "valid": True,
        "state": "MTR_CONFIRMED",
        "reversal_direction": "SELL",
        "quality_score": 100.0,
        "structural_break": True,
        "follow_through": True,
    })

    BookDiagnosticsEngine._synthesize(result)

    assert result.directional_bias == "BUY"
    assert result.reversal_confirmed is True
    assert result.reversal_direction == "SELL"
    assert result.trend_reversal_divergence is True
    assert result.passive_only is True
    assert "CONFIRMED_MTR_OPPOSES_DIRECTIONAL_BIAS" in result.reasons
    assert "MTR_CONFIRMED_OBSERVATIONAL_ONLY" in result.reasons


def test_mtr_same_direction_as_bias_does_not_create_divergence():
    result = BookDiagnosticsResult()
    _base_buy_context(result)
    result.major_trend_reversal.update({
        "valid": True,
        "state": "MTR_CONFIRMED",
        "reversal_direction": "BUY",
        "quality_score": 90.0,
        "structural_break": True,
        "follow_through": True,
    })

    BookDiagnosticsEngine._synthesize(result)

    assert result.reversal_confirmed is True
    assert result.trend_reversal_divergence is False


def test_invalid_mtr_is_ignored_by_overlay():
    result = BookDiagnosticsResult()
    _base_buy_context(result)
    result.major_trend_reversal.update({
        "valid": False,
        "state": "NO_MTR",
        "reversal_direction": "SELL",
        "quality_score": 99.0,
        "structural_break": False,
        "follow_through": False,
    })

    BookDiagnosticsEngine._synthesize(result)

    assert result.directional_bias == "BUY"
    assert result.reversal_watch is False
    assert result.reversal_confirmed is False
    assert result.reversal_direction == "NONE"
    assert result.trend_reversal_divergence is False
