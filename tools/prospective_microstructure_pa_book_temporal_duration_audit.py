from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

import tools.prospective_microstructure_pa_book_temporal_persistence_audit as persistence


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-PA-BOOK-TEMPORAL-DURATION-AUDIT"
EXPECTED_FROZEN_SESSION_COUNT = 10


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _parse_timestamp(value: Any, index: int) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"raw timestamp must be a non-empty string at index {index}")
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid ISO raw timestamp at index {index}: {value!r}") from exc


def _validate_cycle(value: Any, index: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"raw cycle must be an integer at index {index}")
    return value


def _validate_raw_samples(
    payload: Any,
    prospective_samples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list):
        raise ValueError("top-level samples must be a list")
    if any(not isinstance(item, dict) for item in raw_samples):
        raise ValueError("top-level samples contains non-object entries")
    if len(raw_samples) != len(prospective_samples):
        raise ValueError(
            "raw/prospective positional mapping failed: sample counts differ"
        )

    previous_timestamp: datetime | None = None
    previous_cycle: int | None = None

    for index, raw in enumerate(raw_samples):
        timestamp = _parse_timestamp(raw.get("timestamp"), index)
        cycle = _validate_cycle(raw.get("cycle"), index)

        if previous_timestamp is not None and timestamp < previous_timestamp:
            raise ValueError(f"raw timestamp regression at index {index}")
        if previous_cycle is not None and cycle < previous_cycle:
            raise ValueError(f"raw cycle regression at index {index}")

        previous_timestamp = timestamp
        previous_cycle = cycle

    return raw_samples


def _enrich_runs_with_duration(
    runs: list[dict[str, Any]],
    raw_samples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for run in runs:
        start_index = run["start_index"]
        end_index = run["end_index"]

        if (
            not isinstance(start_index, int)
            or isinstance(start_index, bool)
            or not isinstance(end_index, int)
            or isinstance(end_index, bool)
        ):
            raise ValueError("run indices must be integers")

        if not (0 <= start_index <= end_index < len(raw_samples)):
            raise ValueError("run indices fall outside raw positional mapping")

        start_raw = raw_samples[start_index]
        end_raw = raw_samples[end_index]

        start_timestamp = _parse_timestamp(
            start_raw.get("timestamp"),
            start_index,
        )
        end_timestamp = _parse_timestamp(
            end_raw.get("timestamp"),
            end_index,
        )
        start_cycle = _validate_cycle(
            start_raw.get("cycle"),
            start_index,
        )
        end_cycle = _validate_cycle(
            end_raw.get("cycle"),
            end_index,
        )

        duration = (end_timestamp - start_timestamp).total_seconds()
        if duration < 0:
            raise ValueError("run duration must not be negative")

        item = dict(run)
        item.update(
            {
                "start_timestamp": start_raw["timestamp"],
                "end_timestamp": end_raw["timestamp"],
                "start_cycle": start_cycle,
                "end_cycle": end_cycle,
                "observed_duration_seconds": round(duration, 6),
            }
        )
        enriched.append(item)

    return enriched


def _duration_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_relation = {
        "ALIGNED": [
            run["observed_duration_seconds"]
            for run in runs
            if run["relation"] == "ALIGNED"
        ],
        "OPPOSED": [
            run["observed_duration_seconds"]
            for run in runs
            if run["relation"] == "OPPOSED"
        ],
    }

    result: dict[str, Any] = {}
    for relation, durations in by_relation.items():
        key = relation.lower()
        result[f"{key}_run_durations_seconds"] = durations
        result[f"{key}_min_duration_seconds"] = (
            min(durations) if durations else None
        )
        result[f"{key}_median_duration_seconds"] = (
            median(durations) if durations else None
        )
        result[f"{key}_mean_duration_seconds"] = (
            mean(durations) if durations else None
        )
        result[f"{key}_max_duration_seconds"] = (
            max(durations) if durations else None
        )
        result[f"{key}_total_observed_duration_seconds"] = (
            round(sum(durations), 6) if durations else 0.0
        )

    return result


def _audit_session(label: str, raw_path: Path) -> dict[str, Any]:
    payload = _read_json(raw_path)
    prospective_samples = persistence._validate_prospective(payload)
    raw_samples = _validate_raw_samples(payload, prospective_samples)

    runs, sample_counts = persistence._build_runs(prospective_samples)
    persistence_summary = persistence._run_summary(runs)
    enriched_runs = _enrich_runs_with_duration(runs, raw_samples)
    duration_summary = _duration_summary(enriched_runs)

    if (
        sample_counts["simultaneous_directional_samples"]
        != sample_counts["aligned_samples"] + sample_counts["opposed_samples"]
    ):
        raise ValueError("sample identity failed: simultaneous != aligned + opposed")

    if sum(run["length"] for run in enriched_runs) != sample_counts[
        "simultaneous_directional_samples"
    ]:
        raise ValueError("run identity failed: run lengths do not sum to samples")

    return {
        "label": label,
        "raw_session": {
            "path": str(raw_path),
            "sha256": _sha256(raw_path),
        },
        "samples": len(prospective_samples),
        "raw_samples": len(raw_samples),
        "raw_prospective_positional_mapping": "VALIDATED_BY_EXACT_COUNT_AND_INDEX",
        **sample_counts,
        **persistence_summary,
        **duration_summary,
        "runs": enriched_runs,
        "run_definition": {
            "unit": "RUN",
            "requires_simultaneous_directionality": True,
            "requires_immediate_index_contiguity": True,
            "requires_same_exact_pa_book_pair": True,
            "none_breaks_run": True,
            "gap_breaks_run": True,
            "pair_change_breaks_run": True,
            "canonical_conflict_does_not_define_run": True,
        },
        "duration_definition": {
            "unit": "SECONDS",
            "source": "TOP_LEVEL_RAW_SAMPLE_TIMESTAMP_BY_EXACT_POSITIONAL_INDEX",
            "formula": "LAST_RAW_TIMESTAMP_MINUS_FIRST_RAW_TIMESTAMP",
            "single_sample_run_duration_seconds": 0.0,
            "single_sample_zero_means_no_observed_between_sample_interval": True,
        },
    }


def _validate_distinct_paths(paths: list[Path]) -> None:
    resolved = [path.resolve() for path in paths]
    if len(set(resolved)) != len(resolved):
        raise ValueError("all frozen session artifacts must be distinct")


def build_report(session_paths: list[Path]) -> dict[str, Any]:
    paths = [Path(path) for path in session_paths]

    if len(paths) != EXPECTED_FROZEN_SESSION_COUNT:
        raise ValueError("exactly 10 frozen session artifacts are required")

    _validate_distinct_paths(paths)

    before = {path.resolve(): _sha256(path) for path in paths}
    sessions = [
        _audit_session(f"FROZEN_SESSION_{index:02d}", path)
        for index, path in enumerate(paths, start=1)
    ]
    after = {path.resolve(): _sha256(path) for path in paths}

    if before != after:
        raise ValueError("one or more frozen session artifacts mutated during audit")

    aligned_samples = sum(session["aligned_samples"] for session in sessions)
    opposed_samples = sum(session["opposed_samples"] for session in sessions)
    simultaneous = sum(
        session["simultaneous_directional_samples"] for session in sessions
    )
    aligned_runs = sum(session["aligned_runs"] for session in sessions)
    opposed_runs = sum(session["opposed_runs"] for session in sessions)

    all_runs = [run for session in sessions for run in session["runs"]]
    aligned_lengths = [
        run["length"] for run in all_runs if run["relation"] == "ALIGNED"
    ]
    opposed_lengths = [
        run["length"] for run in all_runs if run["relation"] == "OPPOSED"
    ]

    duration_summary = _duration_summary(all_runs)

    pair_run_counts = {
        pair: sum(session["pair_run_counts"][pair] for session in sessions)
        for pair in ("BUY_BUY", "SELL_SELL", "BUY_SELL", "SELL_BUY")
    }

    aggregate = {
        "samples": sum(session["samples"] for session in sessions),
        "simultaneous_directional_samples": simultaneous,
        "aligned_samples": aligned_samples,
        "opposed_samples": opposed_samples,
        "total_runs": aligned_runs + opposed_runs,
        "aligned_runs": aligned_runs,
        "opposed_runs": opposed_runs,
        "pair_run_counts": pair_run_counts,
        "aligned_run_lengths": aligned_lengths,
        "opposed_run_lengths": opposed_lengths,
        "aligned_longest_run": max(aligned_lengths) if aligned_lengths else 0,
        "opposed_longest_run": max(opposed_lengths) if opposed_lengths else 0,
        "aligned_mean_run_length": (
            aligned_samples / aligned_runs if aligned_runs else None
        ),
        "opposed_mean_run_length": (
            opposed_samples / opposed_runs if opposed_runs else None
        ),
        "aligned_conflict_bearing_runs": sum(
            session["aligned_conflict_bearing_runs"] for session in sessions
        ),
        "opposed_conflict_bearing_runs": sum(
            session["opposed_conflict_bearing_runs"] for session in sessions
        ),
        "aligned_canonical_conflict_samples": sum(
            session["aligned_canonical_conflict_samples"] for session in sessions
        ),
        "opposed_canonical_conflict_samples": sum(
            session["opposed_canonical_conflict_samples"] for session in sessions
        ),
        **duration_summary,
    }

    if simultaneous != aligned_samples + opposed_samples:
        raise ValueError("aggregate sample identity failed")
    if sum(aligned_lengths) != aligned_samples:
        raise ValueError("aggregate aligned run lengths do not sum to aligned samples")
    if sum(opposed_lengths) != opposed_samples:
        raise ValueError("aggregate opposed run lengths do not sum to opposed samples")

    return {
        "version": VERSION,
        "status": "PA_BOOK_TEMPORAL_DURATION_AUDIT_COMPLETED",
        "mode": "FROZEN_10_SESSION_RETROSPECTIVE_RESEARCH_AUDIT",
        "session_count": len(sessions),
        "sessions": sessions,
        "aggregate": aggregate,
        "frozen_checkpoint_session_count": 10,
        "checkpoint_extended": False,
        "independent_sessions_appended": False,
        "combined_session_count": None,
        "combined_checkpoint_created": False,
        "cohort_redefinition": False,
        "unit_separation": {
            "sample_unit": "SAMPLE",
            "temporal_unit": "RUN",
            "duration_unit": "SECONDS",
            "frozen_opposed_episode_count": 17,
            "run_is_episode_claim_allowed": False,
            "sample_is_run_claim_allowed": False,
            "sample_is_episode_claim_allowed": False,
            "run_is_canonical_conflict_claim_allowed": False,
            "duration_is_episode_claim_allowed": False,
        },
        "interpretation": "DESCRIPTIVE_ONLY",
        "interpretation_limits": [
            "DESCRIPTIVE_ONLY",
            "OBSERVED_DURATION_IS_LAST_SAMPLE_TIMESTAMP_MINUS_FIRST_SAMPLE_TIMESTAMP",
            "SINGLE_SAMPLE_ZERO_DOES_NOT_CLAIM_TRUE_STATE_DURATION_WAS_ZERO",
            "RAW_AND_PROSPECTIVE_SAMPLES_ARE_JOINED_ONLY_BY_EXACT_POSITIONAL_INDEX",
            "RUNS_ARE_NOT_CANONICAL_CONFLICT_EPISODES",
            "18_OPPOSED_RUNS_MUST_NOT_BE_EQUATED_WITH_17_OPPOSED_EPISODES",
            "SAMPLE_RUN_DURATION_AND_EPISODE_UNITS_REMAIN_DISTINCT",
            "CANONICAL_CONFLICT_COMES_ONLY_FROM_CONFLICT_COUNT",
            "NO_PREDICTIVE_CLAIM",
            "NO_THRESHOLD_CHANGE_ALLOWED",
            "NO_RC17_CHANGE_ALLOWED",
            "NO_OPERATIONAL_INFERENCE_ALLOWED",
            "FROZEN_10_SESSION_CHECKPOINT_IS_NOT_EXTENDED",
            "INDEPENDENT_SESSIONS_11_AND_12_ARE_NOT_APPENDED",
        ],
        **persistence._safety(),
    }


def _write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Passive fail-closed PA x Book temporal duration audit "
            "for the frozen 10-session prospective microstructure cohort."
        )
    )
    parser.add_argument("sessions", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = build_report(args.sessions)
    _write_report(report, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
