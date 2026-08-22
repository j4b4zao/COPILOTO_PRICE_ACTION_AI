"""
analysis/price_action/key_times_dynamics.py

Brooks Reversals - Chapter 11:
Key times of the day.

Diagnostic-only intraday time-context layer. It does not authorize trades,
change Score/Risk/Decision, or send orders.

The implementation uses session-relative windows instead of hard-coding a
specific exchange clock. This lets the same logic be reused for WIN/WDO and
other markets by supplying their local regular-session open and close times.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, time


@dataclass(slots=True)
class KeyTimesResult:
    valid: bool = False
    session_phase: str = "NONE"
    key_time: bool = False
    reversal_watch: bool = False
    breakout_watch: bool = False
    reduced_activity_risk: bool = False
    minutes_from_open: int = 0
    minutes_to_close: int = 0
    context_weight: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class KeyTimesDynamics:
    """Classify important intraday windows using session-relative time."""

    def analyze(self, timestamp, session_open, session_close):
        if not isinstance(timestamp, datetime):
            return KeyTimesResult(reasons=("INVALID_TIMESTAMP",))

        open_minutes = self._time_to_minutes(session_open)
        close_minutes = self._time_to_minutes(session_close)
        if open_minutes is None or close_minutes is None:
            return KeyTimesResult(reasons=("INVALID_SESSION_TIME",))

        now_minutes = timestamp.hour * 60 + timestamp.minute
        if close_minutes <= open_minutes:
            return KeyTimesResult(reasons=("OVERNIGHT_SESSION_NOT_SUPPORTED",))

        if now_minutes < open_minutes or now_minutes > close_minutes:
            return KeyTimesResult(
                valid=True,
                session_phase="OUTSIDE_SESSION",
                reasons=("OUTSIDE_REGULAR_SESSION",),
            )

        from_open = now_minutes - open_minutes
        to_close = close_minutes - now_minutes
        session_len = close_minutes - open_minutes

        phase = "NORMAL_SESSION"
        key_time = False
        reversal_watch = False
        breakout_watch = False
        reduced = False
        weight = 0.35
        reasons = []

        if from_open <= 15:
            phase = "OPENING_AUCTION"
            key_time = True
            reversal_watch = True
            breakout_watch = True
            weight = 1.00
            reasons += ["OPENING_PRICE_DISCOVERY", "HIGH_BREAKOUT_AND_REVERSAL_RISK"]
        elif from_open <= 60:
            phase = "OPENING_WINDOW"
            key_time = True
            reversal_watch = True
            breakout_watch = True
            weight = 0.90
            reasons += ["OPENING_STRUCTURE_FORMING", "WATCH_OPENING_REVERSAL"]
        elif from_open <= 90:
            phase = "OPENING_REVERSAL_WINDOW"
            key_time = True
            reversal_watch = True
            weight = 0.80
            reasons += ["FIRST_MAJOR_REASSESSMENT", "REVERSAL_WINDOW"]
        elif self._is_midday(from_open, session_len):
            phase = "MIDDAY"
            reduced = True
            weight = 0.25
            reasons += ["MIDSESSION_TWO_SIDED_RISK", "LOWER_URGENCY_CONTEXT"]
        elif to_close <= 60:
            phase = "LATE_SESSION"
            key_time = True
            reversal_watch = True
            breakout_watch = True
            weight = 0.80
            reasons += ["LATE_SESSION_REPRICING", "WATCH_LATE_BREAKOUT_OR_REVERSAL"]

        if to_close <= 15:
            phase = "CLOSING_WINDOW"
            key_time = True
            reversal_watch = True
            breakout_watch = True
            reduced = False
            weight = 0.95
            reasons = ["CLOSING_ORDER_FLOW", "HIGH_LATE_VOLATILITY_RISK"]

        if not reasons:
            reasons.append("NORMAL_INTRADAY_WINDOW")

        return KeyTimesResult(
            valid=True,
            session_phase=phase,
            key_time=key_time,
            reversal_watch=reversal_watch,
            breakout_watch=breakout_watch,
            reduced_activity_risk=reduced,
            minutes_from_open=from_open,
            minutes_to_close=to_close,
            context_weight=round(weight, 2),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _time_to_minutes(value):
        if isinstance(value, time):
            return value.hour * 60 + value.minute
        if isinstance(value, str):
            try:
                hh, mm = value.strip().split(":", 1)
                h = int(hh)
                m = int(mm)
                if 0 <= h <= 23 and 0 <= m <= 59:
                    return h * 60 + m
            except (ValueError, AttributeError):
                return None
        return None

    @staticmethod
    def _is_midday(from_open, session_len):
        start = session_len * 0.38
        end = session_len * 0.68
        return start <= from_open <= end
