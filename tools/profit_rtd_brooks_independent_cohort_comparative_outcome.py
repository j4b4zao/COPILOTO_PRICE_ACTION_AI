"""Stage 3.5 - Brooks Independent Cohort Comparative Outcome Research.

Research-only utility.

Consumes the Stage 3.4 independent-episode cohort and compares baseline versus
trailing only across the already-selected independent paired episodes.

This module does NOT:
- select or deduplicate episodes;
- recalculate entries, stops, targets, MFE, MAE, or exits;
- infer missing outcomes;
- validate performance;
- influence Score, Risk, Decision, Alert, or order execution.

It only summarizes already-captured paired outcome evidence from Stage 3.4.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from statistics import mean, median
from typing import Any


STAGE = "BROOKS_STAGE_3_5_INDEPENDENT_COHORT_COMPARATIVE_OUTCOME_V1"
EXPECTED_SOURCE_STAGE = "BROOKS_STAGE_3_4_INDEPENDENT_EPISODE_RESEARCH_V1"


def _safety() -> dict[str, Any]:
    return {
        "research_only": True,
        "observational_only": True,
        "performance_validated": False,
        "dynamic_management_validated": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "performance_claim_allowed": False,
    }


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None}
    return {
        "count": len(values),
        "mean": mean(values),
        "median": median(values),
    }


def _outcome(ep: dict[str, Any], key: str) -> dict[str, Any]:
    value = ep.get(key)
    return value if isinstance(value, dict) else {}


def _status_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        outcome = _outcome(row, key)
        status = outcome.get("status")
        label = str(status) if status is not None else "UNKNOWN"
        counts[label] = counts.get(label, 0) + 1
    return counts


def _exit_type_counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        outcome = _outcome(row, key)
        exit_type = outcome.get("exit_type")
        label = str(exit_type) if exit_type is not None else "NONE"
        counts[label] = counts.get(label, 0) + 1
    return counts


def _metric_values(rows: list[dict[str, Any]], key: str, field: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        value = _number(_outcome(row, key).get(field))
        if value is not None:
            values.append(value)
    return values


def _paired_delta_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build paired deltas only when both arms expose the same metric.

    Positive delta means trailing > baseline for MFE/exit R and
    trailing > baseline for MAE as a raw numeric difference. No claim is made
    that a positive/negative delta is better or worse.
    """
    result: list[dict[str, Any]] = []
    fields = ("exit_r", "confirmed_mfe_r", "possible_mfe_r", "bounded_mae_r")

    for row in rows:
        baseline = _outcome(row, "baseline")
        trailing = _outcome(row, "trailing")
        deltas: dict[str, Any] = {}

        for field in fields:
            b = _number(baseline.get(field))
            t = _number(trailing.get(field))
            deltas[f"{field}_delta_trailing_minus_baseline"] = (
                t - b if b is not None and t is not None else None
            )

        result.append(
            {
                "episode_id": row.get("episode_id"),
                "session": row.get("session"),
                "direction": row.get("direction"),
                "baseline_status": baseline.get("status"),
                "trailing_status": trailing.get("status"),
                "baseline_exit_type": baseline.get("exit_type"),
                "trailing_exit_type": trailing.get("exit_type"),
                "baseline_exit_r": baseline.get("exit_r"),
                "trailing_exit_r": trailing.get("exit_r"),
                **deltas,
            }
        )
    return result


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    source_stage = payload.get("stage")
    episodes = payload.get("independent_episodes")
    if not isinstance(episodes, list):
        episodes = []

    paired_rows: list[dict[str, Any]] = []
    rejected_rows: list[dict[str, Any]] = []

    for ordinal, ep in enumerate(episodes):
        if not isinstance(ep, dict):
            rejected_rows.append(
                {"source_ordinal": ordinal, "reason": "EPISODE_NOT_OBJECT"}
            )
            continue

        baseline = _outcome(ep, "baseline")
        trailing = _outcome(ep, "trailing")
        if not baseline or not trailing:
            rejected_rows.append(
                {
                    "source_ordinal": ordinal,
                    "episode_id": ep.get("episode_id"),
                    "reason": "PAIRED_BASELINE_TRAILING_REQUIRED",
                }
            )
            continue

        paired_rows.append(ep)

    baseline_exit_r = _metric_values(paired_rows, "baseline", "exit_r")
    trailing_exit_r = _metric_values(paired_rows, "trailing", "exit_r")
    baseline_confirmed_mfe = _metric_values(
        paired_rows, "baseline", "confirmed_mfe_r"
    )
    trailing_confirmed_mfe = _metric_values(
        paired_rows, "trailing", "confirmed_mfe_r"
    )
    baseline_possible_mfe = _metric_values(
        paired_rows, "baseline", "possible_mfe_r"
    )
    trailing_possible_mfe = _metric_values(
        paired_rows, "trailing", "possible_mfe_r"
    )
    baseline_bounded_mae = _metric_values(
        paired_rows, "baseline", "bounded_mae_r"
    )
    trailing_bounded_mae = _metric_values(
        paired_rows, "trailing", "bounded_mae_r"
    )

    delta_rows = _paired_delta_rows(paired_rows)
    exit_r_deltas = [
        x["exit_r_delta_trailing_minus_baseline"]
        for x in delta_rows
        if x["exit_r_delta_trailing_minus_baseline"] is not None
    ]
    confirmed_mfe_deltas = [
        x["confirmed_mfe_r_delta_trailing_minus_baseline"]
        for x in delta_rows
        if x["confirmed_mfe_r_delta_trailing_minus_baseline"] is not None
    ]
    possible_mfe_deltas = [
        x["possible_mfe_r_delta_trailing_minus_baseline"]
        for x in delta_rows
        if x["possible_mfe_r_delta_trailing_minus_baseline"] is not None
    ]
    bounded_mae_deltas = [
        x["bounded_mae_r_delta_trailing_minus_baseline"]
        for x in delta_rows
        if x["bounded_mae_r_delta_trailing_minus_baseline"] is not None
    ]

    return {
        "stage": STAGE,
        "status": (
            "INDEPENDENT_COHORT_COMPARATIVE_OUTCOME_COMPLETED"
            if paired_rows
            else "NO_PAIRED_INDEPENDENT_EPISODES_AVAILABLE"
        ),
        "source_stage": source_stage,
        "source_stage_expected": EXPECTED_SOURCE_STAGE,
        "source_stage_matches_expected": source_stage == EXPECTED_SOURCE_STAGE,
        "source_independent_episode_count": payload.get(
            "independent_episode_count", len(episodes)
        ),
        "paired_episode_count": len(paired_rows),
        "rejected_episode_count": len(rejected_rows),
        "baseline_status_counts": _status_counts(paired_rows, "baseline"),
        "trailing_status_counts": _status_counts(paired_rows, "trailing"),
        "baseline_exit_type_counts": _exit_type_counts(paired_rows, "baseline"),
        "trailing_exit_type_counts": _exit_type_counts(paired_rows, "trailing"),
        "baseline_exit_r": _stats(baseline_exit_r),
        "trailing_exit_r": _stats(trailing_exit_r),
        "baseline_confirmed_mfe_r": _stats(baseline_confirmed_mfe),
        "trailing_confirmed_mfe_r": _stats(trailing_confirmed_mfe),
        "baseline_possible_mfe_r": _stats(baseline_possible_mfe),
        "trailing_possible_mfe_r": _stats(trailing_possible_mfe),
        "baseline_bounded_mae_r": _stats(baseline_bounded_mae),
        "trailing_bounded_mae_r": _stats(trailing_bounded_mae),
        "paired_exit_r_delta_trailing_minus_baseline": _stats(exit_r_deltas),
        "paired_confirmed_mfe_r_delta_trailing_minus_baseline": _stats(
            confirmed_mfe_deltas
        ),
        "paired_possible_mfe_r_delta_trailing_minus_baseline": _stats(
            possible_mfe_deltas
        ),
        "paired_bounded_mae_r_delta_trailing_minus_baseline": _stats(
            bounded_mae_deltas
        ),
        "paired_comparisons": delta_rows,
        "rejected_episodes": rejected_rows,
        "source_snapshot": {
            "deduplication_policy": payload.get("deduplication_policy"),
            "paired_interval_policy": payload.get("paired_interval_policy"),
            "deduplication_reduction_count": payload.get(
                "deduplication_reduction_count"
            ),
            "deduplication_reduction_rate": payload.get(
                "deduplication_reduction_rate"
            ),
            "no_post_entry_evidence_count": payload.get(
                "no_post_entry_evidence_count"
            ),
        },
        "validation_reason": (
            "INDEPENDENT_PAIRED_DESCRIPTIVE_RESEARCH_ONLY_NO_PERFORMANCE_CLAIM"
        ),
        **_safety(),
    }


def audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return build_report(payload)


def audit(path_or_payload) -> dict[str, Any]:
    if isinstance(path_or_payload, dict):
        return audit_payload(path_or_payload)

    path = Path(path_or_payload)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    report = audit_payload(payload)
    report["source_path"] = str(path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 3.5 Brooks independent cohort comparative outcome."
    )
    parser.add_argument("stage_3_4_report")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = audit(args.stage_3_4_report)
    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(output)
    else:
        print(text)


if __name__ == "__main__":
    main()
