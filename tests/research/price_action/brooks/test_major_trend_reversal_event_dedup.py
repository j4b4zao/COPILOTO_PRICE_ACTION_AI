from tools.profit_rtd_brooks_major_trend_reversal_audit import audit_payload


def row(
    cid,
    ts,
    *,
    trend="DOWN",
    reversal_candidate=False,
    reversal_direction="NONE",
    reversal_quality="NONE",
    reversal_context="NEUTRAL",
    bos_up=False,
    bos_down=False,
    choch=False,
    structure_trend="SIDEWAYS",
    signal_phase="SETUP_PENDING",
    signal_direction="NONE",
    entry=False,
    follow=False,
):
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


def payload(rows):
    return {"data_ready": True, "samples": rows}


def candidate(cid, ts):
    return row(
        cid,
        ts,
        trend="DOWN",
        reversal_candidate=True,
        reversal_direction="BUY",
        reversal_quality="STRONG",
        reversal_context="COUNTER_TREND",
    )


def test_overlapping_mtr_matches_are_one_unique_event():
    result = audit_payload(
        payload([
            candidate("c1", "2026-09-11T10:39:00"),
            candidate("c2", "2026-09-11T10:41:00"),
            candidate("c3", "2026-09-11T10:43:00"),
            row(
                "c4",
                "2026-09-11T10:44:00",
                trend="DOWN",
                reversal_candidate=True,
                reversal_direction="BUY",
                reversal_quality="STRONG",
                reversal_context="COUNTER_TREND",
                bos_up=True,
                structure_trend="UP",
            ),
            row(
                "c5",
                "2026-09-11T10:45:00",
                trend="UP",
                reversal_candidate=True,
                reversal_direction="BUY",
                reversal_quality="STRONG",
                reversal_context="COUNTER_TREND",
                bos_up=True,
                structure_trend="UP",
                signal_phase="ENTRY_TRIGGERED",
                signal_direction="BUY",
                entry=True,
            ),
            row(
                "c6",
                "2026-09-11T10:46:00",
                trend="UP",
                bos_up=True,
                structure_trend="UP",
                signal_phase="FOLLOW_THROUGH",
                signal_direction="BUY",
                follow=True,
            ),
        ])
    )

    assert result["matched_sequence_count"] >= 2
    assert result["unique_matched_event_count"] == 1
    event = result["unique_matched_events"][0]
    assert event["direction"] == "BUY"
    assert event["event_start_candle_id"] == "c1"
    assert len(event["member_start_candle_ids"]) == result["matched_sequence_count"]


def test_two_separated_mtr_matches_remain_two_unique_events():
    result = audit_payload(
        payload([
            candidate("a1", "2026-09-11T09:00:00"),
            row("a2", "2026-09-11T09:01:00", trend="DOWN", bos_up=True, structure_trend="UP"),
            row(
                "a3",
                "2026-09-11T09:02:00",
                trend="UP",
                signal_phase="FOLLOW_THROUGH",
                signal_direction="BUY",
                follow=True,
            ),
            row("gap", "2026-09-11T09:03:00", trend="UP"),
            candidate("b1", "2026-09-11T09:10:00"),
            row("b2", "2026-09-11T09:11:00", trend="DOWN", bos_up=True, structure_trend="UP"),
            row(
                "b3",
                "2026-09-11T09:12:00",
                trend="UP",
                signal_phase="ENTRY_TRIGGERED",
                signal_direction="BUY",
                entry=True,
            ),
        ])
    )

    assert result["matched_sequence_count"] == 2
    assert result["unique_matched_event_count"] == 2


def test_event_deduplication_remains_research_only():
    result = audit_payload(payload([row("c1", "2026-09-11T12:00:00")]))

    assert result["observational_only"] is True
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
    assert result["hypothesis_freeze_allowed"] is False
