"""Descriptive transitions between adjacent runs inside the frozen sessions."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from tools import prospective_microstructure_pa_book_temporal_duration_audit as duration

VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-PA-BOOK-TEMPORAL-TRANSITION-AUDIT"
ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "prospective_microstructure_conflict_10session_checkpoint_20260926.json"
# Semantic digest permits checkout newline differences, but no manifest changes.
MANIFEST_DIGEST = "066e2e7ad5b1c3cf43a8ae99c08b24b32bd40e8dbfd0f89e1b1765505651af54"
EXPECTED_BASELINE = {
    "samples": 2746, "simultaneous_directional_samples": 356,
    "aligned_samples": 210, "opposed_samples": 146,
    "total_runs": 35, "aligned_runs": 17, "opposed_runs": 18,
}
RELATIONS = ("ALIGNED", "OPPOSED")
PAIRS = ("BUY_BUY", "SELL_SELL", "BUY_SELL", "SELL_BUY")


def _frozen_entries() -> list[tuple[Path, str]]:
    payload = duration._read_json(MANIFEST)
    digest = hashlib.sha256(json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode()).hexdigest()
    if digest != MANIFEST_DIGEST:
        raise ValueError("frozen manifest identity changed")
    return [(ROOT / Path(item["path"].replace("\\", "/")), item["sha256"])
            for item in payload["sessions"]]


def _stats(values: list[int | float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "median": median(values) if values else None,
        "mean": mean(values) if values else None,
        "max": max(values) if values else None,
    }


def _transitions(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Gap samples excludes both endpoints; adjacent exact-pair changes give 0."""
    rows = []
    runs = session["runs"]
    for number, (previous, following) in enumerate(zip(runs, runs[1:]), 1):
        gap = following["start_index"] - previous["end_index"] - 1
        seconds = (duration._parse_timestamp(following["start_timestamp"], following["start_index"])
                   - duration._parse_timestamp(previous["end_timestamp"], previous["end_index"])).total_seconds()
        if gap < 0 or seconds < 0:
            raise ValueError("transition order or timestamp regression")
        row = {"session": session["label"], "previous_run": number,
               "next_run": number + 1, "gap_samples": gap,
               "gap_seconds": round(seconds, 6)}
        for prefix, run in (("previous", previous), ("next", following)):
            for field in ("relation", "pair", "canonical_conflict_samples"):
                row[f"{prefix}_{field}"] = run[field]
        row.update(previous_end_index=previous["end_index"],
                   next_start_index=following["start_index"],
                   previous_end_timestamp=previous["end_timestamp"],
                   next_start_timestamp=following["start_timestamp"])
        rows.append(row)
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_transitions": len(rows),
        "gap_samples": _stats([r["gap_samples"] for r in rows]),
        "gap_sample_distribution": dict(sorted(Counter(r["gap_samples"] for r in rows).items())),
        "gap_seconds": _stats([r["gap_seconds"] for r in rows]),
    }


def _group_summary(rows: list[dict[str, Any]], field: str, values: tuple[str, ...]) -> dict[str, Any]:
    result = {}
    for previous in values:
        for following in values:
            subset = [r for r in rows if (r[f"previous_{field}"], r[f"next_{field}"]) == (previous, following)]
            counts = Counter(r["session"] for r in subset)
            largest = max(counts.values(), default=0)
            result[f"{previous}->{following}"] = {
                **_summary(subset), "session_counts": dict(sorted(counts.items())),
                "sessions_present": len(counts),
                "largest_session_share": largest / len(subset) if subset else None,
                "largest_sessions": sorted(k for k, v in counts.items() if v == largest),
            }
    return result


def _extend_report(report: dict[str, Any]) -> dict[str, Any]:
    """Called only after Duration RC1 validates the raw/prospective inputs."""
    sessions = [{**s, "transitions": _transitions(s)} for s in report["sessions"]]
    rows = [r for s in sessions for r in s["transitions"]]
    expected = sum(max(len(s["runs"]) - 1, 0) for s in sessions)
    if len(rows) != expected:
        raise ValueError("transition identity failed")
    return {
        **report, "version": VERSION, "source_duration_version": duration.VERSION,
        "status": "PA_BOOK_TEMPORAL_TRANSITION_AUDIT_COMPLETED", "sessions": sessions,
        "aggregate": {**report["aggregate"], **_summary(rows),
                      "relation_transitions": _group_summary(rows, "relation", RELATIONS),
                      "pair_transitions": _group_summary(rows, "pair", PAIRS)},
        "unit_separation": {**report["unit_separation"], "transition_unit": "TRANSITION",
                            "transition_is_run_claim_allowed": False,
                            "transition_is_sample_claim_allowed": False,
                            "transition_is_episode_claim_allowed": False},
        "transition_definition": {
            "same_session_only": True, "consecutive_observed_runs_only": True,
            "run_numbering": "ONE_BASED_WITHIN_SESSION",
            "sample_indexing": "ZERO_BASED",
            "gap_samples": "NEXT_START_INDEX_MINUS_PREVIOUS_END_INDEX_MINUS_ONE",
            "gap_seconds": "NEXT_START_TIMESTAMP_MINUS_PREVIOUS_END_TIMESTAMP",
            "gap_is_continuous_state_duration_claim_allowed": False,
            "canonical_conflict_is_attribute_only": True,
        },
        "interpretation_limits": [*report["interpretation_limits"],
            "TRANSITION_RUN_SAMPLE_AND_EPISODE_ARE_DISTINCT",
            "NO_CROSS_SESSION_TRANSITIONS",
            "GAPS_DESCRIBE_OBSERVED_ENDPOINT_SEPARATION_ONLY",
            "COUNTS_ARE_NOT_TRANSITION_PROBABILITY_ESTIMATES",
            "SESSION_CONCENTRATION_LIMITS_POOLED_DESCRIPTIONS"],
    }


def build_report(session_paths: list[Path] | None = None) -> dict[str, Any]:
    entries = _frozen_entries()
    paths = [p for p, _ in entries] if session_paths is None else [Path(p) for p in session_paths]
    if len(paths) != 10:
        raise ValueError("exactly 10 frozen session artifacts are required")
    duration._validate_distinct_paths(paths)
    if [p.resolve() for p in paths] != [p.resolve() for p, _ in entries]:
        raise ValueError("frozen cohort paths or order changed")
    for path, (_, digest) in zip(paths, entries):
        if duration._sha256(path) != digest:
            raise ValueError("frozen input hash mismatch")
    report = duration.build_report(paths)
    if any(report["aggregate"][key] != value for key, value in EXPECTED_BASELINE.items()):
        raise ValueError("frozen numeric identity failed")
    result = _extend_report(report)
    if _frozen_entries() != entries:
        raise ValueError("frozen manifest mutated during audit")
    for path, (_, digest) in zip(paths, entries):
        if duration._sha256(path) != digest:
            raise ValueError("frozen input mutated during transition audit")
    result["frozen_manifest"] = {"path": str(MANIFEST), "semantic_sha256": MANIFEST_DIGEST}
    result["input_hashes_verified_before_and_after"] = True
    result["frozen_identity_exact"] = True
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Passive frozen PA x Book transition audit")
    parser.add_argument("sessions", nargs="*", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    # Exclusive creation prevents overwriting inputs or existing research artifacts.
    report = build_report(args.sessions or None)
    with args.output.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "aggregate": report["aggregate"]}, indent=2))


if __name__ == "__main__":
    main()
