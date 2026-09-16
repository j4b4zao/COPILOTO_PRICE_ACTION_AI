from __future__ import annotations

import json
from types import SimpleNamespace

import tools.profit_rtd_brooks_first_pullback_capture as capture
import tools.profit_rtd_rc54_3_2_brooks_warmed_session as runner


PULLBACK_FIELDS = {
    "brooks_first_pullback_valid": True,
    "brooks_first_pullback_direction": "DOWN",
    "brooks_first_pullback_stage": "BAR_PULLBACK",
    "brooks_first_pullback_stage_index": 1,
    "brooks_first_pullback_bars": 1,
    "brooks_first_pullback_continuation_bias": True,
    "brooks_first_pullback_reversal_risk": False,
    "research_only": True,
    "observational_only": True,
    "predictive_claim_allowed": False,
    "score_influence_allowed": False,
    "risk_influence_allowed": False,
    "decision_influence_allowed": False,
    "alert_influence_allowed": False,
    "order_execution_allowed": False,
}


def test_snapshot_enrichment_does_not_run_stop_target(monkeypatch):
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

    def forbidden(*args, **kwargs):
        raise AssertionError("Stop/Target nao pode rodar antes do candle_evidence persistido")

    monkeypatch.setattr(runner, "enrich_stop_target_snapshot", forbidden)

    item = runner.snapshot_context_with_brooks(
        SimpleNamespace(),
        SimpleNamespace(),
    )

    assert "brooks_stop_target_capture_status" not in item["price_action"]


def test_postprocess_uses_persisted_exact_candle(monkeypatch):
    seen = []
    payload = {
        "samples": [
            {
                "price_action": {
                    "brooks_signal_direction": "BUY",
                    "brooks_entry_triggered": True,
                },
                "candle_evidence": {
                    "status": "CANDLE_EVIDENCE_READY",
                    "ohlc_ready": True,
                    "candle_id": "WINV26|M1|2026-09-14T09:08:00",
                    "open": 100.0,
                    "high": 105.0,
                    "low": 99.0,
                    "close": 104.0,
                },
            }
        ]
    }

    def fake_enrich(item, context):
        assert context is None
        candle = item["candle_evidence"]
        seen.append(candle["candle_id"])
        item["price_action"]["brooks_stop_target_candle_id"] = candle["candle_id"]
        return item

    monkeypatch.setattr(runner, "enrich_stop_target_snapshot", fake_enrich)
    runner._postprocess_stop_target_after_candle_evidence(payload)

    assert seen == ["WINV26|M1|2026-09-14T09:08:00"]
    assert payload["samples"][0]["price_action"]["brooks_stop_target_candle_id"] == "WINV26|M1|2026-09-14T09:08:00"
    assert payload["brooks_stop_target_history_source"] == "PERSISTED_CANDLE_EVIDENCE"


def test_postprocess_skips_non_ready_candle(monkeypatch):
    calls = []
    payload = {
        "samples": [
            {
                "price_action": {},
                "candle_evidence": {
                    "status": "CANDLE_EVIDENCE_NOT_READY",
                    "candle_id": None,
                },
            }
        ]
    }

    monkeypatch.setattr(
        runner,
        "enrich_stop_target_snapshot",
        lambda item, context: calls.append(1),
    )
    runner._postprocess_stop_target_after_candle_evidence(payload)

    assert calls == []


def test_derived_runner_restores_original_snapshot_and_postprocesses(monkeypatch, tmp_path):
    original = object()
    monkeypatch.setattr(runner.base, "snapshot_context", original)
    saved_path = tmp_path / "session.json"

    payload = {
        "status": "COMPLETED",
        "symbol": "WINV26",
        "requested_cycles": 1,
        "analyzable_samples": 1,
        "skipped_cycles": 0,
        "collection_errors": 0,
        "data_ready": True,
        "reasons": [],
        "samples": [
            {
                "price_action": {
                    "brooks_signal_direction": "BUY",
                    "brooks_entry_triggered": True,
                    "brooks_trading_range_valid": False,
                },
                "candle_evidence": {
                    "status": "CANDLE_EVIDENCE_READY",
                    "ohlc_ready": True,
                    "candle_id": "WINV26|M1|2026-09-14T09:08:00",
                    "open": 100.0,
                    "high": 105.0,
                    "low": 99.0,
                    "close": 104.0,
                },
            }
        ],
    }

    def fake_run(symbol, **kwargs):
        assert runner.base.snapshot_context is runner.snapshot_context_with_brooks
        saved_path.write_text(json.dumps(payload), encoding="utf-8")
        return {**payload, "output_path": str(saved_path)}

    monkeypatch.setattr(runner.base, "run_warmed_session", fake_run)

    result = runner.run_warmed_session("WINV26", cycles=1, interval=0)

    assert runner.base.snapshot_context is original

    persisted = json.loads(saved_path.read_text(encoding="utf-8"))
    pa = persisted["samples"][0]["price_action"]

    assert pa["brooks_stop_target_capture_status"] == "ELIGIBLE"
    assert pa["brooks_stop_target_candle_id"] == persisted["samples"][0]["candle_evidence"]["candle_id"]
    assert persisted["brooks_stop_target_postprocessed_after_candle_evidence"] is True
    assert persisted["brooks_stop_target_history_source"] == "PERSISTED_CANDLE_EVIDENCE"
    assert result["brooks_score_influence_allowed"] is False
    assert result["brooks_order_execution_allowed"] is False


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


def test_snapshot_context_with_brooks_persists_delta_rtd_telemetry(monkeypatch):
    receipt = SimpleNamespace(
        symbol="WINV26",
        timestamp="2026-09-16T12:42:12.456",
        continuity="OVERLAP_LOST_REBASE",
        new_trade_count=0,
        state_updated=False,
        baseline_reset=True,
        source_units=0,
    )

    collector = SimpleNamespace(
        last_profit_rtd_receipt=receipt,
    )

    monkeypatch.setattr(
        runner,
        "_ORIGINAL_SNAPSHOT_CONTEXT",
        lambda context, micro: {
            "structure": {"trend": "UP", "choch": False},
            "price_action": {},
        },
    )

    monkeypatch.setattr(
        runner,
        "_ACTIVE_RESEARCH_COLLECTOR",
        collector,
    )

    item = runner.snapshot_context_with_brooks(
        SimpleNamespace(),
        SimpleNamespace(),
    )

    telemetry = item["delta_rtd_telemetry"]

    assert telemetry["available"] is True
    assert telemetry["continuity"] == "OVERLAP_LOST_REBASE"
    assert telemetry["baseline_reset"] is True
    assert telemetry["new_trade_count"] == 0
    assert telemetry["state_updated"] is False
    assert telemetry["source_units"] == 0

    assert telemetry["research_only"] is True
    assert telemetry["observational_only"] is True
    assert telemetry["source_session_validity_changed"] is False
    assert telemetry["selection_eligibility_changed"] is False
    assert telemetry["oos_eligibility_changed"] is False
    assert telemetry["score_influence_allowed"] is False
    assert telemetry["risk_influence_allowed"] is False
    assert telemetry["decision_influence_allowed"] is False
    assert telemetry["alert_influence_allowed"] is False
    assert telemetry["order_execution_allowed"] is False


def test_snapshot_context_without_active_research_collector_is_safe(monkeypatch):
    monkeypatch.setattr(
        runner,
        "_ORIGINAL_SNAPSHOT_CONTEXT",
        lambda context, micro: {
            "structure": {"trend": "UP", "choch": False},
            "price_action": {},
        },
    )

    monkeypatch.setattr(
        runner,
        "_ACTIVE_RESEARCH_COLLECTOR",
        None,
    )

    item = runner.snapshot_context_with_brooks(
        SimpleNamespace(),
        SimpleNamespace(),
    )

    telemetry = item["delta_rtd_telemetry"]

    assert telemetry["available"] is False
    assert telemetry["continuity"] is None
    assert telemetry["baseline_reset"] is None
    assert telemetry["research_only"] is True
    assert telemetry["order_execution_allowed"] is False
