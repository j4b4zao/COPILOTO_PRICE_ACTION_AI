import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.profit_rtd_brooks_research_evidence_suite as suite


def _write_session(tmp_path, name, timestamps):
    path = tmp_path / name
    payload = {
        "data_ready": True,
        "samples": [{"timestamp": ts} for ts in timestamps],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _fake_auditor(paths):
    return {
        "status": "MORE_EVIDENCE_REQUIRED",
        "eligible_sessions": len(paths),
        "complete_sequences": 0,
        "hypothesis_freeze_allowed": False,
        **suite._safety(),
    }


def test_safety_contract_is_fully_off():
    safety = suite._safety()
    assert safety["research_only"] is True
    assert safety["observational_only"] is True
    assert safety["predictive_claim_allowed"] is False
    assert safety["score_influence_allowed"] is False
    assert safety["risk_influence_allowed"] is False
    assert safety["decision_influence_allowed"] is False
    assert safety["alert_influence_allowed"] is False
    assert safety["order_execution_allowed"] is False


def test_rejects_invalid_mode():
    with pytest.raises(ValueError):
        suite.build_report([], mode="LIVE")


def test_selection_accepts_non_overlapping_sessions(tmp_path, monkeypatch):
    first = _write_session(
        tmp_path,
        "a.json",
        ["2026-09-07T09:00:00", "2026-09-07T09:05:00"],
    )
    second = _write_session(
        tmp_path,
        "b.json",
        ["2026-09-07T10:00:00", "2026-09-07T10:05:00"],
    )
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report([first, second], mode="SELECTION")

    assert report["eligible_sessions"] == 2
    assert report["accepted_sessions"] == ["a.json", "b.json"]
    assert report["rejected_sessions"] == []
    assert report["setups"]["TEST_SETUP"]["eligible_sessions"] == 2


def test_selection_rejects_temporal_overlap(tmp_path, monkeypatch):
    first = _write_session(
        tmp_path,
        "a.json",
        ["2026-09-07T09:00:00", "2026-09-07T09:10:00"],
    )
    second = _write_session(
        tmp_path,
        "b.json",
        ["2026-09-07T09:05:00", "2026-09-07T09:15:00"],
    )
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report([first, second])

    assert report["eligible_sessions"] == 1
    assert report["rejected_sessions"][0]["reason"] == "TEMPORAL_OVERLAP"
    assert report["rejected_sessions"][0]["overlaps_with"] == "a.json"


def test_rejects_session_without_interval(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"data_ready": True, "samples": [{}]}), encoding="utf-8")
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report([path])

    assert report["eligible_sessions"] == 0
    assert report["rejected_sessions"][0]["reason"] == "SESSION_INTERVAL_UNAVAILABLE"


def test_oos_requires_cutoff(tmp_path, monkeypatch):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report([path], mode="OOS")

    assert report["eligible_sessions"] == 0
    assert report["rejected_sessions"][0]["reason"] == "SELECTION_CUTOFF_REQUIRED_FOR_OOS"


def test_oos_rejects_session_at_or_before_cutoff(tmp_path, monkeypatch):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report(
        [path],
        mode="OOS",
        selection_cutoff="2026-09-07T09:00:00",
    )

    assert report["eligible_sessions"] == 0
    assert report["rejected_sessions"][0]["reason"] == "SESSION_NOT_STRICTLY_AFTER_SELECTION_CUTOFF"


def test_oos_accepts_session_strictly_after_cutoff(tmp_path, monkeypatch):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:01"])
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report(
        [path],
        mode="OOS",
        selection_cutoff="2026-09-07T09:00:00",
    )

    assert report["eligible_sessions"] == 1
    assert report["accepted_sessions"] == ["a.json"]


def test_invalid_cutoff_raises(tmp_path):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:01"])
    with pytest.raises(ValueError, match="invalid ISO cutoff"):
        suite.build_report([path], mode="OOS", selection_cutoff="not-a-date")


def test_no_eligible_sessions_does_not_call_auditor(tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"samples": []}), encoding="utf-8")

    def should_not_run(_paths):
        raise AssertionError("auditor should not run")

    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": should_not_run})
    report = suite.build_report([path])

    assert report["setups"]["TEST_SETUP"]["status"] == "NO_ELIGIBLE_SESSIONS"


def test_stop_target_is_explicitly_classifier_only(tmp_path, monkeypatch):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report([path])
    management = report["setups"][suite.MANAGEMENT_RESEARCH]

    assert management["status"] == "CLASSIFIER_ONLY_NO_EXACT_AUDITOR"
    assert management["hypothesis_freeze_allowed"] is False
    assert management["predictive_claim_allowed"] is False


def test_report_never_allows_freeze_promotion_or_predictive_claim(tmp_path, monkeypatch):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    monkeypatch.setattr(suite, "AUDITORS", {"TEST_SETUP": _fake_auditor})

    report = suite.build_report([path])

    assert report["hypothesis_freeze_allowed"] is False
    assert report["promotion_allowed"] is False
    assert report["predictive_claim_allowed"] is False
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False


def test_adapter_prefers_path_audit_contract(tmp_path):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    calls = []

    def audit(paths):
        calls.append(paths)
        return {"status": "PATH_AUDIT"}

    module = SimpleNamespace(audit=audit)
    result = suite._call_auditor(module, [path])

    assert result["status"] == "PATH_AUDIT"
    assert calls == [[str(path)]]


def test_adapter_uses_single_payload_contract(tmp_path):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    calls = []

    def audit_payload(payload):
        calls.append(payload)
        return {"status": "PAYLOAD_AUDIT"}

    module = SimpleNamespace(audit_payload=audit_payload)
    result = suite._call_auditor(module, [path])

    assert result["status"] == "PAYLOAD_AUDIT"
    assert len(calls) == 1
    assert calls[0]["data_ready"] is True


def test_adapter_uses_multi_session_payload_contract(tmp_path):
    first = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    second = _write_session(tmp_path, "b.json", ["2026-09-07T10:00:00"])
    calls = []

    def audit_sessions(payloads):
        calls.append(payloads)
        return {"status": "MULTI_PAYLOAD_AUDIT", "count": len(payloads)}

    module = SimpleNamespace(audit_sessions=audit_sessions)
    result = suite._call_auditor(module, [first, second])

    assert result["status"] == "MULTI_PAYLOAD_AUDIT"
    assert result["count"] == 2
    assert len(calls) == 1
    assert len(calls[0]) == 2


def test_adapter_rejects_unsupported_contract(tmp_path):
    path = _write_session(tmp_path, "a.json", ["2026-09-07T09:00:00"])
    with pytest.raises(AttributeError, match="supported audit contract"):
        suite._call_auditor(SimpleNamespace(), [path])
