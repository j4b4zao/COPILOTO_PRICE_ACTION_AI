from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_book_observability_audit as audit


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


def _canonical(
    pressure="BALANCED",
    direction="NONE",
):
    return {
        "book_pressure": pressure,
        "book_direction": direction,
    }


def _payload(
    imbalances,
    canonical=None,
):
    imbalances = list(imbalances)

    if canonical is None:
        canonical = []
        for value in imbalances:
            pressure = audit._expected_pressure(value)
            canonical.append(
                _canonical(
                    pressure,
                    audit._direction_from_pressure(
                        pressure
                    ),
                )
            )

    return {
        "samples": [
            {
                "imbalance": value,
            }
            for value in imbalances
        ],
        "prospective_microstructure": {
            "captured_samples": len(canonical),
            "source_analyzable_samples": len(canonical),
            "sample_count_matches_source": True,
            "samples": canonical,
        },
    }


def test_safety_contract_is_fully_passive():
    safety = audit._safety()

    assert safety["research_only"] is True
    assert safety["observational_only"] is True
    assert safety["descriptive_only"] is True

    assert safety["predictive_claim_allowed"] is False
    assert safety["score_influence_allowed"] is False
    assert safety["risk_influence_allowed"] is False
    assert safety["decision_influence_allowed"] is False
    assert safety["alert_influence_allowed"] is False
    assert safety["order_execution_allowed"] is False
    assert safety["promotion_allowed"] is False

    assert safety["threshold_change_allowed"] is False
    assert safety["rc17_change_allowed"] is False
    assert safety["order_flow_score_change_allowed"] is False


@pytest.mark.parametrize(
    ("imbalance", "pressure", "direction"),
    [
        (0.149999, "BALANCED", "NONE"),
        (0.15, "BID_DOMINANT", "BUY"),
        (0.50, "BID_DOMINANT", "BUY"),
        (-0.149999, "BALANCED", "NONE"),
        (-0.15, "ASK_DOMINANT", "SELL"),
        (-0.50, "ASK_DOMINANT", "SELL"),
        (0.0, "BALANCED", "NONE"),
    ],
)
def test_formal_pressure_boundary(
    imbalance,
    pressure,
    direction,
):
    assert audit._expected_pressure(imbalance) == pressure
    assert audit._direction_from_pressure(pressure) == direction


def test_valid_prospective_metadata_is_accepted():
    payload = _payload(
        [0.0, 0.15],
    )

    samples = audit._validate_prospective(payload)

    assert len(samples) == 2


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "captured_samples",
            None,
            "captured_samples must be an integer",
        ),
        (
            "captured_samples",
            "2",
            "captured_samples must be an integer",
        ),
        (
            "captured_samples",
            True,
            "captured_samples must be an integer",
        ),
        (
            "source_analyzable_samples",
            None,
            "source_analyzable_samples must be an integer",
        ),
        (
            "source_analyzable_samples",
            "2",
            "source_analyzable_samples must be an integer",
        ),
        (
            "source_analyzable_samples",
            False,
            "source_analyzable_samples must be an integer",
        ),
    ],
)
def test_invalid_count_metadata_fails_closed(
    field,
    value,
    message,
):
    payload = _payload([0.0, 0.15])

    if value is None:
        del payload["prospective_microstructure"][field]
    else:
        payload["prospective_microstructure"][field] = value

    with pytest.raises(
        ValueError,
        match=message,
    ):
        audit._validate_prospective(payload)


@pytest.mark.parametrize(
    "field",
    [
        "captured_samples",
        "source_analyzable_samples",
    ],
)
def test_count_mismatch_fails_closed(field):
    payload = _payload([0.0, 0.15])
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
    payload = _payload([0.0])

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


def test_non_object_prospective_sample_fails_closed():
    payload = _payload([0.0])
    payload["prospective_microstructure"]["samples"] = [
        "INVALID"
    ]
    payload["prospective_microstructure"][
        "captured_samples"
    ] = 1
    payload["prospective_microstructure"][
        "source_analyzable_samples"
    ] = 1

    with pytest.raises(
        ValueError,
        match="contains non-object entries",
    ):
        audit._validate_prospective(payload)


def test_non_object_raw_sample_fails_closed():
    payload = {
        "samples": [
            "INVALID",
        ],
    }

    with pytest.raises(
        ValueError,
        match="contains non-object entries",
    ):
        audit._validate_raw_samples(payload)


@pytest.mark.parametrize(
    "value",
    [
        None,
        True,
        "0.10",
        1.01,
        -1.01,
    ],
)
def test_invalid_imbalance_fails_closed(value):
    with pytest.raises(ValueError):
        audit._imbalance(
            {
                "imbalance": value,
            },
            0,
        )


def test_pressure_and_direction_exact_match(tmp_path):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [
                -0.20,
                -0.149,
                0.0,
                0.149,
                0.20,
            ]
        ),
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["samples"] == 5

    assert (
        result["pressure_mismatch_count"]
        == 0
    )
    assert (
        result[
            "direction_not_explained_by_imbalance_count"
        ]
        == 0
    )

    assert (
        result["all_pressure_explained_by_imbalance"]
        is True
    )
    assert (
        result["all_direction_explained_by_imbalance"]
        is True
    )

    assert (
        result["canonical_pressure_counts"]
        == {
            "BID_DOMINANT": 1,
            "ASK_DOMINANT": 1,
            "BALANCED": 3,
        }
    )

    assert (
        result["canonical_direction_counts"]
        == {
            "BUY": 1,
            "SELL": 1,
            "NONE": 3,
        }
    )


def test_pressure_mismatch_is_reported(tmp_path):
    payload = _payload(
        [0.20],
        [
            _canonical(
                "BALANCED",
                "NONE",
            ),
        ],
    )

    path = _write_json(
        tmp_path / "session.json",
        payload,
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["pressure_mismatch_count"] == 1
    assert (
        result["all_pressure_explained_by_imbalance"]
        is False
    )


def test_direction_not_explained_is_reported(tmp_path):
    payload = _payload(
        [0.20],
        [
            _canonical(
                "BID_DOMINANT",
                "NONE",
            ),
        ],
    )

    path = _write_json(
        tmp_path / "session.json",
        payload,
    )

    result = audit._audit_session(
        "TEST",
        path,
    )

    assert result["pressure_mismatch_count"] == 0
    assert (
        result[
            "direction_not_explained_by_imbalance_count"
        ]
        == 1
    )
    assert (
        result["all_direction_explained_by_imbalance"]
        is False
    )


def test_raw_and_prospective_count_mismatch_fails_closed(
    tmp_path,
):
    payload = _payload([0.0, 0.20])
    payload["samples"].pop()

    path = _write_json(
        tmp_path / "session.json",
        payload,
    )

    with pytest.raises(
        ValueError,
        match="raw/prospective sample count mismatch",
    ):
        audit._audit_session(
            "TEST",
            path,
        )


@pytest.mark.parametrize(
    ("pressure", "direction"),
    [
        ("INVALID", "NONE"),
        ("BALANCED", "INVALID"),
    ],
)
def test_invalid_canonical_values_fail_closed(
    tmp_path,
    pressure,
    direction,
):
    path = _write_json(
        tmp_path / "session.json",
        _payload(
            [0.0],
            [
                _canonical(
                    pressure,
                    direction,
                ),
            ],
        ),
    )

    with pytest.raises(ValueError):
        audit._audit_session(
            "TEST",
            path,
        )


def test_same_artifact_is_rejected(tmp_path):
    path = _write_json(
        tmp_path / "same.json",
        _payload([0.0]),
    )

    with pytest.raises(
        ValueError,
        match="must be distinct raw artifacts",
    ):
        audit.build_report(
            path,
            path,
        )


def test_build_report_keeps_sessions_independent(
    tmp_path,
):
    session11 = _write_json(
        tmp_path / "session11.json",
        _payload(
            [
                0.00,
                0.10,
            ]
        ),
    )

    session12 = _write_json(
        tmp_path / "session12.json",
        _payload(
            [
                0.00,
                0.20,
            ]
        ),
    )

    report = audit.build_report(
        session11,
        session12,
    )

    assert (
        report["status"]
        == "BOOK_OBSERVABILITY_AUDIT_COMPLETED"
    )

    assert len(report["sessions"]) == 2

    assert report["combined_session_count"] is None
    assert (
        report["combined_checkpoint_created"]
        is False
    )
    assert report["cohort_redefinition"] is False

    assert (
        report["sessions"][0]["samples"]
        == 2
    )
    assert (
        report["sessions"][1]["samples"]
        == 2
    )


def test_concentration_limit_is_explicit(
    tmp_path,
):
    session11 = _write_json(
        tmp_path / "session11.json",
        _payload([0.0]),
    )
    session12 = _write_json(
        tmp_path / "session12.json",
        _payload([0.20]),
    )

    report = audit.build_report(
        session11,
        session12,
    )

    limits = report["interpretation_limits"]

    assert (
        "CONCENTRATION_BIAS_IS_NOT_PERSISTED"
        in limits
    )
    assert (
        "SUFFICIENCY_DOES_NOT_PROVE_CONCENTRATION_BIAS_WAS_BALANCED"
        in limits
    )

    for session in report["sessions"]:
        interpretation = session["interpretation"]

        assert (
            interpretation[
                "concentration_bias_was_balanced_claim_allowed"
            ]
            is False
        )


def test_build_report_does_not_mutate_inputs(
    tmp_path,
):
    session11 = _write_json(
        tmp_path / "session11.json",
        _payload([0.0]),
    )
    session12 = _write_json(
        tmp_path / "session12.json",
        _payload([0.20]),
    )

    before11 = session11.read_bytes()
    before12 = session12.read_bytes()

    audit.build_report(
        session11,
        session12,
    )

    assert session11.read_bytes() == before11
    assert session12.read_bytes() == before12


def test_report_safety_contract_is_passive(
    tmp_path,
):
    session11 = _write_json(
        tmp_path / "session11.json",
        _payload([0.0]),
    )
    session12 = _write_json(
        tmp_path / "session12.json",
        _payload([0.20]),
    )

    report = audit.build_report(
        session11,
        session12,
    )

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["descriptive_only"] is True

    assert report["predictive_claim_allowed"] is False
    assert report["score_influence_allowed"] is False
    assert report["risk_influence_allowed"] is False
    assert report["decision_influence_allowed"] is False
    assert report["alert_influence_allowed"] is False
    assert report["order_execution_allowed"] is False
    assert report["promotion_allowed"] is False

    assert report["threshold_change_allowed"] is False
    assert report["rc17_change_allowed"] is False
    assert (
        report["order_flow_score_change_allowed"]
        is False
    )
