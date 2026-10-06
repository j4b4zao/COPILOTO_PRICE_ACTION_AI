"""Manual live external intermarket observational synthesis RC3.

Explicit operator entry point only:
real providers -> manual activation -> RC1 monitor -> RC2 view -> RC3 synthesis.
No automatic activation or operational trading influence is introduced.
"""
from __future__ import annotations

import argparse
import json
import os

from external_context.external_intermarket_observational_synthesis_rc3 import (
    build_observational_synthesis,
)
from tools.external_market_manual_live_view_rc2 import run as run_view


def run(*, enabled: bool, reference_timestamp: str, maximum_staleness_seconds: float,
        fmp_api_key: str, twelvedata_api_key: str) -> dict:
    view = run_view(
        enabled=enabled,
        reference_timestamp=reference_timestamp,
        maximum_staleness_seconds=maximum_staleness_seconds,
        fmp_api_key=fmp_api_key,
        twelvedata_api_key=twelvedata_api_key,
    )
    return build_observational_synthesis(view)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--reference-timestamp", required=True)
    parser.add_argument("--maximum-staleness-seconds", type=float, default=3600.0)
    parser.add_argument("--fmp-api-key", default=None)
    parser.add_argument("--twelvedata-api-key", default=None)
    args = parser.parse_args()

    fmp_key = args.fmp_api_key or os.environ.get("FMP_API_KEY", "")
    td_key = args.twelvedata_api_key or os.environ.get("TWELVEDATA_API_KEY", "")
    result = run(
        enabled=args.enable,
        reference_timestamp=args.reference_timestamp,
        maximum_staleness_seconds=args.maximum_staleness_seconds,
        fmp_api_key=fmp_key,
        twelvedata_api_key=td_key,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
