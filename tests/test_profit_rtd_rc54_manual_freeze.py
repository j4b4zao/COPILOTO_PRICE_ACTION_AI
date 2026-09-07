from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.profit_rtd_rc54_manual_freeze as mod


def _ready_packet(paths, cutoff="2026-09-04T09:34:58.256000"):
    return {
        "status": "READY_FOR_MANUAL_FREEZE_REVIEW",
        "manual_freeze_review_allowed": True,
        "review_reference_cutoff": cutoff,
        "accepted_selection_paths": [str(path) for path in paths],
        "robustness_candidates": ["CONTEXT_SELL_MICRO_NEUTRAL"],
        "selection_interval": {
            "first_timestamp": "2026-09-01T10:00:00",
            "last_timestamp": cutoff,
        },
        "source_directory": "data/selection",
        "pattern": "profit_rtd_rc54_3_2_*.json",
    }


def _session(tmp_path, name="s1.json", payload=None):
    path = tmp_path / name
    path.write_text(json.dumps(payload or {"session": name}), encoding="utf-8")
    return path


def test_requires_exact_manual_confirmation(monkeypatch, tmp_path):
    session = _session(tmp_path)
    monkeypatch.setattr(mod, "build_packet", lambda *a, **k: _ready_packet([session]))
    with pytest.raises(mod.FreezeError, match="MANUAL_CONFIRMATION_REQUIRED"):
        mod.build_freeze(tmp_path, confirmed_cutoff="2026-09-04T09:34:58.256000", confirmation_token="YES")


def test_rejects_not_ready_packet(monkeypatch, tmp_path):
    packet = _ready_packet([])
    packet["status"] = "NOT_READY"
    packet["manual_freeze_review_allowed"] = False
    monkeypatch.setattr(mod, "build_packet", lambda *a, **k: packet)
    with pytest.raises(mod.FreezeError, match="FREEZE_REVIEW_NOT_READY"):
        mod.build_freeze(tmp_path, confirmed_cutoff=packet["review_reference_cutoff"], confirmation_token=mod.CONFIRMATION_TOKEN)


def test_rejects_cutoff_mismatch(monkeypatch, tmp_path):
    session = _session(tmp_path)
    packet = _ready_packet([session])
    monkeypatch.setattr(mod, "build_packet", lambda *a, **k: packet)
    with pytest.raises(mod.FreezeError, match="CONFIRMED_CUTOFF_MISMATCH"):
        mod.build_freeze(tmp_path, confirmed_cutoff="2026-09-04T09:35:00", confirmation_token=mod.CONFIRMATION_TOKEN)


def test_rejects_missing_accepted_session(monkeypatch, tmp_path):
    missing = tmp_path / "missing.json"
    packet = _ready_packet([missing])
    monkeypatch.setattr(mod, "build_packet", lambda *a, **k: packet)
    with pytest.raises(mod.FreezeError, match="ACCEPTED_SESSION_MISSING"):
        mod.build_freeze(tmp_path, confirmed_cutoff=packet["review_reference_cutoff"], confirmation_token=mod.CONFIRMATION_TOKEN)


def test_build_freeze_seals_sessions_and_opens_only_future_oos_gate(monkeypatch, tmp_path):
    s1 = _session(tmp_path, "s1.json", {"x": 1})
    s2 = _session(tmp_path, "s2.json", {"x": 2})
    packet = _ready_packet([s1, s2])
    monkeypatch.setattr(mod, "build_packet", lambda *a, **k: packet)

    freeze = mod.build_freeze(
        tmp_path,
        confirmed_cutoff=packet["review_reference_cutoff"],
        confirmation_token=mod.CONFIRMATION_TOKEN,
    )

    assert freeze["selection_cutoff_defined"] is True
    assert freeze["selection_cutoff_is_frozen"] is True
    assert freeze["freeze_immutable"] is True
    assert freeze["accepted_selection_sessions"] == 2
    assert len(freeze["session_seals"]) == 2
    assert all(len(row["sha256"]) == 64 for row in freeze["session_seals"])
    assert freeze["future_oos_collection_allowed"] is True
    assert freeze["oos_collection_started"] is False
    assert freeze["oos_evidence_evaluated"] is False


def test_freeze_id_is_deterministic_for_same_evidence(monkeypatch, tmp_path):
    session = _session(tmp_path)
    packet = _ready_packet([session])
    monkeypatch.setattr(mod, "build_packet", lambda *a, **k: packet)
    kwargs = {
        "confirmed_cutoff": packet["review_reference_cutoff"],
        "confirmation_token": mod.CONFIRMATION_TOKEN,
    }
    first = mod.build_freeze(tmp_path, **kwargs)
    second = mod.build_freeze(tmp_path, **kwargs)
    assert first["freeze_id"] == second["freeze_id"]


def test_write_freeze_is_create_once_immutable(tmp_path):
    output = tmp_path / "freeze.json"
    payload = {"freeze_id": "abc", "freeze_immutable": True}
    mod.write_freeze(output, payload)
    assert json.loads(output.read_text(encoding="utf-8"))["freeze_id"] == "abc"
    with pytest.raises(mod.FreezeError, match="FREEZE_ALREADY_EXISTS"):
        mod.write_freeze(output, {"freeze_id": "different"})


def test_freeze_has_no_operational_or_predictive_influence(monkeypatch, tmp_path):
    session = _session(tmp_path)
    packet = _ready_packet([session])
    monkeypatch.setattr(mod, "build_packet", lambda *a, **k: packet)
    freeze = mod.build_freeze(
        tmp_path,
        confirmed_cutoff=packet["review_reference_cutoff"],
        confirmation_token=mod.CONFIRMATION_TOKEN,
    )
    assert freeze["research_only"] is True
    assert freeze["observational_only"] is True
    assert freeze["predictive_claim_allowed"] is False
    assert freeze["score_influence_allowed"] is False
    assert freeze["risk_influence_allowed"] is False
    assert freeze["decision_influence_allowed"] is False
    assert freeze["alert_influence_allowed"] is False
    assert freeze["order_execution_allowed"] is False
