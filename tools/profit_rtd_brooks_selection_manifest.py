"""Manifesto research-only para sessoes Brooks de selecao.

Padroniza o inventario das novas sessoes reais enriquecidas sem executar
qualquer estrategia e sem promover hipoteses. O manifesto e deliberadamente
separado de OOS: sessoes registradas aqui pertencem a SELECTION.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

SUITE = "BROOKS_RESEARCH_EVIDENCE_SUITE_V1"
MODE = "SELECTION"
REQUIRED_CAPTURE_FLAGS = (
    "brooks_first_pullback_capture",
    "brooks_major_reversal_context_capture",
    "brooks_wedge_three_pushes_capture",
    "brooks_trading_range_capture",
)


def _safety():
    return {
        "research_only": True,
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "hypothesis_freeze_allowed": False,
        "promotion_allowed": False,
    }


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_ts(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _sample_ts(row):
    evidence = row.get("candle_evidence") or {}
    return _parse_ts(evidence.get("timestamp") or row.get("timestamp"))


def inspect_session(path):
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    samples = payload.get("samples") or []
    timestamps = [ts for ts in (_sample_ts(row) for row in samples) if ts is not None]
    missing_flags = [flag for flag in REQUIRED_CAPTURE_FLAGS if payload.get(flag) is not True]
    safety_violations = []
    for key in (
        "brooks_predictive_claim_allowed",
        "brooks_score_influence_allowed",
        "brooks_risk_influence_allowed",
        "brooks_decision_influence_allowed",
        "brooks_alert_influence_allowed",
        "brooks_order_execution_allowed",
    ):
        if payload.get(key) is not False:
            safety_violations.append(key)

    reasons = []
    if payload.get("data_ready") is not True:
        reasons.append("DATA_READY_REQUIRED")
    if not samples:
        reasons.append("SAMPLES_REQUIRED")
    if not timestamps:
        reasons.append("SESSION_INTERVAL_UNAVAILABLE")
    if missing_flags:
        reasons.append("BROOKS_CAPTURE_FLAGS_REQUIRED")
    if safety_violations:
        reasons.append("BROOKS_SAFETY_CONTRACT_VIOLATION")

    return {
        "path": str(source),
        "session": source.name,
        "sha256": _sha256(source),
        "eligible": not reasons,
        "reasons": reasons,
        "start": min(timestamps).isoformat() if timestamps else None,
        "end": max(timestamps).isoformat() if timestamps else None,
        "samples": len(samples),
        "analyzable_samples": payload.get("analyzable_samples"),
        "missing_capture_flags": missing_flags,
        "safety_violations": safety_violations,
    }


def build_manifest(paths):
    inspected = [inspect_session(path) for path in paths]
    inspected.sort(key=lambda item: (item.get("start") is None, item.get("start") or "", item["session"]))

    accepted, rejected, intervals = [], [], []
    for item in inspected:
        if not item["eligible"]:
            rejected.append(item)
            continue
        start = _parse_ts(item["start"])
        end = _parse_ts(item["end"])
        overlap = next((name for name, old_start, old_end in intervals if start <= old_end and end >= old_start), None)
        if overlap:
            rejected.append({**item, "eligible": False, "reasons": [*item["reasons"], "TEMPORAL_OVERLAP"], "overlaps_with": overlap})
            continue
        accepted.append(item)
        intervals.append((item["session"], start, end))

    cutoff = max((_parse_ts(item["end"]) for item in accepted), default=None)
    return {
        "manifest": "BROOKS_SELECTION_SESSION_MANIFEST_V1",
        "evidence_suite": SUITE,
        "mode": MODE,
        "input_sessions": len(inspected),
        "eligible_sessions": len(accepted),
        "rejected_sessions": len(rejected),
        "sessions": accepted,
        "rejected": rejected,
        "selection_cutoff": cutoff.isoformat() if cutoff else None,
        "oos_allowed_from_manifest": False,
        **_safety(),
    }
