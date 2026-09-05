from tools.profit_rtd_brooks_major_trend_reversal_audit import (
    audit_payload,
    audit_sessions,
)


def row(cid, ts, *, trend="UP", reversal_candidate=False, reversal_direction="NONE",
        reversal_quality="NONE", reversal_context="NEUTRAL", bos_up=False,
        bos_down=False, choch=False, structure_trend="SIDEWAYS",
        signal_phase="SETUP_PENDING", signal_direction="NONE",
        entry=False, follow=False):
    return {
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": cid,
            "timestamp": ts,
        },
        "price_action": {
            "trend": trend,
            "brooks_reversal_candidate": reversal_candidate,
            "brooks_reversal_direction": reversal_direction,
            "brooks_reversal_quality": reversal_quality,
            "brooks_reversal_context": reversal_context,
            "brooks_signal_phase": signal_phase,
            "brooks_signal_direction": signal_direction,
            "brooks_entry_triggered": entry,
            "brooks_follow_through": follow,
        },
        "structure": {
            "trend": structure_trend,
            "bos_up": bos_up,
            "bos_down": bos_down,
            "choch": choch,
        },
    }


def payload(rows, **extra):
    value = {"data_ready": True, "samples": rows}
    value.update(extra)
    return value


def test_uptrend_reversal_to_sell_matches_with_bos_down_and_follow_through():
    p = payload([
        row("c1", "2026-09-07T10:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="STRONG", reversal_context="COUNTER_TREND"),
        row("c2", "2026-09-07T10:05:00", trend="UP", bos_down=True, structure_trend="DOWN"),
        row("c3", "2026-09-07T10:10:00", trend="DOWN", signal_phase="FOLLOW_THROUGH",
            signal_direction="SELL", follow=True),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 1
    assert result["sequences"][0]["direction"] == "SELL"


def test_downtrend_reversal_to_buy_matches_with_choch_and_new_up_trend():
    p = payload([
        row("c1", "2026-09-07T11:00:00", trend="DOWN", reversal_candidate=True,
            reversal_direction="BULL", reversal_quality="MODERATE", reversal_context="COUNTER_TREND"),
        row("c2", "2026-09-07T11:05:00", trend="DOWN", choch=True, structure_trend="UP"),
        row("c3", "2026-09-07T11:10:00", trend="UP", signal_phase="ENTRY_TRIGGERED",
            signal_direction="BUY", entry=True),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 1
    assert result["sequences"][0]["direction"] == "BUY"


def test_missing_reversal_context_capture_rejects_session():
    r = row("c1", "2026-09-07T12:00:00")
    del r["price_action"]["brooks_reversal_context"]
    result = audit_payload(payload([r]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert "REVERSAL_CONTEXT_EVIDENCE_REQUIRED" in result["reasons"]


def test_with_trend_reversal_context_does_not_start_sequence():
    p = payload([
        row("c1", "2026-09-07T13:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="STRONG", reversal_context="WITH_TREND"),
    ])
    result = audit_payload(p)
    assert result["sequence_count"] == 0


def test_weak_reversal_does_not_start_sequence():
    p = payload([
        row("c1", "2026-09-07T14:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="WEAK", reversal_context="COUNTER_TREND"),
    ])
    assert audit_payload(p)["sequence_count"] == 0


def test_no_structural_change_never_fabricates_match():
    p = payload([
        row("c1", "2026-09-07T15:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="STRONG", reversal_context="COUNTER_TREND"),
        row("c2", "2026-09-07T15:05:00", trend="UP"),
        row("c3", "2026-09-07T15:10:00", trend="UP", signal_phase="FOLLOW_THROUGH",
            signal_direction="SELL", follow=True),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 0
    assert result["sequences"][0]["reason"] == "STRUCTURAL_CHANGE_NOT_OBSERVED"


def test_opposite_bos_before_change_invalidates_sequence():
    p = payload([
        row("c1", "2026-09-07T16:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="STRONG", reversal_context="COUNTER_TREND"),
        row("c2", "2026-09-07T16:05:00", trend="UP", bos_up=True, structure_trend="UP"),
        row("c3", "2026-09-07T16:10:00", trend="UP", bos_down=True, structure_trend="DOWN"),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 0
    assert result["sequences"][0]["invalidated"] is True


def test_opposite_bos_after_change_invalidates_before_response():
    p = payload([
        row("c1", "2026-09-07T17:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="STRONG", reversal_context="COUNTER_TREND"),
        row("c2", "2026-09-07T17:05:00", trend="UP", bos_down=True, structure_trend="DOWN"),
        row("c3", "2026-09-07T17:10:00", trend="DOWN", bos_up=True, structure_trend="UP"),
        row("c4", "2026-09-07T17:15:00", trend="DOWN", signal_phase="FOLLOW_THROUGH",
            signal_direction="SELL", follow=True),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 0
    assert result["sequences"][0]["invalidated"] is True


def test_last_revision_per_exact_candle_is_used():
    p = payload([
        row("c1", "2026-09-07T18:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="WEAK", reversal_context="COUNTER_TREND"),
        row("c1", "2026-09-07T18:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="BEAR", reversal_quality="STRONG", reversal_context="COUNTER_TREND"),
        row("c2", "2026-09-07T18:05:00", trend="UP", bos_down=True, structure_trend="DOWN"),
        row("c3", "2026-09-07T18:10:00", trend="DOWN", signal_phase="FOLLOW_THROUGH",
            signal_direction="SELL", follow=True),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 1
    assert result["deduplication"] == "EXACT_CANDLE_LAST_REVISION"


def test_non_exact_candle_session_is_rejected():
    r = row("c1", "2026-09-07T19:00:00")
    r["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"
    result = audit_payload(payload([r]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert "EXACT_CANDLE_IDENTITY_REQUIRED" in result["reasons"]


def test_data_not_ready_is_rejected():
    result = audit_payload({"data_ready": False, "samples": []})
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert "DATA_NOT_READY" in result["reasons"]


def test_temporal_overlap_is_rejected():
    p1 = payload([row("a", "2026-09-07T20:00:00"), row("b", "2026-09-07T20:10:00")])
    p2 = payload([row("c", "2026-09-07T20:05:00"), row("d", "2026-09-07T20:15:00")])
    result = audit_sessions([p1, p2])
    assert result["accepted_session_count"] == 1
    assert result["rejected_session_count"] == 1
    assert result["rejected_sessions"][0]["reason"] == "TEMPORAL_OVERLAP"


def test_safety_flags_remain_off():
    result = audit_payload(payload([row("c1", "2026-09-07T21:00:00")]))
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
