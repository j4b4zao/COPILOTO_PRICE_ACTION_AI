import json

from tools.profit_rtd_brooks_breakout_pullback_audit import (
    audit,
    audit_session,
)


def _row(
    candle_id,
    *,
    trend="UP",
    bos_up=False,
    bos_down=False,
    phase="UNKNOWN",
    signal_phase="UNKNOWN",
    signal_direction="NONE",
    entry=False,
    follow=False,
    breakout_follow=False,
    breakout_direction="NONE",
    choch=False,
):
    return {
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": candle_id,
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.5,
            "volume": 1000.0,
        },
        "structure": {
            "trend": trend,
            "bos_up": bos_up,
            "bos_down": bos_down,
            "choch": choch,
        },
        "price_action": {
            "brooks_breakout_phase": phase,
            "brooks_breakout_direction": breakout_direction,
            "brooks_breakout_follow_through": breakout_follow,
            "brooks_signal_phase": signal_phase,
            "brooks_signal_direction": signal_direction,
            "brooks_entry_triggered": entry,
            "brooks_follow_through": follow,
        },
    }


def _write(tmp_path, rows, *, data_ready=True, name="session.json"):
    path = tmp_path / name
    path.write_text(
        json.dumps({"data_ready": data_ready, "samples": rows}),
        encoding="utf-8",
    )
    return path


def test_buy_sequence_uses_breakout_test_as_pullback_and_rejection(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row(
            "WIN|M1|2",
            trend="UP",
            phase="BREAKOUT_TESTED",
            breakout_direction="UP",
        ),
        _row(
            "WIN|M1|3",
            trend="UP",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["status"] == "MATCHES_OBSERVED"
    assert result["complete_sequences"] == 1
    sequence = result["sequences"][0]
    assert sequence["direction"] == "BUY"
    assert sequence["evidence"]["pullback"]["candle_id"] == "WIN|M1|2"
    assert sequence["evidence"]["rejection"]["candle_id"] == "WIN|M1|2"
    assert sequence["evidence"]["resumption"]["candle_id"] == "WIN|M1|3"


def test_sell_sequence_uses_breakout_test_and_entry_trigger(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="DOWN", bos_down=True),
        _row(
            "WIN|M1|2",
            trend="DOWN",
            phase="BREAKOUT_TESTED",
            breakout_direction="DOWN",
        ),
        _row(
            "WIN|M1|3",
            trend="DOWN",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="DOWN",
            entry=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 1
    assert result["sequences"][0]["direction"] == "SELL"


def test_no_breakout_test_never_fabricates_pullback(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row(
            "WIN|M1|2",
            trend="UP",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="UP",
            entry=True,
        ),
        _row(
            "WIN|M1|3",
            trend="UP",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["status"] == "INSUFFICIENT_SEQUENCE_EVIDENCE"
    assert result["complete_sequences"] == 0
    assert "PULLBACK_NOT_CONFIRMED" in result["incomplete"][0]["reasons"]


def test_impossible_signal_pullback_label_is_not_used_as_evidence(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row(
            "WIN|M1|2",
            trend="UP",
            signal_phase="PULLBACK",
            signal_direction="UP",
        ),
        _row(
            "WIN|M1|3",
            trend="UP",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 0
    assert "PULLBACK_NOT_CONFIRMED" in result["incomplete"][0]["reasons"]


def test_breakout_tested_does_not_start_a_new_sequence(tmp_path):
    rows = [
        _row(
            "WIN|M1|1",
            trend="UP",
            phase="BREAKOUT_TESTED",
            breakout_direction="UP",
        ),
        _row(
            "WIN|M1|2",
            trend="UP",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 0
    assert result["incomplete_candidates"] == 0


def test_breakout_pending_can_be_explicit_start_without_structure_bos(tmp_path):
    rows = [
        _row(
            "WIN|M1|1",
            trend="UP",
            phase="BREAKOUT_PENDING",
            breakout_direction="UP",
        ),
        _row(
            "WIN|M1|2",
            trend="UP",
            phase="BREAKOUT_TESTED",
            breakout_direction="UP",
        ),
        _row(
            "WIN|M1|3",
            trend="UP",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="UP",
            entry=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 1
    assert (
        result["sequences"][0]["evidence"]["breakout"]["source"]
        == "PA_BROOKS_BREAKOUT_PENDING"
    )


def test_opposite_choch_after_test_invalidates_candidate(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row(
            "WIN|M1|2",
            trend="UP",
            phase="BREAKOUT_TESTED",
            breakout_direction="UP",
        ),
        _row("WIN|M1|3", trend="DOWN", choch=True),
        _row(
            "WIN|M1|4",
            trend="UP",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 0
    assert result["incomplete"][0]["invalidated"] is True


def test_last_revision_per_exact_candle_is_used(tmp_path):
    first = _row("WIN|M1|1", trend="UP", bos_up=False)
    revised = _row("WIN|M1|1", trend="UP", bos_up=True)
    rows = [
        first,
        revised,
        _row(
            "WIN|M1|2",
            trend="UP",
            phase="BREAKOUT_TESTED",
            breakout_direction="UP",
        ),
        _row(
            "WIN|M1|3",
            trend="UP",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="UP",
            entry=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["exact_candles"] == 3
    assert result["complete_sequences"] == 1


def test_producer_phase_coverage_documents_real_contract(tmp_path):
    rows = [
        _row(
            "WIN|M1|1",
            trend="UP",
            phase="BREAKOUT_PENDING",
            breakout_direction="UP",
            signal_phase="SETUP_PENDING",
            signal_direction="UP",
        ),
        _row(
            "WIN|M1|2",
            trend="UP",
            phase="BREAKOUT_TESTED",
            breakout_direction="UP",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="UP",
            entry=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))
    coverage = result["producer_phase_coverage"]

    assert "PULLBACK" not in coverage["signal_phase_contract"]
    assert "REJECTION" not in coverage["signal_phase_contract"]
    assert "BREAKOUT_TESTED" in coverage["breakout_phase_contract"]
    assert coverage["pullback_source"] == "BROOKS_BREAKOUT_PHASE_BREAKOUT_TESTED"


def test_non_exact_session_is_rejected(tmp_path):
    row = _row("WIN|M1|1", trend="UP", bos_up=True)
    row["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"

    result = audit_session(_write(tmp_path, [row]))

    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["EXACT_CANDLE_IDENTITY_REQUIRED"]


def test_data_not_ready_session_is_rejected(tmp_path):
    result = audit_session(
        _write(
            tmp_path,
            [_row("WIN|M1|1")],
            data_ready=False,
        )
    )

    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["DATA_READY_SESSION_REQUIRED"]


def test_safety_flags_are_always_off_operationally(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row(
            "WIN|M1|2",
            trend="UP",
            phase="BREAKOUT_TESTED",
            breakout_direction="UP",
        ),
        _row(
            "WIN|M1|3",
            trend="UP",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["research_only"] is True
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False


def test_multi_session_audit_rejects_temporal_overlap(tmp_path):
    first = tmp_path / "first.json"
    overlap = tmp_path / "overlap.json"
    later = tmp_path / "later.json"
    payloads = (
        (
            first,
            "2026-09-04T10:00:00",
            "2026-09-04T10:10:00",
            "A",
        ),
        (
            overlap,
            "2026-09-04T10:05:00",
            "2026-09-04T10:15:00",
            "B",
        ),
        (
            later,
            "2026-09-04T10:20:00",
            "2026-09-04T10:21:00",
            "C",
        ),
    )

    for path, start, end, prefix in payloads:
        rows = [_row(f"{prefix}1"), _row(f"{prefix}2")]
        rows[0]["timestamp"] = start
        rows[1]["timestamp"] = end
        path.write_text(
            json.dumps({"data_ready": True, "samples": rows}),
            encoding="utf-8",
        )

    result = audit([later, overlap, first])

    assert result["eligible_sessions"] == 2
    rejected = next(
        item
        for item in result["sessions"]
        if item["session"] == "overlap.json"
    )
    assert rejected["status"] == "SESSION_NOT_ELIGIBLE"
    assert rejected["reasons"] == ["TEMPORAL_OVERLAP"]
    assert rejected["overlaps_with"] == "first.json"
    assert rejected["order_execution_allowed"] is False
