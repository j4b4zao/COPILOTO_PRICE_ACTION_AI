from models.book_diagnostics_result import BookDiagnosticsResult
from analysis.book_diagnostics_engine import BookDiagnosticsEngine


def test_result_clear_resets_wedge_state():
    result = BookDiagnosticsResult()
    result.wedge_reversal["state"] = "WEDGE_REVERSAL_CONFIRMED"
    result.wedge_watch = True
    result.wedge_confirmed = True
    result.wedge_direction = "SELL"
    result.wedge_quality_score = 90.0
    result.mtr_wedge_confluence = True

    result.clear()

    assert result.wedge_reversal == {}
    assert result.wedge_watch is False
    assert result.wedge_confirmed is False
    assert result.wedge_direction == "NONE"
    assert result.wedge_quality_score == 0.0
    assert result.mtr_wedge_confluence is False
    assert result.mtr_wedge_conflict is False


def test_mtr_and_wedge_same_direction_create_confluence():
    result = BookDiagnosticsResult()
    result.directional_bias = "BUY"
    result.major_trend_reversal.update({
        "valid": True,
        "state": "MTR_EXTREME_TEST",
        "reversal_direction": "SELL",
        "quality_score": 65.0,
        "structural_break": True,
        "follow_through": False,
    })
    result.wedge_reversal.update({
        "valid": True,
        "state": "THREE_PUSH_EXHAUSTION_WATCH",
        "reversal_direction": "SELL",
        "quality_score": 70.0,
        "push_count": 3,
        "momentum_loss": True,
        "reversal_confirmed": False,
    })

    BookDiagnosticsEngine._apply_reversal_overlay(result)
    BookDiagnosticsEngine._apply_wedge_overlay(result)

    assert result.reversal_watch is True
    assert result.wedge_watch is True
    assert result.mtr_wedge_confluence is True
    assert result.mtr_wedge_conflict is False
    assert "MTR_WEDGE_REVERSAL_CONFLUENCE" in result.reasons


def test_confirmed_wedge_remains_observational_only():
    result = BookDiagnosticsResult()
    result.directional_bias = "BUY"
    result.wedge_reversal.update({
        "valid": True,
        "state": "WEDGE_REVERSAL_CONFIRMED",
        "reversal_direction": "SELL",
        "quality_score": 95.0,
        "push_count": 3,
        "momentum_loss": True,
        "reversal_confirmed": True,
    })

    BookDiagnosticsEngine._apply_wedge_overlay(result)

    assert result.wedge_watch is True
    assert result.wedge_confirmed is True
    assert result.wedge_direction == "SELL"
    assert result.directional_bias == "BUY"
    assert result.passive_only is True
    assert "WEDGE_REVERSAL_CONFIRMED_OBSERVATIONAL_ONLY" in result.reasons


def test_mtr_wedge_opposite_directions_create_conflict():
    result = BookDiagnosticsResult()
    result.major_trend_reversal.update({
        "valid": True,
        "state": "MTR_BREAK_ONLY",
        "reversal_direction": "SELL",
        "quality_score": 40.0,
        "structural_break": True,
        "follow_through": False,
    })
    result.wedge_reversal.update({
        "valid": True,
        "state": "THREE_PUSH_EXHAUSTION_WATCH",
        "reversal_direction": "BUY",
        "quality_score": 60.0,
        "push_count": 3,
        "momentum_loss": True,
        "reversal_confirmed": False,
    })

    BookDiagnosticsEngine._apply_reversal_overlay(result)
    BookDiagnosticsEngine._apply_wedge_overlay(result)

    assert result.mtr_wedge_confluence is False
    assert result.mtr_wedge_conflict is True
    assert "MTR_WEDGE_REVERSAL_CONFLICT" in result.reasons


def test_invalid_wedge_does_not_create_watch():
    result = BookDiagnosticsResult()
    result.wedge_reversal.update({
        "valid": False,
        "state": "NO_WEDGE_REVERSAL",
        "reversal_direction": "SELL",
        "quality_score": 100.0,
        "push_count": 3,
        "momentum_loss": True,
        "reversal_confirmed": False,
    })

    BookDiagnosticsEngine._apply_wedge_overlay(result)

    assert result.wedge_watch is False
    assert result.wedge_confirmed is False
    assert result.wedge_direction == "NONE"
