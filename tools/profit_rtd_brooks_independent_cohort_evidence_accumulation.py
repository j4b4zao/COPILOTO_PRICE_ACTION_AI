"""Stage 3.6 - Brooks Independent Cohort Evidence Accumulation.

Research-only utility.

Accumulates multiple Stage 3.5 independent-cohort comparative reports without
recalculating market outcomes. Each source report remains a separate evidence
unit. Duplicate source sessions / duplicate paired episode IDs are detected and
excluded from aggregate evidence.

No performance, prediction, promotion, score, risk, decision, alert, or order
execution claim is permitted by this module.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median
from typing import Any


STAGE = "BROOKS_STAGE_3_6_INDEPENDENT_COHORT_EVIDENCE_ACCUMULATION_V1"
EXPECTED_SOURCE_STAGE = "BROOKS_STAGE_3_5_INDEPENDENT_COHORT_COMPARATIVE_OUTCOME_V1"


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
    return {"count": len(values), "mean": mean(values), "median": median(values)}


def _comparison_key(row: dict[str, Any], report_index: int, row_index: int) -> str:
    session = row.get("session")
    episode_id = row.get("episode_id")
    if session is not None and episode_id is not None:
        return f"{session}::{episode_id}"
    if episode_id is not None:
        return f"EPISODE::{episode_id}"
    return f"UNKNOWN::{report_index:06d}::{row_index:06d}"


def _source_identity(report: dict[str, Any], report_index: int) -> str:
    source_path = report.get("source_path")
    if source_path:
        return str(source_path)
    comparisons = report.get("paired_comparisons")
    if isinstance(comparisons, list):
        sessions = sorted(
            {
                str(x.get("session"))
                for x in comparisons
                if isinstance(x, dict) and x.get("session") is not None
            }
        )
        if sessions:
            return "SESSIONS::" + "||".join(sessions)
    return f"UNKNOWN_REPORT_{report_index:06d}"


def accumulate_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    accepted_reports = []
    rejected_reports = []
    accepted_comparisons = []
    duplicate_comparisons = []
    seen_sources: set[str] = set()
    seen_comparisons: set[str] = set()

    for report_index, report in enumerate(reports):
        if not isinstance(report, dict):
            rejected_reports.append(
                {"report_index": report_index, "reason": "REPORT_NOT_OBJECT"}
            )
            continue

        if report.get("stage") != EXPECTED_SOURCE_STAGE:
            rejected_reports.append(
                {
                    "report_index": report_index,
                    "reason": "UNEXPECTED_SOURCE_STAGE",
                    "source_stage": report.get("stage"),
                }
            )
            continue

        source_identity = _source_identity(report, report_index)
        if source_identity in seen_sources:
            rejected_reports.append(
                {
                    "report_index": report_index,
                    "reason": "DUPLICATE_SOURCE_REPORT",
                    "source_identity": source_identity,
                }
            )
            continue
        seen_sources.add(source_identity)

        comparisons = report.get("paired_comparisons")
        if not isinstance(comparisons, list):
            comparisons = []

        accepted_reports.append(
            {
                "report_index": report_index,
                "source_identity": source_identity,
                "paired_episode_count": report.get("paired_episode_count"),
                "source_path": report.get("source_path"),
                "validation_reason": report.get("validation_reason"),
            }
        )

        for row_index, row in enumerate(comparisons):
            if not isinstance(row, dict):
                continue
            key = _comparison_key(row, report_index, row_index)
            if key in seen_comparisons:
                duplicate_comparisons.append(
                    {
                        "report_index": report_index,
                        "row_index": row_index,
                        "episode_id": row.get("episode_id"),
                        "session": row.get("session"),
                        "reason": "DUPLICATE_PAIRED_EPISODE",
                    }
                )
                continue
            seen_comparisons.add(key)
            accepted_comparisons.append(dict(row))

    exit_deltas = []
    confirmed_mfe_deltas = []
    possible_mfe_deltas = []
    bounded_mae_deltas = []
    baseline_exited = 0
    baseline_censored = 0
    trailing_exited = 0
    trailing_censored = 0
    identical_exit_r_count = 0
    differing_exit_r_count = 0

    for row in accepted_comparisons:
        for field, target in (
            ("exit_r_delta_trailing_minus_baseline", exit_deltas),
            ("confirmed_mfe_r_delta_trailing_minus_baseline", confirmed_mfe_deltas),
            ("possible_mfe_r_delta_trailing_minus_baseline", possible_mfe_deltas),
            ("bounded_mae_r_delta_trailing_minus_baseline", bounded_mae_deltas),
        ):
            value = _number(row.get(field))
            if value is not None:
                target.append(value)

        if row.get("baseline_status") == "EXITED":
            baseline_exited += 1
        elif row.get("baseline_status") == "CENSORED":
            baseline_censored += 1

        if row.get("trailing_status") == "EXITED":
            trailing_exited += 1
        elif row.get("trailing_status") == "CENSORED":
            trailing_censored += 1

        delta = _number(row.get("exit_r_delta_trailing_minus_baseline"))
        if delta is not None:
            if delta == 0.0:
                identical_exit_r_count += 1
            else:
                differing_exit_r_count += 1

    return {
        "stage": STAGE,
        "status": (
            "INDEPENDENT_COHORT_EVIDENCE_ACCUMULATED"
            if accepted_reports
            else "NO_VALID_STAGE_3_5_REPORTS"
        ),
        "expected_source_stage": EXPECTED_SOURCE_STAGE,
        "input_report_count": len(reports),
        "accepted_report_count": len(accepted_reports),
        "rejected_report_count": len(rejected_reports),
        "accepted_independent_paired_episode_count": len(accepted_comparisons),
        "duplicate_paired_episode_count": len(duplicate_comparisons),
        "baseline_exited_count": baseline_exited,
        "baseline_censored_count": baseline_censored,
        "trailing_exited_count": trailing_exited,
        "trailing_censored_count": trailing_censored,
        "paired_exit_r_observation_count": len(exit_deltas),
        "identical_exit_r_count": identical_exit_r_count,
        "differing_exit_r_count": differing_exit_r_count,
        "paired_exit_r_delta_trailing_minus_baseline": _stats(exit_deltas),
        "paired_confirmed_mfe_r_delta_trailing_minus_baseline": _stats(
            confirmed_mfe_deltas
        ),
        "paired_possible_mfe_r_delta_trailing_minus_baseline": _stats(
            possible_mfe_deltas
        ),
        "paired_bounded_mae_r_delta_trailing_minus_baseline": _stats(
            bounded_mae_deltas
        ),
        "accepted_reports": accepted_reports,
        "rejected_reports": rejected_reports,
        "duplicate_paired_episodes": duplicate_comparisons,
        "validation_reason": (
            "ACCUMULATED_INDEPENDENT_PAIRED_DESCRIPTIVE_EVIDENCE_ONLY_"
            "NO_PERFORMANCE_CLAIM"
        ),
        **_safety(),
    }


def audit_paths(paths: list[str | Path]) -> dict[str, Any]:
    reports = []
    source_paths = []
    for raw in paths:
        path = Path(raw)
        reports.append(json.loads(path.read_text(encoding="utf-8-sig")))
        source_paths.append(str(path))
    result = accumulate_reports(reports)
    result["source_paths"] = source_paths
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 3.6 Brooks independent cohort evidence accumulation."
    )
    parser.add_argument("stage_3_5_reports", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = audit_paths(args.stage_3_5_reports)
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
