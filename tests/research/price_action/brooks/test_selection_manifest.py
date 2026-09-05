import json

from tools.profit_rtd_brooks_selection_manifest import build_manifest, inspect_session


def _session(tmp_path, name, start, end, **overrides):
    payload = {
        "data_ready": True,
        "analyzable_samples": 2,
        "samples": [
            {"candle_evidence": {"timestamp": start}},
            {"candle_evidence": {"timestamp": end}},
        ],
        "brooks_first_pullback_capture": True,
        "brooks_major_reversal_context_capture": True,
        "brooks_wedge_three_pushes_capture": True,
        "brooks_trading_range_capture": True,
        "brooks_predictive_claim_allowed": False,
        "brooks_score_influence_allowed": False,
        "brooks_risk_influence_allowed": False,
        "brooks_decision_influence_allowed": False,
        "brooks_alert_influence_allowed": False,
        "brooks_order_execution_allowed": False,
    }
    payload.update(overrides)
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_session_is_eligible(tmp_path):
    path = _session(tmp_path, "a.json", "2026-09-08T09:00:00", "2026-09-08T09:05:00")
    result = inspect_session(path)
    assert result["eligible"] is True
    assert result["reasons"] == []
    assert len(result["sha256"]) == 64


def test_data_ready_required(tmp_path):
    path = _session(tmp_path, "a.json", "2026-09-08T09:00:00", "2026-09-08T09:05:00", data_ready=False)
    assert "DATA_READY_REQUIRED" in inspect_session(path)["reasons"]


def test_capture_flags_required(tmp_path):
    path = _session(tmp_path, "a.json", "2026-09-08T09:00:00", "2026-09-08T09:05:00", brooks_wedge_three_pushes_capture=False)
    result = inspect_session(path)
    assert "BROOKS_CAPTURE_FLAGS_REQUIRED" in result["reasons"]
    assert "brooks_wedge_three_pushes_capture" in result["missing_capture_flags"]


def test_safety_contract_required(tmp_path):
    path = _session(tmp_path, "a.json", "2026-09-08T09:00:00", "2026-09-08T09:05:00", brooks_risk_influence_allowed=True)
    result = inspect_session(path)
    assert "BROOKS_SAFETY_CONTRACT_VIOLATION" in result["reasons"]
    assert "brooks_risk_influence_allowed" in result["safety_violations"]


def test_manifest_accepts_independent_sessions(tmp_path):
    a = _session(tmp_path, "a.json", "2026-09-08T09:00:00", "2026-09-08T09:05:00")
    b = _session(tmp_path, "b.json", "2026-09-08T10:00:00", "2026-09-08T10:05:00")
    result = build_manifest([b, a])
    assert result["eligible_sessions"] == 2
    assert [x["session"] for x in result["sessions"]] == ["a.json", "b.json"]
    assert result["selection_cutoff"] == "2026-09-08T10:05:00"


def test_manifest_rejects_temporal_overlap(tmp_path):
    a = _session(tmp_path, "a.json", "2026-09-08T09:00:00", "2026-09-08T09:10:00")
    b = _session(tmp_path, "b.json", "2026-09-08T09:05:00", "2026-09-08T09:15:00")
    result = build_manifest([a, b])
    assert result["eligible_sessions"] == 1
    assert result["rejected_sessions"] == 1
    assert "TEMPORAL_OVERLAP" in result["rejected"][0]["reasons"]
    assert result["rejected"][0]["overlaps_with"] == "a.json"


def test_manifest_is_selection_only_and_never_promotes(tmp_path):
    a = _session(tmp_path, "a.json", "2026-09-08T09:00:00", "2026-09-08T09:05:00")
    result = build_manifest([a])
    assert result["mode"] == "SELECTION"
    assert result["oos_allowed_from_manifest"] is False
    assert result["hypothesis_freeze_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["predictive_claim_allowed"] is False
    assert result["score_influence_allowed"] is False
    assert result["risk_influence_allowed"] is False
    assert result["decision_influence_allowed"] is False
    assert result["alert_influence_allowed"] is False
    assert result["order_execution_allowed"] is False
