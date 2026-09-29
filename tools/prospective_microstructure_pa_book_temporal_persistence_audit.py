from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-PA-BOOK-TEMPORAL-PERSISTENCE-AUDIT"

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


def _safety() -> dict[str, Any]:
    return {
        "research_only": True,
        "observational_only": True,
        "descriptive_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
        "threshold_change_allowed": False,
        "rc17_change_allowed": False,
        "order_flow_score_change_allowed": False,
        "threshold_changed": False,
        "rc17_changed": False,
        "operational_logic_changed": False,
        "canonical_conflict_redefinition": False,
    }


def _validate_prospective(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("session payload must be a JSON object")

    prospective = payload.get("prospective_microstructure")
    if not isinstance(prospective, dict):
        raise ValueError("prospective_microstructure must be an object")

    samples = prospective.get("samples")
    if not isinstance(samples, list):
        raise ValueError(
            "prospective_microstructure.samples must be a list"
        )

    if any(not isinstance(item, dict) for item in samples):
        raise ValueError(
            "prospective_microstructure.samples contains non-object entries"
        )

    captured = prospective.get("captured_samples")
    if not isinstance(captured, int) or isinstance(captured, bool):
        raise ValueError(
            "prospective_microstructure.captured_samples must be an integer"
        )

    source = prospective.get("source_analyzable_samples")
    if not isinstance(source, int) or isinstance(source, bool):
        raise ValueError(
            "prospective_microstructure.source_analyzable_samples "
            "must be an integer"
        )

    if prospective.get("sample_count_matches_source") is not True:
        raise ValueError(
            "prospective_microstructure.sample_count_matches_source "
            "must be true"
        )

    if captured != len(samples):
        raise ValueError(
            "prospective_microstructure.captured_samples "
            "does not match len(samples)"
        )

    if source != len(samples):
        raise ValueError(
            "prospective_microstructure.source_analyzable_samples "
            "does not match len(samples)"
        )

    return samples


def _normalize_direction(
    value: Any,
    field: str,
    index: int,
) -> str:
    direction = str(value or "").strip().upper()

    if direction not in {"BUY", "SELL", "NONE"}:
        raise ValueError(
            f"invalid {field} at index {index}: {direction!r}"
        )

    return direction


def _canonical_conflict(
    sample: dict[str, Any],
    index: int,
) -> bool:
    if "conflict_count" not in sample:
        raise ValueError(
            f"missing canonical conflict_count at index {index}"
        )

    value = sample["conflict_count"]

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            f"canonical conflict_count must be an integer at index {index}"
        )

    if value < 0:
        raise ValueError(
            f"canonical conflict_count must be >= 0 at index {index}"
        )

    return value > 0


def _relation(pa: str, book: str) -> str | None:
    if pa not in {"BUY", "SELL"}:
        return None

    if book not in {"BUY", "SELL"}:
        return None

    if pa == book:
        return "ALIGNED"

    return "OPPOSED"


def _pair(pa: str, book: str) -> str:
    if pa not in {"BUY", "SELL"}:
        raise ValueError(f"PA must be directional: {pa!r}")

    if book not in {"BUY", "SELL"}:
        raise ValueError(f"Book must be directional: {book!r}")

    return f"{pa}_{book}"


def _build_runs(
    samples: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    directional_samples: list[dict[str, Any]] = []

    aligned_samples = 0
    opposed_samples = 0

    for index, sample in enumerate(samples):
        pa = _normalize_direction(
            sample.get("price_action_bias"),
            "price_action_bias",
            index,
        )
        book = _normalize_direction(
            sample.get("book_direction"),
            "book_direction",
            index,
        )

        canonical_conflict = _canonical_conflict(
            sample,
            index,
        )

        relation = _relation(pa, book)

        if relation is None:
            continue

        pair = _pair(pa, book)

        if relation == "ALIGNED":
            aligned_samples += 1
        else:
            opposed_samples += 1

        directional_samples.append(
            {
                "index": index,
                "relation": relation,
                "pair": pair,
                "price_action_bias": pa,
                "book_direction": book,
                "canonical_conflict": canonical_conflict,
            }
        )

    runs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for item in directional_samples:
        if current is None:
            current = {
                "relation": item["relation"],
                "pair": item["pair"],
                "start_index": item["index"],
                "end_index": item["index"],
                "length": 1,
                "canonical_conflict_samples": (
                    1 if item["canonical_conflict"] else 0
                ),
            }
            continue

        contiguous = (
            item["index"] == current["end_index"] + 1
        )
        same_relation = (
            item["relation"] == current["relation"]
        )
        same_pair = (
            item["pair"] == current["pair"]
        )

        if contiguous and same_relation and same_pair:
            current["end_index"] = item["index"]
            current["length"] += 1

            if item["canonical_conflict"]:
                current["canonical_conflict_samples"] += 1
        else:
            runs.append(current)

            current = {
                "relation": item["relation"],
                "pair": item["pair"],
                "start_index": item["index"],
                "end_index": item["index"],
                "length": 1,
                "canonical_conflict_samples": (
                    1 if item["canonical_conflict"] else 0
                ),
            }

    if current is not None:
        runs.append(current)

    counts = {
        "simultaneous_directional_samples": len(
            directional_samples
        ),
        "aligned_samples": aligned_samples,
        "opposed_samples": opposed_samples,
    }

    return runs, counts


def _run_summary(
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    relation_counts: Counter[str] = Counter()
    pair_counts: Counter[str] = Counter()

    lengths = {
        "ALIGNED": [],
        "OPPOSED": [],
    }

    conflict_bearing_runs = {
        "ALIGNED": 0,
        "OPPOSED": 0,
    }

    canonical_conflict_samples = {
        "ALIGNED": 0,
        "OPPOSED": 0,
    }

    for run in runs:
        relation = run["relation"]
        pair = run["pair"]

        relation_counts[relation] += 1
        pair_counts[pair] += 1
        lengths[relation].append(run["length"])

        conflict_samples = run[
            "canonical_conflict_samples"
        ]

        canonical_conflict_samples[
            relation
        ] += conflict_samples

        if conflict_samples > 0:
            conflict_bearing_runs[relation] += 1

    aligned_runs = relation_counts["ALIGNED"]
    opposed_runs = relation_counts["OPPOSED"]

    aligned_lengths = lengths["ALIGNED"]
    opposed_lengths = lengths["OPPOSED"]

    return {
        "total_runs": len(runs),
        "aligned_runs": aligned_runs,
        "opposed_runs": opposed_runs,
        "pair_run_counts": {
            "BUY_BUY": pair_counts["BUY_BUY"],
            "SELL_SELL": pair_counts["SELL_SELL"],
            "BUY_SELL": pair_counts["BUY_SELL"],
            "SELL_BUY": pair_counts["SELL_BUY"],
        },
        "aligned_run_lengths": aligned_lengths,
        "opposed_run_lengths": opposed_lengths,
        "aligned_longest_run": (
            max(aligned_lengths)
            if aligned_lengths
            else 0
        ),
        "opposed_longest_run": (
            max(opposed_lengths)
            if opposed_lengths
            else 0
        ),
        "aligned_mean_run_length": (
            sum(aligned_lengths) / len(aligned_lengths)
            if aligned_lengths
            else None
        ),
        "opposed_mean_run_length": (
            sum(opposed_lengths) / len(opposed_lengths)
            if opposed_lengths
            else None
        ),
        "aligned_conflict_bearing_runs": (
            conflict_bearing_runs["ALIGNED"]
        ),
        "opposed_conflict_bearing_runs": (
            conflict_bearing_runs["OPPOSED"]
        ),
        "aligned_canonical_conflict_samples": (
            canonical_conflict_samples["ALIGNED"]
        ),
        "opposed_canonical_conflict_samples": (
            canonical_conflict_samples["OPPOSED"]
        ),
    }


def _audit_session(
    label: str,
    raw_path: Path,
) -> dict[str, Any]:
    payload = _read_json(raw_path)
    samples = _validate_prospective(payload)

    runs, sample_counts = _build_runs(samples)
    summary = _run_summary(runs)

    if (
        sample_counts["simultaneous_directional_samples"]
        != (
            sample_counts["aligned_samples"]
            + sample_counts["opposed_samples"]
        )
    ):
        raise ValueError(
            "sample identity failed: simultaneous != aligned + opposed"
        )

    if sum(
        run["length"]
        for run in runs
    ) != sample_counts["simultaneous_directional_samples"]:
        raise ValueError(
            "run identity failed: run lengths do not sum to samples"
        )

    return {
        "label": label,
        "raw_session": {
            "path": str(raw_path),
            "sha256": _sha256(raw_path),
        },
        "samples": len(samples),
        **sample_counts,
        **summary,
        "runs": runs,
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
    }


def _validate_distinct_paths(paths: list[Path]) -> None:
    resolved = [path.resolve() for path in paths]

    if len(set(resolved)) != len(resolved):
        raise ValueError(
            "all frozen session artifacts must be distinct"
        )


def build_report(
    session_paths: list[Path],
) -> dict[str, Any]:
    paths = [Path(path) for path in session_paths]

    if len(paths) != EXPECTED_FROZEN_SESSION_COUNT:
        raise ValueError(
            "exactly 10 frozen session artifacts are required"
        )

    _validate_distinct_paths(paths)

    before = {
        path.resolve(): _sha256(path)
        for path in paths
    }

    sessions = [
        _audit_session(
            f"FROZEN_SESSION_{index:02d}",
            path,
        )
        for index, path in enumerate(paths, start=1)
    ]

    after = {
        path.resolve(): _sha256(path)
        for path in paths
    }

    if before != after:
        raise ValueError(
            "one or more frozen session artifacts mutated during audit"
        )

    aligned_samples = sum(
        session["aligned_samples"]
        for session in sessions
    )
    opposed_samples = sum(
        session["opposed_samples"]
        for session in sessions
    )
    simultaneous = sum(
        session["simultaneous_directional_samples"]
        for session in sessions
    )

    aligned_runs = sum(
        session["aligned_runs"]
        for session in sessions
    )
    opposed_runs = sum(
        session["opposed_runs"]
        for session in sessions
    )

    aligned_lengths = [
        length
        for session in sessions
        for length in session["aligned_run_lengths"]
    ]
    opposed_lengths = [
        length
        for session in sessions
        for length in session["opposed_run_lengths"]
    ]

    pair_run_counts = {
        pair: sum(
            session["pair_run_counts"][pair]
            for session in sessions
        )
        for pair in (
            "BUY_BUY",
            "SELL_SELL",
            "BUY_SELL",
            "SELL_BUY",
        )
    }

    aggregate = {
        "samples": sum(
            session["samples"]
            for session in sessions
        ),
        "simultaneous_directional_samples": simultaneous,
        "aligned_samples": aligned_samples,
        "opposed_samples": opposed_samples,
        "total_runs": aligned_runs + opposed_runs,
        "aligned_runs": aligned_runs,
        "opposed_runs": opposed_runs,
        "pair_run_counts": pair_run_counts,
        "aligned_run_lengths": aligned_lengths,
        "opposed_run_lengths": opposed_lengths,
        "aligned_longest_run": (
            max(aligned_lengths)
            if aligned_lengths
            else 0
        ),
        "opposed_longest_run": (
            max(opposed_lengths)
            if opposed_lengths
            else 0
        ),
        "aligned_mean_run_length": (
            aligned_samples / aligned_runs
            if aligned_runs
            else None
        ),
        "opposed_mean_run_length": (
            opposed_samples / opposed_runs
            if opposed_runs
            else None
        ),
        "aligned_conflict_bearing_runs": sum(
            session["aligned_conflict_bearing_runs"]
            for session in sessions
        ),
        "opposed_conflict_bearing_runs": sum(
            session["opposed_conflict_bearing_runs"]
            for session in sessions
        ),
        "aligned_canonical_conflict_samples": sum(
            session["aligned_canonical_conflict_samples"]
            for session in sessions
        ),
        "opposed_canonical_conflict_samples": sum(
            session["opposed_canonical_conflict_samples"]
            for session in sessions
        ),
    }

    if simultaneous != aligned_samples + opposed_samples:
        raise ValueError(
            "aggregate sample identity failed"
        )

    if sum(aligned_lengths) != aligned_samples:
        raise ValueError(
            "aggregate aligned run lengths do not sum to aligned samples"
        )

    if sum(opposed_lengths) != opposed_samples:
        raise ValueError(
            "aggregate opposed run lengths do not sum to opposed samples"
        )

    return {
        "version": VERSION,
        "status": "PA_BOOK_TEMPORAL_PERSISTENCE_AUDIT_COMPLETED",
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
            "frozen_opposed_episode_count": 17,
            "run_is_episode_claim_allowed": False,
            "sample_is_run_claim_allowed": False,
            "sample_is_episode_claim_allowed": False,
            "run_is_canonical_conflict_claim_allowed": False,
        },
        "interpretation": "DESCRIPTIVE_ONLY",
        "interpretation_limits": [
            "DESCRIPTIVE_ONLY",
            "RUNS_ARE_NOT_CANONICAL_CONFLICT_EPISODES",
            "18_OPPOSED_RUNS_MUST_NOT_BE_EQUATED_WITH_17_OPPOSED_EPISODES",
            "SAMPLE_RUN_AND_EPISODE_UNITS_REMAIN_DISTINCT",
            "CANONICAL_CONFLICT_COMES_ONLY_FROM_CONFLICT_COUNT",
            "NO_PREDICTIVE_CLAIM",
            "NO_THRESHOLD_CHANGE_ALLOWED",
            "NO_RC17_CHANGE_ALLOWED",
            "NO_OPERATIONAL_INFERENCE_ALLOWED",
            "FROZEN_10_SESSION_CHECKPOINT_IS_NOT_EXTENDED",
            "INDEPENDENT_SESSIONS_11_AND_12_ARE_NOT_APPENDED",
        ],
        **_safety(),
    }


def _write_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Passive fail-closed PA x Book temporal persistence audit "
            "for the frozen 10-session prospective microstructure cohort."
        )
    )

    parser.add_argument(
        "sessions",
        nargs="+",
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    report = build_report(args.sessions)

    _write_report(
        report,
        args.output,
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
