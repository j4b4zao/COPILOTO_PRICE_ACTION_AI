"""
analysis/price_action/best_trade_dynamics.py

Brooks Reversals - Chapter 24:
The Best Trades: Putting It All Together.

Diagnostic-only layer. It does not alter Score, Risk, Decision or execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class BestTradeResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    aligned_signals: int = 0
    conflicting_signals: int = 0
    neutral_signals: int = 0
    setup_quality: float = 0.0
    context_quality: float = 0.0
    risk_reward: float = 0.0
    confirmation_present: bool = False
    structure_present: bool = False
    higher_timeframe_aligned: bool = False
    clean_context: bool = False
    beginner_friendly: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class BestTradeDynamics:
    """Rank opportunity quality from already-produced diagnostics."""

    VALID_DIRECTIONS = {"BUY", "SELL", "NONE"}

    def analyze(
        self,
        diagnostics=None,
        *,
        setup_quality=0.0,
        context_quality=0.0,
        risk_reward=0.0,
        confirmation_present=False,
        structure_present=False,
        higher_timeframe_direction="NONE",
    ):
        items = list(diagnostics or [])
        directions = [self._direction(item) for item in items]

        buys = directions.count("BUY")
        sells = directions.count("SELL")
        neutral = directions.count("NONE")

        if buys > sells:
            direction = "BUY"
            aligned = buys
            conflicts = sells
        elif sells > buys:
            direction = "SELL"
            aligned = sells
            conflicts = buys
        else:
            direction = "NONE"
            aligned = buys if buys == sells else 0
            conflicts = min(buys, sells)

        sq = self._clamp(setup_quality)
        cq = self._clamp(context_quality)
        rr = max(float(risk_reward or 0.0), 0.0)

        higher = str(higher_timeframe_direction or "NONE").upper()
        if higher not in self.VALID_DIRECTIONS:
            higher = "NONE"

        higher_aligned = direction in ("BUY", "SELL") and higher == direction
        clean_context = direction in ("BUY", "SELL") and conflicts == 0

        result = BestTradeResult(
            valid=True,
            direction=direction,
            aligned_signals=aligned,
            conflicting_signals=conflicts,
            neutral_signals=neutral,
            setup_quality=sq,
            context_quality=cq,
            risk_reward=rr,
            confirmation_present=bool(confirmation_present),
            structure_present=bool(structure_present),
            higher_timeframe_aligned=higher_aligned,
            clean_context=clean_context,
        )

        if direction == "NONE" or aligned == 0:
            result.status = "NO_TRADE_CONTEXT"
            result.quality_score = 20.0
            result.reasons = ("NO_CLEAR_DIRECTIONAL_EDGE",)
            return result

        score = 0.0
        score += min(aligned * 12.0, 36.0)
        score += sq * 0.20
        score += cq * 0.15
        score += 10.0 if confirmation_present else 0.0
        score += 8.0 if structure_present else 0.0
        score += 6.0 if higher_aligned else 0.0
        score += min(rr, 3.0) / 3.0 * 15.0
        score -= conflicts * 18.0

        result.quality_score = round(max(0.0, min(score, 100.0)), 2)
        result.beginner_friendly = (
            clean_context
            and confirmation_present
            and structure_present
            and rr >= 1.5
            and result.quality_score >= 80.0
        )

        reasons = []
        if clean_context:
            reasons.append("NO_DIRECTIONAL_CONFLICT")
        if confirmation_present:
            reasons.append("CONFIRMATION_PRESENT")
        if structure_present:
            reasons.append("STRUCTURE_PRESENT")
        if higher_aligned:
            reasons.append("HIGHER_TIMEFRAME_ALIGNED")
        if rr >= 2.0:
            reasons.append("FAVORABLE_RISK_REWARD")
        elif rr < 1.0:
            reasons.append("POOR_RISK_REWARD")
        if conflicts:
            reasons.append("CONFLICTING_DIAGNOSTICS")

        if conflicts >= 2 or (conflicts and result.quality_score < 60.0):
            result.status = "CONFLICTED_TRADE"
        elif result.quality_score >= 90.0 and result.beginner_friendly:
            result.status = "BEST_TRADE_A_PLUS"
        elif result.quality_score >= 80.0:
            result.status = "HIGH_QUALITY_TRADE"
        elif result.quality_score >= 60.0:
            result.status = "SELECTIVE_TRADE"
        else:
            result.status = "NO_TRADE_CONTEXT"

        reasons.insert(0, result.status)
        result.reasons = tuple(reasons)
        return result

    @classmethod
    def _direction(cls, value):
        if value is None:
            return "NONE"
        if isinstance(value, str):
            direction = value.upper()
        elif isinstance(value, dict):
            direction = str(
                value.get("direction", value.get("bias", value.get("signal", "NONE")))
            ).upper()
        else:
            direction = str(
                getattr(
                    value,
                    "direction",
                    getattr(value, "bias", getattr(value, "signal", "NONE")),
                )
            ).upper()
        return direction if direction in cls.VALID_DIRECTIONS else "NONE"

    @staticmethod
    def _clamp(value):
        try:
            number = float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(number, 100.0))
