"""Stage 3.4 - Brooks Independent Episode / Trade Deduplication Research.

Research-only utility.

Consumes a Brooks lifecycle/outcome report and builds a deterministic,
non-overlapping cohort of paired baseline/trailing episodes. It does not
recalculate entries, stops, targets, MFE, MAE, exits, or performance.

For Stage 3.3 intrabar-bounded reports, the independent interval is defined as:
- start: entry_event_candle_id timestamp (or an explicit entry/start boundary);
- end: the latest available baseline/trailing exit boundary for the SAME episode.

Using the latest paired exit prevents a subsequent accepted episode from
sharing candles with either arm of the baseline-vs-trailing comparison.
"""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


STAGE = "BROOKS_STAGE_3_4_INDEPENDENT_EPISODE_RESEARCH_V1"
POLICY = "GREEDY_NON_OVERLAPPING_BY_SESSION_START_ORDER"
PAIRED_INTERVAL_POLICY = "START_AT_ENTRY_END_AT_LATEST_BASELINE_OR_TRAILING_EXIT"


def _safety() -> dict[str, Any]:
    return {
        "research_only": True,
        "observational_only": True,
        "performance_validated": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def _first(mapping: dict[str, Any], names: Iterable[str], default=None):
    for name in names:
        if name in mapping and mapping[name] is not None:
            return mapping[name]
    return default


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (ValueError, TypeError):
            return None
    return None


def _as_dt(value):
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _dt_from_candle_id(value):
    if not isinstance(value, str) or not value.strip():
        return None
    return _as_dt(value.rsplit("|", 1)[-1])


def _episode_records(payload: Any) -> list[tuple[dict[str, Any], str | None]]:
    """Return episodes with parent-session identity when available.

    Stage 3.3 stores episodes inside ``sessions[]``. Older research artifacts may
    expose a top-level episode list. We support both without synthesizing market
    evidence.
    """
    if not isinstance(payload, dict):
        return []

    sessions = payload.get("sessions")
    if isinstance(sessions, list):
        records: list[tuple[dict[str, Any], str | None]] = []
        for session_index, session in enumerate(sessions):
            if not isinstance(session, dict):
                continue
            episodes = session.get("episodes")
            if not isinstance(episodes, list):
                continue
            session_identity = str(
                _first(
                    session,
                    ("source", "session", "session_id", "session_name"),
                    f"SESSION_{session_index:06d}",
                )
            )
            for ep in episodes:
                if isinstance(ep, dict):
                    records.append((ep, session_identity))
        if records:
            return records

    for key in (
        "episodes",
        "entry_episodes",
        "trade_episodes",
        "outcome_episodes",
        "lifecycle_episodes",
        "observations",
    ):
        value = payload.get(key)
        if isinstance(value, list) and all(isinstance(x, dict) for x in value):
            return [(x, None) for x in value]

    for key in ("report", "result", "outcome", "management", "stage_3_3"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            found = _episode_records(nested)
            if found:
                return found

    return []


def _session_id(ep: dict[str, Any], ordinal: int, parent_session: str | None) -> str:
    value = _first(
        ep,
        ("session", "session_id", "session_name", "source_session", "source_file", "file"),
    )
    if value is not None:
        return str(value)
    if parent_session is not None:
        return parent_session
    # Unknown sessions must not be silently merged, because that could create
    # false overlap rejections across unrelated sessions.
    return f"UNKNOWN_SESSION_{ordinal:06d}"


@dataclass(frozen=True)
class Boundary:
    kind: str
    start: Any
    end: Any
    source: str


def _nested_outcome(ep: dict[str, Any], name: str) -> dict[str, Any]:
    value = ep.get(name)
    return value if isinstance(value, dict) else {}


def _latest_numeric(*values):
    clean = [v for v in values if v is not None]
    return max(clean) if clean else None


def _latest_datetime(*values):
    clean = [v for v in values if v is not None]
    return max(clean) if clean else None


def _boundary(ep: dict[str, Any]) -> Boundary | None:
    baseline = _nested_outcome(ep, "baseline")
    trailing = _nested_outcome(ep, "trailing")

    # 1) Fully explicit legacy integer interval.
    start_index = _as_int(
        _first(
            ep,
            (
                "entry_index",
                "start_index",
                "episode_start_index",
                "entry_exact_index",
                "entry_candle_index",
                "start_candle_index",
            ),
        )
    )
    direct_end_index = _as_int(
        _first(
            ep,
            (
                "exit_index",
                "end_index",
                "episode_end_index",
                "exit_exact_index",
                "exit_candle_index",
                "end_candle_index",
                "last_observed_index",
            ),
        )
    )
    paired_end_index = _latest_numeric(
        direct_end_index,
        _as_int(_first(baseline, ("exit_exact_index", "exit_index"))),
        _as_int(_first(trailing, ("exit_exact_index", "exit_index"))),
    )
    if start_index is not None and paired_end_index is not None and paired_end_index >= start_index:
        source = (
            "PAIRED_NESTED_EXIT_INDEX_INTERVAL"
            if baseline or trailing
            else "EXPLICIT_INDEX_INTERVAL"
        )
        return Boundary("INDEX", start_index, paired_end_index, source)

    # 2) Explicit timestamps, allowing paired nested exits.
    start_ts = _as_dt(
        _first(
            ep,
            (
                "entry_timestamp",
                "start_timestamp",
                "episode_start_timestamp",
                "entry_time",
                "start_time",
            ),
        )
    )
    direct_end_ts = _as_dt(
        _first(
            ep,
            (
                "exit_timestamp",
                "end_timestamp",
                "episode_end_timestamp",
                "exit_time",
                "end_time",
                "last_observed_timestamp",
            ),
        )
    )
    paired_end_ts = _latest_datetime(
        direct_end_ts,
        _as_dt(_first(baseline, ("exit_timestamp", "exit_time"))),
        _as_dt(_first(trailing, ("exit_timestamp", "exit_time"))),
    )
    if start_ts is not None and paired_end_ts is not None and paired_end_ts >= start_ts:
        source = (
            "PAIRED_NESTED_EXIT_TIMESTAMP_INTERVAL"
            if baseline or trailing
            else "EXPLICIT_TIMESTAMP_INTERVAL"
        )
        return Boundary("TIMESTAMP", start_ts, paired_end_ts, source)

    # 3) Candle-ID timestamp interval. This is the canonical Stage 3.3 path:
    #    entry_event_candle_id -> latest baseline/trailing exit_candle_id.
    start_id = _first(
        ep,
        (
            "entry_event_candle_id",
            "entry_candle_id",
            "start_candle_id",
            "episode_start_candle_id",
        ),
    )
    start_dt = _dt_from_candle_id(start_id)
    direct_end_id = _first(ep, ("exit_candle_id", "end_candle_id", "episode_end_candle_id"))
    paired_end_dt = _latest_datetime(
        _dt_from_candle_id(direct_end_id),
        _dt_from_candle_id(_first(baseline, ("exit_candle_id",))),
        _dt_from_candle_id(_first(trailing, ("exit_candle_id",))),
    )
    if start_dt is not None and paired_end_dt is not None and paired_end_dt >= start_dt:
        source = (
            "PAIRED_STAGE_3_3_CANDLE_ID_INTERVAL"
            if baseline or trailing
            else "CANDLE_ID_TIMESTAMP_INTERVAL"
        )
        return Boundary("TIMESTAMP", start_dt, paired_end_dt, source)

    return None


def _episode_id(ep: dict[str, Any], ordinal: int) -> str:
    value = _first(ep, ("episode_id", "trade_id", "entry_episode_id", "id"))
    return str(value) if value is not None else f"EPISODE_{ordinal:06d}"


def _sort_key(item):
    session, ordinal, boundary, _ = item
    if boundary.kind == "INDEX":
        return (session, 0, boundary.start, ordinal)
    return (session, 1, boundary.start.isoformat(), ordinal)


def _outcome_snapshot(ep: dict[str, Any]) -> dict[str, Any]:
    """Copy outcome evidence exactly as captured; never recalculate it."""
    baseline = deepcopy(_nested_outcome(ep, "baseline"))
    trailing = deepcopy(_nested_outcome(ep, "trailing"))
    return {
        "episode_status": ep.get("status"),
        "eligible": ep.get("eligible"),
        "baseline": baseline,
        "trailing": trailing,
        "final_hypothetical_trailing_stop": ep.get("final_hypothetical_trailing_stop"),
    }


def _legacy_metrics(ep: dict[str, Any]) -> dict[str, Any]:
    """Preserve legacy flattened outcome fields when present."""
    return {
        "baseline_exit_reason": _first(
            ep, ("baseline_exit_reason", "baseline_outcome", "baseline_status")
        ),
        "trailing_exit_reason": _first(
            ep, ("trailing_exit_reason", "trailing_outcome", "trailing_status")
        ),
        "baseline_exit_r": _first(ep, ("baseline_exit_r", "baseline_r", "baseline_result_r")),
        "trailing_exit_r": _first(ep, ("trailing_exit_r", "trailing_r", "trailing_result_r")),
        "confirmed_mfe_r": _first(ep, ("confirmed_mfe_r", "mfe_r_confirmed", "mfe_r")),
        "possible_mfe_r": _first(ep, ("possible_mfe_r", "mfe_r_possible")),
        "bounded_mae_r": _first(ep, ("bounded_mae_r", "mae_r_bounded", "mae_r")),
    }


def build_independent_cohort(payload: dict[str, Any]) -> dict[str, Any]:
    records = _episode_records(payload)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    candidates = []
    no_post_entry_evidence_count = 0

    for ordinal, (ep, parent_session) in enumerate(records):
        boundary = _boundary(ep)
        eid = _episode_id(ep, ordinal)
        session = _session_id(ep, ordinal, parent_session)
        episode_status = ep.get("status")

        if episode_status == "NO_POST_ENTRY_EVIDENCE":
            no_post_entry_evidence_count += 1

        if boundary is None:
            reason = (
                "NO_POST_ENTRY_EVIDENCE_NO_EXIT_BOUNDARY"
                if episode_status == "NO_POST_ENTRY_EVIDENCE"
                else "EPISODE_INTERVAL_UNAVAILABLE"
            )
            rejected.append(
                {
                    "episode_id": eid,
                    "session": session,
                    "source_ordinal": ordinal,
                    "reason": reason,
                    "episode_status": episode_status,
                    "outcome_snapshot": _outcome_snapshot(ep),
                }
            )
            continue

        candidates.append((session, ordinal, boundary, ep))

    candidates.sort(key=_sort_key)
    last_by_session: dict[str, Boundary] = {}

    for session, ordinal, boundary, ep in candidates:
        eid = _episode_id(ep, ordinal)
        previous = last_by_session.get(session)

        if previous is not None:
            if previous.kind != boundary.kind:
                rejected.append(
                    {
                        "episode_id": eid,
                        "session": session,
                        "source_ordinal": ordinal,
                        "reason": "BOUNDARY_KIND_MISMATCH_WITHIN_SESSION",
                        "episode_status": ep.get("status"),
                        "outcome_snapshot": _outcome_snapshot(ep),
                    }
                )
                continue

            # Closed intervals: sharing the previous exit candle is overlap.
            if boundary.start <= previous.end:
                rejected.append(
                    {
                        "episode_id": eid,
                        "session": session,
                        "source_ordinal": ordinal,
                        "reason": "OVERLAPS_PREVIOUS_ACCEPTED_EPISODE",
                        "boundary_kind": boundary.kind,
                        "start": str(boundary.start),
                        "end": str(boundary.end),
                        "previous_end": str(previous.end),
                        "episode_status": ep.get("status"),
                        "outcome_snapshot": _outcome_snapshot(ep),
                    }
                )
                continue

        outcome = _outcome_snapshot(ep)
        accepted.append(
            {
                "episode_id": eid,
                "session": session,
                "source_ordinal": ordinal,
                "boundary_kind": boundary.kind,
                "boundary_source": boundary.source,
                "start": str(boundary.start),
                "end": str(boundary.end),
                "direction": _first(ep, ("direction", "trade_direction", "side")),
                "entry_price": _first(ep, ("entry_price", "entry")),
                "initial_stop": _first(ep, ("initial_stop", "stop_price", "baseline_stop")),
                "initial_risk_points": ep.get("initial_risk_points"),
                **_legacy_metrics(ep),
                **outcome,
            }
        )
        last_by_session[session] = boundary

    source_count = len(records)
    independent_count = len(accepted)
    resolved_count = len(candidates)

    paired_baseline_count = sum(
        1 for x in accepted if isinstance(x.get("baseline"), dict) and x["baseline"]
    )
    paired_trailing_count = sum(
        1 for x in accepted if isinstance(x.get("trailing"), dict) and x["trailing"]
    )
    paired_comparison_count = sum(
        1
        for x in accepted
        if isinstance(x.get("baseline"), dict)
        and x["baseline"]
        and isinstance(x.get("trailing"), dict)
        and x["trailing"]
    )

    return {
        "stage": STAGE,
        "status": (
            "INDEPENDENT_EPISODE_COHORT_COMPLETED"
            if independent_count
            else "NO_INDEPENDENT_EPISODES_AVAILABLE"
        ),
        "deduplication_policy": POLICY,
        "paired_interval_policy": PAIRED_INTERVAL_POLICY,
        "source_episode_count": source_count,
        "interval_resolved_episode_count": resolved_count,
        "independent_episode_count": independent_count,
        "rejected_episode_count": len(rejected),
        "no_post_entry_evidence_count": no_post_entry_evidence_count,
        "paired_baseline_count": paired_baseline_count,
        "paired_trailing_count": paired_trailing_count,
        "paired_comparison_count": paired_comparison_count,
        "deduplication_reduction_count": source_count - independent_count,
        "deduplication_reduction_rate": (
            (source_count - independent_count) / source_count if source_count else 0.0
        ),
        "independent_episodes": accepted,
        "rejected_episodes": rejected,
        **_safety(),
    }


def audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return build_independent_cohort(payload)


def audit(path_or_payload) -> dict[str, Any]:
    if isinstance(path_or_payload, dict):
        return audit_payload(path_or_payload)

    path = Path(path_or_payload)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    report = audit_payload(payload)
    report["source_path"] = str(path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Stage 3.4 Brooks independent episode deduplication research."
    )
    parser.add_argument("input_json")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = audit(args.input_json)
    text = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False)

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(output)
    else:
        print(text)


if __name__ == "__main__":
    main()
