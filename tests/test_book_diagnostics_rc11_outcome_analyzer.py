from types import SimpleNamespace

from analysis.replay.book_diagnostics_outcome_analyzer import (
    BookDiagnosticsOutcomeAnalyzer,
)
from analysis.replay.book_diagnostics_outcome_labeler import BookDiagnosticsOutcome
from analysis.replay.book_diagnostics_replay_recorder import BookDiagnosticsReplaySample


def pair(state, direction, first_touch, mfe_r, mae_r, environment="NORMAL_OR_OTHER"):
    sample = BookDiagnosticsReplaySample(
        book_state=state,
        book_direction=direction,
        market_environment_state=environment,
        reversal_pressure_state="NONE",
        trend_control_state="STRONG_CONTROL",
        direction_agreement="AGREE",
    )
    outcome = BookDiagnosticsOutcome(
        book_direction=direction,
        future_direction=direction,
        mfe_r=mfe_r,
        mae_r=mae_r,
        book_first_touch=first_touch,
    )
    return sample, outcome


def test_overall_outcome_metrics():
    records = [
        pair("CLEAN_DIRECTIONAL_CONTEXT", "BUY", "TARGET", 1.5, 0.3),
        pair("CLEAN_DIRECTIONAL_CONTEXT", "BUY", "TARGET", 1.2, 0.4),
        pair("CLEAN_DIRECTIONAL_CONTEXT", "SELL", "STOP", 0.4, 1.1),
    ]

    result = BookDiagnosticsOutcomeAnalyzer().analyze(records)["overall"]

    assert result["samples"] == 3
    assert result["directional_samples"] == 3
    assert result["book_target_first"] == 2
    assert result["book_stop_first"] == 1
    assert result["book_target_first_rate"] == 0.6667
    assert result["future_direction_alignment_rate"] == 1.0
    assert result["avg_mfe_r"] > result["avg_mae_r"]


def test_group_by_synthesis_state_separates_quality():
    records = [
        pair("CLEAN_DIRECTIONAL_CONTEXT", "BUY", "TARGET", 1.8, 0.2),
        pair("CLEAN_DIRECTIONAL_CONTEXT", "BUY", "TARGET", 1.4, 0.3),
        pair("DIRECTIONAL_EDGE_IN_POOR_ENVIRONMENT", "BUY", "STOP", 0.2, 1.2, "TIGHT_RANGE"),
    ]

    grouped = BookDiagnosticsOutcomeAnalyzer().analyze(records)["by_synthesis_state"]

    assert grouped["CLEAN_DIRECTIONAL_CONTEXT"]["book_target_first_rate"] == 1.0
    assert grouped["DIRECTIONAL_EDGE_IN_POOR_ENVIRONMENT"]["book_stop_first_rate"] == 1.0


def test_official_trade_metrics_are_kept_separate():
    sample = BookDiagnosticsReplaySample(
        book_state="CLEAN_DIRECTIONAL_CONTEXT",
        book_direction="BUY",
    )
    outcomes = [
        BookDiagnosticsOutcome(
            book_direction="BUY",
            future_direction="BUY",
            mfe_r=1.2,
            mae_r=0.2,
            book_first_touch="TARGET",
            official_trade_comparable=True,
            official_first_touch="TARGET",
        ),
        BookDiagnosticsOutcome(
            book_direction="BUY",
            future_direction="SELL",
            mfe_r=0.4,
            mae_r=1.1,
            book_first_touch="STOP",
            official_trade_comparable=True,
            official_first_touch="STOP",
        ),
    ]

    result = BookDiagnosticsOutcomeAnalyzer().analyze([(sample, o) for o in outcomes])["overall"]

    assert result["official_comparable"] == 2
    assert result["official_target_first_rate"] == 0.5
    assert result["official_stop_first_rate"] == 0.5


def test_rank_synthesis_states_obeys_minimum_sample_size():
    analyzer = BookDiagnosticsOutcomeAnalyzer()
    records = [
        pair("A", "BUY", "TARGET", 1.5, 0.2),
        pair("A", "BUY", "TARGET", 1.4, 0.3),
        pair("B", "SELL", "TARGET", 2.0, 0.1),
    ]

    ranked = analyzer.rank_synthesis_states(records, min_samples=2)

    assert len(ranked) == 1
    assert ranked[0]["book_state"] == "A"


def test_dict_and_object_pairs_are_supported():
    sample, outcome = pair("CLEAN_DIRECTIONAL_CONTEXT", "BUY", "TARGET", 1.0, 0.2)
    analyzer = BookDiagnosticsOutcomeAnalyzer()

    as_dict = analyzer.analyze([{"sample": sample, "outcome": outcome}])
    as_object = analyzer.analyze([SimpleNamespace(sample=sample, outcome=outcome)])

    assert as_dict["overall"] == as_object["overall"]


def test_empty_analysis_is_safe():
    result = BookDiagnosticsOutcomeAnalyzer().analyze([])

    assert result["overall"]["samples"] == 0
    assert result["overall"]["book_target_first_rate"] == 0.0
