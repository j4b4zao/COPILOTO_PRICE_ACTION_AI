"""Passive conflict-episode diagnostics for eligible prospective sessions.

Contiguous conflict samples are grouped into descriptive episodes.
This module does not change the multi-session audit verdict, cohort,
thresholds, scoring, risk, decisions, alerts, or execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from tools.prospective_microstructure_multi_session_audit import audit_paths
from tools.prospective_microstructure_coverage_report import _coverage


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-EPISODES"

_FALSE_FLAGS = (
    "predictive_claim_allowed",
    "score_influence_allowed",
    "risk_influence_allowed",
    "decision_influence_allowed",
    "alert_influence_allowed",
    "order_execution_allowed",
    "promotion_allowed",
)


def _safety() -> dict:
    return {
        "research_only": True,
        "observational_only": True,
        **{name: False for name in _FALSE_FLAGS},
    }


def _is_conflict(sample: dict) -> bool:
    if not isinstance(sample, dict):
        raise ValueError("prospective sample must be an object")

    if "state" not in sample or "conflict_count" not in sample:
        raise ValueError("prospective sample missing conflict diagnostic fields")

    conflict_count = sample["conflict_count"]
    if not isinstance(conflict_count, int) or isinstance(conflict_count, bool):
        raise ValueError("prospective sample has invalid conflict count")
    if conflict_count < 0:
        raise ValueError("prospective sample has invalid conflict count")

    return sample["state"] == "CONFLICT" or conflict_count > 0


def _predominant(values: list) -> str | None:
    if not values:
        return None

    counts = Counter(values)
    maximum = max(counts.values())
    winners = [value for value, count in counts.items() if count == maximum]

    if len(winners) != 1:
        return "MIXED"

    return winners[0]


def _direction_counts(samples: list[dict], key: str) -> dict:
    values = []
    for sample in samples:
        if key not in sample:
            raise ValueError(f"prospective sample missing {key}")
        values.append(sample[key])

    return dict(Counter(values))


def _optional_counts(samples: list[dict], key: str) -> dict | None:
    present = [key in sample for sample in samples]

    if not any(present):
        return None

    if not all(present):
        raise ValueError(f"prospective samples inconsistently contain {key}")

    values = [sample[key] for sample in samples]
    return dict(Counter(values))


def _episode(
    episode_index: int,
    start_sample_index: int,
    episode_samples: list[dict],
) -> dict:
    if not episode_samples:
        raise ValueError("conflict episode cannot be empty")

    end_sample_index = start_sample_index + len(episode_samples) - 1

    for sample in episode_samples:
        for key in (
            "price_action_bias",
            "flow_direction",
            "book_direction",
            "state",
            "conflict_count",
        ):
            if key not in sample:
                raise ValueError(
                    f"prospective sample missing conflict episode field: {key}"
                )

        if not _is_conflict(sample):
            raise ValueError("non-conflict sample found inside conflict episode")

    pa_counts = _direction_counts(episode_samples, "price_action_bias")
    flow_counts = _direction_counts(episode_samples, "flow_direction")
    book_counts = _direction_counts(episode_samples, "book_direction")

    conflict_counts = [sample["conflict_count"] for sample in episode_samples]
    states = dict(Counter(sample["state"] for sample in episode_samples))

    result = {
        "episode_index": episode_index,
        "start_sample_index": start_sample_index,
        "end_sample_index": end_sample_index,
        "sample_count": len(episode_samples),
        "start_timestamp": None,
        "end_timestamp": None,
        "temporal_reference": "SAMPLE_INDEX_ONLY",
        "price_action_direction_counts": pa_counts,
        "flow_direction_counts": flow_counts,
        "book_direction_counts": book_counts,
        "predominant_price_action_direction": _predominant(
            [sample["price_action_bias"] for sample in episode_samples]
        ),
        "predominant_flow_direction": _predominant(
            [sample["flow_direction"] for sample in episode_samples]
        ),
        "predominant_book_direction": _predominant(
            [sample["book_direction"] for sample in episode_samples]
        ),
        "conflict_count_sum": sum(conflict_counts),
        "max_conflict_count": max(conflict_counts),
        "states": states,
    }

    structural_counts = _optional_counts(
        episode_samples,
        "structural_evidence",
    )
    if structural_counts is not None:
        result["structural_evidence_counts"] = structural_counts

    return result


def _episodes(samples: list[dict]) -> list[dict]:
    if not isinstance(samples, list):
        raise ValueError("prospective samples must be a list")

    episodes = []
    current_samples: list[dict] = []
    current_start: int | None = None

    def close_current() -> None:
        nonlocal current_samples, current_start

        if not current_samples:
            return

        episodes.append(
            _episode(
                episode_index=len(episodes) + 1,
                start_sample_index=current_start,
                episode_samples=current_samples,
            )
        )

        current_samples = []
        current_start = None

    for index, sample in enumerate(samples):
        conflict = _is_conflict(sample)

        if conflict:
            if not current_samples:
                current_start = index
            current_samples.append(sample)
        else:
            close_current()

    close_current()

    return episodes


def _session_report(samples: list[dict], expected_conflicts: int) -> dict:
    coverage = _coverage(samples)

    if coverage["conflicts"] != expected_conflicts:
        raise ValueError(
            "prospective conflict count differs from session report"
        )

    episodes = _episodes(samples)

    conflict_samples = sum(
        episode["sample_count"] for episode in episodes
    )

    if conflict_samples != expected_conflicts:
        raise ValueError(
            "conflict episode sample count differs from session report"
        )

    longest_episode = max(
        (episode["sample_count"] for episode in episodes),
        default=0,
    )

    if len(episodes) != coverage["conflict_runs"]:
        raise ValueError(
            "conflict episode count differs from coverage report"
        )

    if longest_episode != coverage["longest_conflict_run"]:
        raise ValueError(
            "longest conflict episode differs from coverage report"
        )

    mean_episode = (
        conflict_samples / len(episodes)
        if episodes
        else 0.0
    )

    return {
        "samples": len(samples),
        "conflict_samples": conflict_samples,
        "conflict_episodes": len(episodes),
        "longest_episode_samples": longest_episode,
        "mean_episode_samples": round(mean_episode, 4),
        "episodes": episodes,
    }


def report_paths(paths) -> dict:
    audit = audit_paths(paths)
    sessions = []

    for accepted in audit["accepted"]:
        path = Path(accepted["path"])
        raw = path.read_bytes()

        digest = hashlib.sha256(raw).hexdigest()
        if digest != accepted["sha256"]:
            raise ValueError(
                "prospective session changed during conflict episode report"
            )

        payload = json.loads(raw.decode("utf-8-sig"))
        evidence = payload["prospective_microstructure"]

        samples = evidence["samples"]
        expected_conflicts = evidence["report"]["conflict_samples"]

        session = _session_report(samples, expected_conflicts)

        sessions.append(
            {
                **accepted,
                **session,
            }
        )

    return {
        "version": VERSION,
        "status": "DESCRIPTIVE_ONLY",
        "eligible_sessions": audit["eligible_sessions"],
        "rejected_sessions": audit["rejected_sessions"],
        "sessions": sessions,
        "audit_stability": audit["aggregate"]["stability"],
        "audit_recommendation": audit["aggregate"]["recommendation"],
        **_safety(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = report_paths(args.paths)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(
            rendered + "\n",
            encoding="utf-8",
        )

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())