from __future__ import annotations

import copy
import hashlib
import itertools
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

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
    samples = [copy.deepcopy(sample) for sample in samples]
    raw = []
    for index, sample in enumerate(samples):
        timestamp = (datetime(2026, 9, 30) + timedelta(seconds=index)).isoformat()
        sample.update(timestamp=timestamp, cycle=index)
        raw.append({"timestamp": timestamp, "cycle": index})
    return {
        "samples": raw,
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

    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


def test_conflict_count_is_not_a_required_protocol_source():
    payload = _payload(
        [
            {
                "price_action_bias": "BUY",
                "book_direction": "SELL",
            },
            {"price_action_bias": "BUY", "book_direction": "NONE"},
            {"price_action_bias": "BUY", "book_direction": "BUY"},
        ]
    )

    assert evaluator.evaluate_payload(payload)["evaluation_outcome"] == "REPLICATED"


def test_captured_count_mismatch_fails_closed():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
        ]
    )

    payload["prospective_microstructure"][
        "captured_samples"
    ] = 2

    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


def test_source_count_mismatch_fails_closed():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
        ]
    )

    payload["prospective_microstructure"][
        "source_analyzable_samples"
    ] = 2

    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


def test_sample_count_matches_source_must_be_true():
    payload = _payload(
        [
            _sample("BUY", "SELL", 1),
        ]
    )

    payload["prospective_microstructure"][
        "sample_count_matches_source"
    ] = False

    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


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


def _valid_payload():
    return _payload([
        _sample("BUY", "SELL", 1), _sample("BUY", "NONE"),
        _sample("BUY", "BUY"),
    ])


def _assert_not_evaluable(payload, reason):
    before = copy.deepcopy(payload)
    report = evaluator.evaluate_payload(payload)
    assert report["evaluation_outcome"] == report["outcome"] == "NOT_EVALUABLE"
    assert report["reason"] == reason
    assert report["transitions"] == []
    assert payload == before
    return report


@pytest.mark.parametrize("field", ["price_action_bias", "book_direction"])
@pytest.mark.parametrize("index", [0, 1, 2])
def test_missing_required_direction_at_any_position(field, index):
    payload = _valid_payload()
    del payload["prospective_microstructure"]["samples"][index][field]
    report = _assert_not_evaluable(payload, "MISSING_REQUIRED_FORMAL_FIELDS")
    assert report["detail"] == f"missing {field} at index {index}"


@pytest.mark.parametrize("field", ["price_action_bias", "book_direction"])
@pytest.mark.parametrize("value", [None, "", "  "])
def test_empty_direction_is_missing(field, value):
    payload = _valid_payload()
    payload["prospective_microstructure"]["samples"][1][field] = value
    _assert_not_evaluable(payload, "MISSING_REQUIRED_FORMAL_FIELDS")


@pytest.mark.parametrize("field", ["price_action_bias", "book_direction"])
@pytest.mark.parametrize("value", ["INVALID", 1, False, [], {}])
def test_invalid_direction_is_invalid_evidence(field, value):
    payload = _valid_payload()
    payload["prospective_microstructure"]["samples"][1][field] = value
    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


@pytest.mark.parametrize("field", ["captured_samples", "source_analyzable_samples"])
@pytest.mark.parametrize("value", [None, True, "3", -1, 2, 4])
def test_invalid_capture_counter(field, value):
    payload = _valid_payload()
    payload["prospective_microstructure"][field] = value
    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


@pytest.mark.parametrize("value", [False, None, 1, "true"])
def test_capture_flag_requires_literal_true(value):
    payload = _valid_payload()
    payload["prospective_microstructure"]["sample_count_matches_source"] = value
    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


@pytest.mark.parametrize("payload", [
    None, [], {}, {"prospective_microstructure": []},
    {"prospective_microstructure": {"samples": None}},
    {"prospective_microstructure": {"samples": [None]}},
])
def test_invalid_required_structure(payload):
    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")


@pytest.mark.parametrize("case", ["missing", "null", "object", "non_object", "short", "long"])
def test_missing_or_incompatible_raw_is_not_evaluable(case):
    payload = _valid_payload()
    if case == "missing":
        del payload["samples"]
    elif case == "null":
        payload["samples"] = None
    elif case == "object":
        payload["samples"] = {}
    elif case == "non_object":
        payload["samples"][1] = None
    elif case == "short":
        payload["samples"].pop()
    else:
        payload["samples"].append(copy.deepcopy(payload["samples"][-1]))
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("side", ["raw", "prospective"])
def test_timestamp_mismatch_at_any_position(index, side):
    payload = _valid_payload()
    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])
    rows[index]["timestamp"] += ".500000"
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")


@pytest.mark.parametrize("side", ["raw", "prospective"])
@pytest.mark.parametrize("value", [None, "", "invalid", 123])
def test_missing_or_invalid_timestamp(side, value):
    payload = _valid_payload()
    rows = (payload["samples"] if side == "raw"
            else payload["prospective_microstructure"]["samples"])
    rows[1]["timestamp"] = value
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")


@pytest.mark.parametrize("case", ["raw_time_regression", "cycle_regression",
                                 "cycle_bool", "cycle_missing", "cycle_mismatch",
                                 "mixed_timezone", "prospective_reordered"])
def test_duration_identity_and_order_fail_closed_without_crash(case):
    payload = _valid_payload()
    raw = payload["samples"]
    prospective = payload["prospective_microstructure"]["samples"]
    if case == "raw_time_regression":
        raw[1]["timestamp"] = "2026-09-29T23:59:59"
        prospective[1]["timestamp"] = raw[1]["timestamp"]
    elif case == "cycle_regression":
        raw[1]["cycle"] = -1
    elif case == "cycle_bool":
        raw[1]["cycle"] = True
    elif case == "cycle_missing":
        del raw[1]["cycle"]
    elif case == "cycle_mismatch":
        prospective[1]["cycle"] = 100
    elif case == "mixed_timezone":
        raw[1]["timestamp"] += "+00:00"
    else:
        prospective.reverse()
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")


def test_equivalent_iso_timestamps_and_optional_prospective_cycle():
    payload = _valid_payload()
    for sample in payload["prospective_microstructure"]["samples"]:
        sample["timestamp"] += ".000000"
        del sample["cycle"]
    assert evaluator.evaluate_payload(payload)["evaluation_outcome"] == "REPLICATED"


def test_gate_precedence_is_deterministic():
    payload = _valid_payload()
    del payload["samples"]
    del payload["prospective_microstructure"]["samples"][1]["book_direction"]
    payload["prospective_microstructure"]["captured_samples"] = 100
    _assert_not_evaluable(payload, "CAPTURE_INTEGRITY_FAILURE")
    payload["prospective_microstructure"]["captured_samples"] = 3
    _assert_not_evaluable(payload, "MISSING_REQUIRED_FORMAL_FIELDS")
    payload["prospective_microstructure"]["samples"][1]["book_direction"] = "NONE"
    _assert_not_evaluable(payload, "POSITIONAL_IDENTITY_FAILURE")


def test_empty_but_consistent_capture_has_no_transition():
    _assert_not_evaluable(_payload([]), "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION")


@pytest.mark.parametrize("book,condition", [
    ("BUY", "at_least_one_intermediate_book_none"),
    ("SELL", "no_intermediate_book_direction_opposite_to_start_pa_direction_after_opposed_run_end"),
])
def test_nonempty_gap_violating_book_conditions(book, condition):
    payload = _payload([_sample("BUY", "SELL"), _sample("NONE", book),
                        _sample("BUY", "BUY")])
    report = evaluator.evaluate_payload(payload)
    assert report["evaluation_outcome"] == "NOT_REPLICATED"
    assert report["transitions"][0]["conditions"][condition] is False


def test_mixed_transitions_have_individual_outcomes_and_separate_summary():
    payload = _payload([
        _sample("BUY", "SELL"), _sample("BUY", "NONE"), _sample("BUY", "BUY"),
        _sample("SELL", "BUY"), _sample("SELL", "SELL"),
    ])
    report = evaluator.evaluate_payload(payload)
    assert report["evaluation_unit"] == "formal_OPPOSED_to_ALIGNED_transition"
    assert report["outcome_scope"] == "SESSION_SUMMARY"
    assert report["evaluation_outcome"] == "NOT_REPLICATED"
    assert [t["evaluation_outcome"] for t in report["transitions"]] == [
        "REPLICATED", "NOT_REPLICATED",
    ]


def test_formal_runs_match_persistence_for_all_three_sample_direction_paths():
    pairs = list(itertools.product(("BUY", "SELL", "NONE"), repeat=2))
    for path in itertools.product(pairs, repeat=3):
        samples = [_sample(pa, book, i % 2) for i, (pa, book) in enumerate(path)]
        expected_runs, expected_counts = evaluator.persistence._build_runs(samples)
        runs, counts = evaluator._build_formal_runs(samples)
        for run in expected_runs:
            del run["canonical_conflict_samples"]
        assert runs == expected_runs
        assert counts == expected_counts


@pytest.mark.parametrize("field", ["recent_delta", "acceleration", "imbalance",
                                  "spread", "candle_evidence", "conflict_count"])
def test_diagnostics_never_change_evaluation(field):
    payload = _valid_payload()
    expected = evaluator.evaluate_payload(payload)
    for value in (None, -1e100, 0, 1e100, "invalid", {"BUY": 1}):
        altered = copy.deepcopy(payload)
        for sample in altered["samples"] + altered["prospective_microstructure"]["samples"]:
            sample[field] = value
        assert evaluator.evaluate_payload(altered) == expected


@pytest.mark.parametrize("gap,seconds", [(1, 0), (1, 86400), (100, 0.000001), (100, 86400)])
def test_no_gap_length_or_time_threshold(gap, seconds):
    payload = _payload([_sample("BUY", "SELL")] + [_sample("BUY", "NONE")] * gap
                       + [_sample("BUY", "BUY")])
    for index, (raw, prospective) in enumerate(zip(
            payload["samples"], payload["prospective_microstructure"]["samples"])):
        timestamp = (datetime(2026, 9, 30) + timedelta(seconds=index * seconds)).isoformat()
        raw["timestamp"] = prospective["timestamp"] = timestamp
    assert evaluator.evaluate_payload(payload)["evaluation_outcome"] == "REPLICATED"


@pytest.mark.parametrize("case", ["sha", "version", "status", "safety"])
@pytest.mark.parametrize("entry", ["payload", "file"])
def test_protocol_corruption_is_hard_failure(tmp_path, monkeypatch, case, entry):
    protocol = json.loads(evaluator.PROTOCOL_PATH.read_text(encoding="utf-8"))
    if case == "version":
        protocol["version"] = "INVALID"
    elif case == "status":
        protocol["status"] = "UNFROZEN"
    elif case == "safety":
        protocol["research_scope"]["score_changed"] = True
    path = tmp_path / "protocol.json"
    path.write_text(json.dumps(protocol), encoding="utf-8")
    if case != "sha":
        # Isolate semantic checks beyond the production SHA gate, without
        # modifying the real frozen protocol or its production expected hash.
        monkeypatch.setattr(evaluator, "EXPECTED_PROTOCOL_SHA256",
                            hashlib.sha256(path.read_bytes()).hexdigest())
    match = {"sha": "SHA256", "version": "version", "status": "frozen",
             "safety": "safety field"}[case]
    with pytest.raises(ValueError, match=match):
        if entry == "payload":
            evaluator.evaluate_payload(None, protocol_path=path)
        else:
            evaluator.evaluate_file(tmp_path / "missing.json", protocol_path=path)


@pytest.mark.parametrize("content", [None, "{", "[]", "{}", b"\xff"])
def test_session_file_evidence_failure_returns_not_evaluable(tmp_path, content):
    path = tmp_path / "session.json"
    if isinstance(content, bytes):
        path.write_bytes(content)
    elif content is not None:
        path.write_text(content, encoding="utf-8")
    report = evaluator.evaluate_file(path)
    assert report["evaluation_outcome"] == "NOT_EVALUABLE"
    assert report["reason"] == "CAPTURE_INTEGRITY_FAILURE"


@pytest.mark.parametrize("valid", [True, False])
def test_passive_contract_applies_to_evaluable_and_invalid_evidence(valid):
    report = evaluator.evaluate_payload(_valid_payload() if valid else None)
    protocol = json.loads(evaluator.PROTOCOL_PATH.read_text(encoding="utf-8"))
    for key, value in protocol["research_scope"].items():
        assert report["safety"][key] is value
    assert report["cohort_policy"] == protocol["cohort_policy"]
    assert report["interpretation_policy"] == protocol["interpretation_policy"]
    assert report["interpretation"] == "DESCRIPTIVE_ONLY"


def test_independent_evaluations_preserve_frozen_checkpoint_and_session_files(tmp_path):
    checkpoint = Path("prospective_microstructure_conflict_10session_checkpoint_20260926.json")
    frozen_before = checkpoint.read_bytes()
    # Synthetic independent sessions only; no real session is collected/reclassified.
    paths = [tmp_path / f"independent_{i}.json" for i in (11, 12)]
    for path in paths:
        path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
    before = [p.read_bytes() for p in paths]
    reports = [evaluator.evaluate_file(p) for p in paths]
    assert [p.read_bytes() for p in paths] == before
    assert checkpoint.read_bytes() == frozen_before
    assert [r["identity"]["opposed_to_aligned_transition_count"] for r in reports] == [1, 1]
    assert all(r["cohort_policy"]["sessions_11_and_12_remain_independent"] for r in reports)


@pytest.mark.parametrize("target", ["session", "checkpoint", "protocol"])
def test_cli_refuses_to_overwrite_existing_artifacts(tmp_path, monkeypatch, target):
    session = tmp_path / "session.json"
    session.write_text(json.dumps(_valid_payload()), encoding="utf-8")
    # Protected destinations are synthetic files within pytest basetemp.
    output = session if target == "session" else tmp_path / f"{target}.json"
    if output != session:
        output.write_text("frozen artifact", encoding="utf-8")
    before = output.read_bytes()
    monkeypatch.setattr(sys, "argv", ["evaluator", str(session), "--output", str(output)])
    with pytest.raises(FileExistsError):
        evaluator.main()
    assert output.read_bytes() == before


def test_cli_writes_new_report_only(tmp_path, monkeypatch, capsys):
    session = tmp_path / "session.json"
    session.write_text(json.dumps(_valid_payload()), encoding="utf-8")
    before = session.read_bytes()
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys, "argv", ["evaluator", str(session), "--output", str(output)])
    evaluator.main()
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report == json.loads(capsys.readouterr().out)
    assert report["evaluation_outcome"] == "REPLICATED"
    assert session.read_bytes() == before
