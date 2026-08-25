"""CLI offline de avaliação final do ensaio Trading Economics (RC27)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from economic_context import TradingEconomicsTrialEvaluator


MAX_EVIDENCE_BYTES = 100_000
SESSION_IDS = ("D1", "D2", "D3", "D4", "D5")
REQUIRED_KEYS = {
    "expected_event_counts",
    "maximum_clock_errors_seconds",
}


def build_parser():
    parser = argparse.ArgumentParser(
        description="Avaliação offline do ensaio Trading Economics D1-D5"
    )
    parser.add_argument("--directory", required=True)
    parser.add_argument("--evidence-file", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def run(argv=None):
    args = build_parser().parse_args(argv)
    try:
        evidence = _load_evidence(args.evidence_file)
        result = TradingEconomicsTrialEvaluator().evaluate(
            args.directory,
            expected_event_counts=evidence["expected_event_counts"],
            maximum_clock_errors_seconds=evidence[
                "maximum_clock_errors_seconds"
            ],
        )
    except Exception:
        _emit(
            {
                "status": "BLOCKED",
                "reasons": ["INVALID_OR_INCOMPLETE_EVIDENCE"],
                "eligible_for_manual_review": False,
                "automatic_promotion_allowed": False,
                "observational_only": True,
            },
            args.as_json,
        )
        return 2

    report = result.report
    evaluation = report.evidence
    _emit(
        {
            "status": result.status,
            "manifest_checksum_sha256": result.manifest_checksum_sha256,
            "completed_sessions": evaluation.completed_sessions,
            "coverage_ratio": evaluation.coverage_ratio,
            "rejection_ratio": evaluation.rejection_ratio,
            "duplicate_ratio": evaluation.duplicate_ratio,
            "maximum_clock_error_seconds": (
                evaluation.maximum_clock_error_seconds
            ),
            "critical_events_checked": list(
                evaluation.critical_events_checked
            ),
            "reasons": list(result.reasons),
            "eligible_for_manual_review": (
                result.eligible_for_manual_review
            ),
            "automatic_promotion_allowed": False,
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        },
        args.as_json,
    )
    return 0 if result.eligible_for_manual_review else 2


def _load_evidence(path):
    source = Path(path)
    if not source.is_file():
        raise ValueError("Arquivo de evidência ausente.")
    if source.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("Arquivo de evidência excede o limite.")

    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or set(payload) != REQUIRED_KEYS:
        raise ValueError("Esquema de evidência incompatível.")

    expected = _session_values(
        payload["expected_event_counts"],
        minimum=1,
    )
    clocks = _session_values(
        payload["maximum_clock_errors_seconds"],
        minimum=0,
    )
    return {
        "expected_event_counts": expected,
        "maximum_clock_errors_seconds": clocks,
    }


def _session_values(values, *, minimum):
    if not isinstance(values, dict) or set(values) != set(SESSION_IDS):
        raise ValueError("Evidência deve conter exatamente D1-D5.")
    normalized = {}
    for session_id, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("Valores de evidência devem ser inteiros.")
        if value < minimum:
            raise ValueError("Valor de evidência abaixo do mínimo.")
        normalized[session_id] = value
    return normalized


def _emit(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print("=== ECONOMIC CALENDAR TRIAL EVALUATION ===")
    for key, value in payload.items():
        print(f"{key.upper()}: {value}")


def main():
    raise SystemExit(run())


if __name__ == "__main__":
    main()
