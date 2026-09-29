from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_pa_book_opportunity_audit as audit


def _write_json(
    path: Path,
    payload,
) -> Path:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _sample(
    pa="NONE",
    book="NONE",
    conflict_count=0,
):
    return {
        "price_action_bias": pa,
        "book_direction": book,
        "conflict_count": conflict_count,
    }


def _payload(samples):
    samples = list(samples)

    return {
        "prospective_microstructure": {
            "captured_samples": len(samples),
            "source_analyzable_samples": len(samples),
            "sample_count_matches_source": True,
            "samples": samples,
        },
    }


def _ten_paths(
    tmp_path: Path,
    samples=None,
):
    if samples is None:
        samples = [_sample()]

    return [
        _write_json(
            tmp_path / f"session_{index:02d}.json",
            _payload(samples),
        )
        for index in range(1, 11)
    ]


def test_safety_contract_is_fully_passive():
    safety = audit._safety()

    assert safety["research_only"] is True
    assert safety["observational_only"] is True
    assert safety["descriptive_only"] is True

    for key in (
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
        "threshold_change_allowed",
        "rc17_change_allowed",
        "order_flow_score_change_allowed",
        "threshold_changed",
        "rc17_changed",
        "operational_logic_changed",
    ):
        assert safety[key] is False


def test_valid_prospective_metadata_is_accepted():
    payload = _payload(
        [
            _sample("BUY", "BUY"),
            _sample("SELL", "SELL"),
        ]
    )

    samples = audit._validate_prospective(payload)

    assert len(samples) == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("captured_samples", None),
        ("captured_samples", "1"),
        ("captured_samples", True),
        ("source_analyzable_samples", None),
        ("source_analyzable_samples", "1"),
        ("source_analyzable_samples", False),
    ],
)
def test_invalid_count_metadata_fails_closed(
    field,
    value,
):
    payload = _payload([_sample()])

    if value is None:
        del payload["prospective_microstructure"][field]
    else:
        payload["prospective_microstructure"][field] = value

    with pytest.raises(ValueError):
        audit._validate_prospective(payload)


@pytest.mark.parametrize(
    "field",
    [
        "captured_samples",
        "source_analyzable_samples",
    ],
)
def test_count_mismatch_fails_closed(field):
    payload = _payload([_sample(), _sample()])
    payload["prospective_microstructure"][field] = 1

    with pytest.raises(
        ValueError,
        match="does not match len",
    ):
        audit._validate_prospective(payload)


@pytest.mark.parametrize(
    "value",
    [
        False,
        None,
        1,
        "true",
    ],
)
def test_sample_count_matches_source_requires_literal_true(
    value,
):
    payload = _payload([_sample()])

    if value is None:
        del payload["prospective_microstructure"][
            "sample_count_matches_source"
        ]
    else:
        payload["prospective_microstructure"][
            "sample_count_matches_source"
        ] = value

    with pytest.raises(
        ValueError,
        match="sample_count_matches_source must be true",
    ):
        audit._validate_prospective(payload)


def test_non_object_sample_fails_closed():
    payload = _payload([_sample()])
    payload["prospective_microstructure"]["samples"] = [
        "INVALID"
    ]

    with pytest.raises(
        ValueError,
        match="contains non-object entries",
    ):
        audit._validate_prospective(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("price_action_bias", "INVALID"),
        ("price_action_bias", ""),
        ("book_direction", "INVALID"),
        ("book_direction", ""),
    ],
)
def test_invalid_direction_fails_closed(
    tmp_path,
    field,
    value,
):
    sample = _sample("BUY", "BUY")
    sample[field] = value

    path = _write_json(
        tmp_path / "session.json",
        _payload([sample]),
    )

    with pytest.raises(ValueError):
        audit._audit_session(
            "TEST",
            path,
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        False,
        "1",
        1.0,
        -1,
    ],
)
def test_invalid_conflict_count_fails_closed(
    tmp_path,
    value,
):
    sample = _sample("BUY", "SELL")

    if value is None:
        del sample["conflict_count"]
    else:
        sample["conflict_count"] = value

    path = _write_json(
        tmp_path / "session.json",
        _payload([sample]),
    )

    with pytest.raises(ValueError):
        audit._audit_session(
            "TEST",
            path,
        )


def test_opposed_sample_is_not_reinferred_as_conflict(
    tmp_path,
):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample(
                    "BUY",
                    "SELL",
                    conflict_count=0,
                ),
            ]
        ),
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["simultaneous_directional"] == 1
    assert result["opposed"] == 1
    assert result["canonical_conflict_samples"] == 0
    assert result["opposed_canonical_conflict"] == 0


def test_canonical_conflict_count_is_authoritative(
    tmp_path,
):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample(
                    "BUY",
                    "BUY",
                    conflict_count=2,
                ),
            ]
        ),
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["aligned"] == 1
    assert result["canonical_conflict_samples"] == 1
    assert result["simultaneous_canonical_conflict"] == 1
    assert result["aligned_canonical_conflict"] == 1
    assert result["opposed_canonical_conflict"] == 0


def test_exact_relationship_counts(tmp_path):
    samples = [
        _sample("BUY", "BUY", 0),
        _sample("SELL", "SELL", 0),
        _sample("BUY", "SELL", 1),
        _sample("SELL", "BUY", 1),
        _sample("BUY", "NONE", 0),
        _sample("NONE", "BUY", 0),
        _sample("NONE", "NONE", 0),
    ]

    path = _write_json(
        tmp_path / "session.json",
        _payload(samples),
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["samples"] == 7
    assert result["pa_directional"] == 5
    assert result["book_directional"] == 5
    assert result["simultaneous_directional"] == 4

    assert result["aligned"] == 2
    assert result["opposed"] == 2

    assert result["pa_buy_book_buy"] == 1
    assert result["pa_sell_book_sell"] == 1
    assert result["pa_buy_book_sell"] == 1
    assert result["pa_sell_book_buy"] == 1

    assert result["pa_directional_book_none"] == 1

    assert result["canonical_conflict_samples"] == 2
    assert result["simultaneous_canonical_conflict"] == 2
    assert result["aligned_canonical_conflict"] == 0
    assert result["opposed_canonical_conflict"] == 2

    assert (
        result["aligned_rate_among_simultaneous"]
        == pytest.approx(0.5)
    )
    assert (
        result["opposed_rate_among_simultaneous"]
        == pytest.approx(0.5)
    )


def test_zero_simultaneous_has_null_rates(tmp_path):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample("BUY", "NONE"),
                _sample("NONE", "BUY"),
            ]
        ),
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["simultaneous_directional"] == 0
    assert result["aligned_rate_among_simultaneous"] is None
    assert result["opposed_rate_among_simultaneous"] is None


def test_exactly_ten_sessions_are_required(tmp_path):
    paths = _ten_paths(tmp_path)

    with pytest.raises(
        ValueError,
        match="exactly 10",
    ):
        audit.build_report(paths[:9])

    extra = _write_json(
        tmp_path / "session_11.json",
        _payload([_sample()]),
    )

    with pytest.raises(
        ValueError,
        match="exactly 10",
    ):
        audit.build_report(paths + [extra])


def test_duplicate_session_path_fails_closed(tmp_path):
    paths = _ten_paths(tmp_path)
    paths[-1] = paths[0]

    with pytest.raises(
        ValueError,
        match="must be distinct",
    ):
        audit.build_report(paths)


def test_build_report_keeps_frozen_cohort_closed(
    tmp_path,
):
    paths = _ten_paths(
        tmp_path,
        [
            _sample("BUY", "BUY"),
            _sample("BUY", "SELL", 1),
        ],
    )

    report = audit.build_report(paths)

    assert report["session_count"] == 10
    assert report["frozen_checkpoint_session_count"] == 10
    assert report["checkpoint_extended"] is False
    assert report["independent_sessions_appended"] is False
    assert report["combined_session_count"] is None
    assert report["combined_checkpoint_created"] is False
    assert report["cohort_redefinition"] is False

    aggregate = report["aggregate"]

    assert aggregate["samples"] == 20
    assert aggregate["simultaneous_directional"] == 20
    assert aggregate["aligned"] == 10
    assert aggregate["opposed"] == 10
    assert aggregate["canonical_conflict_samples"] == 10
    assert aggregate["opposed_canonical_conflict"] == 10


def test_sample_and_episode_units_remain_separate(
    tmp_path,
):
    report = audit.build_report(
        _ten_paths(tmp_path)
    )

    units = report["unit_separation"]

    assert units["this_audit_unit"] == "SAMPLE"
    assert units["frozen_opposed_episode_count"] == 17
    assert units["episode_count_used_as_sample_count"] is False
    assert units["sample_count_used_as_episode_count"] is False
    assert (
        units["sample_episode_equivalence_claim_allowed"]
        is False
    )

    assert (
        "146_OPPOSED_SAMPLES_MUST_NOT_BE_EQUATED_WITH_17_OPPOSED_EPISODES"
        in report["interpretation_limits"]
    )


def test_report_safety_contract_is_passive(
    tmp_path,
):
    report = audit.build_report(
        _ten_paths(tmp_path)
    )

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["descriptive_only"] is True

    for key in (
        "predictive_claim_allowed",
        "score_influence_allowed",
        "risk_influence_allowed",
        "decision_influence_allowed",
        "alert_influence_allowed",
        "order_execution_allowed",
        "promotion_allowed",
        "threshold_change_allowed",
        "rc17_change_allowed",
        "order_flow_score_change_allowed",
        "threshold_changed",
        "rc17_changed",
        "operational_logic_changed",
    ):
        assert report[key] is False


def test_build_report_does_not_mutate_inputs(
    tmp_path,
):
    paths = _ten_paths(
        tmp_path,
        [
            _sample("BUY", "BUY"),
            _sample("SELL", "BUY", 1),
        ],
    )

    before = {
        path: path.read_bytes()
        for path in paths
    }

    audit.build_report(paths)

    for path in paths:
        assert path.read_bytes() == before[path]
