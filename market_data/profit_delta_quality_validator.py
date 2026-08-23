"""Validador observacional da qualidade do Delta real vindo do Profit/Excel."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math


@dataclass(slots=True, frozen=True)
class ProfitDeltaQualityReport:
    status: str = "NO_DATA"
    sample_count: int = 0
    recent_delta: float = 0.0
    recent_total_aggression: float = 0.0
    dominance: float = 0.0
    persistence: float = 0.0
    acceleration: float = 0.0
    impulse_ratio: float = 0.0
    average_abs_delta: float = 0.0
    max_abs_delta: float = 0.0
    zero_delta_rate: float = 0.0
    anomaly_count: int = 0
    source_status: str = "NO_DATA"
    reasons: tuple[str, ...] = ()
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ProfitDeltaQualityValidator:
    """Classifica a confiabilidade estatística básica do Delta recebido."""

    VERSION = "RC1-PROFIT-DELTA-QUALITY"
    MIN_SAMPLES = 6
    MIN_ACTIVITY = 1.0
    MAX_ZERO_RATE = 0.80
    MAX_SINGLE_SAMPLE_SHARE = 0.95

    def evaluate(self, order_flow, source_snapshot=None) -> ProfitDeltaQualityReport:
        history = tuple(getattr(order_flow, "history", ()) or ())
        aggression_history = tuple(getattr(order_flow, "aggression_history", ()) or ())
        sample_count = len(history)
        source_status = str(getattr(source_snapshot, "status", "NO_DATA") or "NO_DATA")
        reasons: list[str] = []
        anomaly_count = 0

        if source_status in {"AGGRESSION_UNAVAILABLE", "DEGRADED"}:
            reasons.append(f"SOURCE_{source_status}")

        if sample_count == 0:
            return ProfitDeltaQualityReport(
                status="NO_DATA",
                source_status=source_status,
                reasons=tuple(reasons or ["NO_ORDER_FLOW_SAMPLES"]),
            )

        finite_history = [float(value) for value in history if math.isfinite(float(value))]
        if len(finite_history) != sample_count:
            anomaly_count += sample_count - len(finite_history)
            reasons.append("NON_FINITE_DELTA")

        abs_values = [abs(value) for value in finite_history]
        average_abs_delta = sum(abs_values) / len(abs_values) if abs_values else 0.0
        max_abs_delta = max(abs_values) if abs_values else 0.0
        zero_delta_rate = (
            sum(value == 0 for value in finite_history) / len(finite_history)
            if finite_history else 1.0
        )

        total_abs = sum(abs_values)
        if total_abs > 0 and max_abs_delta / total_abs >= self.MAX_SINGLE_SAMPLE_SHARE and sample_count >= self.MIN_SAMPLES:
            anomaly_count += 1
            reasons.append("SINGLE_SAMPLE_DOMINANCE")

        if zero_delta_rate >= self.MAX_ZERO_RATE and sample_count >= self.MIN_SAMPLES:
            anomaly_count += 1
            reasons.append("EXCESSIVE_ZERO_DELTA")

        recent_total_aggression = float(getattr(order_flow, "recent_total_aggression", 0.0) or 0.0)
        if sample_count >= self.MIN_SAMPLES and recent_total_aggression < self.MIN_ACTIVITY:
            reasons.append("LOW_RECENT_ACTIVITY")

        if sample_count < self.MIN_SAMPLES:
            status = "INITIALIZING"
            reasons.append("INSUFFICIENT_SAMPLES")
        elif source_status in {"AGGRESSION_UNAVAILABLE", "DEGRADED"} or anomaly_count > 0:
            status = "DEGRADED"
        elif recent_total_aggression < self.MIN_ACTIVITY:
            status = "LOW_ACTIVITY"
        else:
            status = "VALID"

        return ProfitDeltaQualityReport(
            status=status,
            sample_count=sample_count,
            recent_delta=round(float(getattr(order_flow, "recent_delta", 0.0) or 0.0), 4),
            recent_total_aggression=round(recent_total_aggression, 4),
            dominance=round(float(getattr(order_flow, "recent_delta_dominance", 0.0) or 0.0), 4),
            persistence=round(float(getattr(order_flow, "delta_persistence", 0.0) or 0.0), 4),
            acceleration=round(float(getattr(order_flow, "delta_acceleration", 0.0) or 0.0), 4),
            impulse_ratio=round(float(getattr(order_flow, "delta_impulse_ratio", 0.0) or 0.0), 4),
            average_abs_delta=round(average_abs_delta, 4),
            max_abs_delta=round(max_abs_delta, 4),
            zero_delta_rate=round(zero_delta_rate, 4),
            anomaly_count=anomaly_count,
            source_status=source_status,
            reasons=tuple(dict.fromkeys(reasons)),
            passive_only=True,
        )
