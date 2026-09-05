import json

from tools.profit_rtd_brooks_trend_pullback_audit import audit, audit_session


def _row(cid, trend="UP", *, pullback=True, pb_dir="SELL", stage="BAR_PULLBACK", stage_index=1,
         continuation=True, reversal=False, range_transition=False, signal_phase="SETUP_PENDING",
         signal_direction="NONE", entry=False, follow=False, choch=False):
    return {
        "timestamp": cid.split("|")[-1],
        "candle_evidence": {"status": "CANDLE_EVIDENCE_READY", "candle_id": cid},
        "structure": {"trend": trend, "choch": choch},
        "price_action": {
            "brooks_first_pullback_valid": pullback,
            "brooks_first_pullback_direction": pb_dir,
            "brooks_first_pullback_stage": stage,
            "brooks_first_pullback_stage_index": stage_index,
            "brooks_first_pullback_continuation_bias": continuation,
            "brooks_first_pullback_reversal_risk": reversal,
            "brooks_first_pullback_trading_range_transition": range_transition,
            "brooks_signal_phase": signal_phase,
            "brooks_signal_direction": signal_direction,
            "brooks_entry_triggered": entry,
            "brooks_follow_through": follow,
        },
    }


def _write(tmp_path, name, rows, *, data_ready=True):
    p = tmp_path / name
    p.write_text(json.dumps({"data_ready": data_ready, "samples": rows}), encoding="utf-8")
    return p


def test_buy_sequence_matches_with_follow_through(tmp_path):
    rows = [
        _row("WIN|M1|2026-09-04T10:00:00"),
        _row("WIN|M1|2026-09-04T10:01:00", pullback=False, signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ]
    r = audit_session(_write(tmp_path, "buy.json", rows))
    assert r["status"] == "MATCHES_OBSERVED"
    assert r["complete_sequences"] == 1


def test_sell_sequence_matches_with_entry_triggered(tmp_path):
    rows = [
        _row("WIN|M1|2026-09-04T11:00:00", trend="DOWN", pb_dir="BUY"),
        _row("WIN|M1|2026-09-04T11:01:00", trend="DOWN", pullback=False, pb_dir="BUY", signal_phase="ENTRY_TRIGGERED", signal_direction="SELL", entry=True),
    ]
    r = audit_session(_write(tmp_path, "sell.json", rows))
    assert r["complete_sequences"] == 1


def test_missing_capture_fields_rejected_instead_of_inferred(tmp_path):
    row = _row("WIN|M1|2026-09-04T12:00:00")
    del row["price_action"]["brooks_first_pullback_stage_index"]
    r = audit_session(_write(tmp_path, "missing.json", [row]))
    assert r["status"] == "SESSION_NOT_ELIGIBLE"
    assert "FIRST_PULLBACK_SEQUENCE_EVIDENCE_REQUIRED" in r["reasons"]


def test_late_stage_does_not_match(tmp_path):
    rows = [
        _row("WIN|M1|2026-09-04T13:00:00", stage="MAJOR_TRENDLINE_BREAK", stage_index=6, continuation=False, reversal=True),
        _row("WIN|M1|2026-09-04T13:01:00", pullback=False, signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ]
    r = audit_session(_write(tmp_path, "late.json", rows))
    assert r["complete_sequences"] == 0


def test_opposite_choch_invalidates_before_resumption(tmp_path):
    rows = [
        _row("WIN|M1|2026-09-04T14:00:00"),
        _row("WIN|M1|2026-09-04T14:01:00", trend="DOWN", pullback=False, choch=True),
        _row("WIN|M1|2026-09-04T14:02:00", pullback=False, signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ]
    r = audit_session(_write(tmp_path, "choch.json", rows))
    assert r["complete_sequences"] == 0
    assert r["incomplete"][0]["invalidated"] is True


def test_last_revision_per_exact_candle_is_used(tmp_path):
    cid = "WIN|M1|2026-09-04T15:00:00"
    rows = [
        _row(cid, pullback=False),
        _row(cid, pullback=True),
        _row("WIN|M1|2026-09-04T15:01:00", pullback=False, signal_phase="FOLLOW_THROUGH", signal_direction="BUY", follow=True),
    ]
    r = audit_session(_write(tmp_path, "dedup.json", rows))
    assert r["exact_candles"] == 2
    assert r["complete_sequences"] == 1


def test_data_not_ready_rejected(tmp_path):
    r = audit_session(_write(tmp_path, "notready.json", [_row("WIN|M1|2026-09-04T16:00:00")], data_ready=False))
    assert r["status"] == "SESSION_NOT_ELIGIBLE"
    assert "DATA_READY_SESSION_REQUIRED" in r["reasons"]


def test_temporal_overlap_rejected(tmp_path):
    a = _write(tmp_path, "a.json", [
        _row("WIN|M1|2026-09-04T17:00:00"),
        _row("WIN|M1|2026-09-04T17:02:00", pullback=False),
    ])
    b = _write(tmp_path, "b.json", [
        _row("WIN|M1|2026-09-04T17:01:00"),
        _row("WIN|M1|2026-09-04T17:03:00", pullback=False),
    ])
    r = audit([a, b])
    assert sum(s.get("reasons") == ["TEMPORAL_OVERLAP"] for s in r["sessions"]) == 1


def test_safety_flags_remain_off(tmp_path):
    r = audit_session(_write(tmp_path, "safe.json", [_row("WIN|M1|2026-09-04T18:00:00")]))
    assert r["research_only"] is True
    assert r["observational_only"] is True
    assert r["predictive_claim_allowed"] is False
    assert r["score_influence_allowed"] is False
    assert r["risk_influence_allowed"] is False
    assert r["decision_influence_allowed"] is False
    assert r["alert_influence_allowed"] is False
    assert r["order_execution_allowed"] is False
