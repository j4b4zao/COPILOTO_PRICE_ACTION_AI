import copy
import json
from datetime import datetime, timedelta

import pytest

from tools.prospective_microstructure_multi_session_audit import audit_paths
from tools.prospective_microstructure_coverage_report import report_paths


FALSE_FLAGS = (
    "predictive_claim_allowed", "score_influence_allowed", "risk_influence_allowed",
    "decision_influence_allowed", "alert_influence_allowed", "order_execution_allowed",
    "promotion_allowed",
)


def _payload(samples=100, *, quality="WEAK", start=0):
    safety = {"research_only": True, "observational_only": True,
              **{name: False for name in FALSE_FLAGS}}
    report = {
        "samples": samples, "high_quality_samples": 1, "medium_quality_samples": 2,
        "low_quality_samples": 3, "conflict_samples": 4, "correlated_samples": 5,
        "one_source_samples": samples - 2, "two_source_samples": 1,
        "three_source_samples": 1, "high_quality_rate": 0.01,
        "three_source_rate": 0.01, "conflict_rate": 0.04,
        "correlation_rate": 0.05, "average_confidence": 0.12,
        "session_quality": quality, "recommendation": "KEEP_OBSERVING",
        "passive_only": True,
    }
    return {
        "status": "COMPLETED", "data_ready": True,
        "trade_context_ready_at_start": True, **safety,
        "samples": [
            {"timestamp": (datetime(2026, 9, 21) + timedelta(seconds=start + index)).isoformat()}
            for index in range(samples)
        ],
        "prospective_microstructure": {
            "stage": "RC1-PROSPECTIVE-MICROSTRUCTURE-EVIDENCE",
            "source_analyzable_samples": samples, "captured_samples": samples,
            "sample_count_matches_source": True, "report": report,
            "samples": [{} for _ in range(samples)], **safety,
        },
    }


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_one_valid_session_is_insufficient_and_keeps_safety(tmp_path):
    path = _write(tmp_path / "one.json", _payload(samples=292))
    result = audit_paths([path])
    assert result["eligible_sessions"] == 1
    assert result["aggregate"]["stability"] == "INSUFFICIENT_DATA"
    assert result["aggregate"]["recommendation"] == "COLLECT_MORE_DATA"
    assert result["evidence_gap"] == {
        "additional_independent_sessions_lower_bound": 2,
        "additional_samples_lower_bound": 8,
    }
    assert result["observational_only"] is True
    assert all(result[name] is False for name in FALSE_FLAGS)


def test_three_distinct_valid_sessions_delegate_to_existing_comparator(tmp_path):
    paths = []
    for index, samples in enumerate((100, 101, 102)):
        payload = _payload(samples=samples, start=index * 1000)
        payload["session_id"] = index
        paths.append(_write(tmp_path / f"{index}.json", payload))
    result = audit_paths(paths)
    assert result["eligible_sessions"] == 3
    assert result["aggregate"]["samples"] == 303
    assert result["aggregate"]["stability"] == "STABLE_WEAK"
    assert result["aggregate"]["recommendation"] == "KEEP_OBSERVING"
    assert result["evidence_gap"]["additional_independent_sessions_lower_bound"] == 0


def test_duplicate_path_and_hash_are_fail_closed(tmp_path):
    first = _write(tmp_path / "first.json", _payload())
    clone = _write(tmp_path / "clone.json", _payload())
    result = audit_paths([first, first, clone])
    assert result["eligible_sessions"] == 1
    assert [item["reasons"] for item in result["rejected"]] == [
        ("DUPLICATE_PATH",), ("DUPLICATE_SHA256",),
    ]


def test_technical_context_count_and_safety_failures_are_rejected(tmp_path):
    cases = []
    for name, mutation in (
        ("data", lambda p: p.update(data_ready=False)),
        ("context", lambda p: p.update(trade_context_ready_at_start=False)),
        ("count", lambda p: p["prospective_microstructure"].update(captured_samples=99)),
        ("safety", lambda p: p.update(score_influence_allowed=True)),
    ):
        payload = _payload()
        mutation(payload)
        payload["case"] = name
        cases.append(_write(tmp_path / f"{name}.json", payload))
    result = audit_paths(cases)
    assert result["eligible_sessions"] == 0
    assert result["rejected_sessions"] == 4
    reasons = {reason for item in result["rejected"] for reason in item["reasons"]}
    assert "DATA_NOT_READY" in reasons
    assert "TRADE_CONTEXT_NOT_READY_AT_START" in reasons
    assert "CAPTURED_SAMPLE_COUNT_MISMATCH" in reasons
    assert "SESSION_SCORE_INFLUENCE_ALLOWED_NOT_FALSE" in reasons


def test_inputs_are_not_mutated(tmp_path):
    payload = _payload()
    before = copy.deepcopy(payload)
    audit_paths([_write(tmp_path / "one.json", payload)])
    assert payload == before


def test_overlapping_distinct_files_are_rejected(tmp_path):
    first = _write(tmp_path / "first.json", _payload(start=0))
    second = _payload(start=50)
    second["session_id"] = "different hash, overlapping time"
    result = audit_paths([first, _write(tmp_path / "second.json", second)])
    assert result["eligible_sessions"] == 1
    assert result["rejected_sessions"] == 1
    assert result["rejected"][0]["reasons"] == ("TEMPORAL_OVERLAP:" + str(first.resolve()),)


def test_nonmonotonic_source_timestamps_are_rejected(tmp_path):
    payload = _payload()
    payload["samples"][1]["timestamp"] = payload["samples"][0]["timestamp"]
    result = audit_paths([_write(tmp_path / "bad-time.json", payload)])
    assert result["eligible_sessions"] == 0
    assert "SOURCE_TIMESTAMPS_NOT_STRICTLY_INCREASING" in result["rejected"][0]["reasons"]


def test_coverage_report_counts_directional_denominators_and_conflict_runs(tmp_path):
    payload = _payload(samples=5)
    samples = [
        ("BUY", "NONE", True, "SELL", "CONFLICT", 1),
        ("BUY", "NONE", True, "SELL", "CONFLICT", 1),
        ("NONE", "BUY", True, "NONE", "INSUFFICIENT_DATA", 0),
        ("SELL", "SELL", False, "NONE", "INSUFFICIENT_DATA", 0),
        ("BUY", "NONE", True, "SELL", "CONFLICT", 1),
    ]
    payload["prospective_microstructure"]["samples"] = [
        dict(zip(("price_action_bias", "flow_direction", "book_available",
                  "book_direction", "state", "conflict_count"), row))
        for row in samples
    ]
    payload["prospective_microstructure"]["report"]["conflict_samples"] = 3
    result = report_paths([_write(tmp_path / "one.json", payload)])
    assert result["sessions"][0]["coverage"] == {
        "samples": 5, "pa_directional": 4, "flow_directional": 2,
        "book_available": 4, "book_directional": 3,
        "insufficient_data": 2, "pa_directional_insufficient_data": 1,
        "conflicts": 3, "conflict_runs": 2, "longest_conflict_run": 2,
    }
    assert result["audit_stability"] == "INSUFFICIENT_DATA"
    assert result["observational_only"] is True
    assert all(result[name] is False for name in FALSE_FLAGS)


def test_coverage_report_rejects_missing_fields_without_changing_audit(tmp_path):
    path = _write(tmp_path / "one.json", _payload(samples=5))
    assert audit_paths([path])["eligible_sessions"] == 1
    with pytest.raises(ValueError, match="missing directional diagnostic fields"):
        report_paths([path])


def test_coverage_report_rejects_conflict_count_disagreement(tmp_path):
    payload = _payload(samples=1)
    payload["prospective_microstructure"]["samples"] = [{
        "price_action_bias": "BUY", "flow_direction": "NONE",
        "book_available": True, "book_direction": "SELL",
        "state": "CONFLICT", "conflict_count": 1,
    }]
    path = _write(tmp_path / "one.json", payload)
    with pytest.raises(ValueError, match="differs from session report"):
        report_paths([path])
