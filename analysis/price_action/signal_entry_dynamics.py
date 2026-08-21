"""Ciclo informativo sinal/entrada inspirado em Brooks Trends, capítulo 4."""

from enums.trend import Trend


class SignalEntryDynamics:

    DOJI_BODY_RATIO = 0.10
    STRONG_BODY_RATIO = 0.60

    @classmethod
    def analyze(cls, candles, trend=Trend.UNKNOWN):
        closed = list(candles[:-1])

        if len(closed) < 2:
            return {}

        if len(closed) >= 3:
            completed = cls._completed_cycle(
                signal=closed[-3],
                entry=closed[-2],
                follow_through=closed[-1],
                trend=trend,
            )
            if completed:
                return completed

        triggered = cls._triggered_cycle(
            signal=closed[-2],
            entry=closed[-1],
            trend=trend,
        )
        if triggered:
            return triggered

        signal = closed[-1]
        direction = cls._setup_direction(signal, trend)

        return cls._result(
            phase="SETUP_PENDING",
            direction=direction,
            signal=signal,
            trend=trend,
            entry_level=cls._entry_level(signal, direction),
        )

    @classmethod
    def _completed_cycle(
        cls,
        *,
        signal,
        entry,
        follow_through,
        trend,
    ):
        direction = cls._trigger_direction(signal, entry)

        if direction == "NONE":
            return None

        followed = cls._follows(direction, entry, follow_through)
        phase = "FOLLOW_THROUGH" if followed else "ENTRY_STALLED"

        return cls._result(
            phase=phase,
            direction=direction,
            signal=signal,
            trend=trend,
            entry_level=cls._entry_level(signal, direction),
            entry_triggered=True,
            follow_through=followed,
            follow_through_strength=cls._follow_through_strength(
                direction,
                follow_through,
                followed,
            ),
        )

    @classmethod
    def _triggered_cycle(cls, *, signal, entry, trend):
        direction = cls._trigger_direction(signal, entry)

        if direction == "NONE":
            return None

        return cls._result(
            phase="ENTRY_TRIGGERED",
            direction=direction,
            signal=signal,
            trend=trend,
            entry_level=cls._entry_level(signal, direction),
            entry_triggered=True,
        )

    @classmethod
    def _trigger_direction(cls, signal, entry):
        broke_up = entry.high > signal.high
        broke_down = entry.low < signal.low

        if broke_up and not broke_down:
            return "UP"
        if broke_down and not broke_up:
            return "DOWN"
        if broke_up and broke_down:
            if entry.close > signal.high:
                return "UP"
            if entry.close < signal.low:
                return "DOWN"

        return "NONE"

    @classmethod
    def _setup_direction(cls, signal, trend):
        if trend == Trend.UP:
            return "UP"
        if trend == Trend.DOWN:
            return "DOWN"
        if signal.close > signal.open:
            return "UP"
        if signal.close < signal.open:
            return "DOWN"
        return "NONE"

    @staticmethod
    def _entry_level(signal, direction):
        if direction == "UP":
            return float(signal.high)
        if direction == "DOWN":
            return float(signal.low)
        return 0.0

    @classmethod
    def _follows(cls, direction, entry, follow_through):
        if direction == "UP":
            return (
                follow_through.close > entry.close
                and follow_through.close > follow_through.open
            )
        return (
            follow_through.close < entry.close
            and follow_through.close < follow_through.open
        )

    @classmethod
    def _signal_quality(cls, signal, direction):
        body_ratio = cls._body_ratio(signal)

        if body_ratio <= cls.DOJI_BODY_RATIO:
            return "WEAK"

        aligned_body = (
            direction == "UP"
            and signal.close > signal.open
        ) or (
            direction == "DOWN"
            and signal.close < signal.open
        )

        if aligned_body and body_ratio >= cls.STRONG_BODY_RATIO:
            return "STRONG"
        if aligned_body:
            return "MODERATE"
        return "WEAK"

    @classmethod
    def _follow_through_strength(
        cls,
        direction,
        candle,
        followed,
    ):
        if not followed:
            return "NONE"

        body_ratio = cls._body_ratio(candle)
        directional_close = (
            direction == "UP"
            and cls._close_position(candle) >= 0.75
        ) or (
            direction == "DOWN"
            and cls._close_position(candle) <= 0.25
        )

        if body_ratio >= cls.STRONG_BODY_RATIO and directional_close:
            return "STRONG"
        return "MODERATE"

    @staticmethod
    def _context_alignment(direction, trend):
        if trend == Trend.UP:
            return "WITH_TREND" if direction == "UP" else "COUNTER_TREND"
        if trend == Trend.DOWN:
            return "WITH_TREND" if direction == "DOWN" else "COUNTER_TREND"
        return "NEUTRAL"

    @staticmethod
    def _body_ratio(candle):
        if candle.range <= 0.0:
            return 0.0
        return candle.body / candle.range

    @staticmethod
    def _close_position(candle):
        if candle.range <= 0.0:
            return 0.5
        return (candle.close - candle.low) / candle.range

    @classmethod
    def _result(
        cls,
        *,
        phase,
        direction,
        signal,
        trend,
        entry_level,
        entry_triggered=False,
        follow_through=False,
        follow_through_strength="NONE",
    ):
        return {
            "brooks_signal_phase": phase,
            "brooks_signal_direction": direction,
            "brooks_signal_quality": cls._signal_quality(
                signal,
                direction,
            ),
            "brooks_signal_context": cls._context_alignment(
                direction,
                trend,
            ),
            "brooks_entry_level": entry_level,
            "brooks_entry_triggered": entry_triggered,
            "brooks_follow_through": follow_through,
            "brooks_follow_through_strength": (
                follow_through_strength
            ),
        }
