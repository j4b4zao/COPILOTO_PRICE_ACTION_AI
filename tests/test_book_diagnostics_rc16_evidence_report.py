from types import SimpleNamespace

from analysis.replay.book_diagnostics_evidence_report import BookDiagnosticsEvidenceReporter
from analysis.replay.book_diagnostics_promotion_gate import BookDiagnosticsPromotionGate
from analysis.replay.book_diagnostics_walk_forward import BookDiagnosticsWalkForward


STATE = "CLEAN_DIRECTIONAL_CONTEXT"


def _record(day, *, positive=True, state=STATE):
    sample = SimpleNamespace(
        timestamp=f"2026-08-{day:02d}T10:00:00",
        book_state=state,
        book_direction="BUY",
        market_environment_state="NORMAL_OR_OTHER",
        reversal_pressure_state="NONE",
        trend_control_state="CONTROL",
        direction_agreement="AGREE",
    )
    outcome = SimpleNamespace(
        book_direction="BUY",
        book_first_touch="TARGET" if positive else "STOP",
        future_direction="BUY" if positive else "SELL",
        official_trade_comparable=False,
        official_first_touch="NONE",
        mfe_r=1.2 if positive else 0.2,
        mae_r=0.2 if positive else 1.2,
    )
    return sample, outcome


def _reporter():
    gate = BookDiagnosticsPromotionGate(
        min_samples=2,
        promotion_samples=4,
        min_sessions=2,
        min_stability_rate=1.0,
    )
    walk = BookDiagnosticsWalkForward(
        train_size=2,
        validation_size=1,
        step_size=1,
    )
    return BookDiagnosticsEvidenceReporter(gate=gate, walk_forward=walk)


def test_complete_positive_evidence_reaches_manual_review():
    records = [_record(day) for day in range(1, 7)]
    enriched = [
        {"sample": sample, "outcome": outcome, "meta": {
            "regime": "TREND",
            "volatility": "NORMAL",
            "structural_strength": 80,
        }}
        for sample, outcome in records
    ]

    report = _reporter().build(records, book_state=STATE, enriched_records=enriched)

    assert report.promotion_gate["status"] == "CANDIDATE_FOR_PROMOTION"
    assert report.walk_forward["walk_forward_stable"] is True
    assert report.evidence_status == "READY_FOR_MANUAL_REVIEW"
    assert report.ready_for_manual_review is True
    assert "NO_AUTOMATIC_RUNTIME_PROMOTION" in report.reasons


def test_missing_regime_evidence_keeps_researching():
    records = [_record(day) for day in range(1, 7)]
    report = _reporter().build(records, book_state=STATE)

    assert report.ready_for_manual_review is False
    assert report.evidence_status == "KEEP_RESEARCHING"
    assert "REGIME_EVIDENCE_NOT_AVAILABLE" in report.reasons


def test_negative_out_of_sample_blocks_manual_review():
    records = [_record(1), _record(2), _record(3, positive=False), _record(4, positive=False)]
    enriched = [
        {"sample": sample, "outcome": outcome, "meta": {
            "regime": "TREND", "volatility": "NORMAL", "structural_strength": 80
        }}
        for sample, outcome in records
    ]
    report = _reporter().build(records, book_state=STATE, enriched_records=enriched)

    assert report.walk_forward["walk_forward_stable"] is False
    assert report.ready_for_manual_review is False
    assert "OUT_OF_SAMPLE_NOT_STABLE" in report.reasons


def test_state_filter_excludes_other_states():
    records = [_record(1), _record(2), _record(3, state="OTHER")]
    report = _reporter().build(records, book_state=STATE)
    assert report.sample_count == 2
    assert report.book_state == STATE


def test_empty_state_has_insufficient_evidence():
    report = _reporter().build([], book_state=STATE)
    assert report.evidence_status == "INSUFFICIENT_EVIDENCE"
    assert report.ready_for_manual_review is False
    assert "NO_DIRECTIONAL_OUTCOMES" in report.reasons
