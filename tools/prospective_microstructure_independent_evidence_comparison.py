from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VERSION = (
    "RC1-PROSPECTIVE-MICROSTRUCTURE-"
    "INDEPENDENT-EVIDENCE-COMPARISON"
)

_DIRECTIONS = {"BUY", "SELL"}

_FALSE_SAFETY_FLAGS = (
    "predictive_claim_allowed",
    "score_influence_allowed",
    "risk_influence_allowed",
    "decision_influence_allowed",
    "alert_influence_allowed",
    "order_execution_allowed",
    "promotion_allowed",
)


def _safety() -> dict[str, bool]:
    return {
        "research_only": True,
        "observational_only": True,
        **{key: False for key in _FALSE_SAFETY_FLAGS},
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"not a readable file: {path}")

    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return payload


def _validate_safety(
    label: str,
    payload: dict[str, Any],
) -> None:
    expected = _safety()

    for key, expected_value in expected.items():
        if payload.get(key) is not expected_value:
            raise ValueError(
                f"{label}: unsafe or missing flag "
                f"{key}={payload.get(key)!r}; "
                f"expected {expected_value!r}"
            )


def _single_session(
    label: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if payload.get("status") != "DESCRIPTIVE_ONLY":
        raise ValueError(
            f"{label}: expected DESCRIPTIVE_ONLY"
        )

    if payload.get("eligible_sessions") != 1:
        raise ValueError(
            f"{label}: expected exactly one eligible session"
        )

    if payload.get("rejected_sessions") != 0:
        raise ValueError(
            f"{label}: rejected session present"
        )

    sessions = payload.get("sessions")

    if (
        not isinstance(sessions, list)
        or len(sessions) != 1
        or not isinstance(sessions[0], dict)
    ):
        raise ValueError(
            f"{label}: expected one session object"
        )

    _validate_safety(label, payload)

    return sessions[0]


def _coverage_summary(
    path: Path,
) -> dict[str, Any]:
    payload = _read_json(path)

    if (
        payload.get("version")
        != "RC1-PROSPECTIVE-MICROSTRUCTURE-COVERAGE"
    ):
        raise ValueError(
            "unexpected coverage version"
        )

    session = _single_session("coverage", payload)
    coverage = session.get("coverage")

    if not isinstance(coverage, dict):
        raise ValueError("missing coverage object")

    required = (
        "samples",
        "pa_directional",
        "flow_directional",
        "book_available",
        "book_directional",
        "insufficient_data",
        "pa_directional_insufficient_data",
        "conflicts",
        "conflict_runs",
        "longest_conflict_run",
    )

    for key in required:
        value = coverage.get(key)

        if not isinstance(value, int) or value < 0:
            raise ValueError(
                f"invalid coverage field: {key}"
            )

    return {
        "path": str(path),
        "sha256": _sha256(path),
        "session_path": session.get("path"),
        "session_sha256": session.get("sha256"),
        **{key: coverage[key] for key in required},
    }


def _episode_summary(
    path: Path,
) -> dict[str, Any]:
    payload = _read_json(path)

    if (
        payload.get("version")
        != (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-"
            "CONFLICT-EPISODES"
        )
    ):
        raise ValueError(
            "unexpected episodes version"
        )

    session = _single_session("episodes", payload)

    required = (
        "samples",
        "conflict_samples",
        "conflict_episodes",
        "longest_episode_samples",
    )

    for key in required:
        value = session.get(key)

        if not isinstance(value, int) or value < 0:
            raise ValueError(
                f"invalid episode field: {key}"
            )

    return {
        "path": str(path),
        "sha256": _sha256(path),
        **{key: session[key] for key in required},
        "mean_episode_samples": session.get(
            "mean_episode_samples"
        ),
    }


def _followthrough_summary(
    path: Path,
) -> dict[str, Any]:
    payload = _read_json(path)

    if (
        payload.get("version")
        != (
            "RC1-PROSPECTIVE-MICROSTRUCTURE-"
            "CONFLICT-PRICE-FOLLOWTHROUGH"
        )
    ):
        raise ValueError(
            "unexpected followthrough version"
        )

    session = _single_session(
        "followthrough",
        payload,
    )

    episodes = session.get("episodes")

    if not isinstance(episodes, list):
        raise ValueError(
            "followthrough episodes missing"
        )

    opposed = 0
    buy_sell = 0
    sell_buy = 0
    book_none = 0

    for episode in episodes:
        if not isinstance(episode, dict):
            raise ValueError(
                "invalid followthrough episode"
            )

        pa = episode.get(
            "predominant_price_action_direction"
        )
        book = episode.get(
            "predominant_book_direction"
        )

        if book == "NONE":
            book_none += 1

        if pa in _DIRECTIONS and book in _DIRECTIONS:
            if pa != book:
                opposed += 1

                if pa == "BUY" and book == "SELL":
                    buy_sell += 1

                elif pa == "SELL" and book == "BUY":
                    sell_buy += 1

    return {
        "path": str(path),
        "sha256": _sha256(path),
        "conflict_samples": session.get(
            "conflict_samples"
        ),
        "conflict_episodes": session.get(
            "conflict_episodes"
        ),
        "pa_book_opposed_episodes": opposed,
        "pa_buy_book_sell_episodes": buy_sell,
        "pa_sell_book_buy_episodes": sell_buy,
        "book_none_conflict_episodes": book_none,
    }


def _validate_same_session(
    coverage: dict[str, Any],
    episodes: dict[str, Any],
    followthrough: dict[str, Any],
) -> None:
    if (
        coverage["samples"]
        != episodes["samples"]
    ):
        raise ValueError(
            "coverage/episodes sample mismatch"
        )

    if (
        coverage["conflicts"]
        != episodes["conflict_samples"]
    ):
        raise ValueError(
            "coverage/episodes conflict mismatch"
        )

    if (
        episodes["conflict_samples"]
        != followthrough["conflict_samples"]
    ):
        raise ValueError(
            "episodes/followthrough conflict mismatch"
        )

    if (
        episodes["conflict_episodes"]
        != followthrough["conflict_episodes"]
    ):
        raise ValueError(
            "episode count mismatch"
        )


def _rates(
    summary: dict[str, Any],
) -> dict[str, float | None]:
    samples = summary["samples"]
    conflicts = summary["conflicts"]
    episodes = summary["conflict_episodes"]

    def rate(
        numerator: int,
        denominator: int,
    ) -> float | None:
        if denominator == 0:
            return None

        return round(numerator / denominator, 6)

    return {
        "pa_directional_rate": rate(
            summary["pa_directional"],
            samples,
        ),
        "flow_directional_rate": rate(
            summary["flow_directional"],
            samples,
        ),
        "book_directional_rate": rate(
            summary["book_directional"],
            samples,
        ),
        "conflict_sample_rate": rate(
            conflicts,
            samples,
        ),
        "pa_book_opposed_episode_rate": rate(
            summary["pa_book_opposed_episodes"],
            episodes,
        ),
    }


def _observation(
    label: str,
    coverage_path: Path,
    episodes_path: Path,
    followthrough_path: Path,
) -> dict[str, Any]:
    coverage = _coverage_summary(coverage_path)
    episodes = _episode_summary(episodes_path)
    followthrough = _followthrough_summary(
        followthrough_path
    )

    _validate_same_session(
        coverage,
        episodes,
        followthrough,
    )

    summary = {
        "label": label,
        "samples": coverage["samples"],
        "pa_directional": coverage[
            "pa_directional"
        ],
        "flow_directional": coverage[
            "flow_directional"
        ],
        "book_available": coverage[
            "book_available"
        ],
        "book_directional": coverage[
            "book_directional"
        ],
        "insufficient_data": coverage[
            "insufficient_data"
        ],
        "conflicts": coverage["conflicts"],
        "conflict_runs": coverage[
            "conflict_runs"
        ],
        "longest_conflict_run": coverage[
            "longest_conflict_run"
        ],
        "conflict_episodes": episodes[
            "conflict_episodes"
        ],
        "longest_episode_samples": episodes[
            "longest_episode_samples"
        ],
        "pa_book_opposed_episodes": followthrough[
            "pa_book_opposed_episodes"
        ],
        "pa_buy_book_sell_episodes": followthrough[
            "pa_buy_book_sell_episodes"
        ],
        "pa_sell_book_buy_episodes": followthrough[
            "pa_sell_book_buy_episodes"
        ],
        "book_none_conflict_episodes": followthrough[
            "book_none_conflict_episodes"
        ],
    }

    summary["rates"] = _rates(summary)

    return {
        "summary": summary,
        "artifacts": {
            "coverage": {
                "path": str(coverage_path),
                "sha256": coverage["sha256"],
            },
            "episodes": {
                "path": str(episodes_path),
                "sha256": episodes["sha256"],
            },
            "followthrough": {
                "path": str(followthrough_path),
                "sha256": followthrough["sha256"],
            },
        },
    }


def build_report(
    baseline_checkpoint: str | Path,
    session11_coverage: str | Path,
    session11_episodes: str | Path,
    session11_followthrough: str | Path,
    session12_coverage: str | Path,
    session12_episodes: str | Path,
    session12_followthrough: str | Path,
) -> dict[str, Any]:
    baseline_checkpoint = Path(
        baseline_checkpoint
    )

    checkpoint_sha_before = _sha256(
        baseline_checkpoint
    )
    checkpoint = _read_json(
        baseline_checkpoint
    )

    if checkpoint.get("session_count") != 10:
        raise ValueError(
            "baseline must remain 10 sessions"
        )

    if checkpoint.get("status") != "IDENTITY_LOCK_ONLY":
        raise ValueError(
            "baseline must remain identity locked"
        )

    _validate_safety(
        "baseline checkpoint",
        checkpoint,
    )

    session11 = _observation(
        "INDEPENDENT_SESSION_11",
        Path(session11_coverage),
        Path(session11_episodes),
        Path(session11_followthrough),
    )

    session12 = _observation(
        "INDEPENDENT_SESSION_12",
        Path(session12_coverage),
        Path(session12_episodes),
        Path(session12_followthrough),
    )

    sha11 = session11["summary"]
    sha12 = session12["summary"]

    if (
        session11["artifacts"]["coverage"]["sha256"]
        == session12["artifacts"]["coverage"]["sha256"]
    ):
        raise ValueError(
            "independent observations are not distinct"
        )

    report = {
        "version": VERSION,
        "status": (
            "INDEPENDENT_EVIDENCE_COMPARISON_COMPLETED"
        ),
        "mode": (
            "FROZEN_BASELINE_WITH_SEPARATE_"
            "INDEPENDENT_OBSERVATIONS"
        ),
        "baseline": {
            "label": "FROZEN_BASELINE_10",
            "path": str(baseline_checkpoint),
            "sha256": checkpoint_sha_before,
            "session_count": 10,
            "status": checkpoint.get("status"),
            "protocol": checkpoint.get("protocol"),
        },
        "independent_observations": [
            session11,
            session12,
        ],
        "comparison": {
            "baseline_session_count": 10,
            "independent_observation_count": 2,
            "independent_session_numbers": [11, 12],
            "combined_session_count": None,
            "combined_checkpoint_created": False,
            "cohort_redefinition": False,
            "interpretation": "DESCRIPTIVE_ONLY",
        },
        "architecture": {
            "explicit_paths_only": True,
            "glob_discovery_allowed": False,
            "baseline_mutated": False,
            "independent_sessions_appended": False,
            "independent_observations_combined": False,
            "post_result_rule_change_allowed": False,
            "automatic_promotion_allowed": False,
        },
        "diagnostic": {
            "session11_pa_book_opposed_episodes": (
                sha11["pa_book_opposed_episodes"]
            ),
            "session12_pa_book_opposed_episodes": (
                sha12["pa_book_opposed_episodes"]
            ),
            "independent_pa_book_replication_observed": (
                sha11["pa_book_opposed_episodes"] > 0
                or sha12["pa_book_opposed_episodes"] > 0
            ),
            "interpretation_limit": (
                "NO_CONFIRMATION_OR_REFUTATION_OF_"
                "FROZEN_BASELINE_PA_BOOK_PATTERN"
            ),
        },
        **_safety(),
    }

    if (
        _sha256(baseline_checkpoint)
        != checkpoint_sha_before
    ):
        raise ValueError(
            "baseline checkpoint changed during comparison"
        )

    return report


def _write_json(
    path: Path,
    payload: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_suffix(
        path.suffix + ".tmp"
    )

    temporary.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare two independent prospective "
            "microstructure observations while "
            "preserving the frozen 10-session "
            "baseline boundary."
        )
    )

    parser.add_argument("baseline_checkpoint")
    parser.add_argument("session11_coverage")
    parser.add_argument("session11_episodes")
    parser.add_argument("session11_followthrough")
    parser.add_argument("session12_coverage")
    parser.add_argument("session12_episodes")
    parser.add_argument("session12_followthrough")

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    args = parser.parse_args()

    try:
        report = build_report(
            args.baseline_checkpoint,
            args.session11_coverage,
            args.session11_episodes,
            args.session11_followthrough,
            args.session12_coverage,
            args.session12_episodes,
            args.session12_followthrough,
        )

        _write_json(args.output, report)

    except Exception as exc:
        failure = {
            "version": VERSION,
            "status": (
                "INDEPENDENT_EVIDENCE_COMPARISON_FAILED"
            ),
            "error_type": type(exc).__name__,
            "error": str(exc),
            **_safety(),
        }

        print(
            json.dumps(
                failure,
                ensure_ascii=False,
                indent=2,
            )
        )

        return 1

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())