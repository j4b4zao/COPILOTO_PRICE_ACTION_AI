"""
analysis/price_action/trade_trap_dynamics.py

Brooks Trading Ranges - Chapter 32:
Getting Trapped In or Out of a Trade.

Diagnostic-only layer. It identifies common execution/management traps without
sending orders or mutating Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TradeTrapResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_TRAP"
    trap_in: bool = False
    trap_out: bool = False
    premature_entry: bool = False
    premature_stop_tightening: bool = False
    signal_deteriorated: bool = False
    entry_bar_strong_close: bool = False
    follow_through_strong: bool = False
    original_plan_still_valid: bool = False
    breakeven_hold_preferred: bool = False
    reentry_watch: bool = False
    discipline_score: float = 0.0
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TradeTrapDynamics:
    """Detect being trapped into a weak trade or trapped out of a good trade."""

    MIN_HISTORY = 5
    STRONG_BODY_RATIO = 0.60
    STRONG_CLOSE_POSITION = 0.70

    def analyze(
        self,
        candles,
        direction,
        signal_index=None,
        entry_index=None,
        entered_before_signal_close=False,
        original_stop=None,
        tightened_stop=None,
        stopped_out=False,
        original_plan_valid=True,
    ):
        direction = str(direction or "").upper()
        if direction not in ("BUY", "SELL"):
            return TradeTrapResult(
                reason="INVALID_DIRECTION",
                reasons=("INVALID_DIRECTION",),
            )

        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return TradeTrapResult(
                direction=direction,
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        if signal_index is None:
            signal_index = max(len(closed) - 3, 0)
        if entry_index is None:
            entry_index = min(signal_index + 1, len(closed) - 1)

        if not (0 <= signal_index < len(closed)) or not (0 <= entry_index < len(closed)):
            return TradeTrapResult(
                direction=direction,
                reason="INVALID_INDEX",
                reasons=("INVALID_INDEX",),
            )

        signal = closed[signal_index]
        entry = closed[entry_index]
        after = closed[entry_index + 1: entry_index + 3]

        signal_deteriorated = self._signal_deteriorated(signal, direction)
        entry_strong = self._strong_directional_close(entry, direction)
        follow_through = any(self._strong_directional_close(c, direction) for c in after)

        reasons = []
        trap_in = False
        trap_out = False
        premature_entry = False
        premature_stop = False
        reentry_watch = False
        breakeven_hold = False

        if entered_before_signal_close:
            premature_entry = True
            reasons.append("ENTRY_BEFORE_SIGNAL_BAR_CLOSED")
            if signal_deteriorated:
                trap_in = True
                reasons.extend(("SIGNAL_DETERIORATED_AT_CLOSE", "TRAPPED_IN_WEAK_TRADE"))

        if tightened_stop is not None and original_stop is not None:
            if self._is_tighter(direction, float(tightened_stop), float(original_stop)):
                # Tightening becomes premature when the entry has not yet produced
                # enough closed-bar evidence to justify abandoning initial risk.
                if not entry_strong and not follow_through:
                    premature_stop = True
                    reasons.append("STOP_TIGHTENED_BEFORE_CLOSED_BAR_CONFIRMATION")

                if stopped_out and original_plan_valid:
                    trap_out = True
                    reentry_watch = True
                    reasons.extend(("STOPPED_OUT_WHILE_ORIGINAL_PLAN_VALID", "TRAPPED_OUT_OF_GOOD_TRADE"))

        if original_plan_valid and (entry_strong or follow_through):
            breakeven_hold = True
            reasons.append("STRONG_CLOSE_SUPPORTS_HOLDING_REMAINDER")

        if trap_in:
            state = "TRAPPED_IN"
        elif trap_out:
            state = "TRAPPED_OUT"
        elif premature_entry:
            state = "PREMATURE_ENTRY_RISK"
        elif premature_stop:
            state = "PREMATURE_STOP_RISK"
        elif entry_strong or follow_through:
            state = "PLAN_HOLD_SUPPORTED"
        else:
            state = "NO_TRAP"

        score = 100.0
        if premature_entry:
            score -= 25.0
        if premature_stop:
            score -= 25.0
        if trap_in:
            score -= 25.0
        if trap_out:
            score -= 25.0
        if entry_strong:
            score += 5.0
        if follow_through:
            score += 5.0
        score = max(0.0, min(score, 100.0))

        if not reasons:
            reasons.append("NO_EXECUTION_TRAP_DETECTED")

        return TradeTrapResult(
            valid=True,
            direction=direction,
            state=state,
            trap_in=trap_in,
            trap_out=trap_out,
            premature_entry=premature_entry,
            premature_stop_tightening=premature_stop,
            signal_deteriorated=signal_deteriorated,
            entry_bar_strong_close=entry_strong,
            follow_through_strong=follow_through,
            original_plan_still_valid=bool(original_plan_valid),
            breakeven_hold_preferred=breakeven_hold,
            reentry_watch=reentry_watch,
            discipline_score=round(score, 1),
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    @classmethod
    def _strong_directional_close(cls, candle, direction):
        high = float(candle.high)
        low = float(candle.low)
        open_ = float(candle.open)
        close = float(candle.close)
        rng = max(high - low, 1e-9)
        body = abs(close - open_)
        body_ratio = body / rng

        if direction == "BUY":
            close_pos = (close - low) / rng
            directional = close > open_
        else:
            close_pos = (high - close) / rng
            directional = close < open_

        return directional and body_ratio >= cls.STRONG_BODY_RATIO and close_pos >= cls.STRONG_CLOSE_POSITION

    @classmethod
    def _signal_deteriorated(cls, candle, direction):
        # A signal that closes weakly/opposite after looking attractive intrabar
        # is treated as deterioration, never as a confirmed setup.
        high = float(candle.high)
        low = float(candle.low)
        open_ = float(candle.open)
        close = float(candle.close)
        rng = max(high - low, 1e-9)
        body_ratio = abs(close - open_) / rng

        if direction == "BUY":
            close_pos = (close - low) / rng
            return close <= open_ or close_pos < 0.55 or body_ratio < 0.25

        close_pos = (high - close) / rng
        return close >= open_ or close_pos < 0.55 or body_ratio < 0.25

    @staticmethod
    def _is_tighter(direction, tightened, original):
        if direction == "BUY":
            return tightened > original
        return tightened < original
