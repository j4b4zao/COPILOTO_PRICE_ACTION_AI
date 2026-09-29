from __future__ import annotations

import copy

import pytest

from tools import (
    prospective_microstructure_pa_book_structural_replication_evaluator
    as evaluator,
)


def _sample(
    pa: str,
    book: str,
    conflict_count: int = 0,
) -> dict:
    return {
        "price_action_bias": pa,
        "book_direction": book,
        "conflict_count": conflict_count,
    }


def _payload(samples: list[dict]) -> dict:
    return {
        "prospective_microstructure": {
            "samples": samples,
            "captured_samples": len(samples),
            "source_analyzable_samples": len(samples),
            "sample_count_matches_source": True,
        }
    }


def test_replicated_buy_path():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
            _sample("BUY", "SELL", 1),
            _sample("BUY", "NONE"),
            _sample("BUY", "NONE"),
            _sample("BUY", "BUY"),
            _sample("BUY", "BUY"),
        ]
    )

    report = evaluator.evaluate_payload(payload)

    assert report["outcome"] == "REPLICATED"
    assert (
        report["identity"][
            "opposed_to_aligned_transition_count"
        ]
        == 1
    )

    transition = report["transitions"][0]

    assert transition["previous_pair"] == "BUY_SELL"
    assert transition["following_pair"] == "BUY_BUY"
    assert transition["gap_samples"] == 2
    assert transition["replicated"] is True
    assert all(transition["conditions"].values())


def test_replicated_sell_path_is_symmetric():
    payload = _payload(
        [
            _sample("SELL", "BUY", 1),
            _sample("SELL", "NONE"),
            _sample("SELL", "NONE"),
            _sample("SELL", "SELL"),
        ]
    )

    report = evaluator.evaluate_payload(payload)

    assert report["outcome"] == "REPLICATED"

    transition = report["transitions"][0]

    assert transition["previous_pair"] == "SELL_BUY"
    assert transition["following_pair"] == "SELL_SELL"
    assert transition["start_pa_direction"] == "SELL"
    assert transition["end_pa_direction"] == "SELL"


def test_not_replicated_when_pa_changes_in_gap():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
            _sample("SELL", "NONE"),
            _sample("BUY", "NONE"),
            _sample("BUY", "BUY"),
        ]
    )

    report = evaluator.evaluate_payload(payload)

    assert report["outcome"] == "NOT_REPLICATED"

    transition = report["transitions"][0]

    assert (
        transition["conditions"][
            "all_intermediate_pa_directions_equal_start_pa_direction"
        ]
        is False
    )


def test_not_replicated_when_pa_direction_changes_at_end():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
            _sample("BUY", "NONE"),
            _sample("SELL", "SELL"),
        ]
    )

    report = evaluator.evaluate_payload(payload)

    assert report["outcome"] == "NOT_REPLICATED"

    transition = report["transitions"][0]

    assert (
        transition["conditions"][
            "same_pa_direction_from_opposed_end_to_aligned_start"
        ]
        is False
    )


def test_not_replicated_without_intermediate_sample():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
            _sample("BUY", "BUY"),
        ]
    )

    report = evaluator.evaluate_payload(payload)

    assert report["outcome"] == "NOT_REPLICATED"

    transition = report["transitions"][0]

    assert transition["gap_samples"] == 0
    assert (
        transition["conditions"][
            "at_least_one_intermediate_sample"
        ]
        is False
    )


def test_not_evaluable_without_target_transition():
    payload = _payload(
        [
            _sample("BUY", "BUY"),
            _sample("BUY", "NONE"),
            _sample("BUY", "BUY"),
        ]
    )

    report = evaluator.evaluate_payload(payload)

    assert report["outcome"] == "NOT_EVALUABLE"
    assert (
        report["reason"]
        == "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION"
    )
    assert report["transitions"] == []


def test_invalid_direction_fails_closed():
    payload = _payload(
        [
            _sample("BUY", "INVALID"),
        ]
    )

    with pytest.raises(ValueError):
        evaluator.evaluate_payload(payload)


def test_missing_conflict_count_fails_closed():
    payload = _payload(
        [
            {
                "price_action_bias": "BUY",
                "book_direction": "SELL",
            }
        ]
    )

    with pytest.raises(ValueError):
        evaluator.evaluate_payload(payload)


def test_captured_count_mismatch_fails_closed():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
        ]
    )

    payload["prospective_microstructure"][
        "captured_samples"
    ] = 2

    with pytest.raises(ValueError):
        evaluator.evaluate_payload(payload)


def test_source_count_mismatch_fails_closed():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
        ]
    )

    payload["prospective_microstructure"][
        "source_analyzable_samples"
    ] = 2

    with pytest.raises(ValueError):
        evaluator.evaluate_payload(payload)


def test_sample_count_matches_source_must_be_true():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
        ]
    )

    payload["prospective_microstructure"][
        "sample_count_matches_source"
    ] = False

    with pytest.raises(ValueError):
        evaluator.evaluate_payload(payload)


def test_input_is_not_mutated():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
            _sample("BUY", "NONE"),
            _sample("BUY", "BUY"),
        ]
    )

    before = copy.deepcopy(payload)

    evaluator.evaluate_payload(payload)

    assert payload == before


def test_safety_flags_are_fixed():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
            _sample("BUY", "NONE"),
            _sample("BUY", "BUY"),
        ]
    )

    report = evaluator.evaluate_payload(payload)

    safety = report["safety"]

    assert safety["research_only"] is True
    assert safety["descriptive_only"] is True

    for field in (
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
        "post_hoc_gate_added",
    ):
        assert safety[field] is False
