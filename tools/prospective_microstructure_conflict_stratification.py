"""Passive RC2 stratification of prospective conflict price follow-through.

Reads an RC1 conflict-price-followthrough JSON and stratifies only episodes where
Price Action and Book are directionally opposed:
  - PA BUY x Book SELL
  - PA SELL x Book BUY

Each mirror is split into:
  - SINGLE: one-sample conflict episode
  - PERSISTENT: conflict episode with more than one sample

This is descriptive research only. It does not change the prospective cohort,
audit verdict, thresholds, scoring, risk, decisions, alerts, execution, or
promotion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


VERSION = "RC2-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-STRATIFICATION"
EXPECTED_INPUT_VERSION = (
    "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-PRICE-FOLLOWTHROUGH"
)
MIRRORS = (
    ("BUY", "SELL"),
    ("SELL", "BUY"),
)

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


def _positive_int(value, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"invalid positive integer field: {field}")
    return value


def _validate_input(payload: dict) -> tuple[int, ...]:
    if not isinstance(payload, dict):
        raise ValueError("RC1 payload must be a JSON object")

    if payload.get("version") != EXPECTED_INPUT_VERSION:
        raise ValueError(
            "unexpected input version: "
            f"{payload.get('version')!r}"
        )

    if payload.get("status") != "DESCRIPTIVE_ONLY":
        raise ValueError("RC1 input must be DESCRIPTIVE_ONLY")

    if payload.get("research_only") is not True:
        raise ValueError("RC1 input must remain research_only")

    if payload.get("observational_only") is not True:
        raise ValueError("RC1 input must remain observational_only")

    for name in _FALSE_FLAGS:
        if payload.get(name) is not False:
            raise ValueError(f"RC1 safety flag must be false: {name}")

    eligible = payload.get("eligible_sessions")
    rejected = payload.get("rejected_sessions")

    if isinstance(eligible, bool) or not isinstance(eligible, int) or eligible < 0:
        raise ValueError("invalid eligible_sessions")
    if isinstance(rejected, bool) or not isinstance(rejected, int) or rejected < 0:
        raise ValueError("invalid rejected_sessions")

    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError("RC1 sessions must be a list")

    if len(sessions) != eligible:
        raise ValueError("eligible session count differs from session list length")

    horizons = payload.get("horizons_in_samples")
    if not isinstance(horizons, list) or not horizons:
        raise ValueError("RC1 horizons_in_samples must be a non-empty list")

    normalized = tuple(
        _positive_int(value, f"horizons_in_samples[{index}]")
        for index, value in enumerate(horizons)
    )

    if len(set(normalized)) != len(normalized):
        raise ValueError("RC1 horizons must be unique")

    return tuple(sorted(normalized))


def _mirror_name(pa: str, book: str) -> str:
    return f"PA_{pa}_BOOK_{book}"


def _bucket(sample_count: int) -> str:
    return "SINGLE" if sample_count == 1 else "PERSISTENT"


def _validate_episode(
    episode: dict,
    session_index: int,
    horizons: tuple[int, ...],
) -> None:
    if not isinstance(episode, dict):
        raise ValueError(f"invalid episode object in session {session_index}")

    _positive_int(
        episode.get("episode_index"),
        f"sessions[{session_index}].episode_index",
    )
    _positive_int(
        episode.get("sample_count"),
        f"sessions[{session_index}].sample_count",
    )

    followthrough = episode.get("followthrough")
    if not isinstance(followthrough, dict):
        raise ValueError(
            f"missing followthrough in session {session_index} episode"
        )

    for horizon in horizons:
        key = str(horizon)
        observation = followthrough.get(key)
        if not isinstance(observation, dict):
            raise ValueError(
                f"missing horizon {horizon} in session {session_index}"
            )

        available = observation.get("available")
        if not isinstance(available, bool):
            raise ValueError("followthrough available must be boolean")

        if not available:
            continue

        side = observation.get("observed_side")
        if side not in {
            "PRICE_ACTION",
            "BOOK",
            "FLAT",
            "SAME_DIRECTION",
            "UNRESOLVED",
        }:
            raise ValueError(f"invalid observed_side: {side!r}")

        _finite_number(
            observation.get("raw_displacement"),
            "raw_displacement",
        )

        pa_signed = observation.get("price_action_signed_displacement")
        book_signed = observation.get("book_signed_displacement")

        if pa_signed is not None:
            _finite_number(pa_signed, "price_action_signed_displacement")
        if book_signed is not None:
            _finite_number(book_signed, "book_signed_displacement")


def _collect(payload: dict, horizons: tuple[int, ...]) -> list[dict]:
    rows = []

    for session_index, session in enumerate(payload["sessions"], start=1):
        if not isinstance(session, dict):
            raise ValueError(f"invalid session object at index {session_index}")

        if session.get("alignment_validated") is not True:
            raise ValueError(
                f"session {session_index} lacks validated RC1 alignment"
            )

        path = session.get("path")
        sha256 = session.get("sha256")
        if not isinstance(path, str) or not path:
            raise ValueError(f"session {session_index} missing path")
        if not isinstance(sha256, str) or len(sha256) != 64:
            raise ValueError(f"session {session_index} missing SHA256")

        episodes = session.get("episodes")
        if not isinstance(episodes, list):
            raise ValueError(f"session {session_index} episodes must be a list")

        declared_episode_count = session.get("conflict_episodes")
        if (
            isinstance(declared_episode_count, bool)
            or not isinstance(declared_episode_count, int)
            or declared_episode_count < 0
            or declared_episode_count != len(episodes)
        ):
            raise ValueError(
                f"session {session_index} conflict episode count mismatch"
            )

        for episode in episodes:
            _validate_episode(episode, session_index, horizons)

            pa = episode.get("predominant_price_action_direction")
            book = episode.get("predominant_book_direction")

            if (pa, book) not in MIRRORS:
                continue

            sample_count = episode["sample_count"]
            mirror = _mirror_name(pa, book)
            bucket = _bucket(sample_count)

            for horizon in horizons:
                observation = episode["followthrough"][str(horizon)]
                if not observation["available"]:
                    continue

                rows.append(
                    {
                        "session_index": session_index,
                        "session_path": path,
                        "session_sha256": sha256,
                        "episode_index": episode["episode_index"],
                        "sample_count": sample_count,
                        "duration_bucket": bucket,
                        "mirror": mirror,
                        "price_action_direction": pa,
                        "book_direction": book,
                        "horizon": horizon,
                        "observed_side": observation["observed_side"],
                        "raw_displacement": float(
                            observation["raw_displacement"]
                        ),
                        "price_action_signed_displacement": float(
                            observation["price_action_signed_displacement"]
                        ),
                        "book_signed_displacement": float(
                            observation["book_signed_displacement"]
                        ),
                    }
                )

    return rows


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _summarize(rows: list[dict], horizons: tuple[int, ...]) -> dict:
    output = {}

    for pa, book in MIRRORS:
        mirror = _mirror_name(pa, book)
        output[mirror] = {}

        mirror_episode_keys = {
            (
                row["session_index"],
                row["episode_index"],
            )
            for row in rows
            if row["mirror"] == mirror
        }

        output[mirror]["episode_count_with_available_followthrough"] = len(
            mirror_episode_keys
        )

        for bucket in ("SINGLE", "PERSISTENT"):
            bucket_rows = [
                row
                for row in rows
                if row["mirror"] == mirror
                and row["duration_bucket"] == bucket
            ]

            bucket_episode_keys = {
                (row["session_index"], row["episode_index"])
                for row in bucket_rows
            }

            bucket_report = {
                "episode_count_with_available_followthrough": len(
                    bucket_episode_keys
                ),
                "by_horizon": {},
            }

            for horizon in horizons:
                current = [
                    row for row in bucket_rows
                    if row["horizon"] == horizon
                ]

                sides = Counter(row["observed_side"] for row in current)
                pa_wins = sides.get("PRICE_ACTION", 0)
                book_wins = sides.get("BOOK", 0)
                flats = sides.get("FLAT", 0)
                unresolved = sides.get("UNRESOLVED", 0)
                same_direction = sides.get("SAME_DIRECTION", 0)

                # SAME_DIRECTION should not normally occur in opposed mirrors.
                if same_direction:
                    raise ValueError(
                        "opposed PA/Book mirror produced SAME_DIRECTION"
                    )

                decisive = pa_wins + book_wins

                bucket_report["by_horizon"][str(horizon)] = {
                    "available_episode_count": len(current),
                    "observed_side_counts": dict(sorted(sides.items())),
                    "price_action_follow_count": pa_wins,
                    "book_follow_count": book_wins,
                    "flat_count": flats,
                    "unresolved_count": unresolved,
                    "decisive_episode_count": decisive,
                    "price_action_share_of_decisive": (
                        round(pa_wins / decisive, 6)
                        if decisive else None
                    ),
                    "mean_raw_displacement": _mean(
                        [row["raw_displacement"] for row in current]
                    ),
                    "mean_price_action_signed_displacement": _mean(
                        [
                            row["price_action_signed_displacement"]
                            for row in current
                        ]
                    ),
                    "mean_book_signed_displacement": _mean(
                        [
                            row["book_signed_displacement"]
                            for row in current
                        ]
                    ),
                }

            output[mirror][bucket] = bucket_report

    return output


def report_file(path: str | Path) -> dict:
    path = Path(path)
    raw = path.read_bytes()
    input_sha256 = hashlib.sha256(raw).hexdigest()
    payload = json.loads(raw.decode("utf-8-sig"))

    horizons = _validate_input(payload)
    rows = _collect(payload, horizons)

    opposed_episode_keys = {
        (row["session_index"], row["episode_index"])
        for row in rows
    }

    return {
        "version": VERSION,
        "status": "DESCRIPTIVE_ONLY",
        "source": {
            "path": str(path.resolve()),
            "sha256": input_sha256,
            "version": payload["version"],
        },
        "eligible_sessions": payload["eligible_sessions"],
        "rejected_sessions": payload["rejected_sessions"],
        "horizons_in_samples": list(horizons),
        "opposed_direction_episode_count_with_available_followthrough": len(
            opposed_episode_keys
        ),
        "stratification": _summarize(rows, horizons),
        "audit_stability": payload.get("audit_stability"),
        "audit_recommendation": payload.get("audit_recommendation"),
        "interpretation_guardrails": {
            "sample_horizons_are_not_minutes": True,
            "descriptive_counts_are_not_predictive_accuracy": True,
            "no_threshold_or_weight_change_allowed": True,
            "new_sessions_should_increase_group_sample_sizes_before_promotion": True,
        },
        **_safety(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = report_file(args.input)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")

    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
