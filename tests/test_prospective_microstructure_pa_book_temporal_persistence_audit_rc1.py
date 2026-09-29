from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_pa_book_temporal_persistence_audit as audit


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
        "canonical_conflict_redefinition",
    ):
        assert safety[key] is False


def test_valid_prospective_metadata_is_accepted():
    payload = _payload(
        [
            _sample("BUY", "BUY"),
            _sample("BUY", "SELL"),
        ]
    )

    assert len(
        audit._validate_prospective(payload)
    ) == 2


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

    with pytest.raises(ValueError):
        audit._validate_prospective(payload)


def test_non_object_sample_fails_closed():
    payload = _payload([_sample()])
    payload["prospective_microstructure"]["samples"] = [
        "INVALID"
    ]

    with pytest.raises(ValueError):
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


def test_contiguous_same_pair_forms_one_run():
    samples = [
        _sample("BUY", "SELL"),
        _sample("BUY", "SELL"),
        _sample("BUY", "SELL"),
    ]

    runs, counts = audit._build_runs(samples)

    assert counts["opposed_samples"] == 3
    assert len(runs) == 1

    run = runs[0]

    assert run["relation"] == "OPPOSED"
    assert run["pair"] == "BUY_SELL"
    assert run["start_index"] == 0
    assert run["end_index"] == 2
    assert run["length"] == 3


def test_none_breaks_run():
    samples = [
        _sample("BUY", "SELL"),
        _sample("BUY", "NONE"),
        _sample("BUY", "SELL"),
    ]

    runs, counts = audit._build_runs(samples)

    assert counts["opposed_samples"] == 2
    assert len(runs) == 2
    assert [run["length"] for run in runs] == [1, 1]


def test_pa_none_breaks_run():
    samples = [
        _sample("BUY", "SELL"),
        _sample("NONE", "SELL"),
        _sample("BUY", "SELL"),
    ]

    runs, _ = audit._build_runs(samples)

    assert len(runs) == 2


def test_pair_change_breaks_run_even_if_relation_same():
    samples = [
        _sample("BUY", "SELL"),
        _sample("SELL", "BUY"),
    ]

    runs, counts = audit._build_runs(samples)

    assert counts["opposed_samples"] == 2
    assert len(runs) == 2
    assert runs[0]["pair"] == "BUY_SELL"
    assert runs[1]["pair"] == "SELL_BUY"


def test_aligned_pair_change_also_breaks_run():
    samples = [
        _sample("BUY", "BUY"),
        _sample("SELL", "SELL"),
    ]

    runs, counts = audit._build_runs(samples)

    assert counts["aligned_samples"] == 2
    assert len(runs) == 2
    assert runs[0]["pair"] == "BUY_BUY"
    assert runs[1]["pair"] == "SELL_SELL"


def test_relation_change_breaks_run():
    samples = [
        _sample("BUY", "BUY"),
        _sample("BUY", "SELL"),
    ]

    runs, _ = audit._build_runs(samples)

    assert len(runs) == 2
    assert runs[0]["relation"] == "ALIGNED"
    assert runs[1]["relation"] == "OPPOSED"


def test_canonical_conflict_does_not_split_run():
    samples = [
        _sample("BUY", "SELL", 0),
        _sample("BUY", "SELL", 1),
        _sample("BUY", "SELL", 0),
    ]

    runs, _ = audit._build_runs(samples)

    assert len(runs) == 1
    assert runs[0]["length"] == 3
    assert runs[0]["canonical_conflict_samples"] == 1


def test_opposed_does_not_create_canonical_conflict():
    samples = [
        _sample("BUY", "SELL", 0),
        _sample("BUY", "SELL", 0),
    ]

    runs, _ = audit._build_runs(samples)

    assert len(runs) == 1
    assert runs[0]["relation"] == "OPPOSED"
    assert runs[0]["canonical_conflict_samples"] == 0


def test_run_summary_exact_counts():
    samples = [
        _sample("BUY", "BUY", 0),
        _sample("BUY", "BUY", 1),
        _sample("BUY", "NONE", 0),
        _sample("BUY", "SELL", 1),
        _sample("BUY", "SELL", 1),
        _sample("SELL", "BUY", 0),
        _sample("NONE", "BUY", 0),
        _sample("SELL", "SELL", 0),
    ]

    runs, counts = audit._build_runs(samples)
    summary = audit._run_summary(runs)

    assert counts["simultaneous_directional_samples"] == 6
    assert counts["aligned_samples"] == 3
    assert counts["opposed_samples"] == 3

    assert summary["total_runs"] == 4
    assert summary["aligned_runs"] == 2
    assert summary["opposed_runs"] == 2

    assert summary["pair_run_counts"] == {
        "BUY_BUY": 1,
        "SELL_SELL": 1,
        "BUY_SELL": 1,
        "SELL_BUY": 1,
    }

    assert summary["aligned_run_lengths"] == [2, 1]
    assert summary["opposed_run_lengths"] == [2, 1]

    assert summary["aligned_longest_run"] == 2
    assert summary["opposed_longest_run"] == 2

    assert summary["aligned_conflict_bearing_runs"] == 1
    assert summary["opposed_conflict_bearing_runs"] == 1

    assert summary["aligned_canonical_conflict_samples"] == 1
    assert summary["opposed_canonical_conflict_samples"] == 2


def test_session_run_lengths_sum_back_to_samples(
    tmp_path,
):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample("BUY", "BUY"),
                _sample("BUY", "BUY"),
                _sample("BUY", "NONE"),
                _sample("BUY", "SELL"),
                _sample("BUY", "SELL"),
                _sample("BUY", "SELL"),
            ]
        ),
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["simultaneous_directional_samples"] == 5
    assert result["aligned_samples"] == 2
    assert result["opposed_samples"] == 3

    assert sum(result["aligned_run_lengths"]) == 2
    assert sum(result["opposed_run_lengths"]) == 3


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
            _sample("BUY", "BUY"),
            _sample("BUY", "NONE"),
            _sample("BUY", "SELL", 1),
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

    assert aggregate["simultaneous_directional_samples"] == 40
    assert aggregate["aligned_samples"] == 20
    assert aggregate["opposed_samples"] == 20

    assert aggregate["aligned_runs"] == 10
    assert aggregate["opposed_runs"] == 10
    assert aggregate["total_runs"] == 20


def test_sample_run_episode_units_remain_separate(
    tmp_path,
):
    report = audit.build_report(
        _ten_paths(tmp_path)
    )

    units = report["unit_separation"]

    assert units["sample_unit"] == "SAMPLE"
    assert units["temporal_unit"] == "RUN"
    assert units["frozen_opposed_episode_count"] == 17

    assert units["run_is_episode_claim_allowed"] is False
    assert units["sample_is_run_claim_allowed"] is False
    assert units["sample_is_episode_claim_allowed"] is False
    assert (
        units["run_is_canonical_conflict_claim_allowed"]
        is False
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
        "canonical_conflict_redefinition",
    ):
        assert report[key] is False


def test_build_report_does_not_mutate_inputs(
    tmp_path,
):
    paths = _ten_paths(
        tmp_path,
        [
            _sample("BUY", "BUY"),
            _sample("BUY", "SELL", 1),
        ],
    )

    before = {
        path: path.read_bytes()
        for path in paths
    }

    audit.build_report(paths)

    for path in paths:
        assert path.read_bytes() == before[path]
