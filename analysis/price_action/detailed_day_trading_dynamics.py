"""
analysis/price_action/detailed_day_trading_dynamics.py

Brooks Reversals - Chapter 21:
Detailed Day Trading Examples.

This is a synthesis layer: it combines already-produced diagnostic results
without replacing Score, Risk, Decision or execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class DetailedDayTradingResult:
    valid: bool = False
    status: str = "UNKNOWN"
    direction: str = "NONE"
    aligned_components: int = 0
    conflicting_components: int = 0
    neutral_components: int = 0
    strong_context: bool = False
    conflict_risk: bool = False
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class DetailedDayTradingDynamics:
    """Synthesize independent price-action diagnostics into one context view."""

    def analyze(self, components):
        items = list(components or [])
        if not items:
            return DetailedDayTradingResult(reasons=("NO_COMPONENTS",))

        buy = sell = neutral = 0
        weighted_buy = weighted_sell = 0.0
        reasons = []

        for item in items:
            direction = self._direction(item)
            weight = self._weight(item)
            name = type(item).__name__

            if direction == "BUY":
                buy += 1
                weighted_buy += weight
                reasons.append(f"{name}_BUY")
            elif direction == "SELL":
                sell += 1
                weighted_sell += weight
                reasons.append(f"{name}_SELL")
            else:
                neutral += 1
                reasons.append(f"{name}_NEUTRAL")

        if weighted_buy > weighted_sell:
            direction = "BUY"
            aligned = buy
            conflicts = sell
        elif weighted_sell > weighted_buy:
            direction = "SELL"
            aligned = sell
            conflicts = buy
        else:
            direction = "NONE"
            aligned = 0
            conflicts = buy + sell

        directional_total = buy + sell
        if directional_total == 0:
            return DetailedDayTradingResult(
                valid=True,
                status="DAY_TRADE_CONTEXT_NEUTRAL",
                neutral_components=neutral,
                quality_score=25.0,
                reasons=tuple(reasons + ["NO_DIRECTIONAL_CONFLUENCE"]),
            )

        agreement = aligned / directional_total if directional_total else 0.0
        conflict_risk = conflicts > 0
        strong_context = aligned >= 3 and agreement >= 0.70

        score = 35.0 + aligned * 12.0 - conflicts * 15.0
        if strong_context:
            score += 15.0
        score = min(max(score, 0.0), 100.0)

        if direction == "NONE" or agreement < 0.55:
            status = "DAY_TRADE_CONTEXT_CONFLICT"
        elif strong_context and not conflict_risk:
            status = "DAY_TRADE_CONTEXT_STRONG_ALIGNMENT"
        elif strong_context:
            status = "DAY_TRADE_CONTEXT_ALIGNED_WITH_CONFLICT"
        elif conflicts:
            status = "DAY_TRADE_CONTEXT_MIXED"
        else:
            status = "DAY_TRADE_CONTEXT_PARTIAL_ALIGNMENT"

        reasons.extend([
            status,
            f"ALIGNED_{aligned}",
            f"CONFLICTS_{conflicts}",
            f"NEUTRAL_{neutral}",
        ])

        return DetailedDayTradingResult(
            valid=True,
            status=status,
            direction=direction,
            aligned_components=aligned,
            conflicting_components=conflicts,
            neutral_components=neutral,
            strong_context=strong_context,
            conflict_risk=conflict_risk,
            quality_score=round(score, 1),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _direction(item):
        if item is None:
            return "NONE"
        if isinstance(item, dict):
            value = item.get("direction") or item.get("bias") or item.get("signal")
        else:
            value = (
                getattr(item, "direction", None)
                or getattr(item, "bias", None)
                or getattr(item, "signal", None)
            )

        if hasattr(value, "name"):
            value = value.name

        text = str(value or "").upper()
        if text in {"BUY", "LONG", "UP", "BULL", "BULLISH"}:
            return "BUY"
        if text in {"SELL", "SHORT", "DOWN", "BEAR", "BEARISH"}:
            return "SELL"
        return "NONE"

    @staticmethod
    def _weight(item):
        if item is None:
            return 0.0
        if isinstance(item, dict):
            score = item.get("quality_score", item.get("score", 50.0))
            valid = item.get("valid", True)
        else:
            score = getattr(item, "quality_score", getattr(item, "score", 50.0))
            valid = getattr(item, "valid", True)

        if not valid:
            return 0.0
        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 50.0
        return min(max(score, 0.0), 100.0) / 100.0
