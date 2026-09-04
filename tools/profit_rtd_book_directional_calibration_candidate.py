from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

CURRENT_THRESHOLD = 0.062149
PERCENTILES = (0.50, 0.75, 0.90, 0.95)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = (len(ordered) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1.0 - frac) + ordered[hi] * frac


def _extract_imbalances(payload: object) -> list[float]:
    rows = payload if isinstance(payload, list) else payload.get("samples", payload.get("records", [])) if isinstance(payload, dict) else []
    result: list[float] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in ("raw_imbalance", "raw_imb", "snapshot_imbalance", "snap_imb", "imbalance"):
            if key in row and row[key] is not None:
                result.append(float(row[key]))
                break
    return result


def analyze(paths: Iterable[str], current_threshold: float = CURRENT_THRESHOLD) -> dict:
    values: list[float] = []
    session_count = 0
    for raw_path in paths:
        path = Path(raw_path)
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        session_values = _extract_imbalances(payload)
        if session_values:
            session_count += 1
            values.extend(session_values)

    positive = [v for v in values if v > 0]
    negative_abs = [abs(v) for v in values if v < 0]

    pos = {f"p{int(q*100)}": _percentile(positive, q) for q in PERCENTILES}
    neg = {f"p{int(q*100)}": _percentile(negative_abs, q) for q in PERCENTILES}

    # Candidates are evidence only. P90 is intentionally robust to isolated extremes.
    candidate_buy = pos["p90"]
    candidate_sell = neg["p90"]
    ratio = candidate_buy / candidate_sell if candidate_sell > 0 else 0.0

    reasons: list[str] = []
    if session_count < 3:
        reasons.append("INSUFFICIENT_SESSION_COUNT")
    if len(positive) < 50:
        reasons.append("INSUFFICIENT_POSITIVE_SAMPLE_COVERAGE")
    if len(negative_abs) < 50:
        reasons.append("INSUFFICIENT_NEGATIVE_SAMPLE_COVERAGE")
    if candidate_sell > 0 and ratio >= 1.5:
        reasons.append("DIRECTIONAL_MAGNITUDE_ASYMMETRY_OBSERVED")
    if not reasons:
        reasons.append("CANDIDATE_READY_FOR_REVIEW")

    return {
        "status": "COMPLETED",
        "sessions": session_count,
        "samples": len(values),
        "positive_samples": len(positive),
        "negative_samples": len(negative_abs),
        "current_threshold": current_threshold,
        "positive_percentiles": pos,
        "negative_abs_percentiles": neg,
        "positive_max": max(positive, default=0.0),
        "negative_max_abs": max(negative_abs, default=0.0),
        "candidate_buy_threshold": candidate_buy,
        "candidate_sell_threshold": candidate_sell,
        "p90_magnitude_ratio_buy_to_sell": ratio,
        "current_positive_cross_count": sum(v >= current_threshold for v in positive),
        "current_negative_cross_count": sum(v >= current_threshold for v in negative_abs),
        "reasons": reasons,
        "observational_only": True,
        "threshold_change_allowed": False,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    result = analyze(args.paths)
    print("PROFIT_RTD_BOOK_DIRECTIONAL_CALIBRATION_CANDIDATE=COMPLETED")
    for key, value in result.items():
        if isinstance(value, dict):
            for subkey, subvalue in value.items():
                print(f"{key}_{subkey}={subvalue:.6f}")
        elif isinstance(value, list):
            print(f"{key}={','.join(value)}")
        elif isinstance(value, float):
            print(f"{key}={value:.6f}")
        else:
            print(f"{key}={value}")


if __name__ == "__main__":
    main()
