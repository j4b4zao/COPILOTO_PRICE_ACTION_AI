"""Render a supplied economic calendar state as observational console text."""

from dataclasses import asdict
from datetime import datetime
import json

from economic_context.economic_calendar_state import EconomicCalendarState


def _timestamp(value):
    if not isinstance(value, datetime):
        raise TypeError("Calendar values must be JSON data or timestamps")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Calendar timestamps require a timezone")
    return value.isoformat()


def render_calendar(state: EconomicCalendarState | None) -> str:
    """Copy supplied evidence into deterministic text without consulting a clock."""
    heading = "ECONOMIC CALENDAR OBSERVATIONAL"
    if state is None:
        return heading + "\nCALENDAR DATA UNAVAILABLE"
    if type(state) is not EconomicCalendarState:
        raise TypeError("Expected EconomicCalendarState or None")
    if state.observational_only is not True:
        raise ValueError("Calendar presentation requires observational evidence")
    return heading + "\n" + json.dumps(
        asdict(state),
        default=_timestamp,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        indent=2,
    )
