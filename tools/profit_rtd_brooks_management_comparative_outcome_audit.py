"""
tools/profit_rtd_brooks_management_comparative_outcome_audit.py

Stage 3.1 — Brooks Comparative Outcome Audit.

Compara, por episodio, o comportamento do baseline (initial stop)
contra o trailing hipotetico produzido pela Stage 3.

Classificacoes principais:
- BOTH_STOPPED_SAME_CANDLE
- TRAILING_EXITED_BEFORE_BASELINE
- BASELINE_STOPPED_TRAILING_SURVIVED
- TRAILING_ONLY_EXIT
- BASELINE_ONLY_EXIT
- BOTH_SURVIVED

Metricas descritivas:
- contagens por classe;
- MFE/MAE medios e medianos;
- R protegido no trailing;
- distribuicao simples de trailing_exit_protected_r;
- proporcao de saidas trailing em break-even ou lucro.

Este modulo nao declara edge, nao valida performance e nao promove
qualquer hipotese operacional.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

SETUP_NAME = "BROOKS_MANAGEMENT_COMPARATIVE_OUTCOME_AUDIT_V1"


def _safety():
    return {
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "performance_claim_allowed": False,
        "hypothesis_freeze_allowed": False,
        "dynamic_management_validated": False,
        "performance_validated": False,
    }


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _mean(values):
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def _median(values):
    values = list(values)
    return statistics.median(values) if values else 0.0


def classify_episode(episode):
    baseline_hit = bool(episode.get("baseline_initial_stop_hit"))
    trailing_hit = bool(episode.get("trailing_stop_hit"))

    baseline_idx = episode.get("baseline_exit_exact_index")
    trailing_idx = episode.get("trailing_exit_exact_index")

    if baseline_hit and trailing_hit:
        if baseline_idx == trailing_idx:
            return "BOTH_STOPPED_SAME_CANDLE"

        if (
            baseline_idx is not None
            and trailing_idx is not None
            and trailing_idx < baseline_idx
        ):
            return "TRAILING_EXITED_BEFORE_BASELINE"

        if (
            baseline_idx is not None
            and trailing_idx is not None
            and baseline_idx < trailing_idx
        ):
            return "BASELINE_STOPPED_BEFORE_TRAILING"

        return "BOTH_STOPPED_ORDER_UNKNOWN"

    if trailing_hit and not baseline_hit:
        return "TRAILING_ONLY_EXIT"

    if baseline_hit and not trailing_hit:
        return "BASELINE_ONLY_EXIT"

    return "BOTH_SURVIVED"


def _protected_r_bucket(value):
    if value is None:
        return "NO_TRAILING_EXIT"

    value = _f(value)

    if value < 0:
        return "NEGATIVE_R"
    if value == 0:
        return "BREAKEVEN"
    if value < 0.5:
        return "POSITIVE_LT_0_5R"
    if value < 1.0:
        return "POSITIVE_0_5_TO_1R"
    return "POSITIVE_GE_1R"


def audit_episode(episode):
    category = classify_episode(episode)

    return {
        "episode_id": episode.get("episode_id"),
        "direction": episode.get("direction"),
        "category": category,
        "mfe_r": _f(episode.get("mfe_r")),
        "mae_r": _f(episode.get("mae_r")),
        "baseline_initial_stop_hit": bool(
            episode.get("baseline_initial_stop_hit")
        ),
        "trailing_stop_hit": bool(
            episode.get("trailing_stop_hit")
        ),
        "baseline_exit_exact_index": (
            episode.get("baseline_exit_exact_index")
        ),
        "trailing_exit_exact_index": (
            episode.get("trailing_exit_exact_index")
        ),
        "trailing_exit_protected_r": (
            episode.get("trailing_exit_protected_r")
        ),
        "protected_r_bucket": _protected_r_bucket(
            episode.get("trailing_exit_protected_r")
        ),
        "stop_revision_count": int(
            episode.get("stop_revision_count") or 0
        ),
    }


def audit_payload(outcome_payload):
    sessions = outcome_payload.get("sessions") or []

    audited = []
    for session in sessions:
        for episode in session.get("episodes") or []:
            if (
                isinstance(episode, dict)
                and episode.get("eligible")
            ):
                audited.append(audit_episode(episode))

    category_counts = {}
    bucket_counts = {}

    for item in audited:
        category_counts[item["category"]] = (
            category_counts.get(item["category"], 0) + 1
        )
        bucket = item["protected_r_bucket"]
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

    mfe_values = [x["mfe_r"] for x in audited]
    mae_values = [x["mae_r"] for x in audited]

    protected_values = [
        _f(x["trailing_exit_protected_r"])
        for x in audited
        if x["trailing_exit_protected_r"] is not None
    ]

    trailing_exit_count = sum(
        1 for x in audited if x["trailing_stop_hit"]
    )

    trailing_be_or_better = sum(
        1
        for x in audited
        if (
            x["trailing_exit_protected_r"] is not None
            and _f(x["trailing_exit_protected_r"]) >= 0
        )
    )

    trailing_positive = sum(
        1
        for x in audited
        if (
            x["trailing_exit_protected_r"] is not None
            and _f(x["trailing_exit_protected_r"]) > 0
        )
    )

    return {
        "setup": SETUP_NAME,
        "status": (
            "COMPARATIVE_OUTCOME_AUDIT_COMPLETED"
            if audited
            else "MORE_EVIDENCE_REQUIRED"
        ),
        "episode_count": len(audited),
        "category_counts": category_counts,
        "protected_r_bucket_counts": bucket_counts,
        "mfe_r_mean": _mean(mfe_values),
        "mfe_r_median": _median(mfe_values),
        "mae_r_mean": _mean(mae_values),
        "mae_r_median": _median(mae_values),
        "trailing_exit_count": trailing_exit_count,
        "trailing_exit_protected_r_mean": _mean(
            protected_values
        ),
        "trailing_exit_protected_r_median": _median(
            protected_values
        ),
        "trailing_breakeven_or_better_exits": (
            trailing_be_or_better
        ),
        "trailing_positive_r_exits": trailing_positive,
        "comparative_performance_validated": False,
        "validation_reason": (
            "DESCRIPTIVE_COMPARISON_ONLY_NO_EDGE_OR_PERFORMANCE_CLAIM"
        ),
        "episodes": audited,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Brooks comparative outcome audit."
    )
    parser.add_argument("outcome_report")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    payload = json.loads(
        Path(args.outcome_report).read_text(encoding="utf-8")
    )

    report = audit_payload(payload)

    if args.output:
        Path(args.output).write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print("status=", report["status"])
    print("episode_count=", report["episode_count"])
    print("category_counts=", json.dumps(
        report["category_counts"],
        ensure_ascii=False,
        sort_keys=True,
    ))
    print("mfe_r_mean=", report["mfe_r_mean"])
    print("mfe_r_median=", report["mfe_r_median"])
    print("mae_r_mean=", report["mae_r_mean"])
    print("mae_r_median=", report["mae_r_median"])
    print(
        "trailing_exit_protected_r_mean=",
        report["trailing_exit_protected_r_mean"],
    )
    print(
        "trailing_exit_protected_r_median=",
        report["trailing_exit_protected_r_median"],
    )
    print(
        "trailing_breakeven_or_better_exits=",
        report["trailing_breakeven_or_better_exits"],
    )
    print(
        "trailing_positive_r_exits=",
        report["trailing_positive_r_exits"],
    )
    print(
        "comparative_performance_validated=",
        report["comparative_performance_validated"],
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
