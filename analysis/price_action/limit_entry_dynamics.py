"""
analysis/price_action/limit_entry_dynamics.py

Brooks Trading Ranges - Chapter 28:
Entering on limit orders.

Diagnostic-only layer. It does not send orders and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class LimitEntryResult:
    valid: bool = False
    direction: str = "NONE"
    state: str = "NO_SETUP"
    context: str = "NONE"
    reference_price: float = 0.0
    limit_price: float = 0.0
    protective_stop: float = 0.0
    target_price: float = 0.0
    risk_reward: float = 0.0
    touched: bool = False
    favorable_location: bool = False
    countertrend_entry: bool = False
    strong_trend_block: bool = False
    confirmation_required: bool = True
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class LimitEntryDynamics:
    """Diagnose whether a limit-entry idea is coherent with market context."""

    MIN_HISTORY = 12
    SAMPLE = 14
    STRONG_EFFICIENCY = 0.58
    TIGHT_RANGE_WIDTH_ATR = 2.2
    EDGE_ZONE = 0.30
    MIN_RR = 1.0

    def analyze(
        self,
        candles,
        direction,
        reference_price=None,
        limit_price=None,
        stop_price=None,
        target_price=None,
    ):
        # The last candle is assumed current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        direction = str(direction or "").upper()

        if direction not in ("BUY", "SELL"):
            return LimitEntryResult(
                reason="INVALID_DIRECTION",
                reasons=("INVALID_DIRECTION",),
            )

        if len(closed) < self.MIN_HISTORY:
            return LimitEntryResult(
                direction=direction,
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        sample = closed[-self.SAMPLE:]
        atr = max(self._average_range(sample), 1e-9)
        high = max(float(x.high) for x in sample)
        low = min(float(x.low) for x in sample)
        width = max(high - low, 1e-9)
        first_close = float(sample[0].close)
        last_close = float(sample[-1].close)
        efficiency = abs(last_close - first_close) / width
        overlap = self._overlap_ratio(sample)
        two_sided = self._two_sided(sample)

        context = (
            "TREND"
            if efficiency >= self.STRONG_EFFICIENCY and not two_sided
            else "TRADING_RANGE"
        )
        width_atr = width / atr
        if width_atr <= self.TIGHT_RANGE_WIDTH_ATR and overlap >= 0.65:
            context = "TIGHT_TRADING_RANGE"

        trend_direction = (
            "BUY"
            if last_close > first_close
            else "SELL"
            if last_close < first_close
            else "NONE"
        )

        ref = float(reference_price) if reference_price is not None else last_close
        if limit_price is None:
            # Default diagnostic location: buy near the lower edge,
            # sell near the upper edge.
            limit = low + width * 0.20 if direction == "BUY" else high - width * 0.20
        else:
            limit = float(limit_price)

        position = (limit - low) / width
        favorable_location = (
            position <= self.EDGE_ZONE
            if direction == "BUY"
            else position >= (1.0 - self.EDGE_ZONE)
        )

        touched = any(
            float(c.low) <= limit <= float(c.high)
            for c in sample[-4:]
        )

        countertrend = (
            context == "TREND"
            and trend_direction in ("BUY", "SELL")
            and direction != trend_direction
        )
        strong_trend_block = countertrend and efficiency >= 0.72

        stop = (
            float(stop_price)
            if stop_price is not None
            else low - 0.25 * atr
            if direction == "BUY"
            else high + 0.25 * atr
        )
        target = (
            float(target_price)
            if target_price is not None
            else high
            if direction == "BUY"
            else low
        )

        risk = abs(limit - stop)
        reward = abs(target - limit)
        rr = reward / risk if risk > 0 else 0.0

        reasons = [f"CONTEXT_{context}"]

        if context == "TIGHT_TRADING_RANGE":
            state = "LIMIT_ENTRY_AVOID"
            reasons.append("TIGHT_RANGE_POOR_EDGE")
        elif strong_trend_block:
            state = "LIMIT_ENTRY_COUNTERTREND_BLOCKED"
            reasons.extend(
                (
                    "COUNTERTREND_IN_STRONG_TREND",
                    "WAIT_FOR_STRUCTURAL_REVERSAL",
                )
            )
        elif not favorable_location:
            state = "LIMIT_ENTRY_POOR_LOCATION"
            reasons.append("LIMIT_NOT_NEAR_RANGE_EDGE_OR_PULLBACK_EXTREME")
        elif rr < self.MIN_RR:
            state = "LIMIT_ENTRY_POOR_EQUATION"
            reasons.append("INSUFFICIENT_REWARD_RISK")
        elif countertrend:
            state = "LIMIT_ENTRY_COUNTERTREND_WAIT"
            reasons.extend(
                (
                    "COUNTERTREND_LIMIT_REQUIRES_EXTRA_CONFIRMATION",
                    "DO_NOT_ASSUME_REVERSAL",
                )
            )
        elif touched:
            state = "LIMIT_ENTRY_TOUCHED"
            reasons.append("LIMIT_PRICE_TRADED")
        else:
            state = "LIMIT_ENTRY_CANDIDATE"
            reasons.append("FAVORABLE_LIMIT_LOCATION")

        if context == "TRADING_RANGE" and favorable_location:
            reasons.append("BUY_LOW_SELL_HIGH_CONTEXT")

        # Limit entries accept adverse movement before momentum confirms them.
        reasons.append("LIMIT_ENTRY_HAS_LESS_MOMENTUM_CONFIRMATION_THAN_STOP_ENTRY")

        return LimitEntryResult(
            valid=state in ("LIMIT_ENTRY_CANDIDATE", "LIMIT_ENTRY_TOUCHED"),
            direction=direction,
            state=state,
            context=context,
            reference_price=round(ref, 6),
            limit_price=round(limit, 6),
            protective_stop=round(stop, 6),
            target_price=round(target, 6),
            risk_reward=round(rr, 3),
            touched=touched,
            favorable_location=favorable_location,
            countertrend_entry=countertrend,
            strong_trend_block=strong_trend_block,
            confirmation_required=True,
            reason=reasons[-1],
            reasons=tuple(reasons),
        )

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(
            max(float(c.high) - float(c.low), 0.0)
            for c in candles
        ) / len(candles)

    @staticmethod
    def _overlap_ratio(candles):
        if len(candles) < 2:
            return 0.0
        total = 0
        overlaps = 0
        for a, b in zip(candles, candles[1:]):
            total += 1
            if min(float(a.high), float(b.high)) >= max(float(a.low), float(b.low)):
                overlaps += 1
        return overlaps / total if total else 0.0

    @staticmethod
    def _two_sided(candles):
        bulls = sum(float(c.close) > float(c.open) for c in candles)
        bears = sum(float(c.close) < float(c.open) for c in candles)
        n = len(candles)
        threshold = max(3, int(n * 0.25))
        return bulls >= threshold and bears >= threshold
