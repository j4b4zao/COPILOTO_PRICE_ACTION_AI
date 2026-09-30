import hashlib
import json
from pathlib import Path


VALIDATOR_VERSION = (
    "RC1-PA-BOOK-INDEPENDENT-REPLICATION-"
    "ACCUMULATION-PROTOCOL-VALIDATOR"
)

PROTOCOL_PATH = Path(
    "pa_book_replication_accumulation_protocol_rc1_20260930.json"
)

EXPECTED_SHA256 = (
    "df868857d61205d9d95ff43e9259f7f8528e8feb66f0561869f20b4be78479b0"
)

EXPECTED_VERSION = (
    "RC1-PA-BOOK-INDEPENDENT-REPLICATION-ACCUMULATION-PROTOCOL"
)

SOURCE_PROTOCOL_SHA256 = (
    "53efb327f613934c483f6bec36ffe04bd"
    "98743b2973815f3b54ec2b84e91f01c"
)


def sha256_file(path):
    h = hashlib.sha256()

    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate():
    require(PROTOCOL_PATH.is_file(), "protocol file missing")

    actual_sha = sha256_file(PROTOCOL_PATH)

    require(
        actual_sha == EXPECTED_SHA256,
        "protocol SHA256 mismatch",
    )

    payload = json.loads(
        PROTOCOL_PATH.read_text(encoding="utf-8-sig")
    )

    require(
        payload.get("version") == EXPECTED_VERSION,
        "protocol version mismatch",
    )

    require(
        payload.get("status") == "FROZEN_BEFORE_FUTURE_COLLECTION",
        "protocol status mismatch",
    )

    require(
        payload.get("created_after_independent_sessions")
        == ["11", "12", "13"],
        "prior independent session identity mismatch",
    )

    prior = payload.get("prior_evidence")
    require(isinstance(prior, dict), "prior_evidence missing")

    require(prior.get("independent_session_count") == 3, "prior count mismatch")
    require(prior.get("evaluable_session_count") == 1, "prior evaluable mismatch")
    require(prior.get("replicated_session_count") == 1, "prior replicated mismatch")
    require(prior.get("not_replicated_session_count") == 0, "prior failure mismatch")
    require(prior.get("not_evaluable_session_count") == 2, "prior NE mismatch")
    require(prior.get("session_11") == "NOT_EVALUABLE", "session 11 mismatch")
    require(prior.get("session_12") == "NOT_EVALUABLE", "session 12 mismatch")
    require(prior.get("session_13") == "REPLICATED", "session 13 mismatch")
    require(prior.get("interpretation") == "DESCRIPTIVE_ONLY", "prior interpretation mismatch")

    hypothesis = payload.get("frozen_hypothesis")
    require(isinstance(hypothesis, dict), "frozen_hypothesis missing")

    require(
        hypothesis.get("name") == "PA_PERSISTENT_BOOK_OPPOSED_NONE_ALIGNED",
        "hypothesis name mismatch",
    )

    require(
        hypothesis.get("source_protocol_sha256") == SOURCE_PROTOCOL_SHA256,
        "source protocol SHA mismatch",
    )

    require(
        hypothesis.get("evaluation_unit")
        == "formal_OPPOSED_to_ALIGNED_transition",
        "evaluation unit mismatch",
    )

    require(
        hypothesis.get("hypothesis_redefinition_allowed") is False,
        "hypothesis redefinition unexpectedly allowed",
    )

    block = payload.get("future_block")
    require(isinstance(block, dict), "future_block missing")

    require(
        block.get("session_ids") == ["14", "15", "16", "17", "18"],
        "future session IDs mismatch",
    )

    require(block.get("planned_session_count") == 5, "planned count mismatch")
    require(block.get("fixed_before_session_14") is True, "block not frozen")
    require(block.get("sessions_evaluated_independently") is True, "independence disabled")
    require(block.get("automatic_extension_beyond_session_18") is False, "automatic extension enabled")
    require(block.get("early_stop_for_apparent_success") is False, "success early-stop enabled")
    require(block.get("early_stop_for_apparent_failure") is False, "failure early-stop enabled")

    outcomes = payload.get("session_outcomes")
    require(isinstance(outcomes, dict), "session_outcomes missing")

    require(
        outcomes.get("allowed")
        == ["REPLICATED", "NOT_REPLICATED", "NOT_EVALUABLE"],
        "allowed outcomes mismatch",
    )

    require(
        outcomes.get("not_evaluable_is_not_failure") is True,
        "NOT_EVALUABLE can be treated as failure",
    )

    require(
        outcomes.get("not_evaluable_is_not_replication") is True,
        "NOT_EVALUABLE can be treated as replication",
    )

    accumulation = payload.get("accumulation_policy")
    require(isinstance(accumulation, dict), "accumulation_policy missing")

    require(accumulation.get("preserve_each_session_outcome") is True, "session outcomes not preserved")
    require(accumulation.get("pool_raw_samples_across_sessions") is False, "raw pooling enabled")
    require(accumulation.get("pool_sessions_into_single_cohort") is False, "cohort pooling enabled")
    require(accumulation.get("combined_session_count") is None, "combined session count introduced")
    require(accumulation.get("replication_rate_over_all_sessions") is None, "all-session replication rate introduced")
    require(accumulation.get("replication_rate_over_evaluable_sessions") is None, "evaluable replication rate introduced")
    require(accumulation.get("no_percentage_success_claim") is True, "percentage success claim enabled")
    require(accumulation.get("report_descriptive_counts_only") is True, "non-descriptive accumulation enabled")
    require(accumulation.get("report_transition_counts_separately") is True, "transition reporting changed")
    require(accumulation.get("do_not_reclassify_prior_sessions") is True, "prior reclassification enabled")

    interpretation = payload.get("interpretation_policy")
    require(isinstance(interpretation, dict), "interpretation_policy missing")

    require(interpretation.get("descriptive_only") is True, "descriptive_only disabled")
    require(interpretation.get("predictive_validation_allowed") is False, "predictive validation enabled")
    require(interpretation.get("causal_claim_allowed") is False, "causal claims enabled")
    require(interpretation.get("operational_promotion_allowed") is False, "operational promotion enabled")
    require(interpretation.get("threshold_optimization_allowed") is False, "threshold optimization enabled")
    require(interpretation.get("post_hoc_admission_gate_allowed") is False, "post-hoc gate enabled")
    require(interpretation.get("single_replication_is_not_predictive_validation") is True, "single replication policy changed")
    require(interpretation.get("single_failure_is_not_refutation") is True, "single failure policy changed")
    require(interpretation.get("future_block_does_not_modify_prior_evidence") is True, "prior evidence mutation enabled")

    cohort = payload.get("cohort_policy")
    require(isinstance(cohort, dict), "cohort_policy missing")

    require(cohort.get("frozen_10_session_checkpoint_remains_immutable") is True, "checkpoint mutability changed")
    require(cohort.get("sessions_11_to_13_remain_independent") is True, "sessions 11-13 independence changed")
    require(cohort.get("sessions_14_to_18_are_new_independent_prospective_evidence") is True, "future evidence independence changed")
    require(cohort.get("sessions_14_to_18_are_not_appended_to_frozen_checkpoint") is True, "future sessions appended to checkpoint")
    require(cohort.get("sessions_14_to_18_are_not_merged_into_sessions_11_to_13") is True, "future sessions merged into prior evidence")
    require(cohort.get("no_retroactive_reclassification") is True, "retroactive reclassification enabled")

    safety = payload.get("safety")
    require(isinstance(safety, dict), "safety missing")

    require(safety.get("research_only") is True, "research_only disabled")
    require(safety.get("descriptive_only") is True, "safety descriptive_only disabled")

    required_false = (
        "score_changed",
        "risk_changed",
        "decision_changed",
        "alert_changed",
        "execution_changed",
        "operational_logic_changed",
        "rc17_changed",
        "threshold_changed",
        "canonical_conflict_redefined",
        "checkpoint_extended",
        "post_hoc_gate_added",
        "predictive_claim_allowed",
    )

    for key in required_false:
        require(
            safety.get(key) is False,
            f"unsafe policy enabled: {key}",
        )

    return {
        "validator_version": VALIDATOR_VERSION,
        "protocol_path": str(PROTOCOL_PATH),
        "expected_sha256": EXPECTED_SHA256,
        "actual_sha256": actual_sha,
        "protocol_sha256_exact": True,
        "protocol_version_exact": True,
        "prior_evidence_exact": True,
        "frozen_hypothesis_exact": True,
        "future_block_exact": True,
        "outcome_policy_exact": True,
        "accumulation_policy_exact": True,
        "interpretation_policy_exact": True,
        "cohort_policy_exact": True,
        "safety_policy_exact": True,
        "future_collection_block": ["14", "15", "16", "17", "18"],
        "status": "PASS",
        "future_collection_authorization": "ACCUMULATION_PROTOCOL_VALIDATED_ONLY",
    }


def main():
    result = validate()

    for key, value in result.items():
        print(f"{key} = {value}")


if __name__ == "__main__":
    main()
