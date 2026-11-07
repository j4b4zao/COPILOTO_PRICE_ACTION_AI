"""Manual offline display of a local economic calendar JSON file."""

import argparse
from datetime import datetime
import json
from pathlib import Path

from dashboard.economic_calendar_readonly_dashboard import render_calendar
from economic_context import EconomicCalendarRuntime


def _reference_time(value):
    try:
        stamp = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use an ISO timestamp with timezone") from error
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise argparse.ArgumentTypeError("Reference timestamp requires a timezone")
    return stamp


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--now", required=True, type=_reference_time)
    args = parser.parse_args(argv)

    def load_local(*, now):
        return json.loads(args.file.read_text(encoding="utf-8-sig"))

    runtime = EconomicCalendarRuntime(
        load_local, source="LOCAL_FILE", allow_partial=False
    )
    state = runtime.snapshot(symbol=args.symbol, now=args.now)
    print(render_calendar(state))
    return 2 if state.status == "UNAVAILABLE" else 0


if __name__ == "__main__":
    raise SystemExit(run())

