from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


VERSION = "RC3-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-SESSION-STABILITY"
EXPECTED_INPUT_VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-CONFLICT-PRICE-FOLLOWTHROUGH"
STATUS = "DESCRIPTIVE_ONLY"

HORIZONS = (1, 5, 10, 20)
MIRRORS = (("BUY", "SELL"), ("SELL", "BUY"))
BUCKETS = ("SINGLE", "PERSISTENT")
VALID_SIDES = {"PRICE_ACTION", "BOOK", "FLAT", "UNRESOLVED", "SAME_DIRECTION"}

SAFETY = {
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


def _fail(message: str) -> None:
    raise ValueError(message)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        obj = json.load(fh)
    if not isinstance(obj, dict):
        _fail("Input JSON root must be an object.")
    return obj


def _direction(value: Any, field: str) -> str:
    if not isinstance(value, str):
        _fail(f"{field} must be a string.")
    value = value.upper()
    if value not in {"BUY", "SELL", "NONE", "MIXED"}:
        _fail(f"{field} has invalid direction: {value!r}")
    return value


def _bucket(sample_count: int) -> str:
    return "SINGLE" if sample_count == 1 else "PERSISTENT"


def _mirror_name(pa: str, book: str) -> str:
    return f"PA_{pa}_BOOK_{book}"


def _validate_safety(obj: dict[str, Any]) -> None:
    for key, expected in SAFETY.items():
        if obj.get(key) is not expected:
            _fail(f"Safety invariant failed: {key} must be {expected!r}.")


def _validate_input(obj: dict[str, Any]) -> None:
    if obj.get("version") != EXPECTED_INPUT_VERSION:
        _fail(
            f"Expected input version {EXPECTED_INPUT_VERSION!r}, "
            f"got {obj.get('version')!r}."
        )
    if obj.get("status") != STATUS:
        _fail(f"Input status must be {STATUS!r}.")
    _validate_safety(obj)

    eligible = obj.get("eligible_sessions")
    rejected = obj.get("rejected_sessions")
    if not _is_int(eligible) or eligible < 0:
        _fail("eligible_sessions must be a non-negative integer.")
    if not _is_int(rejected) or rejected < 0:
        _fail("rejected_sessions must be a non-negative integer.")

    horizons = obj.get("horizons_in_samples")
    if not isinstance(horizons, list) or tuple(horizons) != HORIZONS:
        _fail(f"horizons_in_samples must be exactly {list(HORIZONS)}.")

    sessions = obj.get("sessions")
    if not isinstance(sessions, list):
        _fail("sessions must be a list.")
    if len(sessions) != eligible:
        _fail("sessions length must equal eligible_sessions.")


def _validate_followthrough(ft: Any, session_i: int, episode_i: int) -> dict[str, Any]:
    if not isinstance(ft, dict):
        _fail(f"Session {session_i}, episode {episode_i}: followthrough must be an object.")

    for horizon in HORIZONS:
        item = ft.get(str(horizon))
        if not isinstance(item, dict):
            _fail(
                f"Session {session_i}, episode {episode_i}: "
                f"missing followthrough horizon {horizon}."
            )

        available = item.get("available")
        if not isinstance(available, bool):
            _fail(
                f"Session {session_i}, episode {episode_i}, horizon {horizon}: "
                "available must be boolean."
            )

        if available:
            side = item.get("observed_side")
            if side not in VALID_SIDES:
                _fail(
                    f"Session {session_i}, episode {episode_i}, horizon {horizon}: "
                    f"invalid observed_side {side!r}."
                )
            for field in (
                "raw_displacement",
                "price_action_signed_displacement",
            ):
                if not _finite_number(item.get(field)):
                    _fail(
                        f"Session {session_i}, episode {episode_i}, horizon {horizon}: "
                        f"{field} must be finite."
                    )

            book_signed = item.get("book_signed_displacement")
            if book_signed is not None and not _finite_number(book_signed):
                _fail(
                    f"Session {session_i}, episode {episode_i}, horizon {horizon}: "
                    "book_signed_displacement must be finite or null."
                )

    return ft


def _collect(obj: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    session_meta: list[dict[str, Any]] = []

    for session_i, session in enumerate(obj["sessions"], start=1):
        if not isinstance(session, dict):
            _fail(f"Session {session_i} must be an object.")
        if session.get("alignment_validated") is not True:
            _fail(f"Session {session_i}: alignment_validated must be true.")

        path = session.get("path")
        sha = session.get("sha256")
        if not isinstance(path, str) or not path:
            _fail(f"Session {session_i}: path is required.")
        if not isinstance(sha, str) or len(sha) != 64:
            _fail(f"Session {session_i}: sha256 must be a 64-character string.")

        episodes = session.get("episodes")
        if not isinstance(episodes, list):
            _fail(f"Session {session_i}: episodes must be a list.")

        expected_episode_count = session.get("conflict_episodes")
        if not _is_int(expected_episode_count) or expected_episode_count < 0:
            _fail(f"Session {session_i}: conflict_episodes must be non-negative integer.")
        if expected_episode_count != len(episodes):
            _fail(f"Session {session_i}: conflict_episodes does not match episodes length.")

        opposed_episode_ids: set[int] = set()
        for episode in episodes:
            if not isinstance(episode, dict):
                _fail(f"Session {session_i}: episode must be an object.")

            episode_i = episode.get("episode_index")
            sample_count = episode.get("sample_count")
            if not _is_int(episode_i) or episode_i <= 0:
                _fail(f"Session {session_i}: invalid episode_index.")
            if not _is_int(sample_count) or sample_count <= 0:
                _fail(f"Session {session_i}, episode {episode_i}: invalid sample_count.")

            pa = _direction(
                episode.get("predominant_price_action_direction"),
                "predominant_price_action_direction",
            )
            book = _direction(
                episode.get("predominant_book_direction"),
                "predominant_book_direction",
            )
            ft = _validate_followthrough(
                episode.get("followthrough"), session_i, episode_i
            )

            if (pa, book) not in MIRRORS:
                continue

            opposed_episode_ids.add(episode_i)
            mirror = _mirror_name(pa, book)
            bucket = _bucket(sample_count)

            for horizon in HORIZONS:
                item = ft[str(horizon)]
                if item["available"] is not True:
                    continue
                side = item["observed_side"]
                if side == "SAME_DIRECTION":
                    _fail(
                        f"Session {session_i}, episode {episode_i}: SAME_DIRECTION "
                        "is impossible for an opposed PA/Book mirror."
                    )
                rows.append(
                    {
                        "session_index": session_i,
                        "session_path": path,
                        "session_sha256": sha,
                        "episode_index": episode_i,
                        "sample_count": sample_count,
                        "duration_bucket": bucket,
                        "mirror": mirror,
                        "price_action_direction": pa,
                        "book_direction": book,
                        "horizon": horizon,
                        "observed_side": side,
                        "raw_displacement": float(item["raw_displacement"]),
                        "price_action_signed_displacement": float(
                            item["price_action_signed_displacement"]
                        ),
                        "book_signed_displacement": (
                            None
                            if item.get("book_signed_displacement") is None
                            else float(item["book_signed_displacement"])
                        ),
                    }
                )

        session_meta.append(
            {
                "session_index": session_i,
                "path": path,
                "sha256": sha,
                "samples": session.get("samples"),
                "conflict_samples": session.get("conflict_samples"),
                "conflict_episodes": expected_episode_count,
                "opposed_direction_episode_count": len(opposed_episode_ids),
            }
        )

    return rows, session_meta


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _session_horizon_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["observed_side"] for row in rows)
    pa = counts["PRICE_ACTION"]
    book = counts["BOOK"]
    flat = counts["FLAT"]
    unresolved = counts["UNRESOLVED"]
    decisive = pa + book

    return {
        "available_episode_count": len(rows),
        "observed_side_counts": dict(sorted(counts.items())),
        "price_action_follow_count": pa,
        "book_follow_count": book,
        "flat_count": flat,
        "unresolved_count": unresolved,
        "decisive_episode_count": decisive,
        "price_action_share_of_decisive": (
            None if decisive == 0 else _round(pa / decisive)
        ),
        "mean_raw_displacement": _round(
            _mean([row["raw_displacement"] for row in rows])
        ),
        "mean_price_action_signed_displacement": _round(
            _mean([row["price_action_signed_displacement"] for row in rows])
        ),
        "mean_book_signed_displacement": _round(
            _mean(
                [
                    row["book_signed_displacement"]
                    for row in rows
                    if row["book_signed_displacement"] is not None
                ]
            )
        ),
    }


def _build_session_matrix(
    rows: list[dict[str, Any]],
    session_meta: list[dict[str, Any]],
) -> dict[str, Any]:
    by_key: dict[tuple[str, str, int, int], list[dict[str, Any]]] = defaultdict(list)
    episode_ids: dict[tuple[str, str, int], set[int]] = defaultdict(set)

    for row in rows:
        key = (
            row["mirror"],
            row["duration_bucket"],
            row["horizon"],
            row["session_index"],
        )
        by_key[key].append(row)
        episode_ids[
            (row["mirror"], row["duration_bucket"], row["session_index"])
        ].add(row["episode_index"])

    result: dict[str, Any] = {}

    for pa, book in MIRRORS:
        mirror = _mirror_name(pa, book)
        result[mirror] = {}
        for bucket in BUCKETS:
            bucket_obj: dict[str, Any] = {"by_horizon": {}}
            for horizon in HORIZONS:
                session_rows: list[dict[str, Any]] = []
                observed_session_count = 0
                for meta in session_meta:
                    session_i = meta["session_index"]
                    subset = by_key.get((mirror, bucket, horizon, session_i), [])
                    if subset:
                        observed_session_count += 1
                    session_rows.append(
                        {
                            "session_index": session_i,
                            "path": meta["path"],
                            "sha256": meta["sha256"],
                            "episode_count_with_available_followthrough": len(
                                episode_ids.get((mirror, bucket, session_i), set())
                            ),
                            **_session_horizon_summary(subset),
                        }
                    )

                bucket_obj["by_horizon"][str(horizon)] = {
                    "sessions_with_observations": observed_session_count,
                    "sessions_without_observations": len(session_meta)
                    - observed_session_count,
                    "session_results": session_rows,
                }
            result[mirror][bucket] = bucket_obj

    return result


def _cross_session_descriptive(matrix: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pa, book in MIRRORS:
        mirror = _mirror_name(pa, book)
        out[mirror] = {}
        for bucket in BUCKETS:
            out[mirror][bucket] = {}
            for horizon in HORIZONS:
                node = matrix[mirror][bucket]["by_horizon"][str(horizon)]
                observed = [
                    s for s in node["session_results"]
                    if s["available_episode_count"] > 0
                ]
                means = [
                    s["mean_price_action_signed_displacement"]
                    for s in observed
                    if s["mean_price_action_signed_displacement"] is not None
                ]
                positive = sum(1 for x in means if x > 0)
                negative = sum(1 for x in means if x < 0)
                zero = sum(1 for x in means if x == 0)

                out[mirror][bucket][str(horizon)] = {
                    "sessions_with_observations": len(observed),
                    "positive_session_mean_pa_signed_displacement_count": positive,
                    "negative_session_mean_pa_signed_displacement_count": negative,
                    "zero_session_mean_pa_signed_displacement_count": zero,
                    "mean_of_session_mean_pa_signed_displacements": _round(
                        _mean([float(x) for x in means])
                    ),
                    "min_session_mean_pa_signed_displacement": (
                        None if not means else _round(min(means))
                    ),
                    "max_session_mean_pa_signed_displacement": (
                        None if not means else _round(max(means))
                    ),
                }
    return out


def build_report(input_path: Path) -> dict[str, Any]:
    obj = _load(input_path)
    _validate_input(obj)
    rows, session_meta = _collect(obj)
    matrix = _build_session_matrix(rows, session_meta)

    opposed_episode_ids = {
        (row["session_index"], row["episode_index"])
        for row in rows
    }

    return {
        "version": VERSION,
        "status": STATUS,
        "source": {
            "path": str(input_path.resolve()),
            "sha256": _sha256(input_path),
            "version": obj["version"],
        },
        "eligible_sessions": obj["eligible_sessions"],
        "rejected_sessions": obj["rejected_sessions"],
        "horizons_in_samples": list(HORIZONS),
        "predeclared_strata": {
            "mirrors": [
                _mirror_name(pa, book) for pa, book in MIRRORS
            ],
            "duration_buckets": {
                "SINGLE": "sample_count == 1",
                "PERSISTENT": "sample_count >= 2",
            },
        },
        "opposed_direction_episode_count_with_available_followthrough": len(
            opposed_episode_ids
        ),
        "sessions": session_meta,
        "session_stability_matrix": matrix,
        "cross_session_descriptive_summary": _cross_session_descriptive(matrix),
        "audit_stability": obj.get("audit_stability"),
        "audit_recommendation": obj.get("audit_recommendation"),
        "interpretation_guardrails": {
            "sample_horizons_are_not_minutes": True,
            "session_counts_are_not_predictive_accuracy": True,
            "pooled_episode_counts_are_not_independent_session_replications": True,
            "absence_in_a_session_is_not_negative_evidence": True,
            "no_threshold_or_weight_change_allowed": True,
            "no_promotion_from_this_report_allowed": True,
            "future_sessions_must_use_the_same_predeclared_strata": True,
        },
        **SAFETY,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "RC3 passive session-level stability report for prospective "
            "microstructure PA/Book conflict follow-through."
        )
    )
    parser.add_argument(
        "input",
        help="RC1 prospective_microstructure_conflict_price_followthrough JSON.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON path.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    report = build_report(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print("status=", report["status"])
    print("version=", report["version"])
    print("eligible_sessions=", report["eligible_sessions"])
    print(
        "opposed_direction_episodes=",
        report["opposed_direction_episode_count_with_available_followthrough"],
    )
    print("audit_stability=", report["audit_stability"])
    print("audit_recommendation=", report["audit_recommendation"])
    print("output=", str(output_path))


if __name__ == "__main__":
    main()
