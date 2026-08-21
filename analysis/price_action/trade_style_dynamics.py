"""
analysis/price_action/trade_style_dynamics.py

Brooks Trading Ranges - Chapter 24:
Scalping, Swing Trading, and Investing.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TradeStyleResult:
    valid: bool = False
    style: str = "NO_TRADE"
    context: str = "NONE"
    direction: str = "NONE"
    range_width_atr: float = 0.0
    directional_efficiency: float = 0.0
    reward_risk_estimate: float = 0.0
    target_space_atr: float = 0.0
    scalp_appropriate: bool = False
    swing_appropriate: bool = False
    investing_applicable: bool = False
    no_trade: bool = True
    reason: str = ""
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TradeStyleDynamics:
    """Classify the management style that fits the current price context."""

    MIN_HISTORY = 12
    SAMPLE = 14
    TIGHT_RANGE_ATR = 2.2
    WIDE_RANGE_ATR = 5.0
    STRONG_EFFICIENCY = 0.55
    MIN_SWING_RR = 1.50
    MIN_SWING_SPACE_ATR = 2.0

    def analyze(self, candles, structural_target=None, stop_price=None):
        # Last candle is assumed current/forming and is excluded.
        closed = list(candles[:-1]) if candles else []
        if len(closed) < self.MIN_HISTORY:
            return TradeStyleResult(
                reason="INSUFFICIENT_HISTORY",
                reasons=("INSUFFICIENT_HISTORY",),
            )

        sample = closed[-self.SAMPLE:]
        atr = max(self._average_range(sample), 1e-9)
        high = max(float(x.high) for x in sample)
        low = min(float(x.low) for x in sample)
        width = high - low
        range_width_atr = width / atr

        first_close = float(sample[0].close)
        last_close = float(sample[-1].close)
        net = abs(last_close - first_close)
        efficiency = min(net / max(width, 1e-9), 1.0)

        direction = "UP" if last_close > first_close else "DOWN" if last_close < first_close else "NONE"
        two_sided = self._two_sided(sample)
        overlap = self._overlap_ratio(sample)

        context = "TREND" if efficiency >= self.STRONG_EFFICIENCY and not two_sided else "TRADING_RANGE"
        if range_width_atr <= self.TIGHT_RANGE_ATR and overlap >= 0.65:
            context = "TIGHT_TRADING_RANGE"

        rr = 0.0
        target_space_atr = 0.0
        if structural_target is not None:
            target = float(structural_target)
            target_space = abs(target - last_close)
            target_space_atr = target_space / atr
            if stop_price is not None:
                risk = abs(last_close - float(stop_price))
                if risk > 0:
                    rr = target_space / risk

        scalp = False
        swing = False
        no_trade = False
        reasons = [f"CONTEXT_{context}"]

        if context == "TIGHT_TRADING_RANGE":
            no_trade = True
            reasons.extend(("TIGHT_RANGE", "INSUFFICIENT_MANAGEMENT_SPACE"))
            style = "NO_TRADE"
        elif context == "TRADING_RANGE":
            if range_width_atr < self.WIDE_RANGE_ATR:
                scalp = True
                style = "SCALP"
                reasons.append("SMALL_TO_MEDIUM_RANGE_FAVORS_SCALP")
            elif target_space_atr >= self.MIN_SWING_SPACE_ATR and (rr == 0.0 or rr >= self.MIN_SWING_RR):
                swing = True
                style = "SWING"
                reasons.append("WIDE_RANGE_SUPPORTS_SWING_PORTION")
            else:
                scalp = True
                style = "SCALP"
                reasons.append("WIDE_RANGE_WITHOUT_CONFIRMED_SWING_SPACE")
        else:
            if target_space_atr >= self.MIN_SWING_SPACE_ATR and (rr == 0.0 or rr >= self.MIN_SWING_RR):
                swing = True
                style = "SWING"
                reasons.extend(("DIRECTIONAL_CONTEXT", "STRUCTURAL_SPACE_SUPPORTS_SWING"))
            else:
                scalp = True
                style = "SCALP"
                reasons.append("TREND_BUT_LIMITED_CONFIRMED_TARGET_SPACE")

        # Investing is intentionally outside an intraday price-action engine.
        reasons.append("INVESTING_OUTSIDE_INTRADAY_SCOPE")

        if rr > 0 and rr < 1.0:
            reasons.append("LOW_REWARD_RISK_REQUIRES_HIGHER_WIN_RATE")

        return TradeStyleResult(
            valid=True,
            style=style,
            context=context,
            direction=direction,
            range_width_atr=round(range_width_atr, 3),
            directional_efficiency=round(efficiency, 3),
            reward_risk_estimate=round(rr, 3),
            target_space_atr=round(target_space_atr, 3),
            scalp_appropriate=scalp,
            swing_appropriate=swing,
            investing_applicable=False,
            no_trade=no_trade,
            reason=reasons[-1] if reasons else "",
            reasons=tuple(reasons),
        )

    @staticmethod
    def _two_sided(candles):
        bulls = sum(float(x.close) > float(x.open) for x in candles)
        bears = sum(float(x.close) < float(x.open) for x in candles)
        n = len(candles)
        return bulls >= max(3, int(n * 0.25)) and bears >= max(3, int(n * 0.25))

    @staticmethod
    def _overlap_ratio(candles):
        if len(candles) < 2:
            return 0.0
        overlaps = 0
        total = 0
        for a, b in zip(candles, candles[1:]):
            total += 1
            if min(float(a.high), float(b.high)) >= max(float(a.low), float(b.low)):
                overlaps += 1
        return overlaps / total if total else 0.0

    @staticmethod
    def _average_range(candles):
        if not candles:
            return 0.0
        return sum(max(float(x.high) - float(x.low), 0.0) for x in candles) / len(candles)
