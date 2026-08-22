"""
analysis/price_action/higher_timeframe_context_dynamics.py

Brooks Reversals - Chapter 22:
Daily, Weekly and Monthly Charts.

Diagnostic-only layer. It does not alter Score, Risk, Decision or execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class HigherTimeframeContextResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    daily_direction: str = "NONE"
    weekly_direction: str = "NONE"
    monthly_direction: str = "NONE"
    daily_strength: float = 0.0
    weekly_strength: float = 0.0
    monthly_strength: float = 0.0
    alignment_count: int = 0
    conflict_count: int = 0
    higher_timeframe_bias: str = "NONE"
    execution_allowed: bool = True
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class HigherTimeframeContextDynamics:
    """Synthesize D1/W1/MN1 context without turning it into an entry signal."""

    VALID = {"BUY", "SELL", "NONE"}

    def analyze(self, *, daily=None, weekly=None, monthly=None):
        d_dir, d_str = self._extract(daily)
        w_dir, w_str = self._extract(weekly)
        m_dir, m_str = self._extract(monthly)

        directions = [d_dir, w_dir, m_dir]
        directional = [d for d in directions if d in ("BUY", "SELL")]

        if not directional:
            return HigherTimeframeContextResult(
                valid=True,
                status="HIGHER_TIMEFRAME_NEUTRAL",
                daily_direction=d_dir,
                weekly_direction=w_dir,
                monthly_direction=m_dir,
                daily_strength=d_str,
                weekly_strength=w_str,
                monthly_strength=m_str,
                higher_timeframe_bias="NONE",
                quality_score=35.0,
                reasons=("NO_DIRECTIONAL_HIGHER_TIMEFRAME_BIAS",),
            )

        buy_count = directional.count("BUY")
        sell_count = directional.count("SELL")
        bias = "BUY" if buy_count > sell_count else "SELL" if sell_count > buy_count else "NONE"
        alignment_count = max(buy_count, sell_count)
        conflict_count = min(buy_count, sell_count)

        result = HigherTimeframeContextResult(
            valid=True,
            daily_direction=d_dir,
            weekly_direction=w_dir,
            monthly_direction=m_dir,
            daily_strength=d_str,
            weekly_strength=w_str,
            monthly_strength=m_str,
            alignment_count=alignment_count,
            conflict_count=conflict_count,
            higher_timeframe_bias=bias,
            direction=bias,
        )

        if buy_count == 3 or sell_count == 3:
            result.status = "HIGHER_TIMEFRAME_FULL_ALIGNMENT"
            result.quality_score = 95.0
            result.reasons = ("D1_W1_MN1_ALIGNED",)
        elif alignment_count == 2 and conflict_count == 0:
            result.status = "HIGHER_TIMEFRAME_PARTIAL_ALIGNMENT"
            result.quality_score = 78.0
            result.reasons = ("TWO_HIGHER_TIMEFRAMES_ALIGNED",)
        elif alignment_count == 2 and conflict_count == 1:
            result.status = "HIGHER_TIMEFRAME_MIXED"
            result.quality_score = 58.0
            result.reasons = ("HIGHER_TIMEFRAME_DIRECTION_CONFLICT",)
        elif alignment_count == 1 and conflict_count == 0:
            result.status = "HIGHER_TIMEFRAME_SINGLE_CONTEXT"
            result.quality_score = 50.0
            result.reasons = ("ONLY_ONE_DIRECTIONAL_HIGHER_TIMEFRAME",)
        else:
            result.status = "HIGHER_TIMEFRAME_CONFLICT"
            result.direction = "NONE"
            result.higher_timeframe_bias = "NONE"
            result.quality_score = 42.0
            result.reasons = ("NO_CLEAR_HIGHER_TIMEFRAME_MAJORITY",)

        # Higher timeframe context can filter confidence, but never forces an entry.
        result.execution_allowed = True
        return result

    @classmethod
    def _extract(cls, value):
        if value is None:
            return "NONE", 0.0
        if isinstance(value, str):
            direction = value.upper()
            return (direction if direction in cls.VALID else "NONE"), 0.0
        if isinstance(value, dict):
            direction = str(value.get("direction", "NONE")).upper()
            strength = float(value.get("strength", value.get("quality_score", 0.0)) or 0.0)
            return (direction if direction in cls.VALID else "NONE"), strength
        direction = str(getattr(value, "direction", "NONE")).upper()
        strength = float(getattr(value, "strength", getattr(value, "quality_score", 0.0)) or 0.0)
        return (direction if direction in cls.VALID else "NONE"), strength
