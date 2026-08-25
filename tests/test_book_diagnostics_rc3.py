from types import SimpleNamespace

from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from models.book_diagnostics_result import BookDiagnosticsResult


class FakeMetrics:
    def __init__(self, data):
        self.data = data

    def to_dict(self):
        return dict(self.data)


def test_result_clear_resets_breakout_diagnostics():
    result = BookDiagnosticsResult()
    result.breakout_strength["direction"] = "BUY"
    result.aligned_diagnostics = 3
    result.conflicting_diagnostics = 1

    result.clear()

    assert result.breakout_strength == {}
    assert result.aligned_diagnostics == 0
    assert result.conflicting_diagnostics == 0
    assert result.passive_only is True


def test_three_diagnostics_can_reach_full_alignment():
    result = BookDiagnosticsResult()
    result.always_in.update({"direction": "BUY", "quality_score": 80.0})
    result.trend_strength.update({
        "brooks_trend_strength_direction": "BUY",
        "brooks_trend_strength_score": 90.0,
    })
    result.breakout_strength.update({
        "valid": True,
        "direction": "BUY",
        "score": 85.0,
    })

    BookDiagnosticsEngine._synthesize(result)

    assert result.directional_bias == "BUY"
    assert result.alignment == "FULL_ALIGNMENT"
    assert result.aligned_diagnostics == 3
    assert result.conflicting_diagnostics == 0
    assert result.quality_score > 0


def test_breakout_conflict_is_observed_not_operationally_resolved():
    result = BookDiagnosticsResult()
    result.always_in.update({"direction": "BUY", "quality_score": 80.0})
    result.trend_strength.update({
        "brooks_trend_strength_direction": "BUY",
        "brooks_trend_strength_score": 80.0,
    })
    result.breakout_strength.update({
        "valid": True,
        "direction": "SELL",
        "score": 90.0,
    })

    BookDiagnosticsEngine._synthesize(result)

    assert result.directional_bias == "BUY"
    assert result.alignment == "MAJORITY_WITH_CONFLICT"
    assert result.aligned_diagnostics == 2
    assert result.conflicting_diagnostics == 1
    assert result.passive_only is True


def test_invalid_breakout_does_not_vote_direction():
    result = BookDiagnosticsResult()
    result.always_in.update({"direction": "SELL", "quality_score": 75.0})
    result.trend_strength.update({
        "brooks_trend_strength_direction": "SELL",
        "brooks_trend_strength_score": 85.0,
    })
    result.breakout_strength.update({
        "valid": False,
        "direction": "BUY",
        "score": 99.0,
    })

    BookDiagnosticsEngine._synthesize(result)

    assert result.directional_bias == "SELL"
    assert result.alignment == "ALIGNED"
    assert result.aligned_diagnostics == 2
    assert result.conflicting_diagnostics == 0
