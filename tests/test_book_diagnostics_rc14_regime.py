from analysis.replay.book_diagnostics_regime_segmenter import BookDiagnosticsRegimeSegmenter
from analysis.replay.book_diagnostics_replay_recorder import BookDiagnosticsReplaySample
from analysis.replay.book_diagnostics_outcome_labeler import BookDiagnosticsOutcome


def rec(regime, volatility, strength, touch="TARGET"):
    sample = BookDiagnosticsReplaySample(book_direction="BUY", book_state="CLEAN_DIRECTIONAL_CONTEXT")
    outcome = BookDiagnosticsOutcome(book_direction="BUY", mfe_r=1.4, mae_r=0.4, book_first_touch=touch, future_direction="BUY")
    return {"sample": sample, "outcome": outcome, "meta": {"regime": regime, "volatility": volatility, "structural_strength": strength}}


def test_bucket_helpers():
    s = BookDiagnosticsRegimeSegmenter()
    assert s.regime_bucket("strong_trend") == "TREND"
    assert s.regime_bucket("lateral_range") == "RANGE"
    assert s.volatility_bucket("volatile") == "HIGH"
    assert s.volatility_bucket("calm") == "LOW"
    assert s.strength_bucket(80) == "STRONG"
    assert s.strength_bucket(50) == "NORMAL"
    assert s.strength_bucket(20) == "WEAK"


def test_analyze_groups_regime_volatility_strength():
    s = BookDiagnosticsRegimeSegmenter()
    data = [rec("trend", "high", 80), rec("range", "low", 25, "STOP")]
    result = s.analyze(data)
    assert result["by_regime"]["TREND"]["samples"] == 1
    assert result["by_regime"]["RANGE"]["samples"] == 1
    assert result["by_volatility"]["HIGH"]["samples"] == 1
    assert result["by_structural_strength"]["WEAK"]["samples"] == 1
    assert "TREND|HIGH" in result["by_regime_volatility"]


def test_promotion_regime_metrics_respects_min_samples():
    s = BookDiagnosticsRegimeSegmenter()
    data = [rec("trend", "normal", 75), rec("trend", "normal", 70), rec("range", "low", 20)]
    rows = s.promotion_regime_metrics(data, min_samples=2)
    assert len(rows) == 1
    assert rows[0]["regime"] == "TREND"
    assert rows[0]["directional_samples"] == 2


def test_unknown_metadata_is_explicit():
    s = BookDiagnosticsRegimeSegmenter()
    result = s.analyze([rec(None, None, None)])
    assert "UNKNOWN" in result["by_regime"]
    assert "UNKNOWN" in result["by_volatility"]
    assert "UNKNOWN" in result["by_structural_strength"]
