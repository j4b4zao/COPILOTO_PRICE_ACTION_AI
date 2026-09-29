"""Frozen descriptive session concentration, pair persistence and conflict overlap."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from tools import prospective_microstructure_pa_book_temporal_transition_audit as transition

VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-PA-BOOK-SESSION-HETEROGENEITY-AUDIT"
MEASURES = ("simultaneous_directional_samples", "total_runs", "aligned_samples",
            "opposed_samples", "aligned_runs", "opposed_runs")


def _concentration(counts: dict[str, int]) -> dict[str, Any]:
    total = sum(counts.values())
    ordered = sorted(counts.values(), reverse=True)
    return {
        "total": total, "counts": counts,
        "shares": {s: n / total if total else None for s, n in counts.items()},
        "top_one_share": ordered[0] / total if total else None,
        "top_two_share": sum(ordered[:2]) / total if total else None,
        "sum_squared_shares": sum((n / total) ** 2 for n in counts.values()) if total else None,
        "largest_sessions": sorted(s for s, n in counts.items() if total and n == ordered[0]),
    }


def _summarize(base: dict[str, Any]) -> dict[str, Any]:
    sessions = base["sessions"]
    runs = [{**r, "session": s["label"], "run": number}
            for s in sessions for number, r in enumerate(s["runs"], 1)]
    rows = [t for s in sessions for t in s["transitions"]]
    concentration = {m: _concentration({s["label"]: s[m] for s in sessions}) for m in MEASURES}
    pairs = {}
    for pair in transition.PAIRS:
        subset = [r for r in runs if r["pair"] == pair]
        pairs[pair] = {
            "samples": sum(r["length"] for r in subset), "runs": len(subset),
            "run_lengths": transition._stats([r["length"] for r in subset]),
            "observed_duration_seconds": transition._stats([r["observed_duration_seconds"] for r in subset]),
            "total_observed_duration_seconds": round(sum(r["observed_duration_seconds"] for r in subset), 6),
            "sessions": dict(sorted(Counter(r["session"] for r in subset).items())),
            "incoming_gap": transition._summary([t for t in rows if t["next_pair"] == pair]),
            "outgoing_gap": transition._summary([t for t in rows if t["previous_pair"] == pair]),
        }
    overlap = {}
    for relation in transition.RELATIONS:
        subset = [r for r in runs if r["relation"] == relation]
        annotated = [{**r, "conflict_sample_fraction": r["canonical_conflict_samples"] / r["length"],
                      "overlap": ("NONE" if r["canonical_conflict_samples"] == 0 else
                                  "FULL" if r["canonical_conflict_samples"] == r["length"] else "PARTIAL")}
                     for r in subset]
        counts = Counter(r["overlap"] for r in annotated)
        overlap[relation] = {
            "run_counts": {k: counts[k] for k in ("NONE", "PARTIAL", "FULL")},
            "conflict_samples": sum(r["canonical_conflict_samples"] for r in subset),
            "samples": sum(r["length"] for r in subset), "rows": annotated,
        }
    aggregate = base["aggregate"]
    if sum(p["samples"] for p in pairs.values()) != aggregate["simultaneous_directional_samples"]:
        raise ValueError("pair sample partition failed")
    if sum(p["runs"] for p in pairs.values()) != aggregate["total_runs"]:
        raise ValueError("pair run partition failed")
    for relation, item in overlap.items():
        key = relation.lower()
        if (item["samples"] != aggregate[key + "_samples"]
                or item["conflict_samples"] != aggregate[key + "_canonical_conflict_samples"]
                or sum(item["run_counts"].values()) != aggregate[key + "_runs"]):
            raise ValueError("canonical attribute partition failed")
    return {
        "transition_gaps": {
            "pooled": transition._summary(rows),
            "by_session": {s["label"]: transition._summary(s["transitions"]) for s in sessions},
            "omit_one_session_descriptive_sensitivity": {
                s["label"]: transition._summary([t for t in rows if t["session"] != s["label"]])
                for s in sessions},
            "largest_gap": max(rows, key=lambda t: t["gap_seconds"]) if rows else None,
            "zero_gap_samples_count": sum(t["gap_samples"] == 0 for t in rows),
            "positive_gap_samples_count": sum(t["gap_samples"] > 0 for t in rows),
        },
        "session_concentration": concentration, "pair_persistence": pairs,
        "canonical_conflict_overlap": overlap,
    }


def build_report() -> dict[str, Any]:
    base = transition.build_report()
    summary = _summarize(base)
    # Recheck the pinned cohort after computing every descriptive table.
    for path, digest in transition._frozen_entries():
        if transition.duration._sha256(path) != digest:
            raise ValueError("frozen input mutated during heterogeneity audit")
    return {
        **base, "version": VERSION, "source_transition_version": transition.VERSION,
        "status": "PA_BOOK_SESSION_HETEROGENEITY_AUDIT_COMPLETED", **summary,
        "descriptive_definitions": {
            "share_denominator": "SUM_OF_NAMED_MEASURE_ACROSS_ALL_TEN_FROZEN_SESSIONS",
            "sum_squared_shares": "SUM_OF_SQUARED_SESSION_SHARES_NOT_AN_OPERATIONAL_SCORE",
            "empty_measure_share": None,
            "incoming_gap": "TRANSITIONS_WHOSE_NEXT_RUN_HAS_THIS_PAIR",
            "outgoing_gap": "TRANSITIONS_WHOSE_PREVIOUS_RUN_HAS_THIS_PAIR",
            "incoming_and_outgoing_must_not_be_summed": True,
            "full_conflict": "CANONICAL_CONFLICT_SAMPLES_EQUALS_RUN_LENGTH",
            "partial_conflict": "ZERO_LESS_THAN_CANONICAL_CONFLICT_SAMPLES_LESS_THAN_RUN_LENGTH",
            "no_conflict": "CANONICAL_CONFLICT_SAMPLES_EQUALS_ZERO",
            "omission_tables_redefine_cohort": False,
            "omission_tables": "ARITHMETIC_SENSITIVITY_ONLY_ALL_TEN_SESSIONS_RETAINED_IN_BASELINE",
        },
        "interpretation_limits": [*base["interpretation_limits"],
            "UNEQUAL_OBSERVED_SESSION_WINDOWS_NO_EXPOSURE_ADJUSTMENT",
            "ABSENT_PAIR_HAS_NO_OBSERVED_DURATION_DISTRIBUTION",
            "NO_SHORT_LONG_GAP_THRESHOLDS",
            "NO_CAUSAL_CLAIM_FROM_CONFLICT_OVERLAP",
            "CONCENTRATION_IS_NOT_A_SCORE_OR_PROMOTION_CRITERION"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Passive frozen PA x Book session heterogeneity audit")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = build_report()
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "frozen_identity_exact": report["frozen_identity_exact"]}))


if __name__ == "__main__":
    main()
