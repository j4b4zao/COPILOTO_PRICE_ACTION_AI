from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_pa_book_temporal_duration_audit as audit


def _sample(pa="NONE", book="NONE", conflict_count=0):
    return {
        "price_action_bias": pa,
        "book_direction": book,
        "conflict_count": conflict_count,
    }


def _payload(samples, timestamps=None, cycles=None):
    samples = list(samples)
    if timestamps is None:
        timestamps = [
            f"2026-09-29T10:00:{index:02d}.000"
            for index in range(len(samples))
        ]
    if cycles is None:
        cycles = list(range(1, len(samples) + 1))

    return {
        "samples": [
            {"timestamp": ts, "cycle": cycle}
            for ts, cycle in zip(timestamps, cycles)
        ],
        "prospective_microstructure": {
            "captured_samples": len(samples),
            "source_analyzable_samples": len(samples),
            "sample_count_matches_source": True,
            "samples": samples,
        },
    }


def _write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _ten_paths(tmp_path: Path, samples=None):
    if samples is None:
        samples = [_sample()]
    return [
        _write_json(
            tmp_path / f"session_{index:02d}.json",
            _payload(samples),
        )
        for index in range(1, 11)
    ]


def test_version_and_safety_are_passive():
    assert audit.VERSION == (
        "RC1-PROSPECTIVE-MICROSTRUCTURE-PA-BOOK-TEMPORAL-DURATION-AUDIT"
    )
    safety = audit.persistence._safety()
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


def test_exact_positional_mapping_is_required():
    payload = _payload([_sample(), _sample()])
    payload["samples"].pop()
    prospective = audit.persistence._validate_prospective(payload)
    with pytest.raises(ValueError, match="sample counts differ"):
        audit._validate_raw_samples(payload, prospective)


@pytest.mark.parametrize("value", [None, "", 123, "not-a-time"])
def test_invalid_timestamp_fails_closed(value):
    payload = _payload([_sample()])
    payload["samples"][0]["timestamp"] = value
    prospective = audit.persistence._validate_prospective(payload)
    with pytest.raises(ValueError):
        audit._validate_raw_samples(payload, prospective)


@pytest.mark.parametrize("value", [None, True, False, "1", 1.5])
def test_invalid_cycle_fails_closed(value):
    payload = _payload([_sample()])
    payload["samples"][0]["cycle"] = value
    prospective = audit.persistence._validate_prospective(payload)
    with pytest.raises(ValueError):
        audit._validate_raw_samples(payload, prospective)


def test_non_object_raw_sample_fails_closed():
    payload = _payload([_sample()])
    payload["samples"] = ["INVALID"]
    prospective = audit.persistence._validate_prospective(payload)
    with pytest.raises(ValueError, match="non-object"):
        audit._validate_raw_samples(payload, prospective)


def test_timestamp_regression_fails_closed():
    payload = _payload(
        [_sample(), _sample()],
        timestamps=[
            "2026-09-29T10:00:02.000",
            "2026-09-29T10:00:01.000",
        ],
    )
    prospective = audit.persistence._validate_prospective(payload)
    with pytest.raises(ValueError, match="timestamp regression"):
        audit._validate_raw_samples(payload, prospective)


def test_cycle_regression_fails_closed():
    payload = _payload(
        [_sample(), _sample()],
        cycles=[2, 1],
    )
    prospective = audit.persistence._validate_prospective(payload)
    with pytest.raises(ValueError, match="cycle regression"):
        audit._validate_raw_samples(payload, prospective)


def test_single_sample_run_has_zero_observed_duration(tmp_path):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [_sample("BUY", "SELL", 1)],
            timestamps=["2026-09-29T10:00:05.250"],
            cycles=[10],
        ),
    )
    result = audit._audit_session("TEST", path)
    assert result["total_runs"] == 1
    run = result["runs"][0]
    assert run["length"] == 1
    assert run["observed_duration_seconds"] == 0.0
    assert run["start_timestamp"] == run["end_timestamp"]


def test_multi_sample_duration_uses_actual_timestamps(tmp_path):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample("BUY", "SELL", 1),
                _sample("BUY", "SELL", 1),
                _sample("BUY", "SELL", 1),
            ],
            timestamps=[
                "2026-09-29T10:00:00.100",
                "2026-09-29T10:00:01.750",
                "2026-09-29T10:00:04.486",
            ],
            cycles=[10, 12, 15],
        ),
    )
    result = audit._audit_session("TEST", path)
    run = result["runs"][0]
    assert run["length"] == 3
    assert run["observed_duration_seconds"] == 4.386
    assert run["start_cycle"] == 10
    assert run["end_cycle"] == 15


def test_none_breaks_run_and_duration_is_per_run(tmp_path):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample("BUY", "SELL"),
                _sample("BUY", "NONE"),
                _sample("BUY", "SELL"),
            ],
            timestamps=[
                "2026-09-29T10:00:00.000",
                "2026-09-29T10:00:05.000",
                "2026-09-29T10:00:10.000",
            ],
        ),
    )
    result = audit._audit_session("TEST", path)
    assert result["opposed_runs"] == 2
    assert [r["observed_duration_seconds"] for r in result["runs"]] == [0.0, 0.0]


def test_pair_change_preserves_persistence_rc1_semantics(tmp_path):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample("BUY", "SELL"),
                _sample("SELL", "BUY"),
            ],
            timestamps=[
                "2026-09-29T10:00:00.000",
                "2026-09-29T10:00:01.000",
            ],
        ),
    )
    result = audit._audit_session("TEST", path)
    assert result["opposed_runs"] == 2
    assert [r["pair"] for r in result["runs"]] == ["BUY_SELL", "SELL_BUY"]


def test_canonical_conflict_does_not_define_or_split_duration_run(tmp_path):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                _sample("BUY", "SELL", 0),
                _sample("BUY", "SELL", 1),
                _sample("BUY", "SELL", 0),
            ],
            timestamps=[
                "2026-09-29T10:00:00.000",
                "2026-09-29T10:00:01.000",
                "2026-09-29T10:00:03.000",
            ],
        ),
    )
    result = audit._audit_session("TEST", path)
    assert result["opposed_runs"] == 1
    run = result["runs"][0]
    assert run["canonical_conflict_samples"] == 1
    assert run["observed_duration_seconds"] == 3.0


def test_duration_summary_exact_values():
    runs = [
        {"relation": "ALIGNED", "observed_duration_seconds": 0.0},
        {"relation": "ALIGNED", "observed_duration_seconds": 2.0},
        {"relation": "ALIGNED", "observed_duration_seconds": 4.0},
        {"relation": "OPPOSED", "observed_duration_seconds": 1.0},
        {"relation": "OPPOSED", "observed_duration_seconds": 5.0},
    ]
    result = audit._duration_summary(runs)
    assert result["aligned_min_duration_seconds"] == 0.0
    assert result["aligned_median_duration_seconds"] == 2.0
    assert result["aligned_mean_duration_seconds"] == 2.0
    assert result["aligned_max_duration_seconds"] == 4.0
    assert result["aligned_total_observed_duration_seconds"] == 6.0
    assert result["opposed_median_duration_seconds"] == 3.0
    assert result["opposed_mean_duration_seconds"] == 3.0


def test_exactly_ten_sessions_are_required(tmp_path):
    paths = _ten_paths(tmp_path)
    with pytest.raises(ValueError, match="exactly 10"):
        audit.build_report(paths[:9])


def test_duplicate_session_path_fails_closed(tmp_path):
    paths = _ten_paths(tmp_path)
    paths[-1] = paths[0]
    with pytest.raises(ValueError, match="must be distinct"):
        audit.build_report(paths)


def test_build_report_keeps_frozen_cohort_closed(tmp_path):
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


def test_unit_separation_includes_duration(tmp_path):
    report = audit.build_report(_ten_paths(tmp_path))
    units = report["unit_separation"]
    assert units["sample_unit"] == "SAMPLE"
    assert units["temporal_unit"] == "RUN"
    assert units["duration_unit"] == "SECONDS"
    assert units["frozen_opposed_episode_count"] == 17
    assert units["run_is_episode_claim_allowed"] is False
    assert units["duration_is_episode_claim_allowed"] is False


def test_report_safety_contract_is_passive(tmp_path):
    report = audit.build_report(_ten_paths(tmp_path))
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


def test_build_report_does_not_mutate_inputs(tmp_path):
    paths = _ten_paths(
        tmp_path,
        [_sample("BUY", "BUY"), _sample("BUY", "SELL", 1)],
    )
    before = {path: path.read_bytes() for path in paths}
    audit.build_report(paths)
    for path in paths:
        assert path.read_bytes() == before[path]
