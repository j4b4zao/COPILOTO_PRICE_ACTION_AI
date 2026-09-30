import copy

import pytest

from tools import (
    prospective_microstructure_pa_book_independent_replication_consolidation
    as consolidation
)


def _valid_payload(outcome, reason, transitions=None):
    if transitions is None:
        transitions = []

    return {
        "status": "COMPLETED",
        "interpretation": "DESCRIPTIVE_ONLY",
        "evaluation_unit": "formal_OPPOSED_to_ALIGNED_transition",
        "evaluation_outcome": outcome,
        "outcome": outcome,
        "reason": reason,
        "protocol": {
            "sha256": consolidation.PROTOCOL_SHA256,
        },
        "identity": {
            "raw_prospective_positional_identity": "VALIDATED",
            "raw_sample_count": 100,
            "prospective_sample_count": 100,
            "simultaneous_directional_samples": 0,
            "opposed_to_aligned_transition_count": len(transitions),
        },
        "safety": {
            "alert_changed": False,
            "canonical_conflict_redefined": False,
            "checkpoint_extended": False,
            "decision_changed": False,
            "descriptive_only": True,
            "execution_changed": False,
            "operational_logic_changed": False,
            "post_hoc_gate_added": False,
            "predictive_claim_allowed": False,
            "rc17_changed": False,
            "research_only": True,
            "risk_changed": False,
            "score_changed": False,
            "threshold_changed": False,
        },
        "transitions": transitions,
    }


def test_expected_sessions_are_exactly_11_12_13():
    assert list(consolidation.EXPECTED) == ["11", "12", "13"]


def test_protocol_sha_is_frozen():
    assert consolidation.PROTOCOL_SHA256 == (
        "53efb327f613934c483f6bec36ffe04bd"
        "98743b2973815f3b54ec2b84e91f01c"
    )


@pytest.mark.parametrize("session_id", ["11", "12"])
def test_not_evaluable_is_preserved_as_not_evaluable(
    tmp_path, monkeypatch, session_id
):
    spec = copy.deepcopy(consolidation.EXPECTED[session_id])

    path = tmp_path / f"session{session_id}.json"

    payload = _valid_payload(
        "NOT_EVALUABLE",
        "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    )

    path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )

    spec["result_path"] = str(path)

    result = consolidation._validate_result(session_id, spec)

    assert result["outcome"] == "NOT_EVALUABLE"
    assert result["reason"] == "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION"
    assert result["transition_outcomes"] == []


def test_replicated_session_is_preserved(tmp_path):
    spec = copy.deepcopy(consolidation.EXPECTED["13"])

    path = tmp_path / "session13.json"

    payload = _valid_payload(
        "REPLICATED",
        "ALL_OBSERVED_TARGET_TRANSITIONS_REPLICATED",
        transitions=[
            {
                "evaluation_outcome": "REPLICATED",
            }
        ],
    )

    path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )

    spec["result_path"] = str(path)

    result = consolidation._validate_result("13", spec)

    assert result["outcome"] == "REPLICATED"
    assert result["transition_outcomes"] == ["REPLICATED"]


def test_missing_result_fails_closed(tmp_path):
    spec = copy.deepcopy(consolidation.EXPECTED["11"])
    spec["result_path"] = str(tmp_path / "missing.json")

    with pytest.raises(ValueError, match="missing structural replication result"):
        consolidation._validate_result("11", spec)


def test_protocol_sha_mismatch_fails_closed(tmp_path):
    spec = copy.deepcopy(consolidation.EXPECTED["11"])
    path = tmp_path / "bad_protocol.json"

    payload = _valid_payload(
        "NOT_EVALUABLE",
        "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    )
    payload["protocol"]["sha256"] = "bad"

    path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )
    spec["result_path"] = str(path)

    with pytest.raises(ValueError, match="protocol SHA mismatch"):
        consolidation._validate_result("11", spec)


def test_outcome_mismatch_fails_closed(tmp_path):
    spec = copy.deepcopy(consolidation.EXPECTED["11"])
    path = tmp_path / "bad_outcome.json"

    payload = _valid_payload(
        "NOT_REPLICATED",
        "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    )

    path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )
    spec["result_path"] = str(path)

    with pytest.raises(ValueError, match="outcome mismatch"):
        consolidation._validate_result("11", spec)


def test_reason_mismatch_fails_closed(tmp_path):
    spec = copy.deepcopy(consolidation.EXPECTED["11"])
    path = tmp_path / "bad_reason.json"

    payload = _valid_payload(
        "NOT_EVALUABLE",
        "OTHER_REASON",
    )

    path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )
    spec["result_path"] = str(path)

    with pytest.raises(ValueError, match="reason mismatch"):
        consolidation._validate_result("11", spec)


def test_positional_identity_failure_fails_closed(tmp_path):
    spec = copy.deepcopy(consolidation.EXPECTED["11"])
    path = tmp_path / "bad_identity.json"

    payload = _valid_payload(
        "NOT_EVALUABLE",
        "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    )
    payload["identity"]["raw_prospective_positional_identity"] = "FAILED"

    path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )
    spec["result_path"] = str(path)

    with pytest.raises(ValueError, match="positional identity not validated"):
        consolidation._validate_result("11", spec)


@pytest.mark.parametrize(
    "unsafe_key",
    [
        "alert_changed",
        "canonical_conflict_redefined",
        "checkpoint_extended",
        "decision_changed",
        "execution_changed",
        "operational_logic_changed",
        "post_hoc_gate_added",
        "predictive_claim_allowed",
        "rc17_changed",
        "risk_changed",
        "score_changed",
        "threshold_changed",
    ],
)
def test_unsafe_flags_fail_closed(tmp_path, unsafe_key):
    spec = copy.deepcopy(consolidation.EXPECTED["11"])
    path = tmp_path / f"unsafe_{unsafe_key}.json"

    payload = _valid_payload(
        "NOT_EVALUABLE",
        "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION",
    )
    payload["safety"][unsafe_key] = True

    path.write_text(
        __import__("json").dumps(payload),
        encoding="utf-8",
    )
    spec["result_path"] = str(path)

    with pytest.raises(ValueError, match="unsafe flag"):
        consolidation._validate_result("11", spec)


def test_real_consolidation_exact_counts():
    result = consolidation.build_consolidation()

    assert result["status"] == "COMPLETED"
    assert result["interpretation"] == "DESCRIPTIVE_ONLY"

    assert result["independent_session_count"] == 3
    assert result["evaluable_session_count"] == 1
    assert result["replicated_session_count"] == 1
    assert result["not_replicated_session_count"] == 0
    assert result["not_evaluable_session_count"] == 2

    assert result["summary"]["session_11"] == "NOT_EVALUABLE"
    assert result["summary"]["session_12"] == "NOT_EVALUABLE"
    assert result["summary"]["session_13"] == "REPLICATED"

    assert result["frozen_checkpoint_extended"] is False
    assert result["summary"]["predictive_validation"] is False
    assert result["summary"]["operational_promotion"] is False
    assert result["summary"]["session_14_authorized_automatically"] is False
