"""Display local headline evidence using explicit time and age policy."""

import argparse
from datetime import datetime, timedelta
import json
import math
from pathlib import Path

from dashboard.local_news_readonly_dashboard import render_local_news
from economic_context.local_news import evaluate_local_news


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--now", required=True, type=datetime.fromisoformat)
    parser.add_argument("--max-age-minutes", required=True, type=float)
    args = parser.parse_args(argv)
    if args.now.tzinfo is None or args.now.utcoffset() is None:
        parser.error("Reference time requires a timezone")
    if not math.isfinite(args.max_age_minutes) or args.max_age_minutes <= 0:
        parser.error("Maximum age must be a finite positive number")
    try:
        age = timedelta(minutes=args.max_age_minutes)
        evaluate_local_news([], now=args.now, max_age=age)
    except (ValueError, OverflowError) as error:
        parser.error(str(error))

    try:
        payload = json.loads(args.file.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, RecursionError):
        payload = None
    state = evaluate_local_news(payload, now=args.now, max_age=age)
    print(render_local_news(state))
    return 2 if state.status == "UNAVAILABLE" else 0


if __name__ == "__main__":
    raise SystemExit(run())

