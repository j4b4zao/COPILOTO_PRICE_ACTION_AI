"""Prospective evaluator for the frozen PA x Book structural replication protocol RC1.

Research-only. Descriptive-only. No operational promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools import (
    prospective_microstructure_pa_book_temporal_duration_audit as duration,
    prospective_microstructure_pa_book_temporal_persistence_audit
    as persistence,
)


VERSION = (
    "RC1-PA-BOOK-OPPOSED-TO-ALIGNED-"
    "PROSPECTIVE-REPLICATION-EVALUATOR"
)

PROTOCOL_PATH = Path(
    "pa_book_opposed_to_aligned_"
    "prospective_replication_protocol_rc1_20260929.json"
)

EXPECTED_PROTOCOL_SHA256 = (
    "53efb327f613934c483f6bec36ffe04bd"
    "98743b2973815f3b54ec2b84e91f01c"
)

EXPECTED_PROTOCOL_VERSION = (
    "RC1-PA-BOOK-OPPOSED-TO-ALIGNED-"
    "PROSPECTIVE-REPLICATION-PROTOCOL"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"protocol not found: {path}")

    actual_sha = _sha256(path)

    if actual_sha != EXPECTED_PROTOCOL_SHA256:
        raise ValueError(
            "protocol SHA256 mismatch: "
            f"expected={EXPECTED_PROTOCOL_SHA256} "
            f"actual={actual_sha}"
        )

    payload = json.loads(path.read_text(encoding="utf-8"))

    if payload.get("version") != EXPECTED_PROTOCOL_VERSION:
        raise ValueError("protocol version mismatch")

    if payload.get("status") != "FROZEN_BEFORE_FUTURE_COLLECTION":
        raise ValueError("protocol is not frozen")

    scope = payload.get("research_scope")

    if not isinstance(scope, dict):
        raise ValueError("missing research_scope")

    if scope.get("research_only") is not True:
        raise ValueError("research_only must be true")

    if scope.get("descriptive_only") is not True:
        raise ValueError("descriptive_only must be true")

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
    ):
        if scope.get(field) is not False:
            raise ValueError(
                f"protocol safety field must remain false: {field}"
            )

    return payload


def _load_session(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"session not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("session payload must be a JSON object")

    return payload


def _direction(
    sample: dict[str, Any],
    field: str,
    index: int,
) -> str:
    return persistence._normalize_direction(
        sample.get(field),
        field,
        index,
    )


def _pair_pa_direction(pair: str) -> str:
    parts = pair.split("_")

    if len(parts) != 2:
        raise ValueError(f"invalid formal pair: {pair!r}")

    pa, book = parts

    if pa not in {"BUY", "SELL"}:
        raise ValueError(f"invalid PA in pair: {pair!r}")

    if book not in {"BUY", "SELL"}:
        raise ValueError(f"invalid Book in pair: {pair!r}")

    return pa


def _evaluate_transition(
    samples: list[dict[str, Any]],
    previous: dict[str, Any],
    following: dict[str, Any],
) -> dict[str, Any]:
    if previous["relation"] != "OPPOSED":
        raise ValueError("previous run must be OPPOSED")

    if following["relation"] != "ALIGNED":
        raise ValueError("following run must be ALIGNED")

    opposed_end = previous["end_index"]
    aligned_start = following["start_index"]

    if aligned_start <= opposed_end:
        raise ValueError("invalid transition ordering")

    start_pa = _pair_pa_direction(previous["pair"])
    end_pa = _pair_pa_direction(following["pair"])

    gap_start = opposed_end + 1
    gap_end = aligned_start - 1

    intermediate_indices = list(
        range(gap_start, aligned_start)
    )

    intermediate_rows: list[dict[str, Any]] = []

    for index in intermediate_indices:
        sample = samples[index]

        pa = _direction(
            sample,
            "price_action_bias",
            index,
        )
        book = _direction(
            sample,
            "book_direction",
            index,
        )

        intermediate_rows.append(
            {
                "index": index,
                "price_action_bias": pa,
                "book_direction": book,
            }
        )

    same_pa_direction = start_pa == end_pa

    at_least_one_intermediate_sample = (
        len(intermediate_rows) >= 1
    )

    all_intermediate_pa_same = (
        at_least_one_intermediate_sample
        and all(
            row["price_action_bias"] == start_pa
            for row in intermediate_rows
        )
    )

    at_least_one_book_none = (
        at_least_one_intermediate_sample
        and any(
            row["book_direction"] == "NONE"
            for row in intermediate_rows
        )
    )

    opposite_to_start_pa = (
        "SELL" if start_pa == "BUY" else "BUY"
    )

    no_intermediate_opposing_book = (
        at_least_one_intermediate_sample
        and all(
            row["book_direction"] != opposite_to_start_pa
            for row in intermediate_rows
        )
    )

    conditions = {
        "same_pa_direction_from_opposed_end_to_aligned_start":
            same_pa_direction,
        "at_least_one_intermediate_sample":
            at_least_one_intermediate_sample,
        "all_intermediate_pa_directions_equal_start_pa_direction":
            all_intermediate_pa_same,
        "at_least_one_intermediate_book_none":
            at_least_one_book_none,
        "no_intermediate_book_direction_opposite_to_start_pa_direction_after_opposed_run_end":
            no_intermediate_opposing_book,
    }

    replicated = all(conditions.values())

    return {
        "evaluation_outcome": "REPLICATED" if replicated else "NOT_REPLICATED",
        "previous_relation": previous["relation"],
        "previous_pair": previous["pair"],
        "previous_start_index": previous["start_index"],
        "previous_end_index": opposed_end,
        "following_relation": following["relation"],
        "following_pair": following["pair"],
        "following_start_index": aligned_start,
        "following_end_index": following["end_index"],
        "gap_samples": len(intermediate_rows),
        "start_pa_direction": start_pa,
        "end_pa_direction": end_pa,
        "conditions": conditions,
        "replicated": replicated,
    }


def _validate_positional_identity(
    payload: dict[str, Any], samples: list[dict[str, Any]],
) -> None:
    # Duration establishes equal counts, index mapping and raw time/cycle order.
    # It does not compare prospective timestamps; require that evidence here.
    raw_samples = duration._validate_raw_samples(payload, samples)
    for index, (raw, prospective) in enumerate(zip(raw_samples, samples)):
        raw_time = duration._parse_timestamp(raw.get("timestamp"), index)
        prospective_time = duration._parse_timestamp(
            prospective.get("timestamp"), index,
        )
        if raw_time != prospective_time:
            raise ValueError(f"raw/prospective timestamp mismatch at index {index}")
        if "cycle" in prospective:
            cycle = duration._validate_cycle(prospective["cycle"], index)
            if cycle != raw["cycle"]:
                raise ValueError(f"raw/prospective cycle mismatch at index {index}")


def _build_formal_runs(
    samples: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Persistence RC1 run semantics without its unrelated conflict telemetry.

    conflict_count is not a protocol source field. Do not invent a canonical
    conflict value or make this diagnostic attribute an admission gate.
    """
    runs: list[dict[str, Any]] = []
    counts = {"aligned_samples": 0, "opposed_samples": 0}
    for index, sample in enumerate(samples):
        pa = _direction(sample, "price_action_bias", index)
        book = _direction(sample, "book_direction", index)
        relation = persistence._relation(pa, book)
        if relation is None:
            continue
        pair = persistence._pair(pa, book)
        counts[f"{relation.lower()}_samples"] += 1
        if (runs and runs[-1]["end_index"] + 1 == index
                and runs[-1]["pair"] == pair
                and runs[-1]["relation"] == relation):
            runs[-1]["end_index"] = index
            runs[-1]["length"] += 1
        else:
            runs.append({"relation": relation, "pair": pair,
                         "start_index": index, "end_index": index, "length": 1})
    counts["simultaneous_directional_samples"] = (
        counts["aligned_samples"] + counts["opposed_samples"]
    )
    return runs, counts


def _evaluate_session(
    payload: Any, protocol_path: Path, protocol: dict[str, Any],
) -> dict[str, Any]:
    # Deterministic precedence: structure/counters, missing directions, invalid
    # directions, positional identity, then formal transition/hypothesis.
    try:
        samples = persistence._validate_prospective(payload)
    except ValueError as exc:
        return _report(protocol_path, protocol, "NOT_EVALUABLE",
                       "CAPTURE_INTEGRITY_FAILURE", detail=str(exc))

    for index, sample in enumerate(samples):
        for field in ("price_action_bias", "book_direction"):
            value = sample.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return _report(
                    protocol_path, protocol, "NOT_EVALUABLE",
                    "MISSING_REQUIRED_FORMAL_FIELDS",
                    detail=f"missing {field} at index {index}",
                )
    try:
        runs, counts = _build_formal_runs(samples)
    except ValueError as exc:
        return _report(protocol_path, protocol, "NOT_EVALUABLE",
                       "CAPTURE_INTEGRITY_FAILURE", detail=str(exc))

    try:
        _validate_positional_identity(payload, samples)
    except (ValueError, TypeError) as exc:
        return _report(protocol_path, protocol, "NOT_EVALUABLE",
                       "POSITIONAL_IDENTITY_FAILURE", detail=str(exc))

    candidates: list[dict[str, Any]] = []

    for previous, following in zip(runs, runs[1:]):
        if (
            previous["relation"] == "OPPOSED"
            and following["relation"] == "ALIGNED"
        ):
            candidates.append(
                _evaluate_transition(
                    samples,
                    previous,
                    following,
                )
            )

    if not candidates:
        outcome = "NOT_EVALUABLE"
        reason = "NO_FORMAL_OPPOSED_TO_ALIGNED_TRANSITION"

    elif all(
        candidate["replicated"]
        for candidate in candidates
    ):
        outcome = "REPLICATED"
        reason = "ALL_OBSERVED_TARGET_TRANSITIONS_REPLICATED"

    else:
        outcome = "NOT_REPLICATED"
        reason = "AT_LEAST_ONE_TARGET_TRANSITION_FAILED_PROTOCOL"

    identity = {
        "prospective_sample_count": len(samples),
        "raw_sample_count": len(payload["samples"]),
        "raw_prospective_positional_identity": "VALIDATED",
        "formal_run_count": len(runs),
        **counts,
        "opposed_to_aligned_transition_count": len(candidates),
    }
    return _report(protocol_path, protocol, outcome, reason,
                   identity=identity, transitions=candidates)


def _report(
    protocol_path: Path, protocol: dict[str, Any], outcome: str, reason: str,
    *, identity: dict[str, Any] | None = None,
    transitions: list[dict[str, Any]] | None = None, detail: str | None = None,
) -> dict[str, Any]:
    return {
        "version": VERSION,
        "status": "COMPLETED",
        "evaluation_outcome": outcome,
        # Retain the RC1 field for existing consumers; individual transition
        # outcomes remain explicit, separate from this session summary.
        "outcome": outcome,
        "outcome_scope": "SESSION_SUMMARY",
        "evaluation_unit": protocol["future_evaluation"]["unit"],
        "reason": reason,
        "detail": detail,
        "protocol": {
            "path": str(protocol_path),
            "sha256": EXPECTED_PROTOCOL_SHA256,
            "version": EXPECTED_PROTOCOL_VERSION,
        },
        "identity": identity,
        "transitions": transitions if transitions is not None else [],
        "cohort_policy": dict(protocol["cohort_policy"]),
        "interpretation_policy": dict(protocol["interpretation_policy"]),
        "safety": {
            "research_only": True,
            "descriptive_only": True,
            "operational_logic_changed": False,
            "score_changed": False,
            "risk_changed": False,
            "decision_changed": False,
            "alert_changed": False,
            "execution_changed": False,
            "rc17_changed": False,
            "threshold_changed": False,
            "canonical_conflict_redefined": False,
            "checkpoint_extended": False,
            "predictive_claim_allowed": False,
            "post_hoc_gate_added": False,
        },
        "interpretation": "DESCRIPTIVE_ONLY",
    }


def evaluate_payload(
    payload: Any,
    protocol_path: Path = PROTOCOL_PATH,
) -> dict[str, Any]:
    # Protocol corruption is a hard failure, outside session-evidence handling.
    protocol = _load_protocol(protocol_path)
    return _evaluate_session(payload, protocol_path, protocol)


def evaluate_file(
    session_path: Path,
    protocol_path: Path = PROTOCOL_PATH,
) -> dict[str, Any]:
    protocol = _load_protocol(protocol_path)
    try:
        payload = _load_session(session_path)
    except (OSError, ValueError) as exc:
        return _report(protocol_path, protocol, "NOT_EVALUABLE",
                       "CAPTURE_INTEGRITY_FAILURE", detail=str(exc))
    return _evaluate_session(payload, protocol_path, protocol)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "session",
        type=Path,
        help="Prospective session JSON to evaluate.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )

    args = parser.parse_args()

    report = evaluate_file(args.session)

    text = json.dumps(
        report,
        indent=2,
        sort_keys=True,
    )

    if args.output is not None:
        # Never overwrite a session, protocol, checkpoint or existing artifact.
        with args.output.open("x", encoding="utf-8") as handle:
            handle.write(text + "\n")

    print(text)


if __name__ == "__main__":
    main()
