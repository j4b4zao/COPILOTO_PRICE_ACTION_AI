"""Extrai evidencias de price action de sessoes RC54 sem duplicar snapshots."""

from __future__ import annotations

import argparse
import json
from statistics import fmean
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


def _multi_horizon_groups(buckets, *, exact_candle_identity=False):
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
        if not exact_candle_identity:
            reasons.append("EXACT_CANDLE_IDENTITY_REQUIRED")
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


def _has_exact_candle_identity(rows):
    return bool(rows) and all(
        isinstance(row.get("candle_evidence"), dict)
        and row["candle_evidence"].get("status") == "CANDLE_EVIDENCE_READY"
        and bool(row["candle_evidence"].get("candle_id"))
        for row in rows
    )


def _last_revision_per_candle(rows):
    latest = {}
    for row in rows:
        latest[row["candle_evidence"]["candle_id"]] = row
    return list(latest.values())


def _candle_price(row):
    try:
        value = float(row["candle_evidence"]["close"])
    except (KeyError, TypeError, ValueError):
        return None
    return value if value > 0 else None


def _volume_pair(rows, index):
    try:
        current = float(rows[index]["candle_evidence"]["volume"])
    except (KeyError, TypeError, ValueError):
        return None, None
    prior = []
    for row in rows[max(0, index - 20):index]:
        try:
            value = float(row["candle_evidence"]["volume"])
        except (KeyError, TypeError, ValueError):
            continue
        if value >= 0:
            prior.append(value)
    baseline = fmean(prior) if prior and fmean(prior) > 0 else None
    return (current, baseline) if baseline is not None else (None, None)


def audit(paths, *, timeframe="M1", minimum_sample=30, minimum_sessions=3):
    evidence = []
    accepted, rejected, edge_occurrences = [], [], 0
    sessions = []
    for raw_path in paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = _rows(payload)
        if not rows:
            rejected.append(path.name)
            continue
        accepted.append(path.name)
        sessions.append((path, rows))

    schema_modes = {
        "EXACT_CANDLE" if _has_exact_candle_identity(rows) else "SNAPSHOT_PROXY"
        for _, rows in sessions
    }
    if len(schema_modes) > 1:
        raise ValueError("MIXED_EXACT_AND_PROXY_SESSION_SCHEMAS_NOT_ALLOWED")
    exact_identity = schema_modes == {"EXACT_CANDLE"}

    for path, source_rows in sessions:
        rows = _last_revision_per_candle(source_rows) if exact_identity else source_rows
        previous_active = {pattern: False for pattern in PATTERNS}
        for index, row in enumerate(rows):
            pa = row.get("price_action") if isinstance(row, dict) else None
            pa = pa if isinstance(pa, dict) else {}
            for pattern in PATTERNS:
                active = pa.get(pattern) is True
                occurrence = active if exact_identity else active and not previous_active[pattern]
                if occurrence:
                    base = _candle_price(row) if exact_identity else _price(row)
                    if base is not None:
                        edge_occurrences += 1
                        regime = str(pa.get("trend") or row.get("structure", {}).get("trend") or "UNKNOWN")
                        location = str(pa.get("brooks_signal_context") or "UNSPECIFIED")
                        for horizon in HORIZONS:
                            target_index = index + horizon
                            if target_index >= len(rows):
                                continue
                            target = _candle_price(rows[target_index]) if exact_identity else _price(rows[target_index])
                            if target is None:
                                continue
                            volume, baseline_volume = _volume_pair(rows, index) if exact_identity else (None, None)
                            evidence.append(
                                PriceActionEvidence(
                                    session_id=path.name,
                                    pattern=pattern,
                                    regime=regime,
                                    timeframe=timeframe,
                                    location_context=location,
                                    horizon_steps=horizon,
                                    forward_return=target - base,
                                    volume=volume,
                                    baseline_volume=baseline_volume,
                                )
                            )
                previous_active[pattern] = active

    report = PriceActionEvidenceObserver.analyze(
        tuple(evidence),
        minimum_sample_per_bucket=minimum_sample,
        minimum_sessions_per_bucket=minimum_sessions,
    )
    multi_horizon = _multi_horizon_groups(
        report.buckets, exact_candle_identity=exact_identity
    )
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
        "deduplication": (
            "LAST_REVISION_PER_EXACT_CANDLE_ID"
            if exact_identity else "FALSE_TO_TRUE_PATTERN_EDGE_PER_SESSION"
        ),
        "deduplication_quality": "EXACT_CANDLE" if exact_identity else "PROXY_ONLY",
        "exact_candle_identity_available": exact_identity,
        "eligible_for_hypothesis_freeze_from_schema": exact_identity,
        "schema_limitations": [] if exact_identity else [
            "CANDLE_ID_NOT_CAPTURED",
            "CANDLE_TIMESTAMP_NOT_CAPTURED",
            "CANDLE_VOLUME_NOT_CAPTURED",
        ],
        "volume_status": (
            "CANDLE_VOLUME_CAPTURED"
            if exact_identity else "NOT_CAPTURED_IN_RC54_SESSION_SCHEMA"
        ),
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
