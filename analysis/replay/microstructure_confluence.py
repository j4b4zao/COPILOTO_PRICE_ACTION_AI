"""Confluência observacional entre Times & Trades/Delta e Price Action.

O Book de ofertas real (profundidade bid/ask por níveis) ainda não possui fonte
no projeto. Por isso este módulo nunca simula depth: ele marca `book_available`
como False até existir um provider real e trabalha somente com evidências já
presentes no AnalysisContext.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class MicrostructureConfluenceSnapshot:
    price_action_bias: str = "NONE"
    order_flow_pressure: str = "INSUFFICIENT_DATA"
    flow_momentum: str = "INSUFFICIENT_DATA"
    pattern_direction: str = "NONE"
    structure_alignment: str = "UNAVAILABLE"
    structural_confidence: float = 0.0
    book_available: bool = False
    state: str = "INSUFFICIENT_DATA"
    direction: str = "NONE"
    confidence: float = 0.0
    duplicate_evidence_risk: bool = False
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class MicrostructureConfluenceAudit:
    """Sintetiza microestrutura sem escrever no score ou decisão."""

    VERSION = "RC1-MICROSTRUCTURE-CONFLUENCE-AUDIT"

    def analyze(self, context) -> MicrostructureConfluenceSnapshot:
        pa = getattr(context, "price_action", None)
        flow = getattr(context, "order_flow", None)

        pa_bias = str(getattr(pa, "bias", "NONE") or "NONE").upper()
        pressure = str(
            getattr(flow, "pressure", "INSUFFICIENT_DATA")
            or "INSUFFICIENT_DATA"
        ).upper()
        momentum = str(
            getattr(flow, "flow_momentum", "INSUFFICIENT_DATA")
            or "INSUFFICIENT_DATA"
        ).upper()
        pattern_direction = str(
            getattr(flow, "pattern_direction", "NONE") or "NONE"
        ).upper()
        structure_alignment = str(
            getattr(flow, "structure_alignment", "UNAVAILABLE") or "UNAVAILABLE"
        ).upper()
        structural_confidence = self._clamp(
            getattr(flow, "structural_pattern_confidence", 0.0)
        )

        flow_direction = self._flow_direction(pressure, momentum, pattern_direction)
        if pa_bias not in {"BUY", "SELL"} or flow_direction == "NONE":
            state = "INSUFFICIENT_DATA"
            direction = "NONE"
        elif pa_bias == flow_direction:
            state = "CONFIRMED"
            direction = pa_bias
        else:
            state = "CONFLICT"
            direction = flow_direction

        confidence = self._confidence(
            state=state,
            momentum=momentum,
            structure_alignment=structure_alignment,
            structural_confidence=structural_confidence,
        )

        duplicate_risk = self._duplicate_risk(
            pressure=pressure,
            momentum=momentum,
            pattern_direction=pattern_direction,
        )

        return MicrostructureConfluenceSnapshot(
            price_action_bias=pa_bias,
            order_flow_pressure=pressure,
            flow_momentum=momentum,
            pattern_direction=pattern_direction,
            structure_alignment=structure_alignment,
            structural_confidence=structural_confidence,
            book_available=False,
            state=state,
            direction=direction,
            confidence=confidence,
            duplicate_evidence_risk=duplicate_risk,
            passive_only=True,
        )

    @staticmethod
    def _flow_direction(pressure: str, momentum: str, pattern_direction: str) -> str:
        candidates = []
        if pressure in {"BUY", "SELL"}:
            candidates.append(pressure)
        if momentum.endswith("_BUY"):
            candidates.append("BUY")
        elif momentum.endswith("_SELL"):
            candidates.append("SELL")
        if pattern_direction in {"BUY", "SELL"}:
            candidates.append(pattern_direction)

        if not candidates:
            return "NONE"
        buy = candidates.count("BUY")
        sell = candidates.count("SELL")
        if buy == sell:
            return "NONE"
        return "BUY" if buy > sell else "SELL"

    @staticmethod
    def _duplicate_risk(*, pressure: str, momentum: str, pattern_direction: str) -> bool:
        """Marca quando várias leituras derivam do mesmo Delta/agressão."""
        derived = 0
        if pressure in {"BUY", "SELL"}:
            derived += 1
        if momentum not in {"INSUFFICIENT_DATA", "MIXED", ""}:
            derived += 1
        if pattern_direction in {"BUY", "SELL"}:
            derived += 1
        return derived >= 2

    @classmethod
    def _confidence(
        cls,
        *,
        state: str,
        momentum: str,
        structure_alignment: str,
        structural_confidence: float,
    ) -> float:
        if state == "INSUFFICIENT_DATA":
            return 0.0

        base = 0.50
        if momentum.startswith("ACCELERATING_"):
            base += 0.20
        elif momentum.startswith("PERSISTENT_"):
            base += 0.12
        elif momentum.startswith("FADING_"):
            base -= 0.10

        if structure_alignment == "ALIGNED":
            base += 0.20 * structural_confidence
        elif structure_alignment == "CONFLICT":
            base -= 0.20 * max(structural_confidence, 0.5)

        if state == "CONFLICT":
            base *= 0.85
        return round(min(max(base, 0.0), 1.0), 4)

    @staticmethod
    def _clamp(value) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(value, 0.0), 1.0), 4)
