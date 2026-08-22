"""
analysis/price_action/stop_entry_dynamics.py

Brooks Trading Ranges - Chapter 27:
Entering on Stops.

Diagnostic-only layer. It models stop-entry mechanics from a completed
signal bar and never sends orders or mutates Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class StopEntryResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_SETUP"
    signal_index: int = -1
    entry_index: int = -1
    trigger_price: float = 0.0
    initial_protective_stop: float = 0.0
    tightened_stop: float = 0.0
    signal_bar_quality: float = 0.0
    entry_bar_quality: float = 0.0
    trigger_hit: bool = False
    strong_entry_bar: bool = False
    tighten_stop_allowed: bool = False
    current_candle_excluded: bool = True
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class StopEntryDynamics:
    """Describe a price-action stop entry from signal bar to entry bar."""

    MIN_HISTORY = 3
    STRONG_BODY_RATIO = 0.60
    STRONG_CLOSE_FRACTION = 0.25

    def analyze(self, candles, direction, tick_size=1.0, signal_index=None):
        direction = str(direction or "").upper()
        if direction not in ("BUY", "SELL"):
            return StopEntryResult(
                reason="INVALID_DIRECTION",
                reasons=("INVALID_DIRECTION",),
            )

        tick = float(tick_size or 0.0)
        if tick <= 0:
            return StopEntryResult(
                direction=direction,
                reason="INVALID_TICK_SIZE",
                reasons=("INVALID_TICK_SIZE",),
            )

        # The last candle is assumed current/forming and cannot confirm entry.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return StopEntryResult(
                direction=direction,
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        if signal_index is None:
            signal_index = len(closed) - 2

        if signal_index < 0 or signal_index >= len(closed):
            return StopEntryResult(
                direction=direction,
                reason="INVALID_SIGNAL_INDEX",
                reasons=("INVALID_SIGNAL_INDEX",),
            )

        signal = closed[signal_index]
        signal_quality = self._signal_quality(signal, direction)

        if direction == "BUY":
            trigger = float(signal.high) + tick
            protective = float(signal.low) - tick
        else:
            trigger = float(signal.low) - tick
            protective = float(signal.high) + tick

        entry_index = -1
        entry_bar = None

        # Only bars AFTER the completed signal bar can trigger the stop entry.
        for idx in range(signal_index + 1, len(closed)):
            bar = closed[idx]
            if direction == "BUY" and float(bar.high) >= trigger:
                entry_index = idx
                entry_bar = bar
                break
            if direction == "SELL" and float(bar.low) <= trigger:
                entry_index = idx
                entry_bar = bar
                break

        reasons = [
            "STOP_ENTRY_USES_MARKET_MOMENTUM",
            "CURRENT_CANDLE_EXCLUDED",
        ]

        if entry_bar is None:
            reasons.append("TRIGGER_NOT_HIT")
            return StopEntryResult(
                valid=True,
                direction=direction,
                state="STOP_ENTRY_PENDING",
                signal_index=signal_index,
                trigger_price=round(trigger, 6),
                initial_protective_stop=round(protective, 6),
                signal_bar_quality=round(signal_quality, 3),
                trigger_hit=False,
                current_candle_excluded=True,
                reason=reasons[-1],
                reasons=tuple(reasons),
            )

        entry_quality = self._entry_quality(entry_bar, direction)
        strong_entry = entry_quality >= 0.70

        tightened_stop = protective
        tighten_allowed = False

        if strong_entry:
            if direction == "BUY":
                candidate = float(entry_bar.low) - tick
                if candidate > protective and candidate < trigger:
                    tightened_stop = candidate
                    tighten_allowed = True
            else:
                candidate = float(entry_bar.high) + tick
                if candidate < protective and candidate > trigger:
                    tightened_stop = candidate
                    tighten_allowed = True

        reasons.append("STOP_ENTRY_TRIGGERED")
        if strong_entry:
            reasons.append("STRONG_ENTRY_BAR")
        if tighten_allowed:
            reasons.append("PROTECTIVE_STOP_CAN_TIGHTEN_TO_ENTRY_BAR")
        else:
            reasons.append("KEEP_STOP_BEYOND_SIGNAL_BAR")

        state = (
            "STOP_ENTRY_TRIGGERED_STRONG"
            if strong_entry
            else "STOP_ENTRY_TRIGGERED"
        )

        return StopEntryResult(
            valid=True,
            direction=direction,
            state=state,
            signal_index=signal_index,
            entry_index=entry_index,
            trigger_price=round(trigger, 6),
            initial_protective_stop=round(protective, 6),
            tightened_stop=round(tightened_stop, 6),
            signal_bar_quality=round(signal_quality, 3),
            entry_bar_quality=round(entry_quality, 3),
            trigger_hit=True,
            strong_entry_bar=strong_entry,
            tighten_stop_allowed=tighten_allowed,
            current_candle_excluded=True,
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    def _signal_quality(self, bar, direction):
        range_ = max(float(bar.high) - float(bar.low), 1e-9)
        body = abs(float(bar.close) - float(bar.open))
        body_ratio = min(body / range_, 1.0)

        if direction == "BUY":
            close_location = (float(bar.close) - float(bar.low)) / range_
            directional = float(bar.close) > float(bar.open)
        else:
            close_location = (float(bar.high) - float(bar.close)) / range_
            directional = float(bar.close) < float(bar.open)

        score = body_ratio * 0.5 + close_location * 0.4 + (0.1 if directional else 0.0)
        return min(max(score, 0.0), 1.0)

    def _entry_quality(self, bar, direction):
        range_ = max(float(bar.high) - float(bar.low), 1e-9)
        body = abs(float(bar.close) - float(bar.open))
        body_ratio = min(body / range_, 1.0)

        if direction == "BUY":
            directional = float(bar.close) > float(bar.open)
            close_near_extreme = (
                float(bar.high) - float(bar.close)
            ) <= range_ * self.STRONG_CLOSE_FRACTION
        else:
            directional = float(bar.close) < float(bar.open)
            close_near_extreme = (
                float(bar.close) - float(bar.low)
            ) <= range_ * self.STRONG_CLOSE_FRACTION

        score = body_ratio * 0.6
        if directional:
            score += 0.2
        if close_near_extreme:
            score += 0.2

        return min(max(score, 0.0), 1.0)
