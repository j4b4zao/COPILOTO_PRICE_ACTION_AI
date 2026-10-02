import copy
import json
from pathlib import Path
import pytest
from tools import rc17_sideways_to_directional_evolution_protocol_validator as validator


def frozen():
    return json.loads(validator.PROTOCOL_PATH.read_text(encoding="utf-8"))


def test_frozen_real_protocol_passes():
    r = validator.validate()
    assert r["status"] == "PASS"
    assert r["planned_sessions"] == [19,20,21,22,23]
    assert r["planned_session_count"] == 5
    assert r["protocol_sha256"] == "2a278e7c4c438098d9ce167a778f7386a09b341a555a73e322598215150ebdb3"


@pytest.mark.parametrize("section,key,value", [
    (None,"version","other"), (None,"status","UNFROZEN"),
    ("future_block","session_ids",[19,20,21,22,24]),
    ("future_block","session_ids",[11,12,13,14,15]),
    ("future_block","planned_session_count",6),
    ("future_block","planned_session_count",True),
    ("future_block","no_auto_extension",False),
    ("future_block","no_early_stop",False),
    ("future_block","sessions_independent",False),
    ("future_block","raw_pooling_for_inference",True),
    ("capture_policy","market_structure_observability_enabled",False),
    ("capture_policy","retrospective_reconstruction_allowed",True),
    ("capture_policy","readiness_and_warmup_unchanged",False),
    ("diagnostic_capture_policy","included_in_future_cohort",True),
    ("diagnostic_capture_policy","classified_as_session19",True),
    ("diagnostic_capture_policy","prospective_evidence",True),
    ("diagnostic_capture_policy","numeric_parameters_derived_from_capture",True),
    ("cohort_policy","frozen10_immutable",False),
    ("cohort_policy","sessions11_13_remain_independent",False),
    ("cohort_policy","sessions14_18_remain_closed_fixed_block",False),
    ("cohort_policy","diagnostic_capture01_excluded",False),
    ("cohort_policy","cohorts_combined",True),
    ("cohort_policy","previous_not_evaluable_reclassified",True),
    ("interpretation","descriptive_only",False),
    ("interpretation","predictive_validation",True),
    ("interpretation","causal_validation",True),
    ("interpretation","operational_promotion",True),
    ("interpretation","threshold_optimization",True),
    ("interpretation","success_percentage_allowed",True),
    ("session_classification","no_transition_is_failure",True),
    ("session_classification","no_transition_is_not_replicated",True),
    ("session_classification","no_transition_is_invalid",True),
    ("event_policy","transition_required",True),
    ("event_policy","alternative_trend_rule_allowed",True),
    ("chronology","transitions_across_missing_invalid_samples_allowed",True),
    ("integrity","diagnostic_unavailable_count",1),
    ("integrity","history_unchanged_false_count",1),
    ("integrity","failure_classification","NOT_REPLICATED"),
])
def test_every_changed_rule_fails_closed(section,key,value):
    p = frozen()
    target = p if section is None else p[section]
    target[key] = value
    with pytest.raises(ValueError): validator.validate_payload(p)


@pytest.mark.parametrize("key", list(frozen()["prohibited_thresholds"]))
def test_no_numeric_threshold_allowed(key):
    p = frozen()
    p["prohibited_thresholds"][key] = 1
    with pytest.raises(ValueError): validator.validate_payload(p)


@pytest.mark.parametrize("key", ["score_influence","risk_influence","decision_influence","alert_influence","execution_influence","rc17_changed","price_action_changed","collector_changed","operational_logic_changed"])
def test_no_operational_influence(key):
    p = frozen();p["safety"][key] = True
    with pytest.raises(ValueError): validator.validate_payload(p)


def test_missing_file_and_divergent_sha(tmp_path):
    with pytest.raises(ValueError, match="missing"): validator.validate(tmp_path/"missing.json")
    path = tmp_path/"protocol.json"
    path.write_bytes(validator.PROTOCOL_PATH.read_bytes()+b"\n")
    with pytest.raises(ValueError, match="SHA256"): validator.validate(path)


def test_missing_or_extra_content_fails_closed():
    p=frozen();del p["safety"]
    with pytest.raises(ValueError): validator.validate_payload(p)
    p=frozen();p["new_threshold"]=5
    with pytest.raises(ValueError): validator.validate_payload(p)


def test_no_transition_is_valid_descriptive_result_and_unknown_is_preserved():
    p=frozen()
    assert p["session_classification"]["all_sideways_none_with_valid_integrity"] == "NO_DIRECTIONAL_TRANSITION_OBSERVED"
    assert p["event_policy"]["transition_required"] is False
    assert p["chronology"]["unknown_preserved_as_separate_state"] is True
    assert len(p["observed_transitions"])==9
    assert "closed_history_sha256" in p["structural_snapshot_fields"]


def test_validation_does_not_mutate_payload():
    p=frozen();before=copy.deepcopy(p)
    validator.validate_payload(p)
    assert p==before
