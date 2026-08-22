from types import SimpleNamespace

from analysis.replay.book_diagnostics_session_analyzer import (
    BookDiagnosticsSessionAnalyzer,
)


def pair(timestamp, state="CLEAN_DIRECTIONAL_CONTEXT", direction="BUY", touch="TARGET"):
    sample = SimpleNamespace(
        timestamp=timestamp,
        book_state=state,
        book_direction=direction,
        market_environment_state="NORMAL_OR_OTHER",
        reversal_pressure_state="NONE",
        trend_control_state="STRONG_CONTROL",
        direction_agreement="AGREE",
    )
    outcome = SimpleNamespace(
        book_direction=direction,
        book_first_touch=touch,
        future_direction=direction,
        mfe_r=1.5,
        mae_r=0.4,
        official_trade_comparable=False,
        official_first_touch="NONE",
    )
    return sample, outcome


def test_segments_opening_lunch_and_closing():
    records = [
        pair("2026-08-20T09:15:00-03:00"),
        pair("2026-08-20T12:30:00-03:00"),
        pair("2026-08-20T17:00:00-03:00"),
    ]

    result = BookDiagnosticsSessionAnalyzer().analyze(records)

    assert result["by_intraday_window"]["OPENING"]["samples"] == 1
    assert result["by_intraday_window"]["LUNCH"]["samples"] == 1
    assert result["by_intraday_window"]["CLOSING"]["samples"] == 1


def test_groups_by_session_date_and_weekday():
    records = [
        pair("2026-08-20T10:00:00-03:00"),
        pair("2026-08-20T11:00:00-03:00"),
        pair("2026-08-21T10:00:00-03:00"),
    ]

    result = BookDiagnosticsSessionAnalyzer().analyze(records)

    assert result["by_session_date"]["2026-08-20"]["samples"] == 2
    assert result["by_session_date"]["2026-08-21"]["samples"] == 1
    assert result["by_weekday"]["THURSDAY"]["samples"] == 2
    assert result["by_weekday"]["FRIDAY"]["samples"] == 1


def test_window_and_state_keeps_contexts_separate():
    records = [
        pair("2026-08-20T09:10:00-03:00", "CLEAN_DIRECTIONAL_CONTEXT"),
        pair("2026-08-20T09:20:00-03:00", "TREND_REVERSAL_TENSION", touch="STOP"),
    ]

    result = BookDiagnosticsSessionAnalyzer().analyze(records)

    assert result["by_window_and_state"][
        "OPENING|CLEAN_DIRECTIONAL_CONTEXT"
    ]["book_target_first_rate"] == 1.0
    assert result["by_window_and_state"][
        "OPENING|TREND_REVERSAL_TENSION"
    ]["book_stop_first_rate"] == 1.0


def test_promotion_metrics_are_returned_per_date():
    records = [
        pair("2026-08-20T09:10:00-03:00"),
        pair("2026-08-20T09:20:00-03:00"),
        pair("2026-08-21T09:10:00-03:00"),
    ]

    metrics = BookDiagnosticsSessionAnalyzer().promotion_session_metrics(
        records,
        book_state="CLEAN_DIRECTIONAL_CONTEXT",
        intraday_window="OPENING",
    )

    assert len(metrics) == 2
    assert metrics[0]["session_date"] == "2026-08-20"
    assert metrics[0]["samples"] == 2
    assert metrics[1]["session_date"] == "2026-08-21"


def test_invalid_timestamp_is_not_silently_forced_into_regular_session():
    result = BookDiagnosticsSessionAnalyzer().analyze([
        pair("not-a-timestamp")
    ])

    assert result["by_intraday_window"]["UNKNOWN"]["samples"] == 1
    assert result["by_session_date"]["UNKNOWN"]["samples"] == 1


def test_outside_regular_windows_is_explicit():
    result = BookDiagnosticsSessionAnalyzer().analyze([
        pair("2026-08-20T08:30:00-03:00")
    ])

    assert result["by_intraday_window"]["OUTSIDE_REGULAR_WINDOWS"]["samples"] == 1
