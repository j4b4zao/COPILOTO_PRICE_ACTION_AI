"""CLI do ensaio sequencial Trading Economics D1-D5 (RC24)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from economic_context import (
    TradingEconomicsControlledPipeline,
    TradingEconomicsSessionCoordinator,
    TradingEconomicsTrialCoordinator,
    TradingEconomicsTrialSessionPlanner,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Planejamento/execução controlada do ensaio D1-D5"
    )
    parser.add_argument("--directory", required=True)
    parser.add_argument(
        "--capture-enabled",
        action="store_true",
        help="Abre a segunda trava sem executar por si só.",
    )
    parser.add_argument(
        "--execute-next",
        action="store_true",
        help="Executa somente a próxima sessão válida.",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def run(argv=None, *, environment=None, transport=None):
    args = build_parser().parse_args(argv)
    planner = TradingEconomicsTrialSessionPlanner()
    plan = planner.evaluate(args.directory)

    if not args.execute_next:
        _emit(_plan_payload(plan), args.as_json)
        return 0 if plan.status in {"READY", "COMPLETE"} else 2

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

    coordinator = TradingEconomicsTrialCoordinator(
        TradingEconomicsSessionCoordinator(pipeline),
        planner=planner,
    )
    try:
        result = coordinator.execute_next(
            args.directory,
            captured_at=datetime.now(timezone.utc),
        )
    except PermissionError:
        _emit(
            {
                "status": coordinator.last_diagnostics.get(
                    "status",
                    "BLOCKED",
                ),
                "session_id": coordinator.last_diagnostics.get("session_id"),
                "package_name": coordinator.last_diagnostics.get(
                    "package_name"
                ),
                "completed_sessions": coordinator.last_diagnostics.get(
                    "completed_sessions",
                    plan.completed_sessions,
                ),
                "remaining_sessions": coordinator.last_diagnostics.get(
                    "remaining_sessions",
                    plan.remaining_sessions,
                ),
                "error_status": coordinator.last_diagnostics.get(
                    "error_status"
                ),
                "observational_only": True,
            },
            args.as_json,
        )
        return 2
    except Exception:
        _emit(
            {
                "status": "SESSION_FAILED",
                "session_id": coordinator.last_diagnostics.get("session_id"),
                "package_name": coordinator.last_diagnostics.get(
                    "package_name"
                ),
                "observational_only": True,
            },
            args.as_json,
        )
        return 3

    _emit(
        {
            "status": result.status,
            "session_id": result.session_id,
            "package_name": result.package_name,
            "completed_sessions": result.completed_sessions,
            "remaining_sessions": result.remaining_sessions,
            "next_session_id": result.next_session_id,
            "checksum_sha256": result.checksum_sha256,
            "observational_only": True,
            "score_influence_allowed": False,
            "order_execution_allowed": False,
        },
        args.as_json,
    )
    return 0


def _plan_payload(plan):
    return {
        "status": plan.status,
        "total_sessions": plan.total_sessions,
        "completed_sessions": plan.completed_sessions,
        "remaining_sessions": plan.remaining_sessions,
        "next_session_id": plan.next_session_id,
        "next_package_name": plan.next_package_name,
        "sessions": [
            {
                "session_id": item.session_id,
                "package_name": item.package_name,
                "status": item.status,
            }
            for item in plan.sessions
        ],
        "observational_only": True,
        "score_influence_allowed": False,
        "order_execution_allowed": False,
    }


def _emit(payload, as_json):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    print("=== ECONOMIC CALENDAR FIVE-SESSION TRIAL ===")
    for key, value in payload.items():
        print(f"{key.upper()}: {value}")


def main():
    raise SystemExit(run())


if __name__ == "__main__":
    main()
