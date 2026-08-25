"""
analysis/price_action/protective_trailing_stop_dynamics.py

Brooks Trading Ranges - Chapter 29:
Protective and Trailing Stops.

Diagnostic-only layer. It does not send orders and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class ProtectiveTrailingStopResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_STOP_CONTEXT"
    entry_price: float = 0.0
    initial_stop: float = 0.0
    current_stop: float = 0.0
    proposed_stop: float = 0.0
    stop_distance: float = 0.0
    trailing_active: bool = False
    stop_improved: bool = False
    stop_loosened: bool = False
    structural_advance_confirmed: bool = False
    latest_swing_index: int = -1
    latest_swing_price: float = 0.0
    protected_r: float = 0.0
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class ProtectiveTrailingStopDynamics:
    """Evaluate initial protective stop and structural trailing stop logic."""

    MIN_HISTORY = 7
    SWING_LEFT = 2
    SWING_RIGHT = 2

    def analyze(
        self,
        candles,
        direction,
        entry_price,
        initial_stop,
        current_stop=None,
        tick_size=1.0,
    ):
        direction = str(direction or "").upper()
        if direction not in ("BUY", "SELL"):
            return ProtectiveTrailingStopResult(
                reason="INVALID_DIRECTION",
                reasons=("INVALID_DIRECTION",),
            )

        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return ProtectiveTrailingStopResult(
                direction=direction,
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        entry = float(entry_price)
        initial = float(initial_stop)
        tick = max(float(tick_size), 0.0)
        current = initial if current_stop is None else float(current_stop)

        if not self._valid_geometry(direction, entry, initial):
            return ProtectiveTrailingStopResult(
                direction=direction,
                entry_price=entry,
                initial_stop=initial,
                current_stop=current,
                state="INVALID_PROTECTIVE_STOP",
                reason="INVALID_PROTECTIVE_STOP_GEOMETRY",
                reasons=("INVALID_PROTECTIVE_STOP_GEOMETRY",),
            )

        reasons = ["PROTECTIVE_STOP_VALID"]
        stop_loosened = self._is_looser(direction, current, initial)
        if stop_loosened:
            reasons.append("CURRENT_STOP_LOOSER_THAN_INITIAL")

        pivots = self._confirmed_pivots(closed)
        proposed = current
        latest_index = -1
        latest_price = 0.0
        advance_confirmed = False

        if direction == "BUY":
            swing_lows = [(i, p) for kind, i, p in pivots if kind == "LOW"]
            swing_highs = [(i, p) for kind, i, p in pivots if kind == "HIGH"]
            if swing_lows and swing_highs:
                latest_index, latest_price = swing_lows[-1]
                later_highs = [p for i, p in swing_highs if i > latest_index]
                prior_highs = [p for i, p in swing_highs if i < latest_index]
                if later_highs and prior_highs and max(later_highs) > max(prior_highs):
                    advance_confirmed = True
                    candidate = latest_price - tick
                    proposed = max(current, initial, candidate)
                    reasons.append("NEW_SWING_HIGH_AFTER_HIGHER_LOW")
        else:
            swing_highs = [(i, p) for kind, i, p in pivots if kind == "HIGH"]
            swing_lows = [(i, p) for kind, i, p in pivots if kind == "LOW"]
            if swing_highs and swing_lows:
                latest_index, latest_price = swing_highs[-1]
                later_lows = [p for i, p in swing_lows if i > latest_index]
                prior_lows = [p for i, p in swing_lows if i < latest_index]
                if later_lows and prior_lows and min(later_lows) < min(prior_lows):
                    advance_confirmed = True
                    candidate = latest_price + tick
                    proposed = min(current, initial, candidate)
                    reasons.append("NEW_SWING_LOW_AFTER_LOWER_HIGH")

        improved = self._is_tighter(direction, proposed, current)
        trailing_active = advance_confirmed and latest_index >= 0

        if stop_loosened:
            state = "STOP_LOOSENING_REJECTED"
            proposed = initial if current_stop is not None else current
            improved = self._is_tighter(direction, proposed, current)
            reasons.append("NEVER_LOOSEN_STOP")
        elif improved:
            state = "TRAILING_STOP_ADVANCE"
            reasons.append("TRAILING_STOP_TIGHTENED")
        elif trailing_active:
            state = "TRAILING_STOP_HOLD"
            reasons.append("STRUCTURAL_ADVANCE_BUT_NO_TIGHTER_STOP")
        else:
            state = "PROTECTIVE_STOP_HOLD"
            reasons.append("NO_CONFIRMED_STRUCTURAL_ADVANCE")

        initial_risk = abs(entry - initial)
        if initial_risk > 0:
            if direction == "BUY":
                protected_r = (proposed - initial) / initial_risk
            else:
                protected_r = (initial - proposed) / initial_risk
        else:
            protected_r = 0.0

        return ProtectiveTrailingStopResult(
            valid=True,
            direction=direction,
            state=state,
            entry_price=round(entry, 6),
            initial_stop=round(initial, 6),
            current_stop=round(current, 6),
            proposed_stop=round(proposed, 6),
            stop_distance=round(abs(entry - proposed), 6),
            trailing_active=trailing_active,
            stop_improved=improved,
            stop_loosened=stop_loosened,
            structural_advance_confirmed=advance_confirmed,
            latest_swing_index=latest_index,
            latest_swing_price=round(latest_price, 6),
            protected_r=round(protected_r, 3),
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    @classmethod
    def _confirmed_pivots(cls, candles):
        pivots = []
        left = cls.SWING_LEFT
        right = cls.SWING_RIGHT
        for i in range(left, len(candles) - right):
            c = candles[i]
            high = float(c.high)
            low = float(c.low)
            left_slice = candles[i - left:i]
            right_slice = candles[i + 1:i + 1 + right]

            if all(high > float(x.high) for x in left_slice + right_slice):
                pivots.append(("HIGH", i, high))
            if all(low < float(x.low) for x in left_slice + right_slice):
                pivots.append(("LOW", i, low))
        return pivots

    @staticmethod
    def _valid_geometry(direction, entry, stop):
        return stop < entry if direction == "BUY" else stop > entry

    @staticmethod
    def _is_tighter(direction, candidate, current):
        return candidate > current if direction == "BUY" else candidate < current

    @staticmethod
    def _is_looser(direction, current, initial):
        return current < initial if direction == "BUY" else current > initial
