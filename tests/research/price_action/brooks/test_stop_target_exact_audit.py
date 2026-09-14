from tools.profit_rtd_brooks_stop_target_audit import audit_payload, audit_sessions


def row(ts, *, cid=None, direction="BUY", entry=100, stop=95, target=110,
        eligible=True, target_valid=True, high=101, low=99):
    cid = cid or f"WIN|M1|{ts}"
    return {
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": cid,
            "timestamp": ts,
            "high": high,
            "low": low,
        },
        "price_action": {
            "brooks_stop_target_capture_status": "ELIGIBLE" if eligible else "NOT_ELIGIBLE",
            "brooks_stop_target_direction": direction,
            "brooks_stop_target_entry_triggered": True,
            "brooks_stop_target_entry_price": entry,
            "brooks_stop_target_initial_stop": stop,
            "brooks_stop_target_stop_geometry_valid": eligible,
            "brooks_stop_target_target_price": target if target_valid else 0,
            "brooks_stop_target_target_valid": target_valid,
            "brooks_stop_target_target_source": "TRADING_RANGE_OPPOSITE_BOUNDARY" if target_valid else "NONE",
            "brooks_stop_target_candle_id": cid if eligible else None,
        },
    }


def payload(rows, *, data_ready=True):
    return {"data_ready": data_ready, "samples": rows}


def test_buy_target_first_is_observed_on_subsequent_candle():
    result = audit_payload(payload([
        row("2026-09-14T10:00:00"),
        row("2026-09-14T10:01:00", eligible=False, high=111, low=99),
    ]))
    assert result["target_first_count"] == 1
    assert result["stop_first_count"] == 0
    assert result["observations"][0]["outcome"] == "TARGET_FIRST"


def test_sell_stop_first_is_observed():
    result = audit_payload(payload([
        row("2026-09-14T11:00:00", direction="SELL", stop=105, target=90),
        row("2026-09-14T11:01:00", eligible=False, direction="SELL", stop=105, target=90, high=106, low=99),
    ]))
    assert result["stop_first_count"] == 1


def test_same_future_candle_hit_is_ambiguous_without_intrabar_order():
    result = audit_payload(payload([
        row("2026-09-14T12:00:00"),
        row("2026-09-14T12:01:00", eligible=False, high=111, low=94),
    ]))
    assert result["ambiguous_same_candle_count"] == 1
    assert result["matched_sequence_count"] == 0


def test_entry_candle_is_never_used_for_outcome():
    result = audit_payload(payload([
        row("2026-09-14T13:00:00", high=111, low=94),
        row("2026-09-14T13:01:00", eligible=False, high=101, low=99),
    ]))
    assert result["unresolved_in_window_count"] == 1


def test_missing_structural_target_remains_non_evaluable():
    result = audit_payload(payload([
        row("2026-09-14T14:00:00", target_valid=False),
        row("2026-09-14T14:01:00", eligible=False),
    ]))
    assert result["observation_count"] == 1
    assert result["evaluable_observation_count"] == 0
    assert result["observations"][0]["reason"] == "STRUCTURAL_TARGET_NOT_AVAILABLE"


def test_last_revision_per_exact_candle_is_used():
    cid = "WIN|M1|REV"
    result = audit_payload(payload([
        row("2026-09-14T15:00:00", cid=cid, eligible=False),
        row("2026-09-14T15:00:00", cid=cid),
        row("2026-09-14T15:01:00", eligible=False, high=111),
    ]))
    assert result["observation_count"] == 1
    assert result["target_first_count"] == 1


def test_pre_fix_capture_is_explicitly_rejected():
    result = audit_payload(payload([row("2026-09-11T09:22:00", eligible=False)]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["NO_PROSPECTIVE_STOP_TARGET_EVIDENCE"]


def test_missing_capture_schema_is_rejected():
    item = row("2026-09-10T10:00:00")
    item["price_action"] = {}
    assert audit_payload(payload([item]))["reasons"] == ["STOP_TARGET_EVIDENCE_REQUIRED"]


def test_data_and_exact_identity_are_required():
    item = row("2026-09-14T16:00:00")
    assert audit_payload(payload([item], data_ready=False))["reasons"] == ["DATA_NOT_READY"]
    item["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"
    assert audit_payload(payload([item]))["reasons"] == ["EXACT_CANDLE_IDENTITY_REQUIRED"]


def test_multi_session_rejects_overlap_and_pre_fix_evidence():
    valid = payload([row("2026-09-14T17:00:00")])
    overlap = payload([row("2026-09-14T17:00:00")])
    pre_fix = payload([row("2026-09-11T09:22:00", eligible=False)])
    result = audit_sessions([valid, overlap, pre_fix])
    assert result["accepted_session_count"] == 1
    assert result["rejected_session_count"] == 2
    assert {item["reason"] for item in result["rejected_sessions"]} == {"TEMPORAL_OVERLAP", "SESSION_NOT_ELIGIBLE"}


def test_safety_contract_remains_fully_off():
    result = audit_payload(payload([row("2026-09-14T18:00:00", target_valid=False)]))
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
