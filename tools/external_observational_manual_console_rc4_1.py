"""Manual read-only RC4.1 console projection."""
from __future__ import annotations
import argparse
import json
from external_context.external_observational_context_console_projection_rc4_1 import build_console_projection
from tools.external_observational_manual_live_context_rc4 import run as run_context

def run(**kwargs):
    return build_console_projection(run_context(**kwargs))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--reference-timestamp", required=True)
    parser.add_argument("--maximum-staleness-seconds", type=float, default=3600.0)
    parser.add_argument("--fmp-api-key", default="")
    parser.add_argument("--twelvedata-api-key", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run(
        enabled=args.enable,
        reference_timestamp=args.reference_timestamp,
        maximum_staleness_seconds=args.maximum_staleness_seconds,
        fmp_api_key=args.fmp_api_key,
        twelvedata_api_key=args.twelvedata_api_key,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else "\n".join(result["lines"]))

if __name__ == "__main__":
    main()
