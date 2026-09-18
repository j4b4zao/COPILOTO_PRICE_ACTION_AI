"""
Brooks Trailing Active Accumulation Audit V1.

Research-only / observational-only diagnostic.

Consumes chronological outputs from
BROOKS_TRAILING_ACTIVE_SURVIVAL_AUDIT_V1 and reports how the cumulative
trailing-active evidence changes from checkpoint to checkpoint.

This audit:
- does not recalculate entries, stops, exits, MFE, MAE, or performance;
- does not change source evidence or source eligibility;
- preserves input checkpoint order;
- rejects duplicate checkpoints;
- rejects regressions in cumulative counters;
- reports only descriptive deltas between cumulative checkpoints;
- has no operational influence and does not authorize OOS execution.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STAGE = "BROOKS_TRAILING_ACTIVE_ACCUMULATION_AUDIT_V1"
SOURCE_STAGE = "BROOKS_TRAILING_ACTIVE_SURVIVAL_AUDIT_V1"

COUNTER_FIELDS = (
    "lifecycle_episode_count",
    "trailing_active_episode_count",
    "stop_advance_observation_count",
    "stage_3_4_independent_episode_count",
    "stage_3_4_rejected_episode_count",
    "trailing_active_survived_stage_3_4_count",
    "trailing_active_rejected_stage_3_4_count",
    "trailing_active_unresolved_count",
    "surviving_both_arms_exited_count",
    "surviving_both_arms_exit_r_observed_count",
    "surviving_identical_exit_r_count",
    "surviving_different_exit_r_count",
    "surviving_status_difference_count",
)

# Unresolved is a state of cross-check completeness, not cumulative evidence.
# It may legitimately fall after a later checkpoint resolves prior evidence.
MONOTONIC_FIELDS = tuple(
    field
    for field in COUNTER_FIELDS
    if field != "trailing_active_unresolved_count"
)


def _safety() -> dict[str, Any]:
    return {
        "research_only": True,
        "observational_only": True,
        "performance_validated": False,
        "dynamic_management_validated": False,
        "performance_claim_allowed": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "oos_execution_allowed": False,
    }


def _as_non_negative_int(payload: dict[str, Any], field: str) -> int:
    if field not in payload:
        raise ValueError(f"missing required counter: {field}")

    value = payload[field]
    if isinstance(value, bool):
        raise ValueError(f"invalid counter {field}: {value!r}")

    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid counter {field}: {value!r}") from exc

    if integer < 0:
        raise ValueError(f"negative counter {field}: {integer}")

    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"non-integer counter {field}: {value!r}")

    return integer


def _validate_source(payload: dict[str, Any]) -> None:
    if payload.get("stage") != SOURCE_STAGE:
        raise ValueError(
            "unexpected source stage: "
            f"{payload.get('stage')!r}; expected {SOURCE_STAGE!r}"
        )

    if payload.get("status") != "TRAILING_ACTIVE_SURVIVAL_AUDIT_COMPLETED":
        raise ValueError(
            "source survival audit is not completed: "
            f"{payload.get('status')!r}"
        )

    if payload.get("research_only") is not True:
        raise ValueError("source survival audit must be research_only")

    if payload.get("observational_only") is not True:
        raise ValueError("source survival audit must be observational_only")

    if payload.get("performance_validated") is not False:
        raise ValueError(
            "source survival audit must keep performance_validated=False"
        )


def _checkpoint_id(
    payload: dict[str, Any],
    source_path: str,
    index: int,
) -> str:
    explicit = payload.get("checkpoint_id")
    if explicit is not None and str(explicit):
        return str(explicit)

    lifecycle_source = payload.get("lifecycle_source_path")
    stage34_source = payload.get("stage_3_4_source_path")

    if lifecycle_source is not None or stage34_source is not None:
        return f"{lifecycle_source or ''}::{stage34_source or ''}"

    if source_path:
        return source_path

    return f"CHECKPOINT_{index:06d}"


def _counter_snapshot(payload: dict[str, Any]) -> dict[str, int]:
    return {
        field: _as_non_negative_int(payload, field)
        for field in COUNTER_FIELDS
    }


def _validate_internal_counts(counters: dict[str, int]) -> None:
    active = counters["trailing_active_episode_count"]
    survived = counters["trailing_active_survived_stage_3_4_count"]
    rejected = counters["trailing_active_rejected_stage_3_4_count"]
    unresolved = counters["trailing_active_unresolved_count"]

    if survived + rejected + unresolved != active:
        raise ValueError(
            "trailing-active disposition counts do not account for all "
            "trailing-active episodes"
        )

    if counters["stop_advance_observation_count"] < active:
        raise ValueError(
            "stop_advance_observation_count cannot be lower than "
            "trailing_active_episode_count"
        )

    exit_r_observed = counters["surviving_both_arms_exit_r_observed_count"]
    identical = counters["surviving_identical_exit_r_count"]
    different = counters["surviving_different_exit_r_count"]

    if identical + different != exit_r_observed:
        raise ValueError(
            "identical/different Exit-R counts do not account for all "
            "paired Exit-R observations"
        )

    if exit_r_observed > counters["surviving_both_arms_exited_count"]:
        raise ValueError(
            "paired Exit-R observations cannot exceed both-arms-exited count"
        )


def accumulate_payloads(
    payloads: list[dict[str, Any]],
    source_paths: list[str] | None = None,
) -> dict[str, Any]:
    if not payloads:
        raise ValueError("at least one survival audit checkpoint is required")

    if source_paths is None:
        source_paths = ["" for _ in payloads]

    if len(source_paths) != len(payloads):
        raise ValueError("source_paths length must match payload count")

    checkpoints: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    previous: dict[str, int] | None = None

    for index, (payload, source_path) in enumerate(
        zip(payloads, source_paths),
        start=1,
    ):
        if not isinstance(payload, dict):
            raise ValueError(f"checkpoint {index} is not a JSON object")

        _validate_source(payload)
        counters = _counter_snapshot(payload)
        _validate_internal_counts(counters)

        checkpoint_id = _checkpoint_id(payload, source_path, index)
        if checkpoint_id in seen_ids:
            raise ValueError(f"duplicate checkpoint: {checkpoint_id}")
        seen_ids.add(checkpoint_id)

        if previous is None:
            deltas = dict(counters)
        else:
            regressions = [
                field
                for field in MONOTONIC_FIELDS
                if counters[field] < previous[field]
            ]
            if regressions:
                field = regressions[0]
                raise ValueError(
                    "cumulative counter regression at checkpoint "
                    f"{checkpoint_id}: {field} "
                    f"{previous[field]} -> {counters[field]}"
                )

            deltas = {
                field: counters[field] - previous[field]
                for field in COUNTER_FIELDS
            }

        checkpoints.append(
            {
                "checkpoint_index": index,
                "checkpoint_id": checkpoint_id,
                "source_path": source_path or None,
                "lifecycle_source_path": payload.get(
                    "lifecycle_source_path"
                ),
                "stage_3_4_source_path": payload.get(
                    "stage_3_4_source_path"
                ),
                "source_stage": payload.get("stage"),
                "cumulative": counters,
                "delta_from_previous": deltas,
            }
        )
        previous = counters

    final_counters = dict(checkpoints[-1]["cumulative"])

    return {
        "stage": STAGE,
        "status": "TRAILING_ACTIVE_ACCUMULATION_AUDIT_COMPLETED",
        "source_stage_expected": SOURCE_STAGE,
        "checkpoint_count": len(checkpoints),
        "source_paths": list(source_paths),
        "checkpoints": checkpoints,
        "final_cumulative": final_counters,
        **final_counters,
        "validation_reason": (
            "CHRONOLOGICAL_CUMULATIVE_DESCRIPTIVE_RESEARCH_ONLY_"
            "NO_PERFORMANCE_CLAIM"
        ),
        **_safety(),
    }


def accumulate(paths) -> dict[str, Any]:
    source_paths = [str(Path(path)) for path in paths]
    payloads = [
        json.loads(Path(path).read_text(encoding="utf-8-sig"))
        for path in paths
    ]
    return accumulate_payloads(payloads, source_paths)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Brooks chronological trailing-active survival evidence "
            "accumulation audit."
        )
    )
    parser.add_argument(
        "survival_json",
        nargs="+",
        help=(
            "Chronological BROOKS_TRAILING_ACTIVE_SURVIVAL_AUDIT_V1 "
            "JSON reports."
        ),
    )
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = accumulate(args.survival_json)

    text = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(output)
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
