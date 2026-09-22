"""Preflight e coleta prospectiva de microestrutura sob um unico lock."""

from __future__ import annotations

import argparse
import json

from tools.profit_rtd_microstructure_prospective_session import run_session
from tools.profit_rtd_rc54_5_3_market_activity_preflight import check_market_activity
from tools.profit_rtd_rc54_5_4_orchestrated_session_runner import (
    RunnerAlreadyActiveError,
    _call_with_output,
    _runner_lock,
)


def _safety():
    return {
        "observational_only": True,
        "predictive_claim_allowed": False,
        "score_influence_allowed": False,
        "risk_influence_allowed": False,
        "decision_influence_allowed": False,
        "alert_influence_allowed": False,
        "order_execution_allowed": False,
        "promotion_allowed": False,
    }


def run_orchestrated_prospective_session(
    symbol,
    *,
    preflight_cycles=90,
    preflight_interval=0.25,
    cycles=600,
    interval=0.25,
    max_warmup_cycles=1800,
    require_trade_context_at_start=True,
    concise_output=True,
    progress_every=50,
    output_dir=None,
    lock_dir=None,
):
    symbol = str(symbol or "").strip().upper()
    try:
        with _runner_lock(symbol, lock_dir=lock_dir):
            preflight = _call_with_output(
                check_market_activity,
                concise_output=concise_output,
                progress_every=progress_every,
                cycles=preflight_cycles,
                interval=preflight_interval,
                min_analyzable=10,
                min_price_changes=2,
                min_candle_growth=1,
            )
            if not preflight["active"]:
                return {
                    "status": "ABORTED_MARKET_ACTIVITY_NOT_READY",
                    "symbol": symbol,
                    "preflight": preflight,
                    "warmup_started": False,
                    "session": None,
                    **_safety(),
                }
            session = _call_with_output(
                lambda **kwargs: run_session(symbol, **kwargs),
                concise_output=concise_output,
                progress_every=progress_every,
                cycles=cycles,
                interval=interval,
                max_warmup_cycles=max_warmup_cycles,
                require_trade_context_at_start=require_trade_context_at_start,
                output_dir=output_dir,
            )
            completed = session.get("status") == "COMPLETED" and session.get("data_ready") is True
            return {
                "status": "SESSION_COMPLETED" if completed else "SESSION_ABORTED_AFTER_PREFLIGHT",
                "symbol": symbol,
                "preflight": preflight,
                "warmup_started": True,
                "session": session,
                **_safety(),
            }
    except RunnerAlreadyActiveError:
        return {
            "status": "ABORTED_RUNNER_ALREADY_ACTIVE",
            "symbol": symbol,
            "preflight": {"active": False, "reasons": ["RC54_RUNNER_ALREADY_ACTIVE"]},
            "warmup_started": False,
            "session": None,
            **_safety(),
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("symbol")
    parser.add_argument("--preflight-cycles", type=int, default=90)
    parser.add_argument("--preflight-interval", type=float, default=0.25)
    parser.add_argument("--cycles", type=int, default=600)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--max-warmup-cycles", type=int, default=1800)
    parser.add_argument("--output-dir")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    result = run_orchestrated_prospective_session(
        args.symbol,
        preflight_cycles=args.preflight_cycles,
        preflight_interval=args.preflight_interval,
        cycles=args.cycles,
        interval=args.interval,
        max_warmup_cycles=args.max_warmup_cycles,
        concise_output=not args.verbose,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "SESSION_COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
