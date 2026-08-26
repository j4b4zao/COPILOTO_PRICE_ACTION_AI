"""CLI para consolidar cobertura shadow apenas de sessoes pos-RC35."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from market_data.order_flow_post_rc35_coverage import OrderFlowPostRC35CoverageAnalyzer


def main(argv=None):
    parser = argparse.ArgumentParser(description="Consolida apenas sessoes shadow com RC35_SIGNED_DELTA.")
    parser.add_argument("session_json", nargs="+")
    args = parser.parse_args(argv)
    try:
        sessions = [json.loads(Path(p).expanduser().resolve().read_text(encoding="utf-8")) for p in args.session_json]
        report = OrderFlowPostRC35CoverageAnalyzer().evaluate(sessions)
    except Exception as exc:
        print("PROFIT_RTD_ORDER_FLOW_POST_RC35_COVERAGE=ERROR")
        print(f"reason={type(exc).__name__}:{exc}")
        return 1

    print(f"PROFIT_RTD_ORDER_FLOW_POST_RC35_COVERAGE={report.coverage_status}")
    print(f"sessions={report.sessions}")
    print(f"samples={report.samples}")
    print(f"bullish_samples={report.bullish_samples}")
    print(f"bearish_samples={report.bearish_samples}")
    print(f"divergent_samples={report.divergent_samples}")
    print(f"neutral_samples={report.neutral_samples}")
    print(f"changed_count={report.changed_count}")
    print(f"changed_rate={report.changed_rate:.6f}")
    print(f"directional_balance_status={report.directional_balance_status}")
    print(f"reasons={','.join(report.reasons)}")
    print("observational_only=True")
    print("score_influence_allowed=False")
    print("decision_influence_allowed=False")
    print("order_execution_allowed=False")
    return 0


if __name__ == "__main__":
    sys.exit(main())
