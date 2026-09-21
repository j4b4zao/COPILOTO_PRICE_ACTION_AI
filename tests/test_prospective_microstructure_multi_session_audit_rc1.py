import copy
import json

from tools.prospective_microstructure_multi_session_audit import audit_paths


FALSE_FLAGS = (
    "predictive_claim_allowed", "score_influence_allowed", "risk_influence_allowed",
    "decision_influence_allowed", "alert_influence_allowed", "order_execution_allowed",
    "promotion_allowed",
)


def _payload(samples=100, *, quality="WEAK"):
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
        payload = _payload(samples=samples)
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
