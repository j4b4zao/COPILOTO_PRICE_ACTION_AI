from __future__ import annotations

import json
from pathlib import Path

import pytest

import tools.prospective_microstructure_book_directionality_diagnostics as diag


def _write_json(path: Path, payload) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _sample(
    pa="NONE",
    flow="NONE",
    book="NONE",
    conflict=None,
):
    sample = {
        "price_action_direction": pa,
        "flow_direction": flow,
        "book_direction": book,
    }

    if conflict is not None:
        sample["conflict"] = conflict

    return sample


def test_safety_contract_is_fully_passive():
    safety = diag._safety()

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
    ("value", "expected"),
    [
        ("BUY", "BUY"),
        ("SELL", "SELL"),
        ("NONE", "NONE"),
        ("LONG", "BUY"),
        ("SHORT", "SELL"),
        ("BULL", "BUY"),
        ("BEAR", "SELL"),
        ("BULLISH", "BUY"),
        ("BEARISH", "SELL"),
        ("NEUTRAL", "NONE"),
        ("UNKNOWN", "NONE"),
        ("", "NONE"),
        (None, "NONE"),
    ],
)
def test_normalize_direction(value, expected):
    assert diag._normalize_direction(value) == expected


def test_extract_samples_from_top_level_samples():
    payload = {
        "samples": [
            {"x": 1},
            {"x": 2},
        ]
    }

    samples = diag._extract_samples(payload)

    assert len(samples) == 2
    assert samples[0]["x"] == 1
    assert samples[1]["x"] == 2


def test_extract_samples_from_nested_session():
    payload = {
        "session": {
            "samples": [
                {"x": 1},
            ]
        }
    }

    samples = diag._extract_samples(payload)

    assert len(samples) == 1
    assert samples[0]["x"] == 1


def test_extract_samples_rejects_unknown_schema():
    with pytest.raises(
        ValueError,
        match="could not locate raw session samples",
    ):
        diag._extract_samples(
            {
                "something_else": [],
            }
        )


def test_direction_extractors_support_direct_fields():
    sample = {
        "price_action_direction": "BUY",
        "flow_direction": "SELL",
        "book_direction": "BUY",
    }

    assert diag._extract_pa_direction(sample) == "BUY"
    assert diag._extract_flow_direction(sample) == "SELL"
    assert diag._extract_book_direction(sample) == "BUY"


def test_direction_extractors_support_nested_fields():
    sample = {
        "price_action": {
            "direction": "BUY",
        },
        "order_flow": {
            "direction": "SELL",
        },
        "order_book": {
            "direction": "SELL",
        },
    }

    assert diag._extract_pa_direction(sample) == "BUY"
    assert diag._extract_flow_direction(sample) == "SELL"
    assert diag._extract_book_direction(sample) == "SELL"


def test_conflict_uses_explicit_flag_when_available():
    sample = _sample(
        pa="BUY",
        flow="SELL",
        book="NONE",
        conflict=False,
    )

    assert (
        diag._is_conflict(
            sample,
            "BUY",
            "SELL",
            "NONE",
        )
        is False
    )


def test_conflict_fallback_detects_opposition():
    sample = _sample(
        pa="BUY",
        flow="SELL",
        book="NONE",
    )

    assert (
        diag._is_conflict(
            sample,
            "BUY",
            "SELL",
            "NONE",
        )
        is True
    )


def test_diagnose_session_counts_book_states(tmp_path):
    raw = _write_json(
        tmp_path / "session.json",
        {
            "samples": [
                _sample("BUY", "BUY", "NONE"),
                _sample("BUY", "SELL", "BUY"),
                _sample("SELL", "SELL", "BUY"),
                _sample("SELL", "BUY", "SELL"),
                _sample("NONE", "NONE", "NONE"),
            ]
        },
    )

    result = diag._diagnose_session(
        "TEST",
        raw,
    )

    assert result["samples"] == 5

    assert result["book"]["directional"] == 3
    assert result["book"]["buy"] == 2
    assert result["book"]["sell"] == 1
    assert result["book"]["none"] == 2

    assert result["book"]["directional_rate"] == 0.6
    assert result["book"]["none_rate"] == 0.4


def test_pairwise_book_context(tmp_path):
    raw = _write_json(
        tmp_path / "session.json",
        {
            "samples": [
                _sample("BUY", "BUY", "BUY"),
                _sample("BUY", "SELL", "SELL"),
                _sample("SELL", "BUY", "BUY"),
                _sample("SELL", "SELL", "BUY"),
            ]
        },
    )

    result = diag._diagnose_session(
        "TEST",
        raw,
    )

    pairwise = result["pairwise_book_context"]

    # PA x Book:
    # BUY  x BUY  = aligned
    # BUY  x SELL = opposed
    # SELL x BUY  = opposed
    # SELL x BUY  = opposed
    assert pairwise["pa_book_aligned_samples"] == 1
    assert pairwise["pa_book_opposed_samples"] == 3

    # Flow x Book:
    # BUY  x BUY  = aligned
    # SELL x SELL = aligned
    # BUY  x BUY  = aligned
    # SELL x BUY  = opposed
    assert pairwise["flow_book_aligned_samples"] == 3
    assert pairwise["flow_book_opposed_samples"] == 1


def test_book_continuity_and_transitions(tmp_path):
    raw = _write_json(
        tmp_path / "session.json",
        {
            "samples": [
                _sample(book="NONE"),
                _sample(book="NONE"),
                _sample(book="BUY"),
                _sample(book="BUY"),
                _sample(book="SELL"),
                _sample(book="NONE"),
            ]
        },
    )

    result = diag._diagnose_session(
        "TEST",
        raw,
    )

    continuity = result["book_continuity"]

    assert continuity["longest_none_run"] == 2
    assert continuity["longest_directional_run"] == 3

    transitions = continuity["transitions"]

    assert transitions["NONE_TO_NONE"] == 1
    assert transitions["NONE_TO_DIRECTIONAL"] == 1
    assert transitions["BUY_TO_BUY"] == 1
    assert transitions["BUY_TO_SELL"] == 1
    assert transitions["DIRECTIONAL_TO_NONE"] == 1


def test_conflict_context_separates_book_none(tmp_path):
    raw = _write_json(
        tmp_path / "session.json",
        {
            "samples": [
                _sample(
                    "BUY",
                    "SELL",
                    "NONE",
                    True,
                ),
                _sample(
                    "BUY",
                    "SELL",
                    "BUY",
                    True,
                ),
                _sample(
                    "BUY",
                    "BUY",
                    "BUY",
                    False,
                ),
            ]
        },
    )

    result = diag._diagnose_session(
        "TEST",
        raw,
    )

    conflict = result["conflict_context"]

    assert conflict["conflict_samples"] == 2

    assert (
        conflict["book_directional_during_conflict"]
        == 1
    )

    assert (
        conflict["book_none_during_conflict"]
        == 1
    )

    assert (
        conflict[
            "book_directional_during_conflict_rate"
        ]
        == 0.5
    )


def test_build_report_keeps_sessions_independent(
    tmp_path,
):
    s11 = _write_json(
        tmp_path / "session11.json",
        {
            "samples": [
                _sample("BUY", "SELL", "NONE"),
                _sample("BUY", "BUY", "NONE"),
            ]
        },
    )

    s12 = _write_json(
        tmp_path / "session12.json",
        {
            "samples": [
                _sample("SELL", "BUY", "BUY"),
                _sample("SELL", "SELL", "SELL"),
            ]
        },
    )

    report = diag.build_report(
        s11,
        s12,
    )

    assert (
        report["status"]
        == "BOOK_DIRECTIONALITY_DIAGNOSTICS_COMPLETED"
    )

    assert len(report["sessions"]) == 2

    assert report["combined_session_count"] is None

    assert (
        report["combined_checkpoint_created"]
        is False
    )

    assert report["cohort_redefinition"] is False

    assert report["research_only"] is True
    assert report["observational_only"] is True
    assert report["descriptive_only"] is True

    assert (
        report["threshold_change_allowed"]
        is False
    )

    assert report["rc17_change_allowed"] is False

    assert (
        report["order_flow_score_change_allowed"]
        is False
    )


def test_same_raw_artifact_is_rejected(tmp_path):
    raw = _write_json(
        tmp_path / "same.json",
        {
            "samples": [
                _sample(),
            ]
        },
    )

    with pytest.raises(
        ValueError,
        match="must be distinct raw artifacts",
    ):
        diag.build_report(
            raw,
            raw,
        )


def test_build_report_does_not_mutate_raw_files(
    tmp_path,
):
    s11 = _write_json(
        tmp_path / "session11.json",
        {
            "samples": [
                _sample("BUY", "SELL", "NONE"),
            ]
        },
    )

    s12 = _write_json(
        tmp_path / "session12.json",
        {
            "samples": [
                _sample("SELL", "BUY", "BUY"),
            ]
        },
    )

    before11 = s11.read_bytes()
    before12 = s12.read_bytes()

    diag.build_report(
        s11,
        s12,
    )

    assert s11.read_bytes() == before11
    assert s12.read_bytes() == before12


def test_interpretation_limits_are_explicit(
    tmp_path,
):
    s11 = _write_json(
        tmp_path / "session11.json",
        {
            "samples": [
                _sample(),
            ]
        },
    )

    s12 = _write_json(
        tmp_path / "session12.json",
        {
            "samples": [
                _sample(),
            ]
        },
    )

    report = diag.build_report(
        s11,
        s12,
    )

    limits = report[
        "diagnostic"
    ]["interpretation_limits"]

    assert "DESCRIPTIVE_ONLY" in limits

    assert (
        "INDEPENDENT_SESSIONS_ARE_NOT_A_COMBINED_COHORT"
        in limits
    )

    assert (
        "BOOK_NONE_DOES_NOT_ESTABLISH_ABSENCE_OF_BOOK_INFORMATION"
        in limits
    )

    assert (
        "ZERO_OPPOSITION_DOES_NOT_ESTABLISH_ABSENCE"
        in limits
    )

    assert (
        "NO_THRESHOLD_CHANGE_ALLOWED"
        in limits
    )

    assert (
        "NO_OPERATIONAL_INFERENCE_ALLOWED"
        in limits
    )

def test_extract_samples_prefers_canonical_prospective_evidence():
    payload = {
        "samples": [
            {
                "price_action": {"bias": "SELL"},
                "imbalance": 0.50,
            },
        ],
        "prospective_microstructure": {
            "captured_samples": 2,
            "source_analyzable_samples": 2,
            "sample_count_matches_source": True,
            "samples": [
                _sample("BUY", "SELL", "NONE"),
                _sample("SELL", "BUY", "BUY"),
            ],
        },
    }

    samples = diag._extract_samples(payload)

    assert len(samples) == 2
    assert samples[0]["price_action_direction"] == "BUY"
    assert samples[0]["flow_direction"] == "SELL"
    assert samples[0]["book_direction"] == "NONE"
    assert samples[1]["price_action_direction"] == "SELL"
    assert samples[1]["flow_direction"] == "BUY"
    assert samples[1]["book_direction"] == "BUY"


def test_prospective_container_with_invalid_samples_fails_closed():
    payload = {
        "samples": [
            _sample("BUY", "SELL", "BUY"),
        ],
        "prospective_microstructure": {
            "samples": None,
        },
    }

    with pytest.raises(
        ValueError,
        match=(
            "prospective_microstructure exists but samples "
            "is not a list"
        ),
    ):
        diag._extract_samples(payload)


def test_diagnose_session_uses_prospective_not_raw_samples(
    tmp_path,
):
    raw = _write_json(
        tmp_path / "session.json",
        {
            "samples": [
                {
                    "price_action": {
                        "bias": "NONE",
                    },
                    "imbalance": 0.90,
                },
            ],
            "prospective_microstructure": {
                "captured_samples": 3,
                "source_analyzable_samples": 3,
                "sample_count_matches_source": True,
                "samples": [
                    _sample("BUY", "SELL", "NONE", True),
                    _sample("BUY", "BUY", "BUY", False),
                    _sample("NONE", "NONE", "BUY", False),
                ],
            },
        },
    )

    result = diag._diagnose_session(
        "TEST",
        raw,
    )

    assert result["samples"] == 3
    assert result["book"]["directional"] == 2
    assert result["book"]["buy"] == 2
    assert result["book"]["sell"] == 0
    assert result["book"]["none"] == 1
    assert result["price_action"]["directional"] == 2
    assert result["flow"]["directional"] == 2
    assert result["conflict_context"]["conflict_samples"] == 1
    assert (
        result["conflict_context"][
            "book_directional_during_conflict"
        ]
        == 0
    )


def test_canonical_prospective_book_direction_is_not_reconstructed_from_raw():
    payload = {
        "samples": [
            {
                "imbalance": 0.99,
                "book_status": "VALID",
                "context_ready": True,
            },
        ],
        "prospective_microstructure": {
            "captured_samples": 1,
            "source_analyzable_samples": 1,
            "sample_count_matches_source": True,
            "samples": [
                _sample(
                    pa="BUY",
                    flow="SELL",
                    book="NONE",
                    conflict=True,
                ),
            ],
        },
    }

    samples = diag._extract_samples(payload)

    assert len(samples) == 1
    assert diag._extract_book_direction(samples[0]) == "NONE"

def test_conflict_count_is_canonical_over_directional_disagreement():
    sample = _sample(
        pa="NONE",
        flow="SELL",
        book="BUY",
    )
    sample["conflict_count"] = 0
    sample["state"] = "INSUFFICIENT_DATA"

    assert (
        diag._is_conflict(
            sample,
            "NONE",
            "SELL",
            "BUY",
        )
        is False
    )


def test_positive_conflict_count_is_canonical():
    sample = _sample(
        pa="BUY",
        flow="BUY",
        book="NONE",
    )
    sample["conflict_count"] = 1
    sample["state"] = "CONFLICT"

    assert (
        diag._is_conflict(
            sample,
            "BUY",
            "BUY",
            "NONE",
        )
        is True
    )


def test_state_is_used_when_conflict_count_is_absent():
    sample = _sample(
        pa="BUY",
        flow="BUY",
        book="NONE",
    )
    sample["state"] = "CONFLICT"

    assert (
        diag._is_conflict(
            sample,
            "BUY",
            "BUY",
            "NONE",
        )
        is True
    )


def test_invalid_conflict_count_fails_closed():
    sample = _sample(
        pa="BUY",
        flow="SELL",
        book="NONE",
    )
    sample["conflict_count"] = "INVALID"

    with pytest.raises(
        ValueError,
        match="conflict_count must be integer-compatible",
    ):
        diag._is_conflict(
            sample,
            "BUY",
            "SELL",
            "NONE",
        )


def _valid_prospective_payload(samples=None):
    if samples is None:
        samples = [_sample("BUY", "SELL", "NONE", True)]

    return {
        "prospective_microstructure": {
            "captured_samples": len(samples),
            "source_analyzable_samples": len(samples),
            "sample_count_matches_source": True,
            "samples": samples,
        },
    }


def test_prospective_metadata_contract_accepts_consistent_counts():
    payload = _valid_prospective_payload([
        _sample("BUY", "SELL", "NONE", True),
        _sample("SELL", "BUY", "BUY", False),
    ])
    assert len(diag._extract_samples(payload)) == 2


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("captured_samples", None, "prospective_microstructure.captured_samples must be an integer"),
        ("captured_samples", "2", "prospective_microstructure.captured_samples must be an integer"),
        ("captured_samples", True, "prospective_microstructure.captured_samples must be an integer"),
        ("source_analyzable_samples", None, "prospective_microstructure.source_analyzable_samples must be an integer"),
        ("source_analyzable_samples", "2", "prospective_microstructure.source_analyzable_samples must be an integer"),
        ("source_analyzable_samples", False, "prospective_microstructure.source_analyzable_samples must be an integer"),
    ],
)
def test_prospective_count_metadata_missing_or_invalid_fails_closed(field, value, message):
    payload = _valid_prospective_payload()
    if value is None:
        del payload["prospective_microstructure"][field]
    else:
        payload["prospective_microstructure"][field] = value

    with pytest.raises(ValueError, match=message):
        diag._extract_samples(payload)


@pytest.mark.parametrize("field", ["captured_samples", "source_analyzable_samples"])
def test_prospective_count_metadata_mismatch_fails_closed(field):
    payload = _valid_prospective_payload([
        _sample("BUY", "SELL", "NONE", True),
        _sample("SELL", "BUY", "BUY", False),
    ])
    payload["prospective_microstructure"][field] = 1

    with pytest.raises(ValueError, match="does not match len"):
        diag._extract_samples(payload)


@pytest.mark.parametrize("value", [False, None, 1, "true"])
def test_sample_count_matches_source_must_be_literal_true(value):
    payload = _valid_prospective_payload()
    if value is None:
        del payload["prospective_microstructure"]["sample_count_matches_source"]
    else:
        payload["prospective_microstructure"]["sample_count_matches_source"] = value

    with pytest.raises(
        ValueError,
        match="prospective_microstructure.sample_count_matches_source must be true",
    ):
        diag._extract_samples(payload)


def test_prospective_non_object_sample_fails_closed():
    payload = _valid_prospective_payload([
        _sample("BUY", "SELL", "NONE", True),
        "INVALID_SAMPLE",
    ])

    with pytest.raises(
        ValueError,
        match="prospective_microstructure.samples contains non-object entries",
    ):
        diag._extract_samples(payload)
