import json

from tools.profit_rtd_brooks_breakout_pullback_audit import audit_session


def _row(candle_id, *, trend="UP", bos_up=False, bos_down=False, phase="UNKNOWN", signal_phase="UNKNOWN", signal_direction="NONE", entry=False, follow=False, breakout_follow=False, breakout_direction="NONE", choch=False):
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


def _write(tmp_path, rows, *, data_ready=True):
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"data_ready": data_ready, "samples": rows}), encoding="utf-8")
    return path


def test_buy_sequence_requires_all_explicit_steps(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row("WIN|M1|2", trend="UP", signal_phase="PULLBACK", signal_direction="BUY"),
        _row("WIN|M1|3", trend="UP", signal_direction="BUY", entry=True),
        _row("WIN|M1|4", trend="UP", signal_direction="BUY", follow=True),
    ]
    result = audit_session(_write(tmp_path, rows))
    assert result["status"] == "MATCHES_OBSERVED"
    assert result["complete_sequences"] == 1
    assert result["sequences"][0]["direction"] == "BUY"


def test_sell_sequence_requires_all_explicit_steps(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="DOWN", bos_down=True),
        _row("WIN|M1|2", trend="DOWN", signal_phase="PULLBACK", signal_direction="SELL"),
        _row("WIN|M1|3", trend="DOWN", signal_direction="SELL", entry=True),
        _row("WIN|M1|4", trend="DOWN", signal_direction="SELL", follow=True),
    ]
    result = audit_session(_write(tmp_path, rows))
    assert result["complete_sequences"] == 1
    assert result["sequences"][0]["direction"] == "SELL"


def test_no_pullback_never_fabricates_match(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row("WIN|M1|2", trend="UP", signal_direction="BUY", entry=True),
        _row("WIN|M1|3", trend="UP", signal_direction="BUY", follow=True),
    ]
    result = audit_session(_write(tmp_path, rows))
    assert result["status"] == "INSUFFICIENT_SEQUENCE_EVIDENCE"
    assert result["complete_sequences"] == 0


def test_opposite_choch_invalidates_candidate(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row("WIN|M1|2", trend="UP", signal_phase="PULLBACK", signal_direction="BUY"),
        _row("WIN|M1|3", trend="DOWN", choch=True),
        _row("WIN|M1|4", trend="UP", signal_direction="BUY", entry=True),
        _row("WIN|M1|5", trend="UP", signal_direction="BUY", follow=True),
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
        _row("WIN|M1|2", trend="UP", signal_phase="PULLBACK", signal_direction="BUY"),
        _row("WIN|M1|3", trend="UP", signal_direction="BUY", entry=True),
        _row("WIN|M1|4", trend="UP", signal_direction="BUY", follow=True),
    ]
    result = audit_session(_write(tmp_path, rows))
    assert result["exact_candles"] == 4
    assert result["complete_sequences"] == 1


def test_non_exact_session_is_rejected(tmp_path):
    row = _row("WIN|M1|1", trend="UP", bos_up=True)
    row["candle_evidence"]["status"] = "CANDLE_EVIDENCE_NOT_READY"
    result = audit_session(_write(tmp_path, [row]))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["EXACT_CANDLE_IDENTITY_REQUIRED"]


def test_data_not_ready_session_is_rejected(tmp_path):
    result = audit_session(_write(tmp_path, [_row("WIN|M1|1")], data_ready=False))
    assert result["status"] == "SESSION_NOT_ELIGIBLE"
    assert result["reasons"] == ["DATA_READY_SESSION_REQUIRED"]


def test_safety_flags_are_always_off_operationally(tmp_path):
    rows = [
        _row("WIN|M1|1", trend="UP", bos_up=True),
        _row("WIN|M1|2", trend="UP", signal_phase="PULLBACK", signal_direction="BUY"),
        _row("WIN|M1|3", trend="UP", signal_direction="BUY", entry=True),
        _row("WIN|M1|4", trend="UP", signal_direction="BUY", follow=True),
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
