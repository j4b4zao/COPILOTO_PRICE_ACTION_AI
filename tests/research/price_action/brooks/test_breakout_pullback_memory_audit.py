import json

from tools.profit_rtd_brooks_breakout_pullback_memory_audit import audit_session


def _row(
    candle_id,
    *,
    trend="UP",
    phase="RANGE",
    breakout_direction="NONE",
    memory_direction="NONE",
    memory_level=0.0,
    signal_phase="UNKNOWN",
    signal_direction="NONE",
    entry=False,
    follow=False,
    open_=101.0,
    high=102.0,
    low=100.5,
    close=101.5,
):
    return {
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": candle_id,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1000.0,
        },
        "structure": {
            "trend": trend,
            "bos_up": False,
            "bos_down": False,
            "choch": False,
        },
        "price_action": {
            "brooks_breakout_phase": phase,
            "brooks_breakout_direction": breakout_direction,
            "brooks_research_breakout_memory_direction": memory_direction,
            "brooks_research_breakout_memory_level": memory_level,
            "brooks_signal_phase": signal_phase,
            "brooks_signal_direction": signal_direction,
            "brooks_entry_triggered": entry,
            "brooks_follow_through": follow,
        },
    }


def _write(tmp_path, rows):
    path = tmp_path / "session.json"
    path.write_text(json.dumps({"data_ready": True, "samples": rows}), encoding="utf-8")
    return path


def test_retest_three_candles_after_breakout_is_preserved_by_research_memory(tmp_path):
    rows = [
        _row(
            "WIN|M1|1",
            phase="BREAKOUT_PENDING",
            breakout_direction="UP",
            memory_direction="UP",
            memory_level=100.0,
            open_=100.5,
            high=102.0,
            low=100.4,
            close=101.5,
        ),
        _row("WIN|M1|2", low=101.0, close=101.6),
        _row("WIN|M1|3", low=100.7, close=101.2),
        _row("WIN|M1|4", low=99.9, close=100.4),
        _row(
            "WIN|M1|5",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
            open_=100.5,
            high=102.5,
            low=100.4,
            close=102.0,
        ),
    ]

    result = audit_session(_write(tmp_path, rows), max_sequence_candles=20)

    assert result["status"] == "MATCHES_OBSERVED"
    assert result["complete_sequences"] == 1
    sequence = result["sequences"][0]
    assert sequence["evidence"]["breakout"]["level"] == 100.0
    assert sequence["evidence"]["pullback"]["candle_id"] == "WIN|M1|4"
    assert sequence["evidence"]["pullback"]["source"] == "RESEARCH_BREAKOUT_MEMORY_LEVEL_RETEST"
    assert sequence["evidence"]["resumption"]["candle_id"] == "WIN|M1|5"


def test_memory_does_not_infer_level_when_real_memory_level_was_not_captured(tmp_path):
    rows = [
        _row(
            "WIN|M1|1",
            phase="BREAKOUT_PENDING",
            breakout_direction="UP",
            memory_direction="UP",
            memory_level=0.0,
        ),
        _row("WIN|M1|2", low=99.0, close=100.5),
        _row(
            "WIN|M1|3",
            signal_phase="FOLLOW_THROUGH",
            signal_direction="UP",
            entry=True,
            follow=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 0
    assert result["incomplete_candidates"] == 1
    assert "PULLBACK_NOT_CONFIRMED" in result["incomplete"][0]["reasons"]
    assert result["incomplete"][0]["evidence"]["breakout"]["level"] is None


def test_memory_direction_must_align_with_breakout_direction(tmp_path):
    rows = [
        _row(
            "WIN|M1|1",
            phase="BREAKOUT_PENDING",
            breakout_direction="UP",
            memory_direction="DOWN",
            memory_level=100.0,
        ),
        _row("WIN|M1|2", low=99.9, close=100.2),
        _row(
            "WIN|M1|3",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="UP",
            entry=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 0
    assert result["incomplete_candidates"] == 1
    assert result["incomplete"][0]["evidence"]["breakout"]["level"] is None
    assert "PULLBACK_NOT_CONFIRMED" in result["incomplete"][0]["reasons"]


def test_memory_uses_real_capture_field_names_only(tmp_path):
    row = _row(
        "WIN|M1|1",
        phase="BREAKOUT_PENDING",
        breakout_direction="UP",
        memory_direction="UP",
        memory_level=100.0,
    )
    row["price_action"]["brooks_breakout_level"] = 999.0
    rows = [
        row,
        _row("WIN|M1|2", low=99.9, close=100.2),
        _row(
            "WIN|M1|3",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="UP",
            entry=True,
        ),
    ]

    result = audit_session(_write(tmp_path, rows))

    assert result["complete_sequences"] == 1
    assert result["sequences"][0]["evidence"]["breakout"]["level"] == 100.0


def test_research_memory_remains_non_operational(tmp_path):
    rows = [
        _row(
            "WIN|M1|1",
            phase="BREAKOUT_PENDING",
            breakout_direction="UP",
            memory_direction="UP",
            memory_level=100.0,
        ),
        _row("WIN|M1|2", low=99.9, close=100.2),
        _row(
            "WIN|M1|3",
            signal_phase="ENTRY_TRIGGERED",
            signal_direction="UP",
            entry=True,
        ),
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
