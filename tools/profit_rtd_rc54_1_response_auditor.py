from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, median

HORIZONS = (1, 3, 5, 10)
ALIGNMENTS = ("BULLISH_ALIGNED", "BEARISH_ALIGNED", "DIVERGENT", "NEUTRAL")


def _stats(deltas):
    if not deltas:
        return {"n": 0, "mean_delta": None, "median_delta": None, "positive_rate": None, "negative_rate": None, "zero_rate": None}
    n = len(deltas)
    return {
        "n": n,
        "mean_delta": mean(deltas),
        "median_delta": median(deltas),
        "positive_rate": sum(v > 0 for v in deltas) / n,
        "negative_rate": sum(v < 0 for v in deltas) / n,
        "zero_rate": sum(v == 0 for v in deltas) / n,
    }


def audit(path: str | Path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    samples = list(payload.get("samples") or [])
    clean = (
        payload.get("status") == "COMPLETED"
        and payload.get("price_capture") is True
        and int(payload.get("collection_errors") or 0) == 0
        and int(payload.get("missing_price_count") or 0) == 0
    )
    if not clean:
        return {
            "status": "RC54_1_RESPONSE_AUDIT_REJECTED",
            "reason": "SESSION_NOT_CLEAN",
            "observational_only": True,
            "predictive_claim_allowed": False,
            "score_influence_allowed": False,
            "risk_influence_allowed": False,
            "decision_influence_allowed": False,
            "order_execution_allowed": False,
        }

    groups = {}
    for alignment in ALIGNMENTS:
        horizons = {}
        for h in HORIZONS:
            deltas = []
            for i, row in enumerate(samples):
                if row.get("alignment") != alignment or i + h >= len(samples):
                    continue
                p0 = row.get("last_price")
                p1 = samples[i + h].get("last_price")
                if p0 is None or p1 is None:
                    continue
                deltas.append(float(p1) - float(p0))
            horizons[str(h)] = _stats(deltas)
        groups[alignment] = {
            "occurrences": sum(1 for s in samples if s.get("alignment") == alignment),
            "horizons": horizons,
        }

    return {
        "status": "RC54_1_RESPONSE_AUDIT_COMPLETED",
        "symbol": payload.get("symbol"),
        "samples": len(samples),
        "groups": groups,
        "interpretation_scope": "SINGLE_SESSION_DESCRIPTIVE_ONLY",
        "price_action_integration": "PENDING_RC54_2",
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "order_execution_allowed": False,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="RC54.1: resposta futura por alinhamento T&T + Book.")
    p.add_argument("session_path")
    a = p.parse_args(argv)
    r = audit(a.session_path)
    print("PROFIT_RTD_RC54_1_RESPONSE_AUDITOR=COMPLETED")
    print("status=" + r["status"])
    if "samples" in r:
        print(f"samples={r['samples']}")
        for alignment in ALIGNMENTS:
            g = r["groups"][alignment]
            print(f"alignment={alignment} occurrences={g['occurrences']} horizons=" + json.dumps(g["horizons"], separators=(",", ":"), sort_keys=True))
    print("observational_only=True")
    print("predictive_claim_allowed=False")
    print("score_influence_allowed=False")
    print("risk_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    return 0 if r["status"] == "RC54_1_RESPONSE_AUDIT_COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
