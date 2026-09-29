from __future__ import annotations

import hashlib
import json
from pathlib import Path


VERSION = (
    "RC1-PA-BOOK-OPPOSED-TO-ALIGNED-"
    "PROSPECTIVE-REPLICATION-PROTOCOL-VALIDATOR"
)

PROTOCOL = Path(
    "pa_book_opposed_to_aligned_"
    "prospective_replication_protocol_rc1_20260929.json"
)

EXPECTED_SHA256 = (
    "53EFB327F613934C483F6BEC36FFE04BD"
    "98743B2973815F3B54EC2B84E91F01C"
).lower()

EXPECTED_VERSION = (
    "RC1-PA-BOOK-OPPOSED-TO-ALIGNED-"
    "PROSPECTIVE-REPLICATION-PROTOCOL"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:

    print(f"validator_version = {VERSION}")
    print("fail_closed = True")
    print("research_only = True")
    print()

    require(
        PROTOCOL.is_file(),
        f"PROTOCOL_NOT_FOUND: {PROTOCOL}",
    )

    actual_sha = sha256(PROTOCOL)

    print(f"protocol_path = {PROTOCOL}")
    print(f"expected_sha256 = {EXPECTED_SHA256}")
    print(f"actual_sha256   = {actual_sha}")

    require(
        actual_sha == EXPECTED_SHA256,
        "PROTOCOL_SHA256_MISMATCH",
    )

    try:
        payload = json.loads(
            PROTOCOL.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise RuntimeError(
            f"PROTOCOL_JSON_INVALID: {exc}"
        ) from exc

    require(
        payload.get("version") == EXPECTED_VERSION,
        "PROTOCOL_VERSION_MISMATCH",
    )

    require(
        payload.get("status")
        == "FROZEN_BEFORE_FUTURE_COLLECTION",
        "PROTOCOL_NOT_FROZEN",
    )

    source = payload.get("created_from", {})

    require(
        source.get("checkpoint")
        == (
            "prospective_microstructure_conflict_"
            "10session_checkpoint_20260926.json"
        ),
        "CHECKPOINT_IDENTITY_MISMATCH",
    )

    require(
        source.get("checkpoint_session_count") == 10,
        "FROZEN_CHECKPOINT_SESSION_COUNT_MISMATCH",
    )

    require(
        source.get(
            "observed_opposed_to_aligned_transition_count"
        ) == 2,
        "FROZEN_TRANSITION_COUNT_MISMATCH",
    )

    scope = payload.get("research_scope", {})

    required_true = (
        "research_only",
        "descriptive_only",
    )

    for key in required_true:
        require(
            scope.get(key) is True,
            f"SAFETY_FLAG_NOT_TRUE: {key}",
        )

    required_false = (
        "operational_logic_changed",
        "score_changed",
        "risk_changed",
        "decision_changed",
        "alert_changed",
        "execution_changed",
        "rc17_changed",
        "threshold_changed",
        "canonical_conflict_redefined",
        "checkpoint_extended",
        "predictive_claim_allowed",
    )

    for key in required_false:
        require(
            scope.get(key) is False,
            f"SAFETY_FLAG_NOT_FALSE: {key}",
        )

    hypothesis = payload.get("frozen_hypothesis", {})

    require(
        hypothesis.get("name")
        == "PA_PERSISTENT_BOOK_OPPOSED_NONE_ALIGNED",
        "FROZEN_HYPOTHESIS_NAME_MISMATCH",
    )

    replication = hypothesis.get(
        "replication_condition", {}
    )

    expected_replication = {
        "same_pa_direction_from_opposed_end_to_aligned_start":
            True,
        "at_least_one_intermediate_sample":
            True,
        "all_intermediate_pa_directions_equal_start_pa_direction":
            True,
        "at_least_one_intermediate_book_none":
            True,
        "no_intermediate_book_direction_opposite_to_start_pa_direction_after_opposed_run_end":
            True,
    }

    for key, expected in expected_replication.items():
        require(
            replication.get(key) is expected,
            f"REPLICATION_CONDITION_MISMATCH: {key}",
        )

    nonreq = payload.get(
        "explicit_non_requirements", {}
    )

    expected_nonrequirements = (
        "recent_delta_threshold",
        "acceleration_threshold",
        "imbalance_threshold",
        "spread_threshold",
        "minimum_gap_samples",
        "maximum_gap_samples",
        "minimum_gap_seconds",
        "maximum_gap_seconds",
        "candle_range_threshold",
        "candle_body_threshold",
        "volume_threshold",
    )

    for key in expected_nonrequirements:
        require(
            key in nonreq and nonreq[key] is None,
            f"POST_HOC_THRESHOLD_PRESENT: {key}",
        )

    future = payload.get("future_evaluation", {})

    require(
        future.get("unit")
        == "formal_OPPOSED_to_ALIGNED_transition",
        "FUTURE_EVALUATION_UNIT_MISMATCH",
    )

    require(
        future.get("outcomes")
        == [
            "REPLICATED",
            "NOT_REPLICATED",
            "NOT_EVALUABLE",
        ],
        "OUTCOME_SCHEMA_MISMATCH",
    )

    cohort = payload.get("cohort_policy", {})

    for key in (
        "frozen_10_session_checkpoint_remains_immutable",
        "sessions_11_and_12_remain_independent",
        "future_sessions_are_not_appended_to_frozen_checkpoint",
        "future_sessions_are_evaluated_as_independent_prospective_replication",
        "no_retroactive_reclassification",
    ):
        require(
            cohort.get(key) is True,
            f"COHORT_POLICY_VIOLATION: {key}",
        )

    interpretation = payload.get(
        "interpretation_policy", {}
    )

    for key in (
        "single_future_replication_is_not_predictive_validation",
        "single_future_failure_is_not_refutation",
        "no_operational_promotion_from_this_protocol",
        "no_threshold_optimization_after_observation",
        "no_post_hoc_admission_gate",
    ):
        require(
            interpretation.get(key) is True,
            f"INTERPRETATION_POLICY_VIOLATION: {key}",
        )

    print()
    print("PROTOCOL_SHA256_EXACT = True")
    print("PROTOCOL_VERSION_EXACT = True")
    print("FROZEN_CHECKPOINT_IDENTITY_EXACT = True")
    print("SAFETY_POLICY_EXACT = True")
    print("REPLICATION_CONDITION_EXACT = True")
    print("NO_THRESHOLDS_EXACT = True")
    print("COHORT_POLICY_EXACT = True")
    print("INTERPRETATION_POLICY_EXACT = True")
    print()
    print("STATUS = PASS")
    print(
        "FUTURE_COLLECTION_AUTHORIZATION = "
        "PROTOCOL_VALIDATED_ONLY"
    )


if __name__ == "__main__":
    main()
