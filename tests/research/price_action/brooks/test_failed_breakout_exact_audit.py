from __future__ import annotations

from tools.profit_rtd_brooks_failed_breakout_audit import audit_payload, audit_sessions


def row(ts, *, phase="RANGE", breakout_direction="NONE", failed=False, signal_phase="SETUP_PENDING", signal_direction="NONE", entry=False, follow=False, choch="NONE", candle_id=None):
    cid = candle_id or f"WINV26|M1|{ts}"
    return {
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": cid,
            "timestamp": ts,
        },
        "price_action": {
            "brooks_breakout_phase": phase,
            "brooks_breakout_direction": breakout_direction,
            "brooks_breakout_failed": failed,
            "brooks_signal_phase": signal_phase,
            "brooks_signal_direction": signal_direction,
            "brooks_entry_triggered": entry,
            "brooks_follow_through": follow,
        },
        "structure": {"choch": choch},
    }


def payload(samples, *, data_ready=True):
    return {"data_ready": data_ready, "samples": samples}


def test_buy_breakout_failure_then_sell_follow_through_matches():
    result = audit_payload(payload([
        row("2026-09-07T10:00:00", phase="BREAKOUT_PENDING", breakout_direction="UP"),
        row("2026-09-07T10:01:00", phase="BREAKOUT_FAILED", breakout_direction="UP", failed=True),
        row("2026-09-07T10:02:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ]))
    assert result["matched_sequence_count"] == 1
    seq = result["sequences"][0]
    assert seq["direction"] == "SELL"
    assert seq["matched"] is True


def test_sell_breakout_failure_then_buy_entry_triggered_matches():
    result = audit_payload(payload([
        row("2026-09-07T11:00:00", phase="BREAKOUT_PENDING", breakout_direction="DOWN"),
        row("2026-09-07T11:01:00", phase="BREAKOUT_FAILED", breakout_direction="DOWN", failed=True),
        row("2026-09-07T11:02:00", signal_phase="ENTRY_TRIGGERED", signal_direction="BUY", entry=True),
    ]))
    assert result["matched_sequence_count"] == 1
    assert result["sequences"][0]["direction"] == "BUY"


def test_breakout_without_explicit_failed_phase_never_fabricates_failure():
    result = audit_payload(payload([
        row("2026-09-07T12:00:00", phase="BREAKOUT_PENDING", breakout_direction="UP"),
        row("2026-09-07T12:01:00", phase="BREAKOUT_TESTED", breakout_direction="UP"),
        row("2026-09-07T12:02:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ]))
    assert result["matched_sequence_count"] == 0
    assert result["sequences"][0]["reason"] == "BREAKOUT_FAILURE_NOT_OBSERVED"


def test_failed_phase_requires_explicit_failed_boolean():
    result = audit_payload(payload([
        row("2026-09-07T13:00:00", phase="BREAKOUT_PENDING", breakout_direction="UP"),
        row("2026-09-07T13:01:00", phase="BREAKOUT_FAILED", breakout_direction="UP", failed=False),
        row("2026-09-07T13:02:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ]))
    assert result["matched_sequence_count"] == 0


def test_wrong_response_direction_does_not_match():
    result = audit_payload(payload([
        row("2026-09-07T14:00:00", phase="BREAKOUT_PENDING", breakout_direction="UP"),
        row("2026-09-07T14:01:00", phase="BREAKOUT_FAILED", breakout_direction="UP", failed=True),
        row("2026-09-07T14:02:00", signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ]))
    assert result["matched_sequence_count"] == 0


def test_opposite_choch_before_failure_invalidates_sequence():
    opposite_choch = row("2026-09-07T15:01:00", choch=True)
    opposite_choch["structure"]["trend"] = "DOWN"
    result = audit_payload(payload([
        row("2026-09-07T15:00:00", phase="BREAKOUT_PENDING", breakout_direction="UP"),
        opposite_choch,
        row("2026-09-07T15:02:00", phase="BREAKOUT_FAILED", breakout_direction="UP", failed=True),
    ]))
    assert result["matched_sequence_count"] == 0
    assert result["sequences"][0]["invalidated"] is True


def test_last_revision_per_exact_candle_is_used():
    cid = "WINV26|M1|2026-09-07T16:01:00"
    result = audit_payload(payload([
        row("2026-09-07T16:00:00", phase="BREAKOUT_PENDING", breakout_direction="UP"),
        row("2026-09-07T16:01:00", phase="BREAKOUT_TESTED", breakout_direction="UP", candle_id=cid),
        row("2026-09-07T16:01:00", phase="BREAKOUT_FAILED", breakout_direction="UP", failed=True, candle_id=cid),
        row("2026-09-07T16:02:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ]))
    assert result["matched_sequence_count"] == 1
    assert result["deduplication"] == "EXACT_CANDLE_LAST_REVISION"


def test_non_exact_session_is_rejected():
    bad = row("2026-09-07T17:00:00")
    bad["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"
    result = audit_payload(payload([bad]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert "EXACT_CANDLE_IDENTITY_REQUIRED" in result["reasons"]


def test_data_not_ready_is_rejected():
    result = audit_payload(payload([row("2026-09-07T18:00:00")], data_ready=False))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["DATA_NOT_READY"]


def test_temporal_overlap_is_rejected_in_multi_session():
    a = payload([
        row("2026-09-07T19:00:00"),
        row("2026-09-07T19:05:00"),
    ])
    b = payload([
        row("2026-09-07T19:04:00"),
        row("2026-09-07T19:10:00"),
    ])
    result = audit_sessions([a, b])
    assert result["accepted_session_count"] == 1
    assert result["rejected_session_count"] == 1
    assert result["rejected_sessions"][0]["reason"] == "TEMPORAL_OVERLAP"


def test_safety_flags_remain_off():
    result = audit_payload(payload([row("2026-09-07T20:00:00")]))
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
