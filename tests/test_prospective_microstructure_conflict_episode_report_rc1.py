from copy import deepcopy

import pytest

from tools.prospective_microstructure_conflict_episode_report import (
    VERSION,
    _episodes,
    _is_conflict,
    _predominant,
    _session_report,
    _safety,
)


def _sample(
    *,
    timestamp,
    state="CONFIRMED",
    conflict_count=0,
    pa="BUY",
    flow="BUY",
    book="BUY",
    book_available=True,
):
    return {
        "timestamp": timestamp,
        "price_action_bias": pa,
        "flow_direction": flow,
        "book_available": book_available,
        "book_direction": book,
        "state": state,
        "conflict_count": conflict_count,
    }


def test_version_is_rc1():
    assert VERSION == (
        "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-EPISODES"
    )


def test_contiguous_conflicts_form_one_episode():
    samples = [
        _sample(
            timestamp="2026-09-22T10:00:00",
            state="CONFLICT",
        ),
        _sample(
            timestamp="2026-09-22T10:00:01",
            state="CONFLICT",
        ),
        _sample(
            timestamp="2026-09-22T10:00:02",
        ),
    ]

    episodes = _episodes(samples)

    assert len(episodes) == 1
    assert episodes[0]["start_sample_index"] == 0
    assert episodes[0]["end_sample_index"] == 1
    assert episodes[0]["sample_count"] == 2


def test_non_conflict_sample_splits_episodes():
    samples = [
        _sample(
            timestamp="2026-09-22T10:00:00",
            state="CONFLICT",
        ),
        _sample(
            timestamp="2026-09-22T10:00:01",
        ),
        _sample(
            timestamp="2026-09-22T10:00:02",
            conflict_count=1,
        ),
    ]

    episodes = _episodes(samples)

    assert len(episodes) == 2
    assert episodes[0]["sample_count"] == 1
    assert episodes[1]["sample_count"] == 1


def test_session_without_conflict_has_zero_episodes():
    samples = [
        _sample(timestamp="2026-09-22T10:00:00"),
        _sample(timestamp="2026-09-22T10:00:01"),
    ]

    report = _session_report(samples, expected_conflicts=0)

    assert report["conflict_samples"] == 0
    assert report["conflict_episodes"] == 0
    assert report["longest_episode_samples"] == 0
    assert report["mean_episode_samples"] == 0.0
    assert report["episodes"] == []


def test_predominant_direction_uses_majority():
    assert _predominant(["BUY", "BUY", "SELL"]) == "BUY"


def test_predominant_direction_tie_is_mixed():
    assert _predominant(["BUY", "SELL"]) == "MIXED"


def test_none_and_unavailable_are_not_inferred():
    samples = [
        _sample(
            timestamp="2026-09-22T10:00:00",
            state="CONFLICT",
            flow="NONE",
            book="UNAVAILABLE",
        ),
        _sample(
            timestamp="2026-09-22T10:00:01",
            state="CONFLICT",
            flow="NONE",
            book="UNAVAILABLE",
        ),
    ]

    episode = _episodes(samples)[0]

    assert episode["predominant_flow_direction"] == "NONE"
    assert episode["predominant_book_direction"] == "UNAVAILABLE"
    assert episode["flow_direction_counts"] == {"NONE": 2}
    assert episode["book_direction_counts"] == {"UNAVAILABLE": 2}


def test_conflict_count_sum_and_max_are_correct():
    samples = [
        _sample(
            timestamp="2026-09-22T10:00:00",
            conflict_count=1,
        ),
        _sample(
            timestamp="2026-09-22T10:00:01",
            conflict_count=3,
        ),
    ]

    episode = _episodes(samples)[0]

    assert episode["conflict_count_sum"] == 4
    assert episode["max_conflict_count"] == 3


def test_state_conflict_counts_even_with_zero_conflict_count():
    sample = _sample(
        timestamp="2026-09-22T10:00:00",
        state="CONFLICT",
        conflict_count=0,
    )

    assert _is_conflict(sample) is True


def test_positive_conflict_count_counts_even_without_conflict_state():
    sample = _sample(
        timestamp="2026-09-22T10:00:00",
        state="CONFIRMED",
        conflict_count=1,
    )

    assert _is_conflict(sample) is True


def test_conflict_count_mismatch_fails_closed():
    samples = [
        _sample(
            timestamp="2026-09-22T10:00:00",
            state="CONFLICT",
        ),
    ]

    with pytest.raises(
        ValueError,
        match="prospective conflict count differs from session report",
    ):
        _session_report(samples, expected_conflicts=0)


def test_input_is_not_mutated():
    samples = [
        _sample(
            timestamp="2026-09-22T10:00:00",
            state="CONFLICT",
        ),
        _sample(
            timestamp="2026-09-22T10:00:01",
        ),
    ]

    original = deepcopy(samples)

    _episodes(samples)

    assert samples == original


def test_safety_flags_are_passive():
    safety = _safety()

    assert safety["research_only"] is True
    assert safety["observational_only"] is True
    assert safety["predictive_claim_allowed"] is False
    assert safety["score_influence_allowed"] is False
    assert safety["risk_influence_allowed"] is False
    assert safety["decision_influence_allowed"] is False
    assert safety["alert_influence_allowed"] is False
    assert safety["order_execution_allowed"] is False
    assert safety["promotion_allowed"] is False


def test_episode_metrics_match_controlled_coverage_semantics():
    samples = [
        _sample(
            timestamp="2026-09-22T10:00:00",
            state="CONFLICT",
        ),
        _sample(
            timestamp="2026-09-22T10:00:01",
            conflict_count=1,
        ),
        _sample(
            timestamp="2026-09-22T10:00:02",
        ),
        _sample(
            timestamp="2026-09-22T10:00:03",
            state="CONFLICT",
        ),
    ]

    report = _session_report(samples, expected_conflicts=3)

    assert report["samples"] == 4
    assert report["conflict_samples"] == 3
    assert report["conflict_episodes"] == 2
    assert report["longest_episode_samples"] == 2
    assert report["mean_episode_samples"] == 1.5


def test_episode_uses_sample_index_when_timestamp_is_unavailable():
    samples = [
        _sample(timestamp="2026-09-22T10:00:00"),
        _sample(timestamp="2026-09-22T10:00:01", state="CONFLICT"),
        _sample(timestamp="2026-09-22T10:00:02", state="CONFLICT"),
    ]

    for sample in samples:
        sample.pop("timestamp")

    episode = _episodes(samples)[0]

    assert episode["episode_index"] == 1
    assert episode["start_sample_index"] == 1
    assert episode["end_sample_index"] == 2
    assert episode["start_timestamp"] is None
    assert episode["end_timestamp"] is None
    assert episode["temporal_reference"] == "SAMPLE_INDEX_ONLY"

def test_structural_evidence_is_only_reported_when_present():
    first = _sample(
        timestamp="2026-09-22T10:00:00",
        state="CONFLICT",
    )
    second = _sample(
        timestamp="2026-09-22T10:00:01",
        state="CONFLICT",
    )

    without = _episodes([first, second])[0]

    assert "structural_evidence_counts" not in without

    first["structural_evidence"] = "ALIGNED"
    second["structural_evidence"] = "CONFLICT"

    with_structural = _episodes([first, second])[0]

    assert with_structural["structural_evidence_counts"] == {
        "ALIGNED": 1,
        "CONFLICT": 1,
    }


def test_invalid_conflict_count_fails_closed():
    sample = _sample(
        timestamp="2026-09-22T10:00:00",
        conflict_count=-1,
    )

    with pytest.raises(
        ValueError,
        match="invalid conflict count",
    ):
        _is_conflict(sample)