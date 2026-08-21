"""
analysis/price_action/inflexion_time_dynamics.py

Brooks Trading Ranges - Chapter 15:
Key inflexion times of day that create breakouts and reversals.

Session-relative diagnostic layer. It intentionally avoids hard-coding the
clock times from Brooks' E-mini examples so it can be configured for WIN/WDO.
It does not authorize trades and does not mutate Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, time, timedelta


@dataclass(slots=True)
class InflexionTimeResult:
    valid: bool = False
    phase: str = "UNKNOWN"
    minutes_from_open: int = -1
    minutes_to_close: int = -1
    in_inflexion_window: bool = False
    opening_extreme_context: bool = False
    breakout_detected: bool = False
    breakout_direction: str = "NONE"
    reversal_detected: bool = False
    reversal_direction: str = "NONE"
    event_type: str = "NONE"
    event_quality: float = 0.0
    temporal_context_only: bool = True
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class InflexionTimeDynamics:
    """Classify session-relative inflexion windows and price-action events."""

    MIN_HISTORY = 10
    OPENING_MINUTES = 60
    POST_OPEN_END = 150
    MIDDAY_END = 300
    LATE_SESSION_MINUTES = 90

    def analyze(self, candles, session_start=None, session_end=None):
        # Last candle is current/forming and is never used for confirmation.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return InflexionTimeResult(reasons=("INSUFFICIENT_HISTORY",))

        timestamps = [self._timestamp(c) for c in closed]
        if any(ts is None for ts in timestamps):
            return InflexionTimeResult(reasons=("MISSING_TIMESTAMP",))

        current_ts = timestamps[-1]
        start_dt = self._resolve_boundary(current_ts, session_start, timestamps[0])
        end_dt = self._resolve_boundary(current_ts, session_end, None)

        if start_dt is None or current_ts < start_dt:
            return InflexionTimeResult(reasons=("OUTSIDE_SESSION",))

        minutes_from_open = int((current_ts - start_dt).total_seconds() // 60)
        minutes_to_close = -1
        if end_dt is not None:
            minutes_to_close = int((end_dt - current_ts).total_seconds() // 60)

        phase = self._phase(minutes_from_open, minutes_to_close)
        in_window = phase in {
            "OPENING_HOUR",
            "POST_OPEN_INFLEXION",
            "MIDDAY_INFLEXION",
            "LATE_SESSION_INFLEXION",
        }

        breakout, breakout_direction, breakout_quality = self._detect_breakout(closed)
        reversal, reversal_direction, reversal_quality = self._detect_reversal(closed)

        if breakout and reversal:
            event_type = "BREAKOUT_REVERSAL_CONFLICT"
            event_quality = max(breakout_quality, reversal_quality)
        elif breakout:
            event_type = "BREAKOUT"
            event_quality = breakout_quality
        elif reversal:
            event_type = "REVERSAL"
            event_quality = reversal_quality
        else:
            event_type = "NO_EVENT"
            event_quality = 0.0

        opening_extreme = self._opening_extreme_context(closed, timestamps, start_dt)

        reasons = [f"SESSION_PHASE_{phase}"]
        if in_window:
            reasons.append("INFLEXION_WINDOW")
        if opening_extreme:
            reasons.append("OPENING_HOUR_EXTREME_CONTEXT")
        if breakout:
            reasons.append(f"BREAKOUT_{breakout_direction}")
        if reversal:
            reasons.append(f"REVERSAL_{reversal_direction}")

        return InflexionTimeResult(
            valid=True,
            phase=phase,
            minutes_from_open=minutes_from_open,
            minutes_to_close=minutes_to_close,
            in_inflexion_window=in_window,
            opening_extreme_context=opening_extreme,
            breakout_detected=breakout,
            breakout_direction=breakout_direction,
            reversal_detected=reversal,
            reversal_direction=reversal_direction,
            event_type=event_type,
            event_quality=round(event_quality, 1),
            temporal_context_only=True,
            reasons=tuple(reasons),
        )

    def _phase(self, minutes_from_open, minutes_to_close):
        if 0 <= minutes_from_open < self.OPENING_MINUTES:
            return "OPENING_HOUR"
        if self.OPENING_MINUTES <= minutes_from_open < self.POST_OPEN_END:
            return "POST_OPEN_INFLEXION"
        if self.POST_OPEN_END <= minutes_from_open < self.MIDDAY_END:
            return "MIDDAY_INFLEXION"
        if 0 <= minutes_to_close <= self.LATE_SESSION_MINUTES:
            return "LATE_SESSION_INFLEXION"
        return "MATURE_SESSION"

    def _opening_extreme_context(self, candles, timestamps, start_dt):
        opening = [
            bar for bar, ts in zip(candles, timestamps)
            if 0 <= (ts - start_dt).total_seconds() < self.OPENING_MINUTES * 60
        ]
        if len(opening) < 3:
            return False
        high = max(float(x.high) for x in opening)
        low = min(float(x.low) for x in opening)
        last = candles[-1]
        atr = max(self._average_range(candles[-10:]), 1e-9)
        return (
            abs(float(last.close) - high) <= atr * 0.5
            or abs(float(last.close) - low) <= atr * 0.5
        )

    def _detect_breakout(self, candles):
        if len(candles) < 9:
            return False, "NONE", 0.0
        signal = candles[-1]
        reference = candles[-9:-1]
        prior_high = max(float(x.high) for x in reference)
        prior_low = min(float(x.low) for x in reference)
        rng = max(float(signal.high) - float(signal.low), 1e-9)
        body = abs(float(signal.close) - float(signal.open))
        body_ratio = body / rng

        if float(signal.close) > prior_high:
            close_location = (float(signal.close) - float(signal.low)) / rng
            quality = min(100.0, 45.0 + body_ratio * 35.0 + close_location * 20.0)
            return True, "UP", quality
        if float(signal.close) < prior_low:
            close_location = (float(signal.high) - float(signal.close)) / rng
            quality = min(100.0, 45.0 + body_ratio * 35.0 + close_location * 20.0)
            return True, "DOWN", quality
        return False, "NONE", 0.0

    def _detect_reversal(self, candles):
        if len(candles) < 7:
            return False, "NONE", 0.0
        signal = candles[-1]
        reference = candles[-7:-1]
        atr = max(self._average_range(reference), 1e-9)
        rng = max(float(signal.high) - float(signal.low), 1e-9)
        body = abs(float(signal.close) - float(signal.open))
        body_ratio = body / rng
        recent_high = max(float(x.high) for x in reference)
        recent_low = min(float(x.low) for x in reference)

        bear_reversal = (
            float(signal.high) >= recent_high
            and float(signal.close) < float(signal.open)
            and float(signal.close) <= float(signal.low) + rng * 0.4
        )
        bull_reversal = (
            float(signal.low) <= recent_low
            and float(signal.close) > float(signal.open)
            and float(signal.close) >= float(signal.high) - rng * 0.4
        )

        expansion = min(rng / atr, 2.0) / 2.0
        quality = min(100.0, 40.0 + body_ratio * 35.0 + expansion * 25.0)
        if bear_reversal:
            return True, "DOWN", quality
        if bull_reversal:
            return True, "UP", quality
        return False, "NONE", 0.0

    @staticmethod
    def _timestamp(candle):
        ts = getattr(candle, "timestamp", None)
        return ts if isinstance(ts, datetime) else None

    @staticmethod
    def _resolve_boundary(current_ts, boundary, fallback):
        if boundary is None:
            return fallback
        if isinstance(boundary, datetime):
            return boundary
        if isinstance(boundary, time):
            return datetime.combine(current_ts.date(), boundary)
        return None

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(x.high) - float(x.low), 0.0)
            for x in candles
        ) / len(candles)
