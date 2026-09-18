"""Brooks Trailing Active Survival Audit V1.

Research-only / observational-only diagnostic.

Cross-checks lifecycle episodes that actually applied one or more trailing-stop
revisions against the Stage 3.4 independent/rejected episode cohort.

This audit:
- does not recalculate entries, stops, exits, MFE, MAE, or performance;
- does not change lifecycle or Stage 3.4 evidence;
- uses canonical session::episode_id identity;
- reports how many trailing-active lifecycle episodes survive independence;
- preserves baseline/trailing outcome evidence from Stage 3.4;
- has no operational influence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STAGE = "BROOKS_TRAILING_ACTIVE_SURVIVAL_AUDIT_V1"


def _safety() -> dict[str, Any]:
    return {
        "research_only": True,
        "observational_only": True,
        "performance_validated": False,
        "dynamic_management_validated": False,
        "performance_claim_allowed": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "oos_execution_allowed": False,
    }


def _identity(session: Any, episode_id: Any) -> str:
    return f"{str(session)}::{str(episode_id)}"


def _lifecycle_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    sessions = payload.get("sessions")
    if isinstance(sessions, list):
        for session_index, session in enumerate(sessions):
            if not isinstance(session, dict):
                continue

            source = str(
                session.get("source")
                or session.get("session")
                or session.get("session_id")
                or f"SESSION_{session_index:06d}"
            )

            episodes = session.get("episodes")
            if not isinstance(episodes, list):
                continue

            for episode in episodes:
                if not isinstance(episode, dict):
                    continue
                records.append(
                    {
                        "session": source,
                        "episode": episode,
                    }
                )

        return records

    episodes = payload.get("episodes")
    if isinstance(episodes, list):
        for index, episode in enumerate(episodes):
            if not isinstance(episode, dict):
                continue
            source = str(
                episode.get("session")
                or episode.get("source_session")
                or f"UNKNOWN_SESSION_{index:06d}"
            )
            records.append({"session": source, "episode": episode})

    return records


def _stage34_index(items: Any) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    if not isinstance(items, list):
        return index

    for item in items:
        if not isinstance(item, dict):
            continue

        session = item.get("session")
        episode_id = item.get("episode_id")

        if session is None or episode_id is None:
            continue

        key = _identity(session, episode_id)

        if key in index:
            raise ValueError(f"duplicate Stage 3.4 episode identity: {key}")

        index[key] = item

    return index


def _outcome(item: dict[str, Any], arm: str) -> dict[str, Any]:
    value = item.get(arm)
    return value if isinstance(value, dict) else {}


def audit_payload(
    lifecycle_payload: dict[str, Any],
    stage34_payload: dict[str, Any],
) -> dict[str, Any]:
    lifecycle_records = _lifecycle_records(lifecycle_payload)

    independent = _stage34_index(stage34_payload.get("independent_episodes"))
    rejected = _stage34_index(stage34_payload.get("rejected_episodes"))

    overlap = set(independent).intersection(rejected)
    if overlap:
        raise ValueError(
            "Stage 3.4 identity present in both independent and rejected cohorts: "
            + sorted(overlap)[0]
        )

    active: list[dict[str, Any]] = []

    for record in lifecycle_records:
        episode = record["episode"]
        revision_count = episode.get("stop_revision_count", 0)

        try:
            revision_count = int(revision_count)
        except (TypeError, ValueError):
            revision_count = 0

        if revision_count <= 0:
            continue

        episode_id = episode.get("episode_id")
        if episode_id is None:
            continue

        session = record["session"]
        key = _identity(session, episode_id)

        active.append(
            {
                "identity": key,
                "session": session,
                "episode_id": str(episode_id),
                "direction": episode.get("direction"),
                "entry_event_candle_id": episode.get("entry_event_candle_id"),
                "stop_revision_count": revision_count,
                "initial_stop": episode.get("initial_stop"),
                "final_lifecycle_stop": episode.get("current_stop"),
            }
        )

    surviving: list[dict[str, Any]] = []
    rejected_active: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    both_arms_exited = 0
    both_arms_exit_r_observed = 0
    different_exit_r = 0
    identical_exit_r = 0
    status_difference_count = 0

    for active_episode in active:
        key = active_episode["identity"]

        if key in independent:
            item = independent[key]
            baseline = _outcome(item, "baseline")
            trailing = _outcome(item, "trailing")

            baseline_status = baseline.get("status")
            trailing_status = trailing.get("status")
            baseline_exit_r = baseline.get("exit_r")
            trailing_exit_r = trailing.get("exit_r")

            if baseline_status != trailing_status:
                status_difference_count += 1

            if baseline_status == "EXITED" and trailing_status == "EXITED":
                both_arms_exited += 1

                if baseline_exit_r is not None and trailing_exit_r is not None:
                    both_arms_exit_r_observed += 1

                    if baseline_exit_r == trailing_exit_r:
                        identical_exit_r += 1
                    else:
                        different_exit_r += 1

            surviving.append(
                {
                    **active_episode,
                    "stage_3_4_disposition": "INDEPENDENT",
                    "baseline": baseline,
                    "trailing": trailing,
                    "final_hypothetical_trailing_stop": item.get(
                        "final_hypothetical_trailing_stop"
                    ),
                }
            )

        elif key in rejected:
            item = rejected[key]
            rejected_active.append(
                {
                    **active_episode,
                    "stage_3_4_disposition": "REJECTED",
                    "rejection_reason": item.get("reason"),
                }
            )

        else:
            unresolved.append(
                {
                    **active_episode,
                    "stage_3_4_disposition": "NOT_FOUND",
                    "reason": "ACTIVE_LIFECYCLE_EPISODE_NOT_FOUND_IN_STAGE_3_4",
                }
            )

    stop_advance_observations = sum(
        item["stop_revision_count"] for item in active
    )

    return {
        "stage": STAGE,
        "status": "TRAILING_ACTIVE_SURVIVAL_AUDIT_COMPLETED",
        "lifecycle_episode_count": len(lifecycle_records),
        "trailing_active_episode_count": len(active),
        "stop_advance_observation_count": stop_advance_observations,
        "stage_3_4_independent_episode_count": len(independent),
        "stage_3_4_rejected_episode_count": len(rejected),
        "trailing_active_survived_stage_3_4_count": len(surviving),
        "trailing_active_rejected_stage_3_4_count": len(rejected_active),
        "trailing_active_unresolved_count": len(unresolved),
        "surviving_both_arms_exited_count": both_arms_exited,
        "surviving_both_arms_exit_r_observed_count": both_arms_exit_r_observed,
        "surviving_identical_exit_r_count": identical_exit_r,
        "surviving_different_exit_r_count": different_exit_r,
        "surviving_status_difference_count": status_difference_count,
        "surviving_episodes": surviving,
        "rejected_active_episodes": rejected_active,
        "unresolved_active_episodes": unresolved,
        **_safety(),
    }


def audit(lifecycle_path, stage34_path) -> dict[str, Any]:
    lifecycle_path = Path(lifecycle_path)
    stage34_path = Path(stage34_path)

    lifecycle_payload = json.loads(
        lifecycle_path.read_text(encoding="utf-8-sig")
    )
    stage34_payload = json.loads(
        stage34_path.read_text(encoding="utf-8-sig")
    )

    report = audit_payload(lifecycle_payload, stage34_payload)
    report["lifecycle_source_path"] = str(lifecycle_path)
    report["stage_3_4_source_path"] = str(stage34_path)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Brooks trailing-active Stage 3.4 survival audit."
    )
    parser.add_argument("lifecycle_json")
    parser.add_argument("stage_3_4_json")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = audit(args.lifecycle_json, args.stage_3_4_json)

    text = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(output)
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
