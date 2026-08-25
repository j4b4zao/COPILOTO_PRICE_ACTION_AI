"""CLI segura para pré-voo e captura controlada do calendário (RC20)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from economic_context import (
    TradingEconomicsCapturePreflight,
    TradingEconomicsControlledPipeline,
    TradingEconomicsSessionCoordinator,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Pré-voo/captura controlada da Trading Economics"
    )
    parser.add_argument("--destination", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument(
        "--capture-enabled",
        action="store_true",
        help="Abre a segunda trava sem executar a captura.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Executa após pré-voo aprovado; ausente = somente pré-voo.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def run(argv=None, *, environment=None, transport=None):
    args = build_parser().parse_args(argv)

    try:
        pipeline = TradingEconomicsControlledPipeline.from_environment(
            environment,
            capture_enabled=args.capture_enabled,
            transport=transport,
        )
    except (TypeError, ValueError):
        _emit(
            {
                "status": "BLOCKED",
                "reasons": ["INVALID_CONFIGURATION"],
                "observational_only": True,
            },
            args.as_json,
        )
        return 2

    preflight = TradingEconomicsCapturePreflight()
    report = preflight.evaluate(
        pipeline,
        args.destination,
        session_id=args.session_id,
    )

    if not args.execute:
        _emit(_preflight_payload(report), args.as_json)
        return 0 if report.approved else 2

    if not report.approved:
        _emit(_preflight_payload(report), args.as_json)
        return 2

    coordinator = TradingEconomicsSessionCoordinator(
        pipeline,
        preflight=preflight,
    )
    try:
        result = coordinator.execute(
            args.destination,
            session_id=args.session_id,
            captured_at=datetime.now(timezone.utc),
        )
    except Exception:
        _emit(
            {
                "status": "CAPTURE_FAILED",
                "package_name": report.package_name,
                "reasons": [],
                "observational_only": True,
            },
            args.as_json,
        )
        return 3

    _emit(
        {
            "status": result.status,
            "package_name": result.capture.package_path,
            "received_count": result.capture.received_count,
            "mapped_count": result.capture.mapped_count,
            "checksum_sha256": result.capture.checksum_sha256,
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        },
        args.as_json,
    )
    return 0


def _preflight_payload(report):
    return {
        "status": report.status,
        "package_name": report.package_name,
        "reasons": list(report.reasons),
        "config_ready": report.config_ready,
        "capture_enabled": report.capture_enabled,
        "destination_valid": report.destination_valid,
        "destination_available": report.destination_available,
        "limits_valid": report.limits_valid,
        "observational_only": True,
        "score_influence_allowed": False,
        "order_execution_allowed": False,
    }


def _emit(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print("=== ECONOMIC CALENDAR CONTROLLED CAPTURE ===")
    for key, value in payload.items():
        print(f"{key.upper()}: {value}")


def main():
    raise SystemExit(run())


if __name__ == "__main__":
    main()
