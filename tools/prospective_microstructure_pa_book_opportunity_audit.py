from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-PA-BOOK-OPPORTUNITY-AUDIT"

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


def _empty_counts() -> dict[str, int]:
    return {
        "samples": 0,
        "pa_directional": 0,
        "book_directional": 0,
        "simultaneous_directional": 0,
        "aligned": 0,
        "opposed": 0,
        "pa_buy_book_buy": 0,
        "pa_sell_book_sell": 0,
        "pa_buy_book_sell": 0,
        "pa_sell_book_buy": 0,
        "pa_directional_book_none": 0,
        "canonical_conflict_samples": 0,
        "simultaneous_canonical_conflict": 0,
        "aligned_canonical_conflict": 0,
        "opposed_canonical_conflict": 0,
    }


def _audit_session(
    label: str,
    raw_path: Path,
) -> dict[str, Any]:
    payload = _read_json(raw_path)
    samples = _validate_prospective(payload)

    counts = _empty_counts()
    counts["samples"] = len(samples)

    relationship_matrix: Counter[tuple[str, str]] = Counter()

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

        relationship_matrix[(pa, book)] += 1

        pa_directional = pa in {"BUY", "SELL"}
        book_directional = book in {"BUY", "SELL"}

        if pa_directional:
            counts["pa_directional"] += 1

            if book == "NONE":
                counts["pa_directional_book_none"] += 1

        if book_directional:
            counts["book_directional"] += 1

        if canonical_conflict:
            counts["canonical_conflict_samples"] += 1

        if not (pa_directional and book_directional):
            continue

        counts["simultaneous_directional"] += 1

        if canonical_conflict:
            counts["simultaneous_canonical_conflict"] += 1

        if pa == book:
            counts["aligned"] += 1

            if canonical_conflict:
                counts["aligned_canonical_conflict"] += 1
        else:
            counts["opposed"] += 1

            if canonical_conflict:
                counts["opposed_canonical_conflict"] += 1

        if pa == "BUY" and book == "BUY":
            counts["pa_buy_book_buy"] += 1
        elif pa == "SELL" and book == "SELL":
            counts["pa_sell_book_sell"] += 1
        elif pa == "BUY" and book == "SELL":
            counts["pa_buy_book_sell"] += 1
        elif pa == "SELL" and book == "BUY":
            counts["pa_sell_book_buy"] += 1

    simultaneous = counts["simultaneous_directional"]

    aligned_rate = (
        counts["aligned"] / simultaneous
        if simultaneous > 0
        else None
    )
    opposed_rate = (
        counts["opposed"] / simultaneous
        if simultaneous > 0
        else None
    )

    return {
        "label": label,
        "raw_session": {
            "path": str(raw_path),
            "sha256": _sha256(raw_path),
        },
        **counts,
        "aligned_rate_among_simultaneous": aligned_rate,
        "opposed_rate_among_simultaneous": opposed_rate,
        "relationship_matrix": [
            {
                "price_action_bias": key[0],
                "book_direction": key[1],
                "count": count,
            }
            for key, count in sorted(relationship_matrix.items())
        ],
        "interpretation": {
            "unit": "SAMPLE",
            "opportunity_definition": (
                "price_action_bias and book_direction are both BUY or SELL"
            ),
            "conflict_source": "canonical conflict_count > 0 only",
            "opposed_does_not_imply_canonical_conflict": True,
            "episode_equivalence_claim_allowed": False,
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

    aggregate = _empty_counts()

    for session in sessions:
        for key in aggregate:
            aggregate[key] += session[key]

    simultaneous = aggregate["simultaneous_directional"]

    aggregate["aligned_rate_among_simultaneous"] = (
        aggregate["aligned"] / simultaneous
        if simultaneous > 0
        else None
    )
    aggregate["opposed_rate_among_simultaneous"] = (
        aggregate["opposed"] / simultaneous
        if simultaneous > 0
        else None
    )

    return {
        "version": VERSION,
        "status": "PA_BOOK_OPPORTUNITY_AUDIT_COMPLETED",
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
            "this_audit_unit": "SAMPLE",
            "frozen_opposed_episode_count": 17,
            "episode_count_used_as_sample_count": False,
            "sample_count_used_as_episode_count": False,
            "sample_episode_equivalence_claim_allowed": False,
        },
        "interpretation": "DESCRIPTIVE_ONLY",
        "interpretation_limits": [
            "DESCRIPTIVE_ONLY",
            "SAMPLE_LEVEL_OPPORTUNITIES_ARE_NOT_EPISODES",
            "146_OPPOSED_SAMPLES_MUST_NOT_BE_EQUATED_WITH_17_OPPOSED_EPISODES",
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
            "Passive fail-closed PA x Book sample-level opportunity audit "
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
