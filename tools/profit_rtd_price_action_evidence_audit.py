"""Extrai evidencias de price action de sessoes RC54 sem duplicar snapshots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis.research.price_action_evidence_observer import (
    PriceActionEvidence,
    PriceActionEvidenceObserver,
)

PATTERNS = (
    "bullish_engulfing",
    "bearish_engulfing",
    "hammer",
    "shooting_star",
    "doji",
    "inside_bar",
    "outside_bar",
)
HORIZONS = (1, 3, 5, 10)


def _multi_horizon_groups(buckets):
    grouped = {}
    for bucket in buckets:
        base_key, horizon = bucket.key.rsplit("|", 1)
        grouped.setdefault(base_key, {})[horizon] = bucket
    reports = []
    required = tuple(f"H{horizon}" for horizon in HORIZONS)
    for key, horizons in sorted(grouped.items()):
        reasons = []
        missing = tuple(horizon for horizon in required if horizon not in horizons)
        if missing:
            reasons.append("MISSING_REQUIRED_HORIZON")
        present = tuple(horizons[horizon] for horizon in required if horizon in horizons)
        if any(not bucket.sample_sufficient for bucket in present):
            reasons.append("HORIZON_SAMPLE_INSUFFICIENT")
        if any(not bucket.cross_session_sufficient for bucket in present):
            reasons.append("HORIZON_RECURRENCE_INSUFFICIENT")
        if any(not bucket.directional_stability_sufficient for bucket in present):
            reasons.append("HORIZON_DIRECTIONAL_STABILITY_NOT_CONFIRMED")
        directions = tuple(dict.fromkeys(
            bucket.consistent_direction for bucket in present
            if bucket.consistent_direction != "NONE"
        ))
        if len(directions) != 1 or any(
            bucket.consistent_direction == "NONE" for bucket in present
        ):
            reasons.append("DIRECTION_CONFLICT_ACROSS_HORIZONS")
        reports.append({
            "key": key,
            "required_horizons": list(required),
            "missing_horizons": list(missing),
            "directions": {
                horizon: horizons[horizon].consistent_direction
                for horizon in required if horizon in horizons
            },
            "consistent_direction": directions[0] if len(directions) == 1 else "NONE",
            "eligible_for_hypothesis_freeze": not reasons,
            "reasons": reasons or ["ALL_HORIZON_GATES_MET"],
        })
    return reports


def _rows(payload):
    if not isinstance(payload, dict) or payload.get("data_ready") is not True:
        return []
    value = payload.get("samples")
    return value if isinstance(value, list) else []


def _price(row):
    try:
        value = float(row.get("last_price"))
    except (AttributeError, TypeError, ValueError):
        return None
    return value if value > 0 else None


def audit(paths, *, timeframe="M1", minimum_sample=30, minimum_sessions=3):
    evidence = []
    accepted, rejected, edge_occurrences = [], [], 0
    for raw_path in paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = _rows(payload)
        if not rows:
            rejected.append(path.name)
            continue
        accepted.append(path.name)
        previous_active = {pattern: False for pattern in PATTERNS}
        for index, row in enumerate(rows):
            pa = row.get("price_action") if isinstance(row, dict) else None
            pa = pa if isinstance(pa, dict) else {}
            for pattern in PATTERNS:
                active = pa.get(pattern) is True
                if active and not previous_active[pattern]:
                    base = _price(row)
                    if base is not None:
                        edge_occurrences += 1
                        regime = str(pa.get("trend") or row.get("structure", {}).get("trend") or "UNKNOWN")
                        location = str(pa.get("brooks_signal_context") or "UNSPECIFIED")
                        for horizon in HORIZONS:
                            target_index = index + horizon
                            if target_index >= len(rows):
                                continue
                            target = _price(rows[target_index])
                            if target is None:
                                continue
                            evidence.append(
                                PriceActionEvidence(
                                    session_id=path.name,
                                    pattern=pattern,
                                    regime=regime,
                                    timeframe=timeframe,
                                    location_context=location,
                                    horizon_steps=horizon,
                                    forward_return=target - base,
                                )
                            )
                previous_active[pattern] = active

    report = PriceActionEvidenceObserver.analyze(
        tuple(evidence),
        minimum_sample_per_bucket=minimum_sample,
        minimum_sessions_per_bucket=minimum_sessions,
    )
    multi_horizon = _multi_horizon_groups(report.buckets)
    return {
        "status": report.status,
        "accepted_sessions": accepted,
        "rejected_sessions": rejected,
        "edge_occurrences": edge_occurrences,
        "evidence_rows": len(evidence),
        "buckets": [
            {
                "key": bucket.key,
                "observations": bucket.observations,
                "mean_forward_return": bucket.mean_forward_return,
                "positive_rate": bucket.positive_rate,
                "mean_volume_ratio": bucket.mean_volume_ratio,
                "sessions": bucket.sessions,
                "maximum_session_share": bucket.maximum_session_share,
                "session_mean_returns": dict(bucket.session_mean_returns),
                "consistent_direction": bucket.consistent_direction,
                "directional_session_share": bucket.directional_session_share,
                "sample_sufficient": bucket.sample_sufficient,
                "cross_session_sufficient": bucket.cross_session_sufficient,
                "directional_stability_sufficient": bucket.directional_stability_sufficient,
                "additional_observations_lower_bound": bucket.additional_observations_lower_bound,
                "additional_sessions_lower_bound": bucket.additional_sessions_lower_bound,
            }
            for bucket in report.buckets
        ],
        "insufficient_buckets": list(report.insufficient_buckets),
        "multi_horizon_groups": multi_horizon,
        "hypothesis_freeze_candidates": [
            item["key"] for item in multi_horizon
            if item["eligible_for_hypothesis_freeze"]
        ],
        "reasons": list(report.reasons),
        "deduplication": "FALSE_TO_TRUE_PATTERN_EDGE_PER_SESSION",
        "volume_status": "NOT_CAPTURED_IN_RC54_SESSION_SCHEMA",
        "observational_only": report.observational_only,
        "predictive_claim_allowed": report.predictive_claim_allowed,
        "score_influence_allowed": report.score_influence_allowed,
        "risk_influence_allowed": report.risk_influence_allowed,
        "decision_influence_allowed": report.decision_influence_allowed,
        "alert_influence_allowed": report.alert_influence_allowed,
        "order_execution_allowed": report.order_execution_allowed,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--minimum-sample", type=int, default=30)
    parser.add_argument("--minimum-sessions", type=int, default=3)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = audit(
        args.paths,
        timeframe=args.timeframe,
        minimum_sample=args.minimum_sample,
        minimum_sessions=args.minimum_sessions,
    )
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
