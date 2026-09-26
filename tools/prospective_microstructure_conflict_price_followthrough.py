"""Passive price follow-through diagnostics for prospective conflict episodes.

This module measures observed last-price displacement after contiguous conflict
episodes from eligible prospective microstructure sessions.

It is descriptive research only. It does not change cohort eligibility, audit
verdicts, thresholds, scoring, risk, decisions, alerts, execution, or promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tools.prospective_microstructure_multi_session_audit import audit_paths
from tools.prospective_microstructure_conflict_episode_report import _episodes


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-PRICE-FOLLOWTHROUGH"
DEFAULT_HORIZONS = (1, 5, 10, 20)

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


def _finite_number(value, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid numeric field: {field}")

    value = float(value)

    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"non-finite numeric field: {field}")

    return value


def _validate_horizons(horizons) -> tuple[int, ...]:
    normalized = []

    for value in horizons:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("follow-through horizons must be positive integers")
        normalized.append(value)

    if not normalized:
        raise ValueError("at least one follow-through horizon is required")

    if len(set(normalized)) != len(normalized):
        raise ValueError("follow-through horizons must be unique")

    return tuple(sorted(normalized))


def _validate_alignment(base_samples: list[dict], micro_samples: list[dict]) -> None:
    if not isinstance(base_samples, list) or not isinstance(micro_samples, list):
        raise ValueError("prospective base and microstructure samples must be lists")

    if len(base_samples) != len(micro_samples):
        raise ValueError(
            "base sample count differs from prospective microstructure sample count"
        )

    for index, (base, micro) in enumerate(zip(base_samples, micro_samples)):
        if not isinstance(base, dict) or not isinstance(micro, dict):
            raise ValueError(f"invalid prospective sample object at index {index}")

        price_action = base.get("price_action")
        if not isinstance(price_action, dict):
            raise ValueError(f"base sample missing price_action at index {index}")

        base_bias = price_action.get("bias")
        micro_bias = micro.get("price_action_bias")

        if base_bias is None or micro_bias is None:
            raise ValueError(
                f"missing price-action alignment field at index {index}"
            )

        if base_bias != micro_bias:
            raise ValueError(
                "base/microstructure price-action alignment mismatch "
                f"at index {index}: {base_bias!r} != {micro_bias!r}"
            )

        _finite_number(base.get("last_price"), f"samples[{index}].last_price")

        timestamp = base.get("timestamp")
        if not isinstance(timestamp, str) or not timestamp:
            raise ValueError(f"base sample missing timestamp at index {index}")


def _signed_displacement(direction: str | None, raw_displacement: float) -> float | None:
    if direction == "BUY":
        return raw_displacement
    if direction == "SELL":
        return -raw_displacement
    return None


def _directional_observation(
    pa_direction: str | None,
    book_direction: str | None,
    raw_displacement: float,
) -> dict:
    pa_signed = _signed_displacement(pa_direction, raw_displacement)
    book_signed = _signed_displacement(book_direction, raw_displacement)

    if raw_displacement == 0:
        observed_side = "FLAT"
    elif pa_direction in ("BUY", "SELL") and book_direction in ("BUY", "SELL"):
        if pa_direction == book_direction:
            observed_side = "SAME_DIRECTION"
        elif pa_signed is not None and pa_signed > 0:
            observed_side = "PRICE_ACTION"
        elif book_signed is not None and book_signed > 0:
            observed_side = "BOOK"
        else:
            observed_side = "UNRESOLVED"
    else:
        observed_side = "UNRESOLVED"

    return {
        "price_action_signed_displacement": pa_signed,
        "book_signed_displacement": book_signed,
        "observed_side": observed_side,
    }


def _episode_followthrough(
    episode: dict,
    base_samples: list[dict],
    horizons: tuple[int, ...],
) -> dict:
    start_index = episode["start_sample_index"]
    end_index = episode["end_sample_index"]

    if start_index < 0 or end_index < start_index or end_index >= len(base_samples):
        raise ValueError("conflict episode indexes are outside base sample range")

    start_sample = base_samples[start_index]
    end_sample = base_samples[end_index]

    start_price = _finite_number(
        start_sample["last_price"],
        f"samples[{start_index}].last_price",
    )
    end_price = _finite_number(
        end_sample["last_price"],
        f"samples[{end_index}].last_price",
    )

    pa_direction = episode["predominant_price_action_direction"]
    book_direction = episode["predominant_book_direction"]

    result = {
        "episode_index": episode["episode_index"],
        "start_sample_index": start_index,
        "end_sample_index": end_index,
        "sample_count": episode["sample_count"],
        "start_timestamp": start_sample["timestamp"],
        "end_timestamp": end_sample["timestamp"],
        "start_price": start_price,
        "end_price": end_price,
        "within_episode_displacement": end_price - start_price,
        "predominant_price_action_direction": pa_direction,
        "predominant_flow_direction": episode["predominant_flow_direction"],
        "predominant_book_direction": book_direction,
        "followthrough": {},
    }

    for horizon in horizons:
        target_index = end_index + horizon
        key = str(horizon)

        if target_index >= len(base_samples):
            result["followthrough"][key] = {
                "available": False,
                "reason": "SESSION_END",
                "target_sample_index": target_index,
            }
            continue

        target_sample = base_samples[target_index]
        target_price = _finite_number(
            target_sample["last_price"],
            f"samples[{target_index}].last_price",
        )
        displacement = target_price - end_price

        result["followthrough"][key] = {
            "available": True,
            "target_sample_index": target_index,
            "target_timestamp": target_sample["timestamp"],
            "target_price": target_price,
            "raw_displacement": displacement,
            **_directional_observation(
                pa_direction=pa_direction,
                book_direction=book_direction,
                raw_displacement=displacement,
            ),
        }

    return result


def _aggregate_episode_results(
    episodes: list[dict],
    horizons: tuple[int, ...],
) -> dict:
    aggregate = {}

    for horizon in horizons:
        key = str(horizon)
        available = []
        side_counts = {}

        for episode in episodes:
            observation = episode["followthrough"][key]
            if not observation["available"]:
                continue

            available.append(observation)
            side = observation["observed_side"]
            side_counts[side] = side_counts.get(side, 0) + 1

        raw_values = [item["raw_displacement"] for item in available]
        pa_values = [
            item["price_action_signed_displacement"]
            for item in available
            if item["price_action_signed_displacement"] is not None
        ]
        book_values = [
            item["book_signed_displacement"]
            for item in available
            if item["book_signed_displacement"] is not None
        ]

        aggregate[key] = {
            "available_episode_count": len(available),
            "unavailable_episode_count": len(episodes) - len(available),
            "observed_side_counts": side_counts,
            "mean_raw_displacement": (
                round(sum(raw_values) / len(raw_values), 6) if raw_values else None
            ),
            "mean_price_action_signed_displacement": (
                round(sum(pa_values) / len(pa_values), 6) if pa_values else None
            ),
            "mean_book_signed_displacement": (
                round(sum(book_values) / len(book_values), 6) if book_values else None
            ),
        }

    return aggregate


def _session_report(
    base_samples: list[dict],
    micro_samples: list[dict],
    expected_conflicts: int,
    horizons: tuple[int, ...],
) -> dict:
    _validate_alignment(base_samples, micro_samples)

    episodes = _episodes(micro_samples)
    conflict_samples = sum(episode["sample_count"] for episode in episodes)

    if conflict_samples != expected_conflicts:
        raise ValueError(
            "conflict episode sample count differs from prospective session report"
        )

    episode_results = [
        _episode_followthrough(episode, base_samples, horizons)
        for episode in episodes
    ]

    return {
        "samples": len(base_samples),
        "alignment_validated": True,
        "alignment_method": "INDEX_AND_PRICE_ACTION_BIAS",
        "conflict_samples": conflict_samples,
        "conflict_episodes": len(episodes),
        "horizons_in_samples": list(horizons),
        "episodes": episode_results,
        "aggregate_by_horizon": _aggregate_episode_results(
            episode_results,
            horizons,
        ),
    }


def report_paths(paths, horizons=DEFAULT_HORIZONS) -> dict:
    horizons = _validate_horizons(tuple(horizons))
    audit = audit_paths(paths)
    sessions = []

    for accepted in audit["accepted"]:
        path = Path(accepted["path"])
        raw = path.read_bytes()

        digest = hashlib.sha256(raw).hexdigest()
        if digest != accepted["sha256"]:
            raise ValueError(
                "prospective session changed during price follow-through report"
            )

        payload = json.loads(raw.decode("utf-8-sig"))

        base_samples = payload.get("samples")
        evidence = payload.get("prospective_microstructure")

        if not isinstance(evidence, dict):
            raise ValueError("prospective_microstructure evidence is missing")

        micro_samples = evidence.get("samples")
        report = evidence.get("report")

        if not isinstance(report, dict):
            raise ValueError("prospective microstructure report is missing")

        expected_conflicts = report.get("conflict_samples")
        if (
            not isinstance(expected_conflicts, int)
            or isinstance(expected_conflicts, bool)
            or expected_conflicts < 0
        ):
            raise ValueError("invalid prospective conflict sample count")

        session = _session_report(
            base_samples=base_samples,
            micro_samples=micro_samples,
            expected_conflicts=expected_conflicts,
            horizons=horizons,
        )

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
        "horizons_in_samples": list(horizons),
        "sessions": sessions,
        "audit_stability": audit["aggregate"]["stability"],
        "audit_recommendation": audit["aggregate"]["recommendation"],
        **_safety(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument(
        "--horizons",
        nargs="+",
        type=int,
        default=list(DEFAULT_HORIZONS),
        help="positive sample-count horizons after each conflict episode",
    )
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = report_paths(args.paths, horizons=args.horizons)
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
