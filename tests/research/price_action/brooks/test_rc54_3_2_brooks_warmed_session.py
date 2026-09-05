from __future__ import annotations

import json
from types import SimpleNamespace

import tools.profit_rtd_brooks_first_pullback_capture as capture
import tools.profit_rtd_rc54_3_2_brooks_warmed_session as runner
from tools.profit_rtd_brooks_trend_pullback_audit import audit_session


PULLBACK_FIELDS = {
    "brooks_first_pullback_valid": True,
    "brooks_first_pullback_direction": "DOWN",
    "brooks_first_pullback_stage": "BAR_PULLBACK",
    "brooks_first_pullback_stage_index": 1,
    "brooks_first_pullback_bars": 1,
    "brooks_first_pullback_minor_trendline_break": False,
    "brooks_first_pullback_moving_average_touch": False,
    "brooks_first_pullback_moving_average_close_cross": False,
    "brooks_first_pullback_moving_average_gap_bar": False,
    "brooks_first_pullback_major_trendline_break": False,
    "brooks_first_pullback_long_two_leg_pullback": False,
    "brooks_first_pullback_two_sided_trading": False,
    "brooks_first_pullback_trading_range_transition": False,
    "brooks_first_pullback_trend_maturity_score": 12.5,
    "brooks_first_pullback_continuation_bias": True,
    "brooks_first_pullback_reversal_risk": False,
    "brooks_first_pullback_reasons": ["TREND_UP", "FIRST_BAR_PULLBACK"],
    "research_only": True,
    "observational_only": True,
    "predictive_claim_allowed": False,
    "score_influence_allowed": False,
    "risk_influence_allowed": False,
    "decision_influence_allowed": False,
    "alert_influence_allowed": False,
    "order_execution_allowed": False,
}


def test_snapshot_enrichment_adds_explicit_first_pullback_fields(monkeypatch):
    monkeypatch.setattr(
        runner,
        "_ORIGINAL_SNAPSHOT_CONTEXT",
        lambda context, micro: {
            "structure": {"trend": "UP", "choch": False},
            "price_action": {
                "brooks_signal_phase": "SETUP_PENDING",
                "brooks_signal_direction": "BUY",
                "brooks_entry_triggered": False,
                "brooks_follow_through": False,
            },
        },
    )
    monkeypatch.setattr(
        capture,
        "snapshot_first_pullback",
        lambda context: dict(PULLBACK_FIELDS),
    )

    item = runner.snapshot_context_with_brooks(SimpleNamespace(), SimpleNamespace())

    pa = item["price_action"]
    assert pa["brooks_first_pullback_valid"] is True
    assert pa["brooks_first_pullback_direction"] == "DOWN"
    assert pa["brooks_first_pullback_stage"] == "BAR_PULLBACK"
    assert pa["brooks_first_pullback_stage_index"] == 1
    assert pa["brooks_first_pullback_continuation_bias"] is True
    assert pa["brooks_first_pullback_reversal_risk"] is False
    assert pa["predictive_claim_allowed"] is False
    assert pa["order_execution_allowed"] is False


def test_derived_runner_restores_original_snapshot_and_sets_safety_metadata(monkeypatch):
    original = object()
    monkeypatch.setattr(runner.base, "snapshot_context", original)

    def fake_run(symbol, **kwargs):
        assert runner.base.snapshot_context is runner.snapshot_context_with_brooks
        return {
            "status": "COMPLETED",
            "symbol": symbol,
            "requested_cycles": 1,
            "analyzable_samples": 1,
            "skipped_cycles": 0,
            "collection_errors": 0,
            "data_ready": True,
            "reasons": [],
        }

    monkeypatch.setattr(runner.base, "run_warmed_session", fake_run)

    result = runner.run_warmed_session("WINV26", cycles=1, interval=0)

    assert runner.base.snapshot_context is original
    assert result["brooks_first_pullback_capture"] is True
    assert result["brooks_first_pullback_research_only"] is True
    assert result["brooks_first_pullback_predictive_claim_allowed"] is False
    assert result["brooks_first_pullback_score_influence_allowed"] is False
    assert result["brooks_first_pullback_risk_influence_allowed"] is False
    assert result["brooks_first_pullback_decision_influence_allowed"] is False
    assert result["brooks_first_pullback_alert_influence_allowed"] is False
    assert result["brooks_first_pullback_order_execution_allowed"] is False


def test_derived_runner_restores_original_snapshot_after_failure(monkeypatch):
    original = object()
    monkeypatch.setattr(runner.base, "snapshot_context", original)

    def fail_run(symbol, **kwargs):
        assert runner.base.snapshot_context is runner.snapshot_context_with_brooks
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(runner.base, "run_warmed_session", fail_run)

    try:
        runner.run_warmed_session("WINV26", cycles=1, interval=0)
    except RuntimeError as exc:
        assert str(exc) == "synthetic failure"
    else:
        raise AssertionError("RuntimeError expected")

    assert runner.base.snapshot_context is original


def test_enriched_json_is_consumed_by_exact_trend_pullback_auditor(tmp_path):
    pullback = {
        "cycle": 1,
        "timestamp": "2026-09-07T10:00:01.000",
        "data_ready": True,
        "structure": {"trend": "UP", "choch": False},
        "price_action": {
            "brooks_signal_phase": "SETUP_PENDING",
            "brooks_signal_direction": "BUY",
            "brooks_entry_triggered": False,
            "brooks_follow_through": False,
            **PULLBACK_FIELDS,
        },
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": "WINV26|M1|2026-09-07T10:00:00",
        },
    }
    resumption = {
        "cycle": 2,
        "timestamp": "2026-09-07T10:01:01.000",
        "data_ready": True,
        "structure": {"trend": "UP", "choch": False},
        "price_action": {
            "brooks_signal_phase": "FOLLOW_THROUGH",
            "brooks_signal_direction": "BUY",
            "brooks_entry_triggered": True,
            "brooks_follow_through": True,
            **{**PULLBACK_FIELDS, "brooks_first_pullback_valid": False},
        },
        "candle_evidence": {
            "status": "CANDLE_EVIDENCE_READY",
            "candle_id": "WINV26|M1|2026-09-07T10:01:00",
        },
    }
    payload = {
        "status": "COMPLETED",
        "data_ready": True,
        "samples": [pullback, resumption],
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
    }
    path = tmp_path / "session.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    result = audit_session(path)

    assert result["status"] == "MATCHES_OBSERVED"
    assert result["complete_sequences"] == 1
    assert result["sequences"][0]["direction"] == "BUY"
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
