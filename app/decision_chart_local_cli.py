"""Generate an offline SVG from a caller-supplied decision and candle snapshot."""

import argparse
import json
from pathlib import Path

from dashboard.copilot_readonly_dashboard import OfficialDecisionView
from dashboard.decision_candle_chart import render_decision_chart
from models.candle import Candle


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.file.read_text(encoding="utf-8-sig"))
        if type(payload) is not dict or set(payload) != {"candles", "decision", "marker_index"}:
            raise ValueError("Expected candles, decision and marker_index")
        if type(payload["candles"]) is not list:
            raise TypeError("Expected a candle list")
        candles = []
        for row in payload["candles"]:
            if type(row) is not dict or set(row) != {"open", "high", "low", "close"}:
                raise ValueError("Candles require exactly open, high, low and close")
            candles.append(Candle(**row))
        reported = payload["decision"]
        if reported is not None and type(reported) is not dict:
            raise TypeError("Expected an official decision snapshot or null")
        decision = OfficialDecisionView(**reported) if reported is not None else None
        svg = render_decision_chart(candles, decision, marker_index=payload["marker_index"])
        if args.output.suffix.lower() != ".svg":
            raise ValueError("Output must use the .svg extension")
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(svg)
    except (OSError, ValueError, TypeError, OverflowError, RecursionError) as error:
        print(f"CHART UNAVAILABLE: {error}")
        return 2
    print(f"OFFLINE SVG CREATED: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

