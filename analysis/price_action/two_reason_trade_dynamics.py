"""
analysis/price_action/two_reason_trade_dynamics.py

Brooks Trading Ranges - Chapter 26:
You Need Two Reasons to Take a Trade.

Diagnostic-only layer. It does not authorize trades and does not mutate
Score/Risk/Decision.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TwoReasonTradeResult:
    valid: bool = False
    direction: str = "NONE"
    reason_count: int = 0
    independent_reason_count: int = 0
    reasons_found: tuple[str, ...] = ()
    duplicate_categories: tuple[str, ...] = ()
    two_reason_rule_met: bool = False
    countertrend_blocked: bool = False
    structural_reversal_required: bool = False
    setup_state: str = "NO_SETUP"
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self):
        return asdict(self)


class TwoReasonTradeDynamics:
    """Require at least two independent, directionally aligned trade reasons."""

    MIN_REASONS = 2

    # Reasons in the same category are not double-counted as independent evidence.
    REASON_CATEGORIES = {
        "BOS": "STRUCTURE",
        "CHOCH": "STRUCTURE",
        "TREND_ALIGNMENT": "STRUCTURE",
        "TRENDLINE_BREAK": "STRUCTURE",
        "CHANNEL_OVERSHOOT": "STRUCTURE",
        "H1": "BAR_COUNT",
        "H2": "BAR_COUNT",
        "H3": "BAR_COUNT",
        "H4": "BAR_COUNT",
        "L1": "BAR_COUNT",
        "L2": "BAR_COUNT",
        "L3": "BAR_COUNT",
        "L4": "BAR_COUNT",
        "WEDGE": "PATTERN",
        "DOUBLE_BOTTOM": "PATTERN",
        "DOUBLE_TOP": "PATTERN",
        "REVERSAL_BAR": "PATTERN",
        "BREAKOUT_PULLBACK": "PATTERN",
        "LIQUIDITY_SWEEP": "LIQUIDITY",
        "ORDER_BLOCK": "LOCATION",
        "FVG": "LOCATION",
        "SUPPORT": "LOCATION",
        "RESISTANCE": "LOCATION",
        "MOVING_AVERAGE": "LOCATION",
        "MEASURED_MOVE": "TARGET_CONTEXT",
        "FAILED_BREAKOUT": "FAILURE",
        "FAILED_REVERSAL": "FAILURE",
        "FOLLOW_THROUGH": "CONFIRMATION",
        "STRONG_SIGNAL_BAR": "CONFIRMATION",
        "VOLUME_CONFIRMATION": "CONFIRMATION",
    }

    def analyze(
        self,
        direction,
        reasons,
        market_trend="NONE",
        steep_trend=False,
        trendline_break=False,
        channel_overshoot=False,
        reversal_confirmation=False,
    ):
        direction = str(direction).upper()
        market_trend = str(market_trend).upper()

        if direction not in ("BUY", "SELL"):
            return TwoReasonTradeResult(reason="INVALID_DIRECTION")

        normalized = self._normalize_reasons(reasons)
        if not normalized:
            return TwoReasonTradeResult(
                direction=direction,
                reason="NO_REASONS",
            )

        categories = {}
        duplicates = set()
        for item in normalized:
            category = self.REASON_CATEGORIES.get(item, item)
            if category in categories:
                duplicates.add(category)
            else:
                categories[category] = item

        independent = tuple(categories.values())
        independent_count = len(independent)
        rule_met = independent_count >= self.MIN_REASONS

        countertrend = (
            (market_trend in ("UP", "BUY", "BULL") and direction == "SELL")
            or (market_trend in ("DOWN", "SELL", "BEAR") and direction == "BUY")
        )

        structural_reversal_required = bool(steep_trend and countertrend)
        structural_break = bool(trendline_break or channel_overshoot)
        countertrend_blocked = bool(
            structural_reversal_required
            and not (structural_break and reversal_confirmation)
        )

        if countertrend_blocked:
            state = "COUNTERTREND_BLOCKED"
        elif rule_met:
            state = "TWO_REASONS_CONFIRMED"
        elif independent_count == 1:
            state = "ONE_REASON_ONLY"
        else:
            state = "NO_SETUP"

        confidence = min(independent_count / 4.0, 1.0)
        if countertrend_blocked:
            confidence = 0.0

        reason = (
            "STEEP_TREND_REQUIRES_STRUCTURAL_REVERSAL"
            if countertrend_blocked
            else "TWO_INDEPENDENT_REASONS_PRESENT"
            if rule_met
            else "SECOND_INDEPENDENT_REASON_REQUIRED"
        )

        return TwoReasonTradeResult(
            valid=True,
            direction=direction,
            reason_count=len(normalized),
            independent_reason_count=independent_count,
            reasons_found=independent,
            duplicate_categories=tuple(sorted(duplicates)),
            two_reason_rule_met=bool(rule_met and not countertrend_blocked),
            countertrend_blocked=countertrend_blocked,
            structural_reversal_required=structural_reversal_required,
            setup_state=state,
            confidence=round(confidence, 3),
            reason=reason,
        )

    @staticmethod
    def _normalize_reasons(reasons):
        if reasons is None:
            return ()
        if isinstance(reasons, str):
            reasons = [reasons]
        seen = []
        for reason in reasons:
            value = str(reason).strip().upper().replace(" ", "_")
            if value and value not in seen:
                seen.append(value)
        return tuple(seen)
