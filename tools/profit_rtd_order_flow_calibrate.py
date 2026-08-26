"""CLI observacional para calibrar thresholds do Order Flow combinado (RC31)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from market_data.order_flow_alignment_calibrator import OrderFlowAlignmentCalibrator


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analisa uma sessão combinada T&T + Book sem alterar Score/Decision.")
    parser.add_argument("session_json")
    args = parser.parse_args(argv)

    path = Path(args.session_json).expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    samples = payload.get("samples", [])
    report = OrderFlowAlignmentCalibrator().evaluate(samples)

    print("PROFIT_RTD_ORDER_FLOW_CALIBRATION=COMPLETED")
    for key, value in report.to_dict().items():
        print(f"{key}={value}")
    print("note=SUGGESTIONS_ARE_OBSERVATIONAL_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
