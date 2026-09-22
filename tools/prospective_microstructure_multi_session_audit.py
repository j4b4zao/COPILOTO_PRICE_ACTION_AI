"""Auditoria fail-closed de sessoes prospectivas de microestrutura.

Somente sessoes tecnicamente validas, direcionais, independentes e passivas
chegam ao comparador multi-sessao existente. O resultado permanece
observacional e nunca autoriza promocao ou influencia operacional.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from pathlib import Path

from analysis.replay.microstructure_confluence_multi_session import (
    MicrostructureConfluenceMultiSessionComparator,
)
from analysis.replay.microstructure_confluence_session_report import (
    MicrostructureConfluenceSessionReport,
)
from tools.profit_rtd_microstructure_prospective_session import STAGE as SOURCE_STAGE


VERSION = "RC1-PROSPECTIVE-MICROSTRUCTURE-MULTI-SESSION-AUDIT"
_FALSE_FLAGS = (
    "predictive_claim_allowed",
    "score_influence_allowed",
    "risk_influence_allowed",
    "decision_influence_allowed",
    "alert_influence_allowed",
    "order_execution_allowed",
    "promotion_allowed",
)


@dataclass(slots=True, frozen=True)
class RejectedSession:
    path: str
    sha256: str | None
    reasons: tuple[str, ...]


def _safety() -> dict:
    return {
        "research_only": True,
        "observational_only": True,
        **{name: False for name in _FALSE_FLAGS},
    }


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate(payload: dict) -> tuple[list[str], dict | None]:
    reasons: list[str] = []
    evidence = payload.get("prospective_microstructure")
    if not isinstance(evidence, dict):
        return ["PROSPECTIVE_EVIDENCE_MISSING"], None

    if payload.get("status") != "COMPLETED":
        reasons.append("SESSION_NOT_COMPLETED")
    if payload.get("data_ready") is not True:
        reasons.append("DATA_NOT_READY")
    if payload.get("trade_context_ready_at_start") is not True:
        reasons.append("TRADE_CONTEXT_NOT_READY_AT_START")
    if evidence.get("stage") != SOURCE_STAGE:
        reasons.append("UNEXPECTED_EVIDENCE_STAGE")

    source_samples = evidence.get("source_analyzable_samples")
    captured_samples = evidence.get("captured_samples")
    samples = evidence.get("samples")
    if not isinstance(samples, list):
        reasons.append("SAMPLES_MISSING")
    else:
        if captured_samples != len(samples):
            reasons.append("CAPTURED_SAMPLE_COUNT_MISMATCH")
        if source_samples != len(samples):
            reasons.append("SOURCE_SAMPLE_COUNT_MISMATCH")
    if evidence.get("sample_count_matches_source") is not True:
        reasons.append("SOURCE_MATCH_NOT_CONFIRMED")

    for scope_name, scope in (("SESSION", payload), ("EVIDENCE", evidence)):
        if scope.get("observational_only") is not True:
            reasons.append(f"{scope_name}_NOT_OBSERVATIONAL")
        for flag in _FALSE_FLAGS:
            if scope.get(flag) is not False:
                reasons.append(f"{scope_name}_{flag.upper()}_NOT_FALSE")

    report = evidence.get("report")
    if not isinstance(report, dict):
        reasons.append("SESSION_REPORT_MISSING")
        return reasons, None
    if report.get("samples") != captured_samples:
        reasons.append("REPORT_SAMPLE_COUNT_MISMATCH")
    if report.get("passive_only") is not True:
        reasons.append("SESSION_REPORT_NOT_PASSIVE")

    required = {field.name for field in fields(MicrostructureConfluenceSessionReport)}
    missing = sorted(required.difference(report))
    if missing:
        reasons.append("SESSION_REPORT_FIELDS_MISSING:" + ",".join(missing))
    return reasons, report


def _source_window(payload: dict) -> tuple[tuple[datetime, datetime] | None, str | None]:
    samples = payload.get("samples")
    if not isinstance(samples, list) or not samples:
        return None, "SOURCE_TIMESTAMPS_MISSING"
    try:
        timestamps = [datetime.fromisoformat(item["timestamp"]) for item in samples]
        if any(current <= previous for previous, current in zip(timestamps, timestamps[1:])):
            return None, "SOURCE_TIMESTAMPS_NOT_STRICTLY_INCREASING"
    except (KeyError, TypeError, ValueError):
        return None, "SOURCE_TIMESTAMPS_INVALID"
    return (timestamps[0], timestamps[-1]), None


def audit_paths(paths) -> dict:
    paths = list(paths)
    comparator = MicrostructureConfluenceMultiSessionComparator()
    accepted_reports = []
    accepted_sessions = []
    rejected_sessions: list[RejectedSession] = []
    seen_paths: set[str] = set()
    seen_hashes: set[str] = set()
    accepted_windows: list[tuple[datetime, datetime, str]] = []

    for value in paths:
        path = Path(value).resolve()
        digest = None
        normalized = str(path).casefold()
        if normalized in seen_paths:
            rejected_sessions.append(RejectedSession(str(path), None, ("DUPLICATE_PATH",)))
            continue
        seen_paths.add(normalized)
        try:
            raw = path.read_bytes()
            digest = _sha256(raw)
            if digest in seen_hashes:
                rejected_sessions.append(RejectedSession(str(path), digest, ("DUPLICATE_SHA256",)))
                continue
            seen_hashes.add(digest)
            payload = json.loads(raw.decode("utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("top-level JSON must be an object")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            rejected_sessions.append(
                RejectedSession(str(path), digest, (f"UNREADABLE_SESSION:{type(exc).__name__}",))
            )
            continue

        reasons, report = _validate(payload)
        window, timestamp_reason = _source_window(payload)
        if timestamp_reason:
            reasons.append(timestamp_reason)
        elif window is not None:
            try:
                overlap = next(
                    (accepted_path for first, last, accepted_path in accepted_windows
                     if window[0] <= last and first <= window[1]),
                    None,
                )
            except TypeError:
                reasons.append("SOURCE_TIMESTAMPS_INVALID")
            else:
                if overlap is not None:
                    reasons.append("TEMPORAL_OVERLAP:" + overlap)
        if reasons:
            rejected_sessions.append(RejectedSession(str(path), digest, tuple(reasons)))
            continue

        allowed_fields = {field.name for field in fields(MicrostructureConfluenceSessionReport)}
        accepted_reports.append(
            MicrostructureConfluenceSessionReport(**{key: report[key] for key in allowed_fields})
        )
        accepted_sessions.append({"path": str(path), "sha256": digest})
        accepted_windows.append((window[0], window[1], str(path)))

    aggregate = comparator.compare(accepted_reports).to_dict()
    eligible = len(accepted_reports)
    total_samples = aggregate["samples"]
    return {
        "version": VERSION,
        "status": "DESCRIPTIVE_ONLY",
        "input_sessions": len(paths),
        "eligible_sessions": eligible,
        "rejected_sessions": len(rejected_sessions),
        "accepted": accepted_sessions,
        "rejected": [asdict(item) for item in rejected_sessions],
        "aggregate": aggregate,
        "evidence_gap": {
            "additional_independent_sessions_lower_bound": max(0, comparator.MIN_SESSIONS - eligible),
            "additional_samples_lower_bound": max(0, comparator.MIN_SAMPLES - total_samples),
        },
        **_safety(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    report = audit_paths(args.paths)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
