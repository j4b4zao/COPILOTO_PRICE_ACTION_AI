"""CLI RC33 para analisar estabilidade de uma ou mais sessoes shadow RC32."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from market_data.order_flow_shadow_stability import OrderFlowShadowStabilityAnalyzer


def build_parser():
    p = argparse.ArgumentParser(description="Analisa estabilidade de sessoes shadow de Order Flow.")
    p.add_argument("session_json", nargs="+")
    return p


def run(paths: list[str]) -> int:
    sessions = []
    try:
        for raw in paths:
            path = Path(raw).expanduser().resolve()
            sessions.append(json.loads(path.read_text(encoding="utf-8")))
        report = OrderFlowShadowStabilityAnalyzer().evaluate(sessions)
    except Exception as exc:
        print("PROFIT_RTD_ORDER_FLOW_SHADOW_STABILITY=ERROR")
        print(f"reason={type(exc).__name__}:{exc}")
        return 1

    print("PROFIT_RTD_ORDER_FLOW_SHADOW_STABILITY=COMPLETED")
    print(f"sessions={report.sessions}")
    print(f"samples={report.samples}")
    print(f"changed_count={report.changed_count}")
    print(f"changed_rate={report.changed_rate:.6f}")
    print(f"directional_balance_status={report.directional_balance_status}")
    print(f"bullish_bearish_ratio={report.bullish_bearish_ratio}")
    for key, value in report.transitions.items():
        print(f"transition[{key}]={value}")
    for key, stats in report.shadow_runs.items():
        print(f"run[{key}].runs={stats['runs']}")
        print(f"run[{key}].max={stats['max_run']}")
        print(f"run[{key}].avg={stats['avg_run']}")
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    return run(args.session_json)


if __name__ == "__main__":
    sys.exit(main())
