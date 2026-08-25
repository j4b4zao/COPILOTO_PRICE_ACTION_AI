from datetime import datetime
from types import SimpleNamespace

from analysis.replay.book_diagnostics_replay_recorder import (
    BookDiagnosticsReplayRecorder,
)
from analysis.analysis_pipeline import AnalysisPipeline


def _context(
    official_action="BUY",
    official_direction="BUY",
    book_direction="BUY",
    book_state="CLEAN_DIRECTIONAL_CONTEXT",
):
    market = SimpleNamespace(
        symbol="WINV26",
        timeframe="M5",
        timestamp=datetime(2026, 8, 22, 10, 15),
        candle_count=120,
        last_price=171500.0,
    )
    decision = SimpleNamespace(
        action=official_action,
        direction=official_direction,
        score=188.0,
        risk_reward=2.0,
        setup="A+",
    )
    book = SimpleNamespace(
        synthesis_state=book_state,
        synthesis_direction=book_direction,
        synthesis_score=86.0,
        caution_count=0,
        trend_control_state="STRONG_CONTROL",
        reversal_pressure_state="NONE",
        market_environment_state="NORMAL_OR_OTHER",
        passive_only=True,
    )
    return SimpleNamespace(
        market=market,
        decision=decision,
        book_diagnostics=book,
    )


def test_replay_records_agreement_without_mutating_context():
    context = _context()
    before = vars(context.book_diagnostics).copy()

    recorder = BookDiagnosticsReplayRecorder()
    sample = recorder.record(context)

    assert sample.direction_agreement == "AGREE"
    assert sample.official_direction == "BUY"
    assert sample.book_direction == "BUY"
    assert recorder.size == 1
    assert vars(context.book_diagnostics) == before


def test_replay_records_direction_conflict():
    recorder = BookDiagnosticsReplayRecorder()
    sample = recorder.record(
        _context(official_action="SELL", official_direction="SELL", book_direction="BUY")
    )

    assert sample.direction_agreement == "CONFLICT"


def test_wait_is_not_comparable_to_book_direction():
    recorder = BookDiagnosticsReplayRecorder()
    sample = recorder.record(
        _context(official_action="WAIT", official_direction="NONE", book_direction="BUY")
    )

    assert sample.direction_agreement == "NOT_COMPARABLE"


def test_summary_counts_only_comparable_directional_samples():
    recorder = BookDiagnosticsReplayRecorder()
    recorder.record(_context())
    recorder.record(
        _context(official_action="SELL", official_direction="SELL", book_direction="BUY")
    )
    recorder.record(
        _context(official_action="WAIT", official_direction="NONE", book_direction="BUY")
    )

    summary = recorder.summary()

    assert summary["samples"] == 3
    assert summary["comparable"] == 2
    assert summary["agreements"] == 1
    assert summary["conflicts"] == 1
    assert summary["agreement_rate"] == 0.5
    assert summary["conflict_rate"] == 0.5


def test_recorder_respects_max_samples_ring_behavior():
    recorder = BookDiagnosticsReplayRecorder(max_samples=2)
    recorder.record(_context())
    recorder.record(_context(book_direction="SELL"))
    recorder.record(_context())

    assert recorder.size == 2


def test_pipeline_owns_passive_replay_recorder():
    pipeline = AnalysisPipeline()

    assert isinstance(
        pipeline.book_diagnostics_replay,
        BookDiagnosticsReplayRecorder,
    )
