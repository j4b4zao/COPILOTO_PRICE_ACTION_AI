import json

from tools.profit_rtd_brooks_mtr_event_tracker import build_report


def row(cid, ts, *, trend="DOWN", reversal_candidate=False, reversal_direction="NONE",
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


def write_payload(tmp_path, name, rows, *, data_ready=True):
    path = tmp_path / name
    path.write_text(json.dumps({"data_ready": data_ready, "samples": rows}), encoding="utf-8")
    return path


def test_tracker_counts_unique_mtr_events_across_sessions(tmp_path):
    s1 = write_payload(tmp_path, "s1.json", [
        row("a1", "2026-09-11T10:39:00", reversal_candidate=True,
            reversal_direction="BUY", reversal_quality="STRONG", reversal_context="COUNTER_TREND"),
        row("a2", "2026-09-11T10:41:00", reversal_candidate=True,
            reversal_direction="BUY", reversal_quality="STRONG", reversal_context="COUNTER_TREND"),
        row("a3", "2026-09-11T10:44:00", bos_up=True, structure_trend="UP"),
        row("a4", "2026-09-11T10:45:00", trend="UP", signal_phase="ENTRY_TRIGGERED",
            signal_direction="BUY", entry=True),
    ])
    s2 = write_payload(tmp_path, "s2.json", [
        row("b1", "2026-09-12T11:00:00", trend="UP", reversal_candidate=True,
            reversal_direction="SELL", reversal_quality="MODERATE", reversal_context="COUNTER_TREND"),
        row("b2", "2026-09-12T11:02:00", trend="UP", bos_down=True, structure_trend="DOWN"),
        row("b3", "2026-09-12T11:03:00", trend="DOWN", signal_phase="FOLLOW_THROUGH",
            signal_direction="SELL", follow=True),
    ])

    result = build_report([s1, s2])

    assert result["eligible_sessions"] == 2
    assert result["sessions_with_unique_events"] == 2
    assert result["matched_sequence_count"] == 3
    assert result["unique_matched_event_count"] == 2


def test_tracker_keeps_ineligible_session_without_counting_it(tmp_path):
    bad = write_payload(tmp_path, "bad.json", [], data_ready=False)
    result = build_report([bad])

    assert result["eligible_sessions"] == 0
    assert result["unique_matched_event_count"] == 0
    assert result["sessions"][0]["status"] == "SESSION_NOT_ELIGIBLE"


def test_tracker_safety_flags_remain_off(tmp_path):
    session = write_payload(tmp_path, "empty.json", [
        row("c1", "2026-09-13T10:00:00"),
    ])
    result = build_report([session])

    assert result["research_only"] is True
    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
    assert result["promotion_allowed"] is False
