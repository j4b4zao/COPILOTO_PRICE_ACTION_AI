"""CLI RC34 para avaliar evidencia multi-sessao do shadow Order Flow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from order_flow.order_flow_shadow_promotion_gate import OrderFlowShadowPromotionGate


def build_parser():
    p = argparse.ArgumentParser(description="Avalia se sessoes shadow estao prontas apenas para revisao de thresholds.")
    p.add_argument("session_json", nargs="+")
    return p


def run(paths: list[str]) -> int:
    try:
        sessions = [json.loads(Path(raw).expanduser().resolve().read_text(encoding="utf-8")) for raw in paths]
        report = OrderFlowShadowPromotionGate().evaluate(sessions)
    except Exception as exc:
        print("PROFIT_RTD_ORDER_FLOW_SHADOW_PROMOTION_GATE=ERROR")
        print(f"reason={type(exc).__name__}:{exc}")
        return 1

    print(f"PROFIT_RTD_ORDER_FLOW_SHADOW_PROMOTION_GATE={report.status}")
    print(f"sessions={report.sessions}")
    print(f"samples={report.samples}")
    print(f"bullish_samples={report.bullish_samples}")
    print(f"bearish_samples={report.bearish_samples}")
    print(f"divergent_samples={report.divergent_samples}")
    print(f"neutral_samples={report.neutral_samples}")
    print(f"bullish_runs={report.bullish_runs}")
    print(f"bearish_runs={report.bearish_runs}")
    print(f"directional_balance_status={report.directional_balance_status}")
    print(f"reasons={','.join(report.reasons)}")
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    print("note=CANDIDATE_FOR_REVIEW_DOES_NOT_PROMOTE_THRESHOLDS")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    return run(args.session_json)


if __name__ == "__main__":
    sys.exit(main())
