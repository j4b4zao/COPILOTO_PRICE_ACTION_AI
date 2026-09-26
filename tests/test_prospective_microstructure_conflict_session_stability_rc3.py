from copy import deepcopy

import pytest

from tools.prospective_microstructure_conflict_session_stability import (
    BUCKETS,
    EXPECTED_INPUT_VERSION,
    HORIZONS,
    MIRRORS,
    SAFETY,
    STATUS,
    VERSION,
    _bucket,
    _build_session_matrix,
    _collect,
    _cross_session_descriptive,
    _direction,
    _mirror_name,
    _session_horizon_summary,
    _validate_input,
    _validate_safety,
)


def _observation(
    *,
    available=True,
    side="PRICE_ACTION",
    raw=10.0,
    pa_signed=10.0,
    book_signed=-10.0,
):
    if not available:
        return {
            "available": False,
            "reason": "SESSION_END",
        }

    return {
        "available": True,
        "observed_side": side,
        "raw_displacement": raw,
        "price_action_signed_displacement": pa_signed,
        "book_signed_displacement": book_signed,
    }


def _episode(
    *,
    episode_index=1,
    sample_count=1,
    pa="BUY",
    book="SELL",
    side="PRICE_ACTION",
    raw=10.0,
    pa_signed=10.0,
    book_signed=-10.0,
):
    return {
        "episode_index": episode_index,
        "sample_count": sample_count,
        "predominant_price_action_direction": pa,
        "predominant_flow_direction": "NONE",
        "predominant_book_direction": book,
        "followthrough": {
            str(horizon): _observation(
                side=side,
                raw=raw,
                pa_signed=pa_signed,
                book_signed=book_signed,
            )
            for horizon in HORIZONS
        },
    }


def _session(
    *episodes,
    path="session.json",
    sha_char="a",
):
    return {
        "path": path,
        "sha256": sha_char * 64,
        "samples": 100,
        "conflict_samples": sum(
            episode["sample_count"]
            for episode in episodes
        ),
        "conflict_episodes": len(episodes),
        "alignment_validated": True,
        "episodes": list(episodes),
    }


def _payload(*sessions):
    return {
        "version": EXPECTED_INPUT_VERSION,
        "status": STATUS,
        "eligible_sessions": len(sessions),
        "rejected_sessions": 0,
        "horizons_in_samples": list(HORIZONS),
        "sessions": list(sessions),
        "audit_stability": "INCONSISTENT",
        "audit_recommendation": "REVIEW_STABILITY",
        **SAFETY,
    }


def test_version_is_rc3():
    assert VERSION == (
        "RC3-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-SESSION-STABILITY"
    )


def test_expected_input_is_rc1_followthrough():
    assert EXPECTED_INPUT_VERSION == (
        "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-PRICE-FOLLOWTHROUGH"
    )


def test_status_is_descriptive_only():
    assert STATUS == "DESCRIPTIVE_ONLY"


def test_horizons_are_frozen():
    assert HORIZONS == (1, 5, 10, 20)


def test_mirrors_are_frozen():
    assert MIRRORS == (
        ("BUY", "SELL"),
        ("SELL", "BUY"),
    )


def test_duration_buckets_are_frozen():
    assert BUCKETS == (
        "SINGLE",
        "PERSISTENT",
    )


def test_bucket_semantics_are_frozen():
    assert _bucket(1) == "SINGLE"
    assert _bucket(2) == "PERSISTENT"
    assert _bucket(20) == "PERSISTENT"


def test_mirror_names_are_deterministic():
    assert (
        _mirror_name("BUY", "SELL")
        == "PA_BUY_BOOK_SELL"
    )

    assert (
        _mirror_name("SELL", "BUY")
        == "PA_SELL_BOOK_BUY"
    )


def test_safety_flags_remain_passive():
    assert SAFETY["research_only"] is True
    assert SAFETY["observational_only"] is True

    assert SAFETY["predictive_claim_allowed"] is False
    assert SAFETY["score_influence_allowed"] is False
    assert SAFETY["risk_influence_allowed"] is False
    assert SAFETY["decision_influence_allowed"] is False
    assert SAFETY["alert_influence_allowed"] is False
    assert SAFETY["order_execution_allowed"] is False
    assert SAFETY["promotion_allowed"] is False


def test_validate_safety_accepts_exact_invariants():
    _validate_safety(
        dict(SAFETY)
    )


@pytest.mark.parametrize(
    "flag",
    [
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
    ],
)
def test_operational_flags_cannot_be_enabled(flag):
    payload = dict(SAFETY)
    payload[flag] = True

    with pytest.raises(
        ValueError,
        match="Safety invariant failed",
    ):
        _validate_safety(payload)


def test_research_only_cannot_be_disabled():
    payload = dict(SAFETY)
    payload["research_only"] = False

    with pytest.raises(
        ValueError,
        match="Safety invariant failed",
    ):
        _validate_safety(payload)


def test_observational_only_cannot_be_disabled():
    payload = dict(SAFETY)
    payload["observational_only"] = False

    with pytest.raises(
        ValueError,
        match="Safety invariant failed",
    ):
        _validate_safety(payload)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("BUY", "BUY"),
        ("buy", "BUY"),
        ("SELL", "SELL"),
        ("sell", "SELL"),
        ("NONE", "NONE"),
        ("none", "NONE"),
        ("MIXED", "MIXED"),
        ("mixed", "MIXED"),
    ],
)
def test_direction_accepts_valid_values(
    value,
    expected,
):
    assert (
        _direction(value, "field")
        == expected
    )


@pytest.mark.parametrize(
    "value",
    [
        None,
        1,
        True,
        "UP",
        "DOWN",
        "UNKNOWN",
    ],
)
def test_direction_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        _direction(
            value,
            "field",
        )


def test_validate_input_accepts_controlled_payload():
    payload = _payload(
        _session(
            _episode(),
        )
    )

    _validate_input(payload)


def test_wrong_version_fails_closed():
    payload = _payload()
    payload["version"] = "WRONG"

    with pytest.raises(
        ValueError,
        match="Expected input version",
    ):
        _validate_input(payload)


def test_wrong_status_fails_closed():
    payload = _payload()
    payload["status"] = "PROMOTED"

    with pytest.raises(
        ValueError,
        match="Input status",
    ):
        _validate_input(payload)


def test_horizons_cannot_change():
    payload = _payload()
    payload["horizons_in_samples"] = [
        1,
        5,
        10,
    ]

    with pytest.raises(
        ValueError,
        match="horizons_in_samples",
    ):
        _validate_input(payload)


def test_session_count_must_match_eligible():
    payload = _payload(
        _session(),
    )

    payload["eligible_sessions"] = 2

    with pytest.raises(
        ValueError,
        match="sessions length",
    ):
        _validate_input(payload)


def test_collect_accepts_buy_sell_opposition():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="SELL",
            )
        )
    )

    _validate_input(payload)

    rows, sessions = _collect(payload)

    assert len(rows) == 4
    assert len(sessions) == 1

    assert {
        row["mirror"]
        for row in rows
    } == {
        "PA_BUY_BOOK_SELL"
    }


def test_collect_accepts_sell_buy_opposition():
    payload = _payload(
        _session(
            _episode(
                pa="SELL",
                book="BUY",
                raw=-10.0,
                pa_signed=10.0,
                book_signed=-10.0,
            )
        )
    )

    rows, _ = _collect(payload)

    assert len(rows) == 4

    assert {
        row["mirror"]
        for row in rows
    } == {
        "PA_SELL_BOOK_BUY"
    }


def test_same_direction_episode_is_not_an_opposed_mirror():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="BUY",
            )
        )
    )

    rows, sessions = _collect(payload)

    assert rows == []

    assert (
        sessions[0][
            "opposed_direction_episode_count"
        ]
        == 0
    )


def test_none_book_is_not_inferred_as_opposed():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="NONE",
            )
        )
    )

    rows, sessions = _collect(payload)

    assert rows == []

    assert (
        sessions[0][
            "opposed_direction_episode_count"
        ]
        == 0
    )


def test_mixed_direction_is_not_inferred_as_opposed():
    payload = _payload(
        _session(
            _episode(
                pa="MIXED",
                book="SELL",
            )
        )
    )

    rows, sessions = _collect(payload)

    assert rows == []

    assert (
        sessions[0][
            "opposed_direction_episode_count"
        ]
        == 0
    )


def test_single_episode_enters_single_bucket():
    payload = _payload(
        _session(
            _episode(
                sample_count=1,
            )
        )
    )

    rows, _ = _collect(payload)

    assert {
        row["duration_bucket"]
        for row in rows
    } == {"SINGLE"}


def test_multi_sample_episode_enters_persistent_bucket():
    payload = _payload(
        _session(
            _episode(
                sample_count=4,
            )
        )
    )

    rows, _ = _collect(payload)

    assert {
        row["duration_bucket"]
        for row in rows
    } == {"PERSISTENT"}


def test_unavailable_horizon_is_not_collected():
    episode = _episode()

    episode["followthrough"]["20"] = {
        "available": False,
        "reason": "SESSION_END",
    }

    payload = _payload(
        _session(episode)
    )

    rows, _ = _collect(payload)

    assert len(rows) == 3

    assert {
        row["horizon"]
        for row in rows
    } == {
        1,
        5,
        10,
    }


def test_alignment_must_be_validated():
    session = _session(
        _episode(),
    )

    session["alignment_validated"] = False

    payload = _payload(session)

    with pytest.raises(
        ValueError,
        match="alignment_validated",
    ):
        _collect(payload)


def test_conflict_episode_count_must_match():
    session = _session(
        _episode(),
    )

    session["conflict_episodes"] = 2

    payload = _payload(session)

    with pytest.raises(
        ValueError,
        match="conflict_episodes",
    ):
        _collect(payload)


def test_same_direction_observation_in_opposed_mirror_fails_closed():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="SELL",
                side="SAME_DIRECTION",
            )
        )
    )

    with pytest.raises(
        ValueError,
        match="SAME_DIRECTION",
    ):
        _collect(payload)


def test_session_horizon_summary_counts_price_action_and_book():
    rows = [
        {
            "observed_side": "PRICE_ACTION",
            "raw_displacement": 10.0,
            "price_action_signed_displacement": 10.0,
            "book_signed_displacement": -10.0,
        },
        {
            "observed_side": "BOOK",
            "raw_displacement": -5.0,
            "price_action_signed_displacement": -5.0,
            "book_signed_displacement": 5.0,
        },
    ]

    result = _session_horizon_summary(rows)

    assert result["available_episode_count"] == 2

    assert result["price_action_follow_count"] == 1
    assert result["book_follow_count"] == 1

    assert result["decisive_episode_count"] == 2

    assert (
        result["price_action_share_of_decisive"]
        == 0.5
    )

    assert (
        result[
            "mean_price_action_signed_displacement"
        ]
        == 2.5
    )


def test_empty_session_horizon_summary_is_not_negative_evidence():
    result = _session_horizon_summary([])

    assert result["available_episode_count"] == 0

    assert result["price_action_follow_count"] == 0
    assert result["book_follow_count"] == 0
    assert result["decisive_episode_count"] == 0

    assert (
        result["price_action_share_of_decisive"]
        is None
    )

    assert (
        result[
            "mean_price_action_signed_displacement"
        ]
        is None
    )


def test_session_matrix_separates_sessions():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="SELL",
                side="PRICE_ACTION",
            ),
            path="session1.json",
            sha_char="a",
        ),
        _session(
            _episode(
                pa="BUY",
                book="SELL",
                side="BOOK",
                raw=-10.0,
                pa_signed=-10.0,
                book_signed=10.0,
            ),
            path="session2.json",
            sha_char="b",
        ),
    )

    rows, session_meta = _collect(payload)

    matrix = _build_session_matrix(
        rows,
        session_meta,
    )

    node = matrix[
        "PA_BUY_BOOK_SELL"
    ]["SINGLE"]["by_horizon"]["1"]

    assert node["sessions_with_observations"] == 2
    assert node["sessions_without_observations"] == 0

    results = node["session_results"]

    assert len(results) == 2

    assert (
        results[0]["price_action_follow_count"]
        == 1
    )

    assert (
        results[1]["book_follow_count"]
        == 1
    )


def test_session_without_stratum_is_counted_as_without_observation():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="SELL",
            ),
            path="session1.json",
            sha_char="a",
        ),
        _session(
            path="session2.json",
            sha_char="b",
        ),
    )

    rows, session_meta = _collect(payload)

    matrix = _build_session_matrix(
        rows,
        session_meta,
    )

    node = matrix[
        "PA_BUY_BOOK_SELL"
    ]["SINGLE"]["by_horizon"]["1"]

    assert node["sessions_with_observations"] == 1
    assert node["sessions_without_observations"] == 1

    empty_session = node["session_results"][1]

    assert (
        empty_session["available_episode_count"]
        == 0
    )

    assert (
        empty_session[
            "mean_price_action_signed_displacement"
        ]
        is None
    )


def test_cross_session_summary_uses_session_means():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="SELL",
                raw=10.0,
                pa_signed=10.0,
                book_signed=-10.0,
            ),
            path="session1.json",
            sha_char="a",
        ),
        _session(
            _episode(
                pa="BUY",
                book="SELL",
                raw=-5.0,
                pa_signed=-5.0,
                book_signed=5.0,
                side="BOOK",
            ),
            path="session2.json",
            sha_char="b",
        ),
    )

    rows, session_meta = _collect(payload)

    matrix = _build_session_matrix(
        rows,
        session_meta,
    )

    summary = _cross_session_descriptive(
        matrix
    )

    node = summary[
        "PA_BUY_BOOK_SELL"
    ]["SINGLE"]["1"]

    assert node["sessions_with_observations"] == 2

    assert (
        node[
            "positive_session_mean_pa_signed_displacement_count"
        ]
        == 1
    )

    assert (
        node[
            "negative_session_mean_pa_signed_displacement_count"
        ]
        == 1
    )

    assert (
        node[
            "zero_session_mean_pa_signed_displacement_count"
        ]
        == 0
    )

    assert (
        node[
            "mean_of_session_mean_pa_signed_displacements"
        ]
        == 2.5
    )

    assert (
        node[
            "min_session_mean_pa_signed_displacement"
        ]
        == -5.0
    )

    assert (
        node[
            "max_session_mean_pa_signed_displacement"
        ]
        == 10.0
    )


def test_collect_does_not_mutate_input():
    payload = _payload(
        _session(
            _episode(),
        )
    )

    original = deepcopy(payload)

    _collect(payload)

    assert payload == original