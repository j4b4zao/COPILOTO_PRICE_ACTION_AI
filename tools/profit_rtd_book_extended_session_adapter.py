from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED_PRICE_KEYS = ("last_price", "price", "last", "close", "ultimo", "snapshot_price")


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _extract_price(row: dict):
    for key in REQUIRED_PRICE_KEYS:
        if key not in row:
            continue
        value = row.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def analyze(samples_path, summary_path=None):
    samples_path = Path(samples_path)
    rows = _load_jsonl(samples_path)
    summary = {}
    if summary_path:
        summary_path = Path(summary_path)
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

    prices = [_extract_price(row) for row in rows]
    synchronized_price_count = sum(price is not None for price in prices)
    missing_price_count = len(rows) - synchronized_price_count
    has_imbalance = sum("imbalance" in row for row in rows)
    valid_quality = sum(str(row.get("quality_status", "")).upper() == "VALID" for row in rows)

    reasons = []
    if not rows:
        reasons.append("NO_EXTENDED_SAMPLES")
    if has_imbalance != len(rows):
        reasons.append("IMBALANCE_FIELD_INCOMPLETE")
    if synchronized_price_count != len(rows):
        reasons.append("SYNCHRONIZED_LAST_PRICE_MISSING")
    if summary and int(summary.get("completed_cycles", 0) or 0) != int(summary.get("requested_cycles", 0) or 0):
        reasons.append("INCOMPLETE_EXTENDED_SESSION")
    if summary and int(summary.get("collection_errors", 0) or 0) > 0:
        reasons.append("EXTENDED_SESSION_COLLECTION_ERRORS")

    compatible = not reasons
    return {
        "status": "EXTENDED_SESSION_COMPATIBLE" if compatible else "EXTENDED_SESSION_INCOMPATIBLE",
        "samples": len(rows),
        "valid_quality_samples": valid_quality,
        "imbalance_samples": has_imbalance,
        "synchronized_price_samples": synchronized_price_count,
        "missing_price_count": missing_price_count,
        "rc53_6_compatible": compatible,
        "rc53_7_compatible": compatible,
        "reasons": reasons or ["OK"],
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
    }


def main():
    parser = argparse.ArgumentParser(description="RC53.8.1 fail-safe compatibility gate for extended Book OOS sessions.")
    parser.add_argument("samples_path")
    parser.add_argument("--summary")
    args = parser.parse_args()
    result = analyze(args.samples_path, args.summary)
    print("PROFIT_RTD_BOOK_EXTENDED_SESSION_ADAPTER=COMPLETED")
    for key, value in result.items():
        if isinstance(value, list):
            print(f"{key}=" + "|".join(value))
        else:
            print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
