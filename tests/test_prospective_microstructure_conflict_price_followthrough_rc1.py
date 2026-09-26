from copy import deepcopy

import pytest

from tools.prospective_microstructure_conflict_price_followthrough import (
    VERSION,
    DEFAULT_HORIZONS,
    _aggregate_episode_results,
    _directional_observation,
    _episode_followthrough,
    _finite_number,
    _session_report,
    _signed_displacement,
    _safety,
    _validate_alignment,
    _validate_horizons,
)


def _base_sample(
    *,
    timestamp,
    price,
    pa="BUY",
):
    return {
        "timestamp": timestamp,
        "last_price": price,
        "price_action": {
            "bias": pa,
        },
    }


def _micro_sample(
    *,
    pa="BUY",
    flow="NONE",
    book="SELL",
    state="CONFIRMED",
    conflict_count=0,
    book_available=True,
):
    return {
        "price_action_bias": pa,
        "flow_direction": flow,
        "book_available": book_available,
        "book_direction": book,
        "state": state,
        "conflict_count": conflict_count,
    }


def _episode(
    *,
    episode_index=1,
    start=0,
    end=0,
    sample_count=1,
    pa="BUY",
    flow="NONE",
    book="SELL",
):
    return {
        "episode_index": episode_index,
        "start_sample_index": start,
        "end_sample_index": end,
        "sample_count": sample_count,
        "predominant_price_action_direction": pa,
        "predominant_flow_direction": flow,
        "predominant_book_direction": book,
    }


def test_version_is_rc1_followthrough():
    assert VERSION == (
        "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-PRICE-FOLLOWTHROUGH"
    )


def test_default_horizons_are_frozen():
    assert DEFAULT_HORIZONS == (1, 5, 10, 20)


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


def test_validate_horizons_sorts_values():
    assert _validate_horizons((20, 1, 10, 5)) == (1, 5, 10, 20)


@pytest.mark.parametrize(
    "horizons",
    [
        (),
        (0,),
        (-1,),
        (1, 1),
        (True,),
        (1.5,),
    ],
)
def test_invalid_horizons_fail_closed(horizons):
    with pytest.raises(ValueError):
        _validate_horizons(horizons)


def test_finite_number_accepts_int_and_float():
    assert _finite_number(10, "x") == 10.0
    assert _finite_number(10.5, "x") == 10.5


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
def test_invalid_numeric_values_fail_closed(value):
    with pytest.raises(ValueError):
        _finite_number(value, "x")


def test_alignment_accepts_matching_price_action():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
            pa="BUY",
        )
    ]

    micro = [
        _micro_sample(
            pa="BUY",
        )
    ]

    _validate_alignment(base, micro)


def test_alignment_rejects_different_sample_counts():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
        )
    ]

    with pytest.raises(
        ValueError,
        match="base sample count differs",
    ):
        _validate_alignment(base, [])


def test_alignment_rejects_price_action_mismatch():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
            pa="BUY",
        )
    ]

    micro = [
        _micro_sample(
            pa="SELL",
        )
    ]

    with pytest.raises(
        ValueError,
        match="price-action alignment mismatch",
    ):
        _validate_alignment(base, micro)


def test_alignment_rejects_missing_timestamp():
    base = [
        {
            "last_price": 100.0,
            "price_action": {
                "bias": "BUY",
            },
        }
    ]

    micro = [
        _micro_sample(
            pa="BUY",
        )
    ]

    with pytest.raises(
        ValueError,
        match="missing timestamp",
    ):
        _validate_alignment(base, micro)


def test_signed_displacement_buy():
    assert _signed_displacement("BUY", 25.0) == 25.0
    assert _signed_displacement("BUY", -25.0) == -25.0


def test_signed_displacement_sell():
    assert _signed_displacement("SELL", 25.0) == -25.0
    assert _signed_displacement("SELL", -25.0) == 25.0


def test_signed_displacement_none_is_not_inferred():
    assert _signed_displacement("NONE", 25.0) is None
    assert _signed_displacement(None, 25.0) is None


def test_directional_observation_price_action_side():
    observation = _directional_observation(
        pa_direction="BUY",
        book_direction="SELL",
        raw_displacement=10.0,
    )

    assert observation["observed_side"] == "PRICE_ACTION"
    assert observation["price_action_signed_displacement"] == 10.0
    assert observation["book_signed_displacement"] == -10.0


def test_directional_observation_book_side():
    observation = _directional_observation(
        pa_direction="BUY",
        book_direction="SELL",
        raw_displacement=-10.0,
    )

    assert observation["observed_side"] == "BOOK"
    assert observation["price_action_signed_displacement"] == -10.0
    assert observation["book_signed_displacement"] == 10.0


def test_directional_observation_flat():
    observation = _directional_observation(
        pa_direction="BUY",
        book_direction="SELL",
        raw_displacement=0.0,
    )

    assert observation["observed_side"] == "FLAT"


def test_same_direction_is_not_called_price_action_or_book():
    observation = _directional_observation(
        pa_direction="BUY",
        book_direction="BUY",
        raw_displacement=10.0,
    )

    assert observation["observed_side"] == "SAME_DIRECTION"


def test_non_directional_book_is_unresolved():
    observation = _directional_observation(
        pa_direction="BUY",
        book_direction="NONE",
        raw_displacement=10.0,
    )

    assert observation["observed_side"] == "UNRESOLVED"


def test_episode_followthrough_uses_end_of_episode_as_reference():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
        ),
        _base_sample(
            timestamp="2026-09-23T10:00:01",
            price=102.0,
        ),
        _base_sample(
            timestamp="2026-09-23T10:00:02",
            price=107.0,
        ),
    ]

    episode = _episode(
        start=0,
        end=1,
        sample_count=2,
        pa="BUY",
        book="SELL",
    )

    result = _episode_followthrough(
        episode,
        base,
        (1,),
    )

    assert result["start_price"] == 100.0
    assert result["end_price"] == 102.0
    assert result["within_episode_displacement"] == 2.0

    follow = result["followthrough"]["1"]

    assert follow["available"] is True
    assert follow["target_sample_index"] == 2
    assert follow["target_price"] == 107.0
    assert follow["raw_displacement"] == 5.0
    assert follow["observed_side"] == "PRICE_ACTION"


def test_episode_followthrough_marks_session_end_unavailable():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
        ),
        _base_sample(
            timestamp="2026-09-23T10:00:01",
            price=101.0,
        ),
    ]

    episode = _episode(
        start=1,
        end=1,
    )

    result = _episode_followthrough(
        episode,
        base,
        (1, 5),
    )

    assert result["followthrough"]["1"]["available"] is False
    assert result["followthrough"]["1"]["reason"] == "SESSION_END"

    assert result["followthrough"]["5"]["available"] is False
    assert result["followthrough"]["5"]["reason"] == "SESSION_END"


def test_episode_indexes_outside_base_samples_fail_closed():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
        )
    ]

    episode = _episode(
        start=0,
        end=1,
        sample_count=2,
    )

    with pytest.raises(
        ValueError,
        match="outside base sample range",
    ):
        _episode_followthrough(
            episode,
            base,
            (1,),
        )


def test_aggregate_counts_observed_sides():
    episodes = [
        {
            "followthrough": {
                "1": {
                    "available": True,
                    "raw_displacement": 10.0,
                    "price_action_signed_displacement": 10.0,
                    "book_signed_displacement": -10.0,
                    "observed_side": "PRICE_ACTION",
                }
            }
        },
        {
            "followthrough": {
                "1": {
                    "available": True,
                    "raw_displacement": -5.0,
                    "price_action_signed_displacement": -5.0,
                    "book_signed_displacement": 5.0,
                    "observed_side": "BOOK",
                }
            }
        },
        {
            "followthrough": {
                "1": {
                    "available": False,
                    "reason": "SESSION_END",
                }
            }
        },
    ]

    aggregate = _aggregate_episode_results(
        episodes,
        (1,),
    )["1"]

    assert aggregate["available_episode_count"] == 2
    assert aggregate["unavailable_episode_count"] == 1

    assert aggregate["observed_side_counts"] == {
        "PRICE_ACTION": 1,
        "BOOK": 1,
    }

    assert aggregate["mean_raw_displacement"] == 2.5
    assert aggregate["mean_price_action_signed_displacement"] == 2.5
    assert aggregate["mean_book_signed_displacement"] == -2.5


def test_session_report_validates_alignment_and_conflicts():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
            pa="BUY",
        ),
        _base_sample(
            timestamp="2026-09-23T10:00:01",
            price=105.0,
            pa="BUY",
        ),
        _base_sample(
            timestamp="2026-09-23T10:00:02",
            price=110.0,
            pa="BUY",
        ),
    ]

    micro = [
        _micro_sample(
            pa="BUY",
            book="SELL",
            state="CONFLICT",
        ),
        _micro_sample(
            pa="BUY",
            book="SELL",
            state="CONFIRMED",
        ),
        _micro_sample(
            pa="BUY",
            book="SELL",
            state="CONFIRMED",
        ),
    ]

    report = _session_report(
        base_samples=base,
        micro_samples=micro,
        expected_conflicts=1,
        horizons=(1,),
    )

    assert report["samples"] == 3
    assert report["alignment_validated"] is True
    assert report["alignment_method"] == "INDEX_AND_PRICE_ACTION_BIAS"

    assert report["conflict_samples"] == 1
    assert report["conflict_episodes"] == 1

    assert report["episodes"][0]["followthrough"]["1"]["available"] is True
    assert (
        report["episodes"][0]["followthrough"]["1"]["observed_side"]
        == "PRICE_ACTION"
    )


def test_session_report_conflict_count_mismatch_fails_closed():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
        )
    ]

    micro = [
        _micro_sample(
            state="CONFLICT",
        )
    ]

    with pytest.raises(
        ValueError,
        match="conflict episode sample count differs",
    ):
        _session_report(
            base_samples=base,
            micro_samples=micro,
            expected_conflicts=0,
            horizons=(1,),
        )


def test_followthrough_does_not_mutate_inputs():
    base = [
        _base_sample(
            timestamp="2026-09-23T10:00:00",
            price=100.0,
        ),
        _base_sample(
            timestamp="2026-09-23T10:00:01",
            price=105.0,
        ),
    ]

    episode = _episode(
        start=0,
        end=0,
    )

    original_base = deepcopy(base)
    original_episode = deepcopy(episode)

    _episode_followthrough(
        episode,
        base,
        (1,),
    )

    assert base == original_base
    assert episode == original_episode