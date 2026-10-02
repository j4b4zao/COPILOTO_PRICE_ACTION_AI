import copy
import json
from pathlib import Path

import pytest

from tools import prospective_microstructure_pa_book_replication_accumulation_consolidation as consolidation


@pytest.fixture
def frozen_results(tmp_path, monkeypatch):
    """Copy exact results; pin fixture hashes independently for semantic mutations."""
    expected = copy.deepcopy(consolidation.EXPECTED)
    for session_id, spec in expected.items():
        source = Path(spec["result_file"])
        target = tmp_path / source.name
        target.write_bytes(source.read_bytes())
        spec["result_file"] = str(target)
    monkeypatch.setattr(consolidation, "EXPECTED", expected)
    return expected


def _mutate(expected, session_id, change):
    spec = expected[session_id]
    path = Path(spec["result_file"])
    payload = consolidation._load_result(session_id, path.read_bytes())
    change(payload)
    text = json.dumps(payload)
    if session_id == "14":
        text = "=== STRUCTURAL EVALUATOR ===\n" + text + "\nEVALUATOR_EXIT_CODE=0\n"
    path.write_text(text, encoding="utf-8")
    # Bypass the first byte-identity gate solely to exercise semantic validation.
    spec["result_sha256"] = consolidation._sha256(path)


def test_happy_path_exact_real_frozen_block():
    result = consolidation.build_consolidation()
    assert result["version"] == "RC1-PA-BOOK-INDEPENDENT-REPLICATION-ACCUMULATION-CONSOLIDATION"
    assert result["status"] == "COMPLETED"
    for key, value in {
        "planned_session_count": 5, "completed_session_count": 5,
        "evaluable_session_count": 0, "replicated_session_count": 0,
        "not_replicated_session_count": 0, "not_evaluable_session_count": 5,
        "formal_transition_count": 0, "replicated_transition_count": 0,
        "not_replicated_transition_count": 0,
    }.items():
        assert result[key] == value
    assert [s["session_id"] for s in result["sessions"]] == [14, 15, 16, 17, 18]
    for session in result["sessions"]:
        assert set(session) == {"session_id", "result_file", "result_sha256", "outcome", "reason", "formal_transition_count"}
        assert session["outcome"] == "NOT_EVALUABLE"
        assert session["formal_transition_count"] == 0
    assert result["sessions"][0]["reason"] == "CAPTURE_INTEGRITY_FAILURE"
    assert result["sessions"][-1]["result_sha256"] == "39c7a2b70c4909240ef758a634e14f28d38c0d5d5c2f04e24d4dff8c46e346de"


def test_missing_result_fails_closed(frozen_results):
    Path(frozen_results["16"]["result_file"]).unlink()
    with pytest.raises(ValueError, match="missing result file"):
        consolidation.build_consolidation()


@pytest.mark.parametrize("change", ["missing", "extra"])
def test_manifest_must_have_exact_sessions(frozen_results, change):
    if change == "missing":
        del frozen_results["15"]
    else:
        frozen_results["19"] = copy.deepcopy(frozen_results["18"])
    with pytest.raises(ValueError, match="missing or extra session"):
        consolidation.build_consolidation()


def test_sha_mismatch_fails_closed(frozen_results):
    path = Path(frozen_results["18"]["result_file"])
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="result SHA mismatch"):
        consolidation.build_consolidation()


@pytest.mark.parametrize("field,value,message", [
    ("evaluation_outcome", "NOT_REPLICATED", "outcome mismatch"),
    ("evaluation_outcome", "REPLICATED", "outcome mismatch"),
    ("outcome", "REPLICATED", "outcome mismatch"),
    ("reason", "OTHER_REASON", "reason mismatch"),
    ("status", "INCOMPLETE", "status mismatch"),
])
def test_frozen_classification_mismatch_fails_closed(frozen_results, field, value, message):
    _mutate(frozen_results, "15", lambda p: p.update({field: value}))
    with pytest.raises(ValueError, match=message):
        consolidation.build_consolidation()


@pytest.mark.parametrize("where", ["identity", "transitions", "boolean_count"])
def test_transition_count_mismatch_fails_closed(frozen_results, where):
    def change(payload):
        if where == "transitions":
            payload["transitions"] = [{"evaluation_outcome": "REPLICATED"}]
        else:
            payload["identity"]["opposed_to_aligned_transition_count"] = False if where == "boolean_count" else 1
    _mutate(frozen_results, "17", change)
    with pytest.raises(ValueError, match="transition count mismatch"):
        consolidation.build_consolidation()


@pytest.mark.parametrize("outcome", ["REPLICATED", "NOT_REPLICATED"])
def test_not_evaluable_is_neither_replication_nor_failure(outcome):
    result = consolidation.build_consolidation()
    assert result["not_evaluable_session_count"] == 5
    assert not any(s["outcome"] == outcome for s in result["sessions"])
    assert result["replicated_session_count"] == result["not_replicated_session_count"] == 0
    assert result["not_evaluable_is_not_failure"] is True
    assert result["not_evaluable_is_not_replication"] is True


def test_no_rates_percentages_or_pooling():
    result = consolidation.build_consolidation()
    def inspect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                assert not {"rate", "rates", "percentage", "percentages", "success"}.intersection(key.lower().split("_"))
                inspect(item)
        elif isinstance(value, list):
            for item in value:
                inspect(item)
    inspect(result)
    assert result["combined_session_count"] is None
    assert result["raw_pooling"] is False


def test_fixed_order_even_with_reversed_manifest(frozen_results, monkeypatch):
    monkeypatch.setattr(consolidation, "EXPECTED", dict(reversed(list(frozen_results.items()))))
    assert consolidation.build_consolidation()["session_ids"] == [14, 15, 16, 17, 18]


def test_accumulation_protocol_exact_sha():
    assert consolidation.PROTOCOL_SHA256 == "df868857d61205d9d95ff43e9259f7f8528e8feb66f0561869f20b4be78479b0"
    assert consolidation.build_consolidation()["protocol_sha256"] == consolidation.PROTOCOL_SHA256


def test_invalid_protocol_fails_closed(tmp_path, monkeypatch):
    validator = consolidation.protocol_validator
    path = tmp_path / "protocol.json"
    path.write_bytes(validator.PROTOCOL_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(validator, "PROTOCOL_PATH", path)
    with pytest.raises(ValueError, match="protocol SHA256 mismatch"):
        consolidation.build_consolidation()


def test_checkpoint_and_prior_evidence_remain_separate():
    result = consolidation.build_consolidation()
    policy = result["cohort_policy"]
    assert result["frozen_checkpoint_extended"] is False
    for key in (
        "frozen_10_session_checkpoint_remains_immutable",
        "sessions_11_to_13_remain_independent",
        "sessions_14_to_18_remain_a_separate_fixed_prospective_block",
        "sessions_14_to_18_are_not_appended_to_frozen_checkpoint",
        "sessions_14_to_18_are_not_merged_into_sessions_11_to_13",
        "no_retroactive_reclassification",
    ):
        assert policy[key] is True
    assert all(s["session_id"] not in (11, 12, 13) for s in result["sessions"])


@pytest.mark.parametrize("flag", consolidation.SAFETY_FALSE)
def test_unsafe_result_fails_closed(frozen_results, flag):
    _mutate(frozen_results, "18", lambda p: p["safety"].update({flag: True}))
    with pytest.raises(ValueError, match="unsafe flag"):
        consolidation.build_consolidation()


def test_session14_capture_failure_is_preserved_without_new_identity(frozen_results):
    result = consolidation.build_consolidation()
    assert result["sessions"][0]["reason"] == "CAPTURE_INTEGRITY_FAILURE"
    _mutate(frozen_results, "14", lambda p: p.update({"identity": {"raw_prospective_positional_identity": "VALIDATED"}}))
    with pytest.raises(ValueError, match="frozen capture-failure identity changed"):
        consolidation.build_consolidation()


def test_descriptive_safety_declarations():
    result = consolidation.build_consolidation()
    assert result["interpretation"] == "DESCRIPTIVE_ONLY"
    assert result["research_only"] is True
    for key in ("predictive_claim_allowed", "causal_claim_allowed", "operational_change_allowed",
                "threshold_optimization_allowed", "post_hoc_admission_gate_allowed"):
        assert result[key] is False


def test_output_does_not_overwrite_existing_evidence(tmp_path, monkeypatch):
    path = tmp_path / "output.json"
    path.write_text("preserved", encoding="utf-8")
    monkeypatch.setattr(consolidation, "OUTPUT", path)
    with pytest.raises(FileExistsError):
        consolidation.main()
    assert path.read_text(encoding="utf-8") == "preserved"
