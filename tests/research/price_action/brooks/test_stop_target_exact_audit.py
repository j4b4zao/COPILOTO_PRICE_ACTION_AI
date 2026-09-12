from __future__ import annotations

from tools.profit_rtd_brooks_stop_target_audit import audit_payload, audit_sessions


def row(
    ts,
    *,
    direction="BUY",
    triggered=True,
    entry=100.0,
    stop=99.0,
    stop_valid=True,
    target=102.0,
    target_valid=True,
    target_source="TRADING_RANGE_OPPOSITE_EDGE",
    rr=2.0,
    status="ELIGIBLE",
    candle_id=None,
):
    cid = candle_id or f"WINV26|M1|{ts}"
    return {
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": cid,
            "timestamp": ts,
        },
        "price_action": {
            "brooks_stop_target_capture_status": status,
            "brooks_stop_target_direction": direction,
            "brooks_stop_target_entry_triggered": triggered,
            "brooks_stop_target_entry_price": entry,
            "brooks_stop_target_initial_stop": stop,
            "brooks_stop_target_stop_geometry_valid": stop_valid,
            "brooks_stop_target_target_price": target,
            "brooks_stop_target_target_valid": target_valid,
            "brooks_stop_target_target_source": target_source,
            "brooks_stop_target_reward_risk": rr,
            "brooks_stop_target_candle_id": cid,
        },
    }


def payload(samples, *, data_ready=True):
    return {"data_ready": data_ready, "samples": samples}


def test_buy_stop_target_geometry_and_rr_are_exact():
    result = audit_payload(payload([row("2026-09-11T10:00:00")]))
    assert result["status"] == "EXACT_AUDIT_COMPLETED"
    assert result["eligible_stop_observations"] == 1
    assert result["valid_target_observations"] == 1
    obs = result["observations"][0]
    assert obs["capture_consistent"] is True
    assert obs["computed_reward_risk"] == 2.0


def test_sell_stop_target_geometry_and_rr_are_exact():
    result = audit_payload(payload([
        row(
            "2026-09-11T10:01:00",
            direction="SELL",
            entry=100.0,
            stop=101.0,
            target=98.0,
            rr=2.0,
        )
    ]))
    assert result["status"] == "EXACT_AUDIT_COMPLETED"
    assert result["observations"][0]["target_valid"] is True


def test_rr_mismatch_is_reported_not_recomputed_silently():
    result = audit_payload(payload([row("2026-09-11T10:02:00", rr=3.0)]))
    assert result["status"] == "CAPTURE_INCONSISTENCY_OBSERVED"
    assert result["capture_inconsistency_count"] == 1
    assert "REWARD_RISK_MISMATCH" in result["observations"][0]["mismatches"]


def test_stop_geometry_flag_mismatch_is_reported():
    result = audit_payload(payload([
        row("2026-09-11T10:03:00", stop=101.0, stop_valid=True, target=0.0, target_valid=False, target_source="NONE", rr=0.0)
    ]))
    assert result["status"] == "CAPTURE_INCONSISTENCY_OBSERVED"
    assert "STOP_GEOMETRY_FLAG_MISMATCH" in result["observations"][0]["mismatches"]


def test_target_source_required_when_target_is_valid():
    result = audit_payload(payload([row("2026-09-11T10:04:00", target_source="NONE")]))
    assert result["status"] == "CAPTURE_INCONSISTENCY_OBSERVED"
    assert "TARGET_SOURCE_REQUIRED" in result["observations"][0]["mismatches"]


def test_candle_id_mismatch_is_reported():
    sample = row("2026-09-11T10:05:00")
    sample["price_action"]["brooks_stop_target_candle_id"] = "OTHER"
    result = audit_payload(payload([sample]))
    assert result["status"] == "CAPTURE_INCONSISTENCY_OBSERVED"
    assert "CAPTURE_CANDLE_ID_MISMATCH" in result["observations"][0]["mismatches"]


def test_last_revision_per_exact_candle_is_used():
    cid = "WINV26|M1|2026-09-11T10:06:00"
    first = row(
        "2026-09-11T10:06:00",
        entry=100.0,
        stop=99.0,
        target=102.0,
        rr=9.0,
        candle_id=cid,
    )
    last = row(
        "2026-09-11T10:06:00",
        entry=100.0,
        stop=99.0,
        target=102.0,
        rr=2.0,
        candle_id=cid,
    )
    result = audit_payload(payload([first, last]))
    assert result["status"] == "EXACT_AUDIT_COMPLETED"
    assert result["exact_candles"] == 1
    assert result["deduplication"] == "EXACT_CANDLE_LAST_REVISION"


def test_missing_capture_contract_rejects_session():
    sample = row("2026-09-11T10:07:00")
    del sample["price_action"]["brooks_stop_target_reward_risk"]
    result = audit_payload(payload([sample]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["STOP_TARGET_CAPTURE_CONTRACT_REQUIRED"]


def test_non_exact_session_is_rejected():
    sample = row("2026-09-11T10:08:00")
    sample["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"
    result = audit_payload(payload([sample]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["EXACT_CANDLE_IDENTITY_REQUIRED"]


def test_data_not_ready_is_rejected():
    result = audit_payload(payload([row("2026-09-11T10:09:00")], data_ready=False))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["DATA_NOT_READY"]


def test_temporal_overlap_is_rejected_in_multi_session():
    a = payload([
        row("2026-09-11T11:00:00"),
        row("2026-09-11T11:05:00"),
    ])
    b = payload([
        row("2026-09-11T11:04:00"),
        row("2026-09-11T11:10:00"),
    ])
    result = audit_sessions([a, b])
    assert result["accepted_session_count"] == 1
    assert result["rejected_session_count"] == 1
    assert result["rejected_sessions"][0]["reason"] == "TEMPORAL_OVERLAP"


def test_dynamic_management_is_explicitly_not_audited():
    result = audit_payload(payload([row("2026-09-11T12:00:00")]))
    assert result["dynamic_management_audited"] is False
    assert result["dynamic_management_reason"] == "TRAILING_PARTIAL_AND_OUTCOME_FIELDS_NOT_CAPTURED"


def test_safety_flags_remain_off():
    result = audit_payload(payload([row("2026-09-11T13:00:00")]))
    assert result["research_only"] is True
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
