from tools.profit_rtd_brooks_trading_range_reversal_audit import audit_payload, audit_sessions


def row(ts, *, cid=None, zone="LOW", range_valid=True, setup_direction="BUY",
        h2=True, l2=False, failed=False, reversal=False, reversal_direction="NONE",
        reversal_quality="NONE", signal_phase="SETUP_PENDING", signal_direction="NONE",
        entry=False, follow=False):
    cid = cid or f"WIN|M5|{ts}"
    return {
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": cid,
            "timestamp": ts,
        },
        "price_action": {
            "brooks_trading_range_valid": range_valid,
            "brooks_trading_range_state": "BUY_LOW_H2" if zone == "LOW" else "SELL_HIGH_L2",
            "brooks_trading_range_low": 100.0,
            "brooks_trading_range_high": 110.0,
            "brooks_trading_range_mid": 105.0,
            "brooks_trading_range_height": 10.0,
            "brooks_trading_range_position": 0.1 if zone == "LOW" else 0.9,
            "brooks_trading_range_zone": zone,
            "brooks_trading_range_setup_direction": setup_direction,
            "brooks_trading_range_h2_near_low": h2,
            "brooks_trading_range_l2_near_high": l2,
            "brooks_trading_range_breakout_attempt": failed,
            "brooks_trading_range_failed_breakout_risk": failed,
            "brooks_trading_range_avoid_middle": zone == "MIDDLE",
            "brooks_reversal_candidate": reversal,
            "brooks_reversal_direction": reversal_direction,
            "brooks_reversal_quality": reversal_quality,
            "brooks_signal_phase": signal_phase,
            "brooks_signal_direction": signal_direction,
            "brooks_entry_triggered": entry,
            "brooks_follow_through": follow,
        },
    }


def payload(rows, data_ready=True):
    return {"data_ready": data_ready, "samples": rows}


def test_low_h2_buy_sequence_matches():
    p = payload([
        row("2026-09-08T10:00:00", zone="LOW", setup_direction="BUY", h2=True),
        row("2026-09-08T10:05:00", zone="LOW", reversal=True, reversal_direction="BUY", reversal_quality="STRONG"),
        row("2026-09-08T10:10:00", zone="LOW", signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ])
    r = audit_payload(p)
    assert r["matched_sequence_count"] >= 1


def test_high_l2_sell_sequence_matches():
    p = payload([
        row("2026-09-08T11:00:00", zone="HIGH", setup_direction="SELL", h2=False, l2=True),
        row("2026-09-08T11:05:00", zone="HIGH", setup_direction="SELL", h2=False, l2=True, reversal=True, reversal_direction="SELL", reversal_quality="MODERATE"),
        row("2026-09-08T11:10:00", zone="HIGH", setup_direction="SELL", h2=False, l2=True, signal_phase="ENTRY_TRIGGERED", signal_direction="SELL", entry=True),
    ])
    r = audit_payload(p)
    assert r["matched_sequence_count"] >= 1


def test_failed_breakout_risk_can_supply_edge_signal():
    p = payload([
        row("2026-09-08T12:00:00", zone="LOW", setup_direction="NONE", h2=False, failed=True),
        row("2026-09-08T12:05:00", zone="LOW", setup_direction="NONE", h2=False, failed=True, reversal=True, reversal_direction="BUY", reversal_quality="STRONG"),
        row("2026-09-08T12:10:00", zone="LOW", setup_direction="NONE", h2=False, failed=True, signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ])
    assert audit_payload(p)["matched_sequence_count"] >= 1


def test_middle_never_starts_sequence():
    p = payload([row("2026-09-08T13:00:00", zone="MIDDLE", setup_direction="NONE", h2=False)])
    r = audit_payload(p)
    assert r["sequence_count"] == 0


def test_edge_without_h2_l2_or_failed_breakout_does_not_start():
    p = payload([row("2026-09-08T14:00:00", zone="LOW", setup_direction="NONE", h2=False, failed=False)])
    assert audit_payload(p)["sequence_count"] == 0


def test_weak_reversal_does_not_complete():
    p = payload([
        row("2026-09-08T15:00:00"),
        row("2026-09-08T15:05:00", reversal=True, reversal_direction="BUY", reversal_quality="WEAK"),
        row("2026-09-08T15:10:00", signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 0


def test_wrong_reversal_direction_does_not_complete():
    p = payload([
        row("2026-09-08T16:00:00"),
        row("2026-09-08T16:05:00", reversal=True, reversal_direction="SELL", reversal_quality="STRONG"),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 0


def test_response_is_required():
    p = payload([
        row("2026-09-08T17:00:00"),
        row("2026-09-08T17:05:00", reversal=True, reversal_direction="BUY", reversal_quality="STRONG"),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 0


def test_wrong_response_direction_does_not_match():
    p = payload([
        row("2026-09-08T18:00:00"),
        row("2026-09-08T18:05:00", reversal=True, reversal_direction="BUY", reversal_quality="STRONG"),
        row("2026-09-08T18:10:00", signal_phase="FOLLOW_THROUGH", signal_direction="SELL", follow=True),
    ])
    assert audit_payload(p)["matched_sequence_count"] == 0


def test_range_invalidation_before_response_blocks_match():
    p = payload([
        row("2026-09-08T19:00:00"),
        row("2026-09-08T19:05:00", reversal=True, reversal_direction="BUY", reversal_quality="STRONG"),
        row("2026-09-08T19:10:00", range_valid=False),
        row("2026-09-08T19:15:00", signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ])
    r = audit_payload(p)
    assert r["matched_sequence_count"] == 0
    assert any(x.get("invalidated") for x in r["sequences"])


def test_last_revision_per_exact_candle_is_used():
    cid = "WIN|M5|REV"
    p = payload([
        row("2026-09-08T20:00:00", cid=cid, zone="MIDDLE", setup_direction="NONE", h2=False),
        row("2026-09-08T20:00:00", cid=cid, zone="LOW", setup_direction="BUY", h2=True),
        row("2026-09-08T20:05:00", reversal=True, reversal_direction="BUY", reversal_quality="STRONG"),
        row("2026-09-08T20:10:00", signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ])
    assert audit_payload(p)["matched_sequence_count"] >= 1


def test_missing_range_schema_rejected():
    r = row("2026-09-08T21:00:00")
    del r["price_action"]["brooks_trading_range_high"]
    a = audit_payload(payload([r]))
    assert a["status"] == "SESSION_NOT_ELIGIBLE"
    assert "TRADING_RANGE_EVIDENCE_REQUIRED" in a["reasons"]


def test_non_exact_session_rejected():
    r = row("2026-09-08T22:00:00")
    r["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"
    assert audit_payload(payload([r]))["status"] == "SESSION_NOT_ELIGIBLE"


def test_data_not_ready_rejected():
    assert audit_payload(payload([row("2026-09-08T23:00:00")], data_ready=False))["status"] == "SESSION_NOT_ELIGIBLE"


def test_temporal_overlap_rejected():
    p1 = payload([row("2026-09-09T10:00:00"), row("2026-09-09T10:05:00")])
    p2 = payload([row("2026-09-09T10:04:00"), row("2026-09-09T10:10:00")])
    r = audit_sessions([p1, p2])
    assert r["accepted_session_count"] == 1
    assert r["rejected_session_count"] == 1
    assert r["rejected_sessions"][0]["reason"] == "TEMPORAL_OVERLAP"


def test_safety_flags_remain_off():
    r = audit_payload(payload([row("2026-09-09T11:00:00")]))
    assert r["observational_only"] is True
    assert r["predictive_claim_allowed"] is False
    assert r["score_influence_allowed"] is False
    assert r["risk_influence_allowed"] is False
    assert r["decision_influence_allowed"] is False
    assert r["alert_influence_allowed"] is False
    assert r["order_execution_allowed"] is False
    assert r["hypothesis_freeze_allowed"] is False
