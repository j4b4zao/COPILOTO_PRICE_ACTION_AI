"""
analysis/price_action/failure_reversal_dynamics.py

Brooks Trading Price Action Reversals - Chapter 9: Failures.
Diagnostic-only layer; does not mutate Score/Risk/Decision.
"""
from dataclasses import dataclass, asdict

@dataclass(slots=True)
class FailureReversalResult:
    valid: bool = False
    original_setup_direction: str = "NONE"
    opposite_direction: str = "NONE"
    state: str = "NO_FAILURE"
    setup_triggered: bool = False
    objective_reached: bool = False
    failed_setup: bool = False
    opposite_signal: bool = False
    opposite_follow_through: bool = False
    second_signal_with_trend: bool = False
    failure_reversal_confirmed: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()
    def to_dict(self): return asdict(self)

class FailureReversalDynamics:
    MIN_HISTORY = 8

    def analyze(self, candles, setup_direction, entry_price=None, objective_price=None, dominant_trend="NONE"):
        direction = str(setup_direction or "NONE").upper()
        trend = str(dominant_trend or "NONE").upper()
        if direction not in {"BUY", "SELL"}:
            return FailureReversalResult(reasons=("INVALID_SETUP_DIRECTION",))
        closed = list(candles[:-1]) if candles else []
        opposite = "SELL" if direction == "BUY" else "BUY"
        if len(closed) < self.MIN_HISTORY:
            return FailureReversalResult(original_setup_direction=direction, opposite_direction=opposite, reasons=("INSUFFICIENT_HISTORY",))

        signal, entry_bar, failure_bar, follow_bar = closed[-4], closed[-3], closed[-2], closed[-1]
        trigger = float(entry_price) if entry_price is not None else (float(signal.high) if direction == "BUY" else float(signal.low))
        risk = max(float(signal.high) - float(signal.low), 1e-9)
        objective = float(objective_price) if objective_price is not None else (trigger + risk if direction == "BUY" else trigger - risk)

        triggered = float(entry_bar.high) >= trigger if direction == "BUY" else float(entry_bar.low) <= trigger
        reached = any((float(b.high) >= objective if direction == "BUY" else float(b.low) <= objective) for b in (entry_bar, failure_bar, follow_bar))
        invalidated = float(failure_bar.close) < float(signal.low) if direction == "BUY" else float(failure_bar.close) > float(signal.high)
        failed = triggered and not reached and invalidated
        opposite_signal = failed and self._strong_bar(failure_bar, opposite)
        opposite_follow = opposite_signal and (float(follow_bar.close) < float(failure_bar.low) if opposite == "SELL" else float(follow_bar.close) > float(failure_bar.high))
        aligned = failed and opposite_signal and ((opposite == "BUY" and trend == "UP") or (opposite == "SELL" and trend == "DOWN"))
        confirmed = failed and opposite_signal and opposite_follow

        if not triggered: state = "SETUP_NOT_TRIGGERED"
        elif reached: state = "SETUP_SUCCEEDED"
        elif not failed: state = "SETUP_ACTIVE"
        elif confirmed and aligned: state = "SECOND_SIGNAL_WITH_TREND"
        elif confirmed: state = "FAILURE_REVERSAL_CONFIRMED"
        elif opposite_signal: state = "FAILURE_REVERSAL_WAIT"
        else: state = "FAILED_SETUP_ONLY"

        score = (35 if failed else 0) + (25 if opposite_signal else 0) + (30 if opposite_follow else 0) + (10 if aligned else 0)
        reasons = [f"ORIGINAL_SETUP_{direction}"]
        if triggered: reasons.append("SETUP_TRIGGERED")
        if reached: reasons.append("OBJECTIVE_REACHED")
        if failed: reasons.append("SETUP_FAILED_BEFORE_OBJECTIVE")
        if opposite_signal: reasons.append(f"OPPOSITE_{opposite}_SIGNAL")
        if opposite_follow: reasons.append("OPPOSITE_FOLLOW_THROUGH")
        if aligned: reasons.append("FAILURE_ALIGNS_WITH_DOMINANT_TREND")

        return FailureReversalResult(True, direction, opposite, state, triggered, reached, failed, opposite_signal, opposite_follow, aligned, confirmed, float(score), tuple(reasons))

    @staticmethod
    def _strong_bar(bar, direction):
        o, h, l, c = map(float, (bar.open, bar.high, bar.low, bar.close))
        rng = max(h-l, 1e-9)
        body = abs(c-o)/rng
        if direction == "BUY": return c > o and body >= 0.45 and (h-c)/rng <= 0.30
        return c < o and body >= 0.45 and (c-l)/rng <= 0.30
