from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from tools.profit_rtd_rc54_freeze_review_packet import build_packet, main


PHASE = "RC54.3.2_WARMED_SYNCHRONIZED_CONTEXT_CAPTURE"


def _sample(ts, *, ready=True, last_price=100.0, bucket="CONTEXT_BUY_MICRO_BUY"):
    structure, pa, micro = bucket.split("_")[-3:]
    return {
        "timestamp": ts.isoformat(),
        "trade_context_ready": ready,
        "last_price": last_price,
        "structure_direction": structure,
        "price_action_direction": pa,
        "microstructure_direction": micro,
    }


def _session(path: Path, start: datetime, *, samples=12):
    rows = []
    for i in range(samples):
        rows.append({
            "timestamp": (start + timedelta(seconds=i)).isoformat(),
            "trade_context_ready": True,
            "last_price": 100.0 + i,
            "structure": {"trend": "UP"},
            "price_action": {"direction": "BUY"},
            "microstructure_direction": "BUY",
        })
    payload = {
        "phase": PHASE,
        "status": "COMPLETED",
        "data_ready": True,
        "collection_errors": 0,
        "missing_price_count": 0,
        "delta_failure_samples": 0,
        "price_capture": True,
        "requested_cycles": samples,
        "analyzable_samples": samples,
        "skipped_cycles": 0,
        "observational_only": True,
        "samples": rows,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_empty_directory_is_not_ready(tmp_path):
    packet = build_packet(tmp_path)
    assert packet["status"] == "NOT_READY"
    assert packet["review_reference_cutoff"] is None
    assert packet["selection_cutoff_defined"] is False


def test_ready_packet_exposes_reference_but_does_not_freeze(tmp_path, monkeypatch):
    paths = [
        _session(tmp_path / f"profit_rtd_rc54_3_2_{i}.json", datetime(2026, 9, 1, 10 + i, 0, 0))
        for i in range(3)
    ]
    fake_robustness = {
        "verdict": "ROBUSTNESS_CANDIDATES_AVAILABLE_FOR_FURTHER_OBSERVATIONAL_VALIDATION",
        "robustness_candidates": ["CONTEXT_BUY_MICRO_BUY"],
        "buckets": {
            "CONTEXT_BUY_MICRO_BUY": {
                "supported_sessions": 3,
                "consistent_horizons": 2,
                "evidence_gap": {"minimum_additional_sessions_lower_bound": 0},
                "robustness_candidate": True,
            }
        },
    }

    def fake_recompose(*args, **kwargs):
        manifest = []
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            manifest.append({
                "path": str(path.resolve()),
                "role": "SELECTION",
                "eligible": True,
                "first_timestamp": payload["samples"][0]["timestamp"],
                "last_timestamp": payload["samples"][-1]["timestamp"],
            })
        return {
            "manifest": manifest,
            "robustness": fake_robustness,
            "accepted_selection_paths": [row["path"] for row in manifest],
        }

    monkeypatch.setattr("tools.profit_rtd_rc54_freeze_review_packet.recompose", fake_recompose)
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.build_readiness_report",
        lambda *args, **kwargs: {
            "manual_freeze_review_allowed": True,
            "status": "READY_FOR_MANUAL_FREEZE_REVIEW",
        },
    )

    packet = build_packet(tmp_path)
    assert packet["status"] == "READY_FOR_MANUAL_FREEZE_REVIEW"
    assert packet["review_reference_cutoff"] == datetime(2026, 9, 1, 12, 0, 11).isoformat()
    assert packet["review_reference_cutoff_is_frozen"] is False
    assert packet["freeze_allowed"] is False
    assert packet["oos_allowed"] is False


def test_candidate_details_are_included(tmp_path, monkeypatch):
    path = _session(tmp_path / "profit_rtd_rc54_3_2_a.json", datetime(2026, 9, 1, 10, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.build_readiness_report",
        lambda *args, **kwargs: {"manual_freeze_review_allowed": True},
    )
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.recompose",
        lambda *args, **kwargs: {
            "manifest": [{
                "path": str(path.resolve()), "role": "SELECTION", "eligible": True,
                "first_timestamp": "2026-09-01T10:00:00", "last_timestamp": "2026-09-01T10:00:11",
            }],
            "robustness": {
                "robustness_candidates": ["X"],
                "buckets": {"X": {
                    "supported_sessions": 3,
                    "consistent_horizons": 2,
                    "evidence_gap": {"minimum_additional_sessions_lower_bound": 0},
                    "robustness_candidate": True,
                }},
            },
        },
    )
    packet = build_packet(tmp_path)
    assert packet["candidate_details"]["X"]["supported_sessions"] == 3
    assert packet["candidate_details"]["X"]["consistent_horizons"] == 2


def test_quarantine_is_preserved(tmp_path, monkeypatch):
    path = _session(tmp_path / "profit_rtd_rc54_3_2_a.json", datetime(2026, 9, 1, 10, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.build_readiness_report",
        lambda *args, **kwargs: {"manual_freeze_review_allowed": False},
    )
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.recompose",
        lambda *args, **kwargs: {
            "manifest": [{
                "path": str(path.resolve()), "role": "SELECTION", "eligible": False,
                "reasons": ["TEMPORAL_OVERLAP"], "overlaps_with": "other.json",
                "first_timestamp": "2026-09-01T10:00:00", "last_timestamp": "2026-09-01T10:00:11",
            }],
            "robustness": {"robustness_candidates": [], "buckets": {}},
        },
    )
    packet = build_packet(tmp_path)
    assert packet["quarantined_sessions"][0]["reasons"] == ["TEMPORAL_OVERLAP"]
    assert packet["review_reference_cutoff"] is None


def test_selection_interval_uses_extremes(tmp_path, monkeypatch):
    paths = [
        _session(tmp_path / "profit_rtd_rc54_3_2_a.json", datetime(2026, 9, 1, 10, 0, 0)),
        _session(tmp_path / "profit_rtd_rc54_3_2_b.json", datetime(2026, 9, 1, 12, 0, 0)),
    ]
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.build_readiness_report",
        lambda *args, **kwargs: {"manual_freeze_review_allowed": False},
    )
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.recompose",
        lambda *args, **kwargs: {
            "manifest": [
                {"path": str(paths[1].resolve()), "role": "SELECTION", "eligible": True,
                 "first_timestamp": "2026-09-01T12:00:00", "last_timestamp": "2026-09-01T12:00:11"},
                {"path": str(paths[0].resolve()), "role": "SELECTION", "eligible": True,
                 "first_timestamp": "2026-09-01T10:00:00", "last_timestamp": "2026-09-01T10:00:11"},
            ],
            "robustness": {"robustness_candidates": [], "buckets": {}},
        },
    )
    packet = build_packet(tmp_path)
    assert packet["selection_interval"] == {
        "first_timestamp": "2026-09-01T10:00:00",
        "last_timestamp": "2026-09-01T12:00:11",
    }


def test_safety_flags_remain_false(tmp_path):
    packet = build_packet(tmp_path)
    for key in (
        "freeze_allowed", "selection_cutoff_defined", "oos_allowed",
        "predictive_claim_allowed", "score_influence_allowed", "risk_influence_allowed",
        "decision_influence_allowed", "alert_influence_allowed", "order_execution_allowed",
    ):
        assert packet[key] is False
    assert packet["research_only"] is True
    assert packet["observational_only"] is True


def test_review_reference_only_exists_when_manual_review_allowed(tmp_path, monkeypatch):
    path = _session(tmp_path / "profit_rtd_rc54_3_2_a.json", datetime(2026, 9, 1, 10, 0, 0))
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.build_readiness_report",
        lambda *args, **kwargs: {"manual_freeze_review_allowed": False},
    )
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.recompose",
        lambda *args, **kwargs: {
            "manifest": [{
                "path": str(path.resolve()), "role": "SELECTION", "eligible": True,
                "first_timestamp": "2026-09-01T10:00:00", "last_timestamp": "2026-09-01T10:00:11",
            }],
            "robustness": {"robustness_candidates": [], "buckets": {}},
        },
    )
    packet = build_packet(tmp_path)
    assert packet["selection_interval"]["last_timestamp"] == "2026-09-01T10:00:11"
    assert packet["review_reference_cutoff"] is None


def test_cli_writes_json(tmp_path, monkeypatch):
    out = tmp_path / "packet.json"
    monkeypatch.setattr(
        "tools.profit_rtd_rc54_freeze_review_packet.build_packet",
        lambda *args, **kwargs: {
            "packet": "RC54_FREEZE_REVIEW_PACKET_V1",
            "status": "NOT_READY",
        },
    )
    assert main([str(tmp_path), "--output", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["packet"] == "RC54_FREEZE_REVIEW_PACKET_V1"
