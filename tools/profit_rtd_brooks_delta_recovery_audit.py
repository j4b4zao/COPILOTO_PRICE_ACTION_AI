"""
tools/profit_rtd_brooks_delta_recovery_audit.py

Auditoria observacional de episódios de indisponibilidade e recuperação
do Delta em sessões Brooks/RC54.3.2 já persistidas.

IMPORTANTE:
- Research-only.
- Não altera o arquivo de sessão original.
- Não altera data_ready do RC54.3.2.
- Não promove sessão rejeitada para válida.
- Não influencia Score, Risk, Decision, Alert ou execução.
- Não define tolerância operacional.
- Apenas descreve episódios observados no Delta persistido.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


STAGE = "BROOKS_DELTA_RECOVERY_AUDIT_V1"

READY_STATUSES = {
    "READY",
    "VALID",
    "LOW_ACTIVITY",
}

INITIALIZING_STATUS = "INITIALIZING"

FAILURE_STATUSES = {
    "NO_DATA",
    "DEGRADED",
}


def _status(sample: dict[str, Any]) -> str:
    return str(sample.get("delta_status", "") or "").strip().upper()


def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _duration_seconds(
    start_timestamp: Any,
    end_timestamp: Any,
) -> float | None:
    start = _parse_timestamp(start_timestamp)
    end = _parse_timestamp(end_timestamp)

    if start is None or end is None:
        return None

    return round((end - start).total_seconds(), 3)


def _sample_snapshot(sample: dict[str, Any]) -> dict[str, Any]:
    return {
        "cycle": sample.get("cycle"),
        "timestamp": sample.get("timestamp"),
        "delta_status": _status(sample),
        "recent_delta": sample.get("recent_delta"),
        "last_price": sample.get("last_price"),
        "data_ready": sample.get("data_ready"),
        "context_ready": sample.get("context_ready"),
        "trade_context_ready": sample.get("trade_context_ready"),
    }


def _is_failure_status(status: str) -> bool:
    return status in FAILURE_STATUSES


def _find_previous_ready(
    samples: list[dict[str, Any]],
    start_index: int,
) -> dict[str, Any] | None:
    for index in range(start_index - 1, -1, -1):
        if _status(samples[index]) in READY_STATUSES:
            return samples[index]

    return None


def _build_episode(
    samples: list[dict[str, Any]],
    failure_index: int,
) -> tuple[dict[str, Any], int]:
    failure_sample = samples[failure_index]
    failure_status = _status(failure_sample)

    previous_ready = _find_previous_ready(
        samples,
        failure_index,
    )

    initializing_samples: list[dict[str, Any]] = []
    additional_failure_samples: list[dict[str, Any]] = []
    recovery_sample: dict[str, Any] | None = None

    index = failure_index + 1

    while index < len(samples):
        sample = samples[index]
        status = _status(sample)

        if status in READY_STATUSES:
            recovery_sample = sample
            break

        if status == INITIALIZING_STATUS:
            initializing_samples.append(sample)
        else:
            additional_failure_samples.append(sample)

        index += 1

    recovered = recovery_sample is not None

    if recovered:
        classification = "TRANSIENT_RECOVERED"
        episode_end = recovery_sample
    else:
        classification = "UNRECOVERED_AT_SESSION_END"

        episode_end = samples[-1]

    failure_to_recovery_seconds = None

    if recovery_sample is not None:
        failure_to_recovery_seconds = _duration_seconds(
            failure_sample.get("timestamp"),
            recovery_sample.get("timestamp"),
        )

    previous_ready_to_recovery_seconds = None

    if previous_ready is not None and recovery_sample is not None:
        previous_ready_to_recovery_seconds = _duration_seconds(
            previous_ready.get("timestamp"),
            recovery_sample.get("timestamp"),
        )

    last_index = index if recovery_sample is not None else len(samples) - 1
    status_sequence = [
        _status(sample)
        for sample in samples[failure_index:last_index + 1]
    ]

    episode = {
        "classification": classification,
        "recovered": recovered,
        "failure_status": failure_status,
        "previous_ready": (
            _sample_snapshot(previous_ready)
            if previous_ready is not None
            else None
        ),
        "failure": _sample_snapshot(failure_sample),
        "initializing_sample_count": len(
            initializing_samples
        ),
        "additional_failure_sample_count": len(
            additional_failure_samples
        ),
        "recovery": (
            _sample_snapshot(recovery_sample)
            if recovery_sample is not None
            else None
        ),
        "episode_end": _sample_snapshot(episode_end),
        "failure_to_recovery_seconds": (
            failure_to_recovery_seconds
        ),
        "previous_ready_to_recovery_seconds": (
            previous_ready_to_recovery_seconds
        ),
        "status_sequence": status_sequence,
        "observational_only": True,
        "session_validity_changed": False,
    }

    if recovery_sample is not None:
        next_index = index + 1
    else:
        next_index = len(samples)

    return episode, next_index


def audit_session(
    payload: dict[str, Any],
    *,
    source_path: str | None = None,
) -> dict[str, Any]:
    samples = list(payload.get("samples", []) or [])

    status_counts = Counter(
        _status(sample)
        for sample in samples
    )

    failure_indices = [
        index
        for index, sample in enumerate(samples)
        if _is_failure_status(_status(sample))
    ]

    known_statuses = (
        READY_STATUSES
        | {INITIALIZING_STATUS}
        | FAILURE_STATUSES
    )

    unknown_status_counts = Counter(
        _status(sample)
        for sample in samples
        if _status(sample) not in known_statuses
    )

    episodes: list[dict[str, Any]] = []

    index = 0

    while index < len(samples):
        status = _status(samples[index])

        if not _is_failure_status(status):
            index += 1
            continue

        episode, next_index = _build_episode(
            samples,
            index,
        )

        episodes.append(episode)
        index = max(next_index, index + 1)

    recovered_episode_count = sum(
        episode["recovered"]
        for episode in episodes
    )

    unrecovered_episode_count = (
        len(episodes) - recovered_episode_count
    )

    transient_recovered_count = sum(
        episode["classification"]
        == "TRANSIENT_RECOVERED"
        for episode in episodes
    )

    unrecovered_at_end_count = sum(
        episode["classification"]
        == "UNRECOVERED_AT_SESSION_END"
        for episode in episodes
    )

    return {
        "stage": STAGE,
        "status": "COMPLETED",
        "source_path": source_path,
        "symbol": payload.get("symbol"),
        "source_session_status": payload.get("status"),
        "source_session_data_ready": payload.get(
            "data_ready"
        ),
        "source_session_reasons": list(
            payload.get("reasons", []) or []
        ),
        "sample_count": len(samples),
        "delta_status_counts": dict(
            sorted(status_counts.items())
        ),
        "failure_sample_count": len(
            failure_indices
        ),
        "unknown_status_sample_count": sum(
            unknown_status_counts.values()
        ),
        "unknown_status_counts": dict(
            sorted(unknown_status_counts.items())
        ),
        "episode_count": len(episodes),
        "recovered_episode_count": (
            recovered_episode_count
        ),
        "unrecovered_episode_count": (
            unrecovered_episode_count
        ),
        "classification_counts": {
            "TRANSIENT_RECOVERED": (
                transient_recovered_count
            ),
            "UNRECOVERED_AT_SESSION_END": (
                unrecovered_at_end_count
            ),
        },
        "episodes": episodes,
        "research_only": True,
        "observational_only": True,
        "source_session_modified": False,
        "source_session_validity_changed": False,
        "selection_eligibility_changed": False,
        "oos_eligibility_changed": False,
        "predictive_claim_allowed": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def audit_file(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    source = Path(input_path)

    payload = json.loads(
        source.read_text(encoding="utf-8")
    )

    report = audit_session(
        payload,
        source_path=str(source),
    )

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        report["output_path"] = str(target)

    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Auditoria research-only de recuperação "
            "do Delta em sessão Brooks/RC54.3.2."
        )
    )

    parser.add_argument(
        "input_json",
        help="Sessão JSON persistida.",
    )

    parser.add_argument(
        "--output",
        help="Caminho opcional do relatório JSON.",
    )

    args = parser.parse_args(argv)

    report = audit_file(
        args.input_json,
        output_path=args.output,
    )

    print("status=", report["status"])
    print("stage=", report["stage"])
    print(
        "source_session_data_ready=",
        report["source_session_data_ready"],
    )
    print(
        "sample_count=",
        report["sample_count"],
    )
    print(
        "delta_status_counts=",
        json.dumps(
            report["delta_status_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )
    print(
        "failure_sample_count=",
        report["failure_sample_count"],
    )
    print(
        "episode_count=",
        report["episode_count"],
    )
    print(
        "recovered_episode_count=",
        report["recovered_episode_count"],
    )
    print(
        "unrecovered_episode_count=",
        report["unrecovered_episode_count"],
    )
    print(
        "classification_counts=",
        json.dumps(
            report["classification_counts"],
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    for number, episode in enumerate(
        report["episodes"],
        start=1,
    ):
        print()
        print(f"EPISODE_{number}")
        print(
            "classification=",
            episode["classification"],
        )
        print(
            "failure_cycle=",
            episode["failure"]["cycle"],
        )
        print(
            "failure_status=",
            episode["failure_status"],
        )
        print(
            "initializing_sample_count=",
            episode["initializing_sample_count"],
        )
        print(
            "additional_failure_sample_count=",
            episode[
                "additional_failure_sample_count"
            ],
        )
        print(
            "recovery_cycle=",
            (
                episode["recovery"]["cycle"]
                if episode["recovery"]
                else None
            ),
        )
        print(
            "recovery_status=",
            (
                episode["recovery"]["delta_status"]
                if episode["recovery"]
                else None
            ),
        )
        print(
            "failure_to_recovery_seconds=",
            episode[
                "failure_to_recovery_seconds"
            ],
        )

    if report.get("output_path"):
        print(
            "output_path=",
            report["output_path"],
        )

    print("research_only=True")
    print("source_session_validity_changed=False")
    print("selection_eligibility_changed=False")
    print("oos_eligibility_changed=False")
    print("score_influence_allowed=False")
    print("risk_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("alert_influence_allowed=False")
    print("order_execution_allowed=False")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
