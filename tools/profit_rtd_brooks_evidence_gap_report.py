"""Resume lacunas observacionais da Brooks Research Evidence Suite.

Opera somente sobre um relatorio offline ja produzido. Nao coleta mercado,
nao escolhe candidato e nunca libera freeze, OOS ou influencia operacional.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


VERSION = "BROOKS_EVIDENCE_GAP_REPORT_V1"


def _safety():
    return {
        "research_only": True,
        "observational_only": True,
        "hypothesis_freeze_allowed": False,
        "oos_collection_allowed": False,
        "promotion_allowed": False,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
    }


def _direct_summary(payload):
    sessions = payload.get("sessions") or []
    reasons = Counter()
    observed_breakout_phases = set()
    for session in sessions:
        for item in session.get("incomplete") or []:
            reasons.update(item.get("reasons") or [])
        coverage = session.get("producer_phase_coverage") or {}
        observed_breakout_phases.update(coverage.get("observed_breakout_phases") or [])
    return {
        "eligible_sessions": int(payload.get("eligible_sessions") or len(sessions)),
        "exact_candles": sum(int(x.get("exact_candles") or 0) for x in sessions),
        "candidate_sequences": sum(int(x.get("incomplete_candidates") or 0) for x in sessions),
        "complete_sequences": int(payload.get("complete_sequences") or 0),
        "matched_sequences": 0,
        "incomplete_reason_counts": dict(sorted(reasons.items())),
        "observed_breakout_phases": sorted(observed_breakout_phases),
    }


def _adapted_summary(payload):
    sessions = payload.get("accepted_sessions") or []
    sequence_count = 0
    matched = 0
    reasons = Counter()
    for session in sessions:
        audit = session.get("audit") or {}
        sequence_count += int(audit.get("sequence_count") or 0)
        matched += int(audit.get("matched_sequence_count") or 0)
        reasons.update(
            item.get("reason")
            for item in (audit.get("sequences") or [])
            if item.get("reason")
        )
    return {
        "eligible_sessions": int(payload.get("accepted_session_count") or len(sessions)),
        "exact_candles": None,
        "candidate_sequences": sequence_count,
        "complete_sequences": sequence_count,
        "matched_sequences": matched,
        "incomplete_reason_counts": dict(sorted(reasons.items())),
        "observed_breakout_phases": [],
    }


def build_report(suite):
    if suite.get("suite") != "BROOKS_RESEARCH_EVIDENCE_SUITE_V1":
        raise ValueError("unsupported evidence suite")
    if suite.get("mode") != "SELECTION":
        raise ValueError("evidence gap report requires SELECTION mode")

    families = {}
    for name, payload in sorted((suite.get("setups") or {}).items()):
        if payload.get("status") == "CLASSIFIER_ONLY_NO_EXACT_AUDITOR":
            summary = {
                "eligible_sessions": int(payload.get("eligible_sessions") or 0),
                "exact_candles": None,
                "candidate_sequences": None,
                "complete_sequences": None,
                "matched_sequences": None,
                "incomplete_reason_counts": {},
                "observed_breakout_phases": [],
                "gap": "EXACT_CANDLE_AUDITOR_NOT_AVAILABLE",
            }
        elif "sessions" in payload:
            summary = _direct_summary(payload)
            summary["gap"] = (
                "NO_COMPLETE_SEQUENCE" if summary["complete_sequences"] == 0
                else "NO_MATCHED_SEQUENCE" if summary["matched_sequences"] == 0
                else "OBSERVATIONAL_MATCHES_AVAILABLE"
            )
        else:
            summary = _adapted_summary(payload)
            summary["gap"] = (
                "NO_CANDIDATE_SEQUENCE" if summary["candidate_sequences"] == 0
                else "NO_MATCHED_SEQUENCE" if summary["matched_sequences"] == 0
                else "OBSERVATIONAL_MATCHES_AVAILABLE"
            )
        families[name] = summary

    gaps = sorted({item["gap"] for item in families.values()})
    return {
        "report": VERSION,
        "source_suite": suite.get("suite"),
        "mode": "SELECTION",
        "eligible_sessions": int(suite.get("eligible_sessions") or 0),
        "rejected_sessions": len(suite.get("rejected_sessions") or []),
        "families": families,
        "evidence_gaps": gaps,
        "verdict": "MORE_INDEPENDENT_SELECTION_EVIDENCE_REQUIRED",
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Resume lacunas da Evidence Suite Brooks.")
    parser.add_argument("suite")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    payload = json.loads(Path(args.suite).read_text(encoding="utf-8"))
    report = build_report(payload)
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
