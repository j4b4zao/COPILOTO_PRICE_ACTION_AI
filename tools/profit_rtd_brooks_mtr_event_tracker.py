"""Agregador research-only de eventos independentes Brooks MTR.

Consome sessoes JSON brutas e reutiliza o auditor EXACT_CANDLE de
BROOKS_MAJOR_TREND_REVERSAL_V1. O objetivo e acompanhar evidencia independente
por sessao sem promover a hipotese e sem alterar Score, Risk, Decision, Alert
ou execucao.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.profit_rtd_brooks_major_trend_reversal_audit import audit_payload


TRACKER = "BROOKS_MTR_EVENT_TRACKER_V1"


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


def build_report(paths):
    sessions = []
    total_raw_matches = 0
    total_unique_events = 0
    eligible_sessions = 0
    event_sessions = 0

    for raw_path in paths:
        path = Path(raw_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        audit = audit_payload(payload)
        status = audit.get("status")

        session = {
            "session": path.name,
            "status": status,
            "matched_sequence_count": audit.get("matched_sequence_count", 0),
            "unique_matched_event_count": audit.get("unique_matched_event_count", 0),
            "unique_matched_events": audit.get("unique_matched_events", []),
        }

        if status == "AUDIT_COMPLETED":
            eligible_sessions += 1
            raw_matches = int(audit.get("matched_sequence_count", 0) or 0)
            unique_events = int(audit.get("unique_matched_event_count", 0) or 0)
            total_raw_matches += raw_matches
            total_unique_events += unique_events
            if unique_events > 0:
                event_sessions += 1
        else:
            session["reasons"] = audit.get("reasons", [])

        sessions.append(session)

    return {
        "tracker": TRACKER,
        "input_sessions": len(sessions),
        "eligible_sessions": eligible_sessions,
        "sessions_with_unique_events": event_sessions,
        "matched_sequence_count": total_raw_matches,
        "unique_matched_event_count": total_unique_events,
        "sessions": sessions,
        **_safety(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    report = build_report(args.paths)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
