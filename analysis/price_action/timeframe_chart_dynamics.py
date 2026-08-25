"""
analysis/price_action/timeframe_chart_dynamics.py

Brooks Reversals - Chapter 13: Time Frames and Chart Types.
Diagnostic-only layer for multi-timeframe context and chart-type suitability.

Design goal for the Copiloto:
    M15 -> context
    M5  -> primary execution/setup timeframe
    M1  -> optional entry refinement

This module does not alter Score, Risk, Decision or order execution.
"""

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class TimeframeChartResult:
    valid: bool = False
    status: str = "UNKNOWN"
    context_timeframe: str = "M15"
    execution_timeframe: str = "M5"
    refinement_timeframe: str = "M1"
    context_bias: str = "NONE"
    execution_bias: str = "NONE"
    refinement_bias: str = "NONE"
    aligned: bool = False
    context_execution_aligned: bool = False
    lower_timeframe_confirms: bool = False
    lower_timeframe_conflict: bool = False
    refinement_allowed: bool = False
    chart_type: str = "CANDLE"
    chart_type_supported: bool = True
    quality_score: float = 0.0
    reasons: tuple[str, ...] = ()

    def to_dict(self):
        return asdict(self)


class TimeframeChartDynamics:
    """Evaluate MTF agreement while keeping M5 as the operational anchor."""

    SUPPORTED_CHART_TYPES = {
        "CANDLE",
        "BAR",
        "OHLC",
        "VOLUME",
        "TICK",
        "RENKO",
    }

    def analyze(
        self,
        signals,
        *,
        chart_type="CANDLE",
        context_timeframe="M15",
        execution_timeframe="M5",
        refinement_timeframe="M1",
    ):
        signals = signals or {}

        context_tf = str(context_timeframe).upper()
        execution_tf = str(execution_timeframe).upper()
        refinement_tf = str(refinement_timeframe).upper()
        ctype = str(chart_type or "CANDLE").upper()

        context_bias = self._normalize_bias(signals.get(context_tf))
        execution_bias = self._normalize_bias(signals.get(execution_tf))
        refinement_bias = self._normalize_bias(signals.get(refinement_tf))

        if context_bias == "NONE" and execution_bias == "NONE":
            return TimeframeChartResult(
                context_timeframe=context_tf,
                execution_timeframe=execution_tf,
                refinement_timeframe=refinement_tf,
                context_bias=context_bias,
                execution_bias=execution_bias,
                refinement_bias=refinement_bias,
                chart_type=ctype,
                chart_type_supported=ctype in self.SUPPORTED_CHART_TYPES,
                reasons=("INSUFFICIENT_DIRECTIONAL_CONTEXT",),
            )

        chart_supported = ctype in self.SUPPORTED_CHART_TYPES

        context_execution_aligned = (
            context_bias in {"BUY", "SELL"}
            and execution_bias == context_bias
        )

        lower_confirms = (
            execution_bias in {"BUY", "SELL"}
            and refinement_bias == execution_bias
        )

        lower_conflict = (
            execution_bias in {"BUY", "SELL"}
            and refinement_bias in {"BUY", "SELL"}
            and refinement_bias != execution_bias
        )

        aligned = context_execution_aligned and (
            refinement_bias == "NONE" or lower_confirms
        )

        # M1 refines an existing M5 thesis. It must not create an opposite
        # thesis by itself when M15/M5 already agree.
        refinement_allowed = (
            execution_bias in {"BUY", "SELL"}
            and not lower_conflict
        )

        score = 0.0

        if execution_bias in {"BUY", "SELL"}:
            score += 35.0

        if context_execution_aligned:
            score += 35.0
        elif context_bias == "NONE":
            score += 10.0

        if lower_confirms:
            score += 20.0
        elif refinement_bias == "NONE":
            score += 10.0
        elif lower_conflict:
            score -= 15.0

        if chart_supported:
            score += 10.0

        score = min(max(score, 0.0), 100.0)

        if context_execution_aligned and lower_conflict:
            status = "MTF_ALIGNED_M1_CONFLICT"
        elif aligned:
            status = "MTF_FULL_ALIGNMENT"
        elif context_execution_aligned:
            status = "MTF_CONTEXT_EXECUTION_ALIGNED"
        elif execution_bias in {"BUY", "SELL"} and context_bias in {"BUY", "SELL"}:
            status = "MTF_CONTEXT_CONFLICT"
        else:
            status = "MTF_PARTIAL_CONTEXT"

        reasons = [
            f"CONTEXT_{context_tf}_{context_bias}",
            f"EXECUTION_{execution_tf}_{execution_bias}",
            f"REFINEMENT_{refinement_tf}_{refinement_bias}",
        ]

        if context_execution_aligned:
            reasons.append("HIGHER_AND_EXECUTION_TIMEFRAME_ALIGNED")
        else:
            reasons.append("HIGHER_AND_EXECUTION_TIMEFRAME_NOT_ALIGNED")

        if lower_confirms:
            reasons.append("LOWER_TIMEFRAME_ENTRY_REFINEMENT_CONFIRMS")
        elif lower_conflict:
            reasons.append("LOWER_TIMEFRAME_CONFLICT_DO_NOT_OVERRIDE_M5_M15")
        else:
            reasons.append("LOWER_TIMEFRAME_OPTIONAL")

        if chart_supported:
            reasons.append("CHART_TYPE_ACCEPTABLE_IF_READ_CONSISTENTLY")
        else:
            reasons.append("UNKNOWN_CHART_TYPE")

        return TimeframeChartResult(
            valid=True,
            status=status,
            context_timeframe=context_tf,
            execution_timeframe=execution_tf,
            refinement_timeframe=refinement_tf,
            context_bias=context_bias,
            execution_bias=execution_bias,
            refinement_bias=refinement_bias,
            aligned=aligned,
            context_execution_aligned=context_execution_aligned,
            lower_timeframe_confirms=lower_confirms,
            lower_timeframe_conflict=lower_conflict,
            refinement_allowed=refinement_allowed,
            chart_type=ctype,
            chart_type_supported=chart_supported,
            quality_score=round(score, 1),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _normalize_bias(value):
        if value is None:
            return "NONE"

        if isinstance(value, dict):
            value = (
                value.get("bias")
                or value.get("direction")
                or value.get("signal")
                or value.get("trend")
            )

        if hasattr(value, "name"):
            value = value.name

        text = str(value).upper().strip()

        if text in {"BUY", "UP", "BULL", "BULLISH", "COMPRA", "LONG"}:
            return "BUY"

        if text in {"SELL", "DOWN", "BEAR", "BEARISH", "VENDA", "SHORT"}:
            return "SELL"

        return "NONE"
