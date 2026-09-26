from copy import deepcopy

import pytest

from tools.prospective_microstructure_conflict_stratification import (
    EXPECTED_INPUT_VERSION,
    MIRRORS,
    VERSION,
    _bucket,
    _collect,
    _finite_number,
    _mirror_name,
    _positive_int,
    _safety,
    _summarize,
    _validate_episode,
    _validate_input,
)


HORIZONS = (1, 5, 10, 20)


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
):
    return {
        "episode_index": episode_index,
        "sample_count": sample_count,
        "predominant_price_action_direction": pa,
        "predominant_flow_direction": "NONE",
        "predominant_book_direction": book,
        "followthrough": {
            str(h): _observation(side=side)
            for h in HORIZONS
        },
    }


def _session(*episodes):
    return {
        "path": "session.json",
        "sha256": "a" * 64,
        "alignment_validated": True,
        "conflict_episodes": len(episodes),
        "episodes": list(episodes),
    }


def _payload(*sessions):
    return {
        "version": EXPECTED_INPUT_VERSION,
        "status": "DESCRIPTIVE_ONLY",
        "eligible_sessions": len(sessions),
        "rejected_sessions": 0,
        "horizons_in_samples": list(HORIZONS),
        "sessions": list(sessions),
        "audit_stability": "INCONSISTENT",
        "audit_recommendation": "REVIEW_STABILITY",
        **_safety(),
    }


def test_version_is_rc2():
    assert VERSION == (
        "RC2-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-STRATIFICATION"
    )


def test_expected_input_is_rc1_followthrough():
    assert EXPECTED_INPUT_VERSION == (
        "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-PRICE-FOLLOWTHROUGH"
    )


def test_mirrors_are_frozen():
    assert MIRRORS == (
        ("BUY", "SELL"),
        ("SELL", "BUY"),
    )


def test_duration_bucket_is_frozen():
    assert _bucket(1) == "SINGLE"
    assert _bucket(2) == "PERSISTENT"
    assert _bucket(10) == "PERSISTENT"


def test_mirror_names_are_deterministic():
    assert _mirror_name("BUY", "SELL") == "PA_BUY_BOOK_SELL"
    assert _mirror_name("SELL", "BUY") == "PA_SELL_BOOK_BUY"


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


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        None,
        "1",
        0,
        -1,
        1.5,
    ],
)
def test_positive_int_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        _positive_int(value, "field")


def test_positive_int_accepts_positive_integer():
    assert _positive_int(1, "field") == 1
    assert _positive_int(20, "field") == 20


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        None,
        "10",
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_finite_number_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        _finite_number(value, "field")


def test_validate_input_accepts_controlled_payload():
    payload = _payload(
        _session(
            _episode(),
        )
    )

    assert _validate_input(payload) == HORIZONS


def test_validate_input_sorts_horizons():
    payload = _payload()
    payload["horizons_in_samples"] = [20, 1, 10, 5]

    assert _validate_input(payload) == HORIZONS


def test_wrong_input_version_fails_closed():
    payload = _payload()
    payload["version"] = "WRONG"

    with pytest.raises(
        ValueError,
        match="unexpected input version",
    ):
        _validate_input(payload)


def test_non_descriptive_input_fails_closed():
    payload = _payload()
    payload["status"] = "PROMOTED"

    with pytest.raises(
        ValueError,
        match="DESCRIPTIVE_ONLY",
    ):
        _validate_input(payload)


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
def test_operational_safety_flags_cannot_be_enabled(flag):
    payload = _payload()
    payload[flag] = True

    with pytest.raises(
        ValueError,
        match="safety flag must be false",
    ):
        _validate_input(payload)


def test_research_only_cannot_be_disabled():
    payload = _payload()
    payload["research_only"] = False

    with pytest.raises(
        ValueError,
        match="research_only",
    ):
        _validate_input(payload)


def test_observational_only_cannot_be_disabled():
    payload = _payload()
    payload["observational_only"] = False

    with pytest.raises(
        ValueError,
        match="observational_only",
    ):
        _validate_input(payload)


def test_eligible_session_count_must_match_sessions():
    payload = _payload(
        _session(),
    )
    payload["eligible_sessions"] = 2

    with pytest.raises(
        ValueError,
        match="eligible session count differs",
    ):
        _validate_input(payload)


def test_duplicate_horizons_fail_closed():
    payload = _payload()
    payload["horizons_in_samples"] = [1, 5, 5, 10]

    with pytest.raises(
        ValueError,
        match="horizons must be unique",
    ):
        _validate_input(payload)


def test_validate_episode_accepts_valid_episode():
    _validate_episode(
        _episode(),
        session_index=1,
        horizons=HORIZONS,
    )


def test_missing_followthrough_horizon_fails_closed():
    episode = _episode()
    del episode["followthrough"]["10"]

    with pytest.raises(
        ValueError,
        match="missing horizon 10",
    ):
        _validate_episode(
            episode,
            session_index=1,
            horizons=HORIZONS,
        )


def test_invalid_observed_side_fails_closed():
    episode = _episode()
    episode["followthrough"]["1"]["observed_side"] = "WINNER"

    with pytest.raises(
        ValueError,
        match="invalid observed_side",
    ):
        _validate_episode(
            episode,
            session_index=1,
            horizons=HORIZONS,
        )


def test_collect_keeps_only_opposed_buy_sell():
    payload = _payload(
        _session(
            _episode(
                episode_index=1,
                pa="BUY",
                book="SELL",
            ),
            _episode(
                episode_index=2,
                pa="BUY",
                book="BUY",
            ),
        )
    )

    horizons = _validate_input(payload)
    rows = _collect(payload, horizons)

    assert len(rows) == 4

    assert {
        row["episode_index"]
        for row in rows
    } == {1}

    assert {
        row["mirror"]
        for row in rows
    } == {"PA_BUY_BOOK_SELL"}


def test_collect_keeps_only_opposed_sell_buy():
    payload = _payload(
        _session(
            _episode(
                pa="SELL",
                book="BUY",
            )
        )
    )

    rows = _collect(
        payload,
        _validate_input(payload),
    )

    assert len(rows) == 4

    assert {
        row["mirror"]
        for row in rows
    } == {"PA_SELL_BOOK_BUY"}


def test_non_directional_book_is_not_inferred_as_opposed():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="NONE",
            )
        )
    )

    rows = _collect(
        payload,
        _validate_input(payload),
    )

    assert rows == []


def test_single_episode_enters_single_bucket():
    payload = _payload(
        _session(
            _episode(
                sample_count=1,
            )
        )
    )

    rows = _collect(
        payload,
        _validate_input(payload),
    )

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

    rows = _collect(
        payload,
        _validate_input(payload),
    )

    assert {
        row["duration_bucket"]
        for row in rows
    } == {"PERSISTENT"}


def test_unavailable_horizon_is_not_collected():
    episode = _episode()

    episode["followthrough"]["20"] = _observation(
        available=False,
    )

    payload = _payload(
        _session(episode)
    )

    rows = _collect(
        payload,
        _validate_input(payload),
    )

    assert len(rows) == 3

    assert {
        row["horizon"]
        for row in rows
    } == {1, 5, 10}


def test_alignment_must_be_validated():
    session = _session(
        _episode(),
    )
    session["alignment_validated"] = False

    payload = _payload(session)

    with pytest.raises(
        ValueError,
        match="lacks validated RC1 alignment",
    ):
        _collect(
            payload,
            _validate_input(payload),
        )


def test_conflict_episode_count_must_match_list():
    session = _session(
        _episode(),
    )
    session["conflict_episodes"] = 2

    payload = _payload(session)

    with pytest.raises(
        ValueError,
        match="conflict episode count mismatch",
    ):
        _collect(
            payload,
            _validate_input(payload),
        )


def test_summarize_separates_single_and_persistent():
    payload = _payload(
        _session(
            _episode(
                episode_index=1,
                sample_count=1,
                pa="BUY",
                book="SELL",
                side="PRICE_ACTION",
            ),
            _episode(
                episode_index=2,
                sample_count=3,
                pa="BUY",
                book="SELL",
                side="BOOK",
            ),
        )
    )

    horizons = _validate_input(payload)
    rows = _collect(payload, horizons)
    result = _summarize(rows, horizons)

    mirror = result["PA_BUY_BOOK_SELL"]

    assert (
        mirror["episode_count_with_available_followthrough"]
        == 2
    )

    assert (
        mirror["SINGLE"][
            "episode_count_with_available_followthrough"
        ]
        == 1
    )

    assert (
        mirror["PERSISTENT"][
            "episode_count_with_available_followthrough"
        ]
        == 1
    )

    single_h1 = mirror["SINGLE"]["by_horizon"]["1"]
    persistent_h1 = mirror["PERSISTENT"]["by_horizon"]["1"]

    assert single_h1["price_action_follow_count"] == 1
    assert single_h1["book_follow_count"] == 0

    assert persistent_h1["price_action_follow_count"] == 0
    assert persistent_h1["book_follow_count"] == 1


def test_summarize_counts_decisive_share_descriptively():
    payload = _payload(
        _session(
            _episode(
                episode_index=1,
                side="PRICE_ACTION",
            ),
            _episode(
                episode_index=2,
                side="BOOK",
            ),
            _episode(
                episode_index=3,
                side="PRICE_ACTION",
            ),
        )
    )

    horizons = _validate_input(payload)
    rows = _collect(payload, horizons)

    report = _summarize(
        rows,
        horizons,
    )

    h1 = report[
        "PA_BUY_BOOK_SELL"
    ]["SINGLE"]["by_horizon"]["1"]

    assert h1["available_episode_count"] == 3
    assert h1["price_action_follow_count"] == 2
    assert h1["book_follow_count"] == 1
    assert h1["decisive_episode_count"] == 3

    assert (
        h1["price_action_share_of_decisive"]
        == 0.666667
    )


def test_same_direction_inside_opposed_mirror_fails_closed():
    payload = _payload(
        _session(
            _episode(
                pa="BUY",
                book="SELL",
                side="SAME_DIRECTION",
            )
        )
    )

    horizons = _validate_input(payload)
    rows = _collect(payload, horizons)

    with pytest.raises(
        ValueError,
        match="opposed PA/Book mirror produced SAME_DIRECTION",
    ):
        _summarize(
            rows,
            horizons,
        )


def test_collect_does_not_mutate_payload():
    payload = _payload(
        _session(
            _episode(),
        )
    )

    original = deepcopy(payload)

    horizons = _validate_input(payload)
    _collect(payload, horizons)

    assert payload == original