from tools.profit_rtd_brooks_wedge_three_pushes_audit import audit_payload, audit_sessions


def row(cid, ts, *, pushes=False, push_direction="NONE", reversal=False,
        reversal_direction="NONE", reversal_quality="NONE", bos_up=False,
        bos_down=False, choch=False, structure_trend="SIDEWAYS", signal_phase="SETUP_PENDING",
        signal_direction="NONE", entry=False, follow=False):
    return {
        "candle_evidence": {"status": "CANDLE_EVIDENCE_READY", "candle_id": cid, "timestamp": ts},
        "price_action": {
            "brooks_three_pushes_detected": pushes,
            "brooks_three_pushes_direction": push_direction,
            "brooks_three_pushes_indices": [1, 3, 5] if pushes else [],
            "brooks_three_pushes_prices": [100.0, 101.0, 101.5] if pushes else [],
            "brooks_reversal_candidate": reversal,
            "brooks_reversal_direction": reversal_direction,
            "brooks_reversal_quality": reversal_quality,
            "brooks_signal_phase": signal_phase,
            "brooks_signal_direction": signal_direction,
            "brooks_entry_triggered": entry,
            "brooks_follow_through": follow,
        },
        "structure": {
            "bos_up": bos_up,
            "bos_down": bos_down,
            "choch": choch,
            "trend": structure_trend,
        },
    }


def payload(rows, *, ready=True):
    return {"data_ready": ready, "samples": rows}


def test_up_pushes_to_sell_sequence_matches():
    p = payload([
        row("1", "2026-09-07T10:00:00", pushes=True, push_direction="UP"),
        row("2", "2026-09-07T10:01:00", reversal=True, reversal_direction="BEAR", reversal_quality="STRONG"),
        row("3", "2026-09-07T10:02:00", bos_down=True),
        row("4", "2026-09-07T10:03:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 1
    assert result["sequences"][0]["direction"] == "SELL"


def test_down_pushes_to_buy_sequence_matches():
    p = payload([
        row("1", "2026-09-07T11:00:00", pushes=True, push_direction="DOWN"),
        row("2", "2026-09-07T11:01:00", reversal=True, reversal_direction="BULL", reversal_quality="MODERATE"),
        row("3", "2026-09-07T11:02:00", bos_up=True),
        row("4", "2026-09-07T11:03:00", signal_phase="ENTRY_TRIGGERED", signal_direction="BUY", entry=True),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 1
    assert result["sequences"][0]["direction"] == "BUY"


def test_missing_three_pushes_does_not_start_sequence():
    result = audit_payload(payload([row("1", "2026-09-07T12:00:00")]))
    assert result["sequence_count"] == 0


def test_push_evidence_requires_three_indices_and_prices():
    r = row("1", "2026-09-07T12:10:00", pushes=True, push_direction="UP")
    r["price_action"]["brooks_three_pushes_indices"] = [1, 3]
    result = audit_payload(payload([r]))
    assert result["sequence_count"] == 0


def test_weak_reversal_does_not_complete():
    p = payload([
        row("1", "2026-09-07T12:20:00", pushes=True, push_direction="UP"),
        row("2", "2026-09-07T12:21:00", reversal=True, reversal_direction="BEAR", reversal_quality="WEAK"),
    ])
    result = audit_payload(p)
    assert result["matched_sequence_count"] == 0


def test_wrong_reversal_direction_does_not_complete():
    p = payload([
        row("1", "2026-09-07T12:30:00", pushes=True, push_direction="UP"),
        row("2", "2026-09-07T12:31:00", reversal=True, reversal_direction="BULL", reversal_quality="STRONG"),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 0


def test_structural_invalidation_before_reversal_blocks():
    p = payload([
        row("1", "2026-09-07T12:40:00", pushes=True, push_direction="UP"),
        row("2", "2026-09-07T12:41:00", bos_up=True),
        row("3", "2026-09-07T12:42:00", reversal=True, reversal_direction="BEAR", reversal_quality="STRONG"),
    ])
    result = audit_payload(p)
    assert result["sequences"][0]["invalidated"] is True


def test_structural_change_is_required():
    p = payload([
        row("1", "2026-09-07T12:50:00", pushes=True, push_direction="UP"),
        row("2", "2026-09-07T12:51:00", reversal=True, reversal_direction="BEAR", reversal_quality="STRONG"),
        row("3", "2026-09-07T12:52:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 0


def test_response_is_required_after_structure():
    p = payload([
        row("1", "2026-09-07T13:00:00", pushes=True, push_direction="DOWN"),
        row("2", "2026-09-07T13:01:00", reversal=True, reversal_direction="BULL", reversal_quality="STRONG"),
        row("3", "2026-09-07T13:02:00", bos_up=True),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 0


def test_last_revision_per_exact_candle_is_used():
    first = row("1", "2026-09-07T13:10:00", pushes=False)
    revised = row("1", "2026-09-07T13:10:00", pushes=True, push_direction="UP")
    p = payload([
        first, revised,
        row("2", "2026-09-07T13:11:00", reversal=True, reversal_direction="BEAR", reversal_quality="STRONG"),
        row("3", "2026-09-07T13:12:00", bos_down=True),
        row("4", "2026-09-07T13:13:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 1


def test_missing_exact_identity_rejected():
    r = row("1", "2026-09-07T13:20:00")
    r["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"
    result = audit_payload(payload([r]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert "EXACT_CANDLE_IDENTITY_REQUIRED" in result["reasons"]


def test_data_not_ready_rejected():
    result = audit_payload(payload([row("1", "2026-09-07T13:30:00")], ready=False))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert "DATA_NOT_READY" in result["reasons"]


def test_missing_three_pushes_capture_schema_rejected():
    r = row("1", "2026-09-07T13:40:00")
    del r["price_action"]["brooks_three_pushes_prices"]
    result = audit_payload(payload([r]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert "THREE_PUSHES_EVIDENCE_REQUIRED" in result["reasons"]


def test_temporal_overlap_rejected():
    a = payload([row("a", "2026-09-07T14:00:00"), row("b", "2026-09-07T14:05:00")])
    b = payload([row("c", "2026-09-07T14:04:00"), row("d", "2026-09-07T14:10:00")])
    result = audit_sessions([a, b])
    assert result["accepted_session_count"] == 1
    assert result["rejected_sessions"][0]["reason"] == "TEMPORAL_OVERLAP"


def test_safety_flags_remain_off():
    result = audit_payload(payload([row("1", "2026-09-07T15:00:00")]))
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
