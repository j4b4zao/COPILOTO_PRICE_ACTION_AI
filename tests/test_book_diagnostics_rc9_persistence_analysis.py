import json

from analysis.replay.book_diagnostics_replay_analyzer import (
    BookDiagnosticsReplayAnalyzer,
)
from analysis.replay.book_diagnostics_replay_recorder import (
    BookDiagnosticsReplayRecorder,
    BookDiagnosticsReplaySample,
)


def sample(
    *,
    book_state="CLEAN_DIRECTIONAL_CONTEXT",
    agreement="AGREE",
    official_action="BUY",
    official_direction="BUY",
    book_direction="BUY",
    book_score=80.0,
    official_score=90.0,
    caution_count=0,
    environment="NORMAL_OR_OTHER",
    rr=2.0,
):
    return BookDiagnosticsReplaySample(
        symbol="WINV26",
        timeframe="M5",
        timestamp="2026-08-22T10:00:00-03:00",
        candle_count=30,
        last_price=170000.0,
        official_action=official_action,
        official_direction=official_direction,
        official_score=official_score,
        official_risk_reward=rr,
        official_setup="TEST",
        book_state=book_state,
        book_direction=book_direction,
        book_score=book_score,
        book_caution_count=caution_count,
        trend_control_state="STRONG_CONTROL",
        reversal_pressure_state="NONE",
        market_environment_state=environment,
        direction_agreement=agreement,
        book_passive_only=True,
    )


def test_jsonl_round_trip(tmp_path):
    recorder = BookDiagnosticsReplayRecorder(max_samples=10)
    recorder.add_sample(sample())
    recorder.add_sample(
        sample(
            book_state="TREND_REVERSAL_TENSION",
            agreement="CONFLICT",
            official_direction="BUY",
            book_direction="SELL",
        )
    )

    path = recorder.export_jsonl(tmp_path / "replay" / "samples.jsonl")
    loaded = BookDiagnosticsReplayRecorder.load_jsonl(path, max_samples=10)

    assert loaded.size == 2
    assert loaded.samples == recorder.samples


def test_csv_export_contains_header_and_rows(tmp_path):
    recorder = BookDiagnosticsReplayRecorder()
    recorder.add_sample(sample())

    path = recorder.export_csv(tmp_path / "samples.csv")
    text = path.read_text(encoding="utf-8")

    assert "official_action" in text.splitlines()[0]
    assert "CLEAN_DIRECTIONAL_CONTEXT" in text
    assert "WINV26" in text


def test_load_jsonl_rejects_invalid_json(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"ok": true}\nnot-json\n', encoding="utf-8")

    try:
        BookDiagnosticsReplayRecorder.load_jsonl(path)
    except ValueError as exc:
        assert "line 2" in str(exc)
    else:
        raise AssertionError("ValueError expected")


def test_analyzer_groups_metrics_by_synthesis_state():
    samples = [
        sample(book_state="CLEAN_DIRECTIONAL_CONTEXT", agreement="AGREE"),
        sample(book_state="CLEAN_DIRECTIONAL_CONTEXT", agreement="AGREE", book_score=90.0),
        sample(
            book_state="TREND_REVERSAL_TENSION",
            agreement="CONFLICT",
            official_direction="BUY",
            book_direction="SELL",
            caution_count=2,
            book_score=55.0,
        ),
    ]

    metrics = BookDiagnosticsReplayAnalyzer(samples).by_synthesis_state()

    clean = metrics["CLEAN_DIRECTIONAL_CONTEXT"]
    tension = metrics["TREND_REVERSAL_TENSION"]

    assert clean["samples"] == 2
    assert clean["agreement_rate"] == 1.0
    assert clean["avg_book_score"] == 85.0
    assert tension["samples"] == 1
    assert tension["conflict_rate"] == 1.0
    assert tension["avg_caution_count"] == 2.0


def test_wait_samples_are_not_directionally_comparable():
    items = [
        sample(
            official_action="WAIT",
            official_direction="NONE",
            book_direction="BUY",
            agreement="NOT_COMPARABLE",
        )
    ]

    metrics = BookDiagnosticsReplayAnalyzer(items).overall()

    assert metrics["samples"] == 1
    assert metrics["comparable"] == 0
    assert metrics["agreement_rate"] == 0.0
    assert metrics["official_approval_rate"] == 0.0


def test_market_environment_metrics_are_separate():
    items = [
        sample(environment="NORMAL_OR_OTHER", agreement="AGREE"),
        sample(
            environment="TIGHT_RANGE_NO_TRADE_WATCH",
            agreement="CONFLICT",
            official_direction="BUY",
            book_direction="SELL",
            caution_count=2,
        ),
    ]

    metrics = BookDiagnosticsReplayAnalyzer(items).by_market_environment()

    assert metrics["NORMAL_OR_OTHER"]["agreement_rate"] == 1.0
    assert metrics["TIGHT_RANGE_NO_TRADE_WATCH"]["conflict_rate"] == 1.0
