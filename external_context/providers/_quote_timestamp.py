"""Normalize quote timestamps from Unix seconds to UTC."""

from datetime import datetime, timezone
from math import isfinite


def normalize_quote_timestamp(value) -> str | None:
    if isinstance(value, bool):
        return None

    try:
        seconds = float(value)
        if not isfinite(seconds) or seconds <= 0:
            return None
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None
