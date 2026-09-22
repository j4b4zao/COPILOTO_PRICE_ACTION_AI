"""Passive directional-coverage diagnostics for eligible prospective sessions.

This does not change the multi-session audit verdict or admit a new cohort.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.prospective_microstructure_multi_session_audit import audit_paths


_DIRECTIONS = {"BUY", "SELL"}


def _coverage(samples: list[dict]) -> dict:
    counts = {
        "samples": len(samples),
        "pa_directional": 0,
        "flow_directional": 0,
        "book_available": 0,
        "book_directional": 0,
        "insufficient_data": 0,
        "pa_directional_insufficient_data": 0,
        "conflicts": 0,
        "conflict_runs": 0,
        "longest_conflict_run": 0,
    }
    current_run = 0
    for sample in samples:
        if not isinstance(sample, dict) or not all(
            key in sample for key in (
                "price_action_bias", "flow_direction", "book_available",
                "book_direction", "state", "conflict_count",
            )
        ):
            raise ValueError("prospective sample missing directional diagnostic fields")
        if not isinstance(sample["conflict_count"], int) or sample["conflict_count"] < 0:
            raise ValueError("prospective sample has invalid conflict count")
        pa = sample["price_action_bias"] in _DIRECTIONS
        counts["pa_directional"] += pa
        counts["flow_directional"] += sample["flow_direction"] in _DIRECTIONS
        counts["book_available"] += sample["book_available"] is True
        counts["book_directional"] += sample["book_direction"] in _DIRECTIONS
        insufficient = sample["state"] == "INSUFFICIENT_DATA"
        counts["insufficient_data"] += insufficient
        counts["pa_directional_insufficient_data"] += pa and insufficient
        conflict = sample["state"] == "CONFLICT" or sample["conflict_count"] > 0
        counts["conflicts"] += conflict
        if conflict:
            if current_run == 0:
                counts["conflict_runs"] += 1
            current_run += 1
            counts["longest_conflict_run"] = max(counts["longest_conflict_run"], current_run)
        else:
            current_run = 0
    return counts


def report_paths(paths) -> dict:
    audit = audit_paths(paths)
    sessions = []
    for accepted in audit["accepted"]:
        raw = Path(accepted["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != accepted["sha256"]:
            raise ValueError("prospective session changed during coverage report")
        payload = json.loads(raw.decode("utf-8-sig"))
        evidence = payload["prospective_microstructure"]
        coverage = _coverage(evidence["samples"])
        if coverage["conflicts"] != evidence["report"]["conflict_samples"]:
            raise ValueError("prospective conflict count differs from session report")
        sessions.append({**accepted, "coverage": coverage})
    return {
        "version": "RC1-PROSPECTIVE-MICROSTRUCTURE-COVERAGE",
        "status": "DESCRIPTIVE_ONLY",
        "eligible_sessions": audit["eligible_sessions"],
        "rejected_sessions": audit["rejected_sessions"],
        "sessions": sessions,
        "audit_stability": audit["aggregate"]["stability"],
        "audit_recommendation": audit["aggregate"]["recommendation"],
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = report_paths(args.paths)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
