"""Auditoria observacional de confluência Price Action + Delta + BookDepth.

A camada trata Order Flow/Delta como uma única família de evidência, mesmo que
pressure, momentum e pattern_direction concordem entre si. BookDepth só aumenta
a contagem de evidências independentes quando não estiver marcado como correlato
com Delta/Order Flow. Nenhum campo deste módulo altera Score ou Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class MicrostructureConfluenceSnapshot:
    price_action_bias: str = "NONE"
    order_flow_pressure: str = "INSUFFICIENT_DATA"
    flow_momentum: str = "INSUFFICIENT_DATA"
    pattern_direction: str = "NONE"
    flow_direction: str = "NONE"
    structure_alignment: str = "UNAVAILABLE"
    structural_confidence: float = 0.0
    book_available: bool = False
    book_pressure: str = "UNAVAILABLE"
    book_direction: str = "NONE"
    book_confidence: float = 0.0
    book_correlated_with_delta: bool = False
    state: str = "INSUFFICIENT_DATA"
    direction: str = "NONE"
    confidence: float = 0.0
    confluence_quality: str = "INSUFFICIENT_DATA"
    independent_evidence_count: int = 0
    correlated_evidence_count: int = 0
    conflict_count: int = 0
    duplicate_evidence_risk: bool = False
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class MicrostructureConfluenceAudit:
    """Sintetiza microestrutura sem escrever no score ou decisão."""

    VERSION = "RC2-INDEPENDENT-MICROSTRUCTURE-CONFLUENCE"

    def analyze(self, context) -> MicrostructureConfluenceSnapshot:
        pa = getattr(context, "price_action", None)
        flow = getattr(context, "order_flow", None)
        book = getattr(context, "book_depth_analysis", None)

        pa_bias = str(getattr(pa, "bias", "NONE") or "NONE").upper()
        pressure = str(
            getattr(flow, "pressure", "INSUFFICIENT_DATA") or "INSUFFICIENT_DATA"
        ).upper()
        momentum = str(
            getattr(flow, "flow_momentum", "INSUFFICIENT_DATA") or "INSUFFICIENT_DATA"
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

        book_available = bool(getattr(book, "valid", False))
        book_pressure = str(
            getattr(book, "pressure", "UNAVAILABLE") or "UNAVAILABLE"
        ).upper()
        book_direction = self._book_direction(
            book_pressure,
            str(getattr(book, "concentration_bias", "BALANCED") or "BALANCED").upper(),
        ) if book_available else "NONE"
        book_confidence = self._clamp(getattr(book, "confidence", 0.0)) if book_available else 0.0
        book_correlated = bool(
            getattr(book, "duplicate_evidence_risk", False)
        ) if book_available else False

        delta_duplicate = self._duplicate_risk(
            pressure=pressure,
            momentum=momentum,
            pattern_direction=pattern_direction,
        )

        independent_count, correlated_count, conflict_count = self._evidence_counts(
            pa_bias=pa_bias,
            flow_direction=flow_direction,
            book_direction=book_direction,
            book_correlated=book_correlated,
            delta_duplicate=delta_duplicate,
        )

        state, direction = self._state(
            pa_bias=pa_bias,
            flow_direction=flow_direction,
            book_direction=book_direction,
            conflict_count=conflict_count,
        )
        quality = self._quality(
            state=state,
            independent_count=independent_count,
            conflict_count=conflict_count,
        )
        confidence = self._confidence(
            state=state,
            momentum=momentum,
            structure_alignment=structure_alignment,
            structural_confidence=structural_confidence,
            book_direction=book_direction,
            pa_bias=pa_bias,
            book_confidence=book_confidence,
            book_correlated=book_correlated,
            conflict_count=conflict_count,
        )

        return MicrostructureConfluenceSnapshot(
            price_action_bias=pa_bias,
            order_flow_pressure=pressure,
            flow_momentum=momentum,
            pattern_direction=pattern_direction,
            flow_direction=flow_direction,
            structure_alignment=structure_alignment,
            structural_confidence=structural_confidence,
            book_available=book_available,
            book_pressure=book_pressure,
            book_direction=book_direction,
            book_confidence=book_confidence,
            book_correlated_with_delta=book_correlated,
            state=state,
            direction=direction,
            confidence=confidence,
            confluence_quality=quality,
            independent_evidence_count=independent_count,
            correlated_evidence_count=correlated_count,
            conflict_count=conflict_count,
            duplicate_evidence_risk=delta_duplicate or book_correlated,
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
    def _book_direction(pressure: str, concentration_bias: str) -> str:
        votes = []
        if pressure == "BID_DOMINANT":
            votes.append("BUY")
        elif pressure == "ASK_DOMINANT":
            votes.append("SELL")
        if concentration_bias == "BID_DOMINANT":
            votes.append("BUY")
        elif concentration_bias == "ASK_DOMINANT":
            votes.append("SELL")
        if not votes or votes.count("BUY") == votes.count("SELL"):
            return "NONE"
        return "BUY" if votes.count("BUY") > votes.count("SELL") else "SELL"

    @staticmethod
    def _duplicate_risk(*, pressure: str, momentum: str, pattern_direction: str) -> bool:
        derived = 0
        if pressure in {"BUY", "SELL"}:
            derived += 1
        if momentum not in {"INSUFFICIENT_DATA", "MIXED", ""}:
            derived += 1
        if pattern_direction in {"BUY", "SELL"}:
            derived += 1
        return derived >= 2

    @staticmethod
    def _evidence_counts(
        *, pa_bias, flow_direction, book_direction, book_correlated, delta_duplicate
    ) -> tuple[int, int, int]:
        if pa_bias not in {"BUY", "SELL"}:
            return 0, 0, 0

        independent = 1  # Price Action é a âncora independente.
        correlated = 0
        conflicts = 0

        if flow_direction in {"BUY", "SELL"}:
            if flow_direction == pa_bias:
                independent += 1  # família Order Flow conta somente uma vez.
                if delta_duplicate:
                    correlated += 1
            else:
                conflicts += 1

        if book_direction in {"BUY", "SELL"}:
            if book_direction == pa_bias:
                if book_correlated:
                    correlated += 1
                else:
                    independent += 1
            else:
                conflicts += 1

        return independent, correlated, conflicts

    @staticmethod
    def _state(*, pa_bias, flow_direction, book_direction, conflict_count):
        if pa_bias not in {"BUY", "SELL"}:
            return "INSUFFICIENT_DATA", "NONE"
        if conflict_count:
            opposing = [d for d in (flow_direction, book_direction) if d in {"BUY", "SELL"} and d != pa_bias]
            return "CONFLICT", opposing[0] if opposing else "NONE"
        if flow_direction == pa_bias or book_direction == pa_bias:
            return "CONFIRMED", pa_bias
        return "INSUFFICIENT_DATA", "NONE"

    @staticmethod
    def _quality(*, state: str, independent_count: int, conflict_count: int) -> str:
        if state == "INSUFFICIENT_DATA":
            return "INSUFFICIENT_DATA"
        if conflict_count:
            return "CONFLICT"
        if independent_count >= 3:
            return "HIGH"
        if independent_count == 2:
            return "MEDIUM"
        return "LOW"

    @classmethod
    def _confidence(
        cls,
        *,
        state,
        momentum,
        structure_alignment,
        structural_confidence,
        book_direction,
        pa_bias,
        book_confidence,
        book_correlated,
        conflict_count,
    ) -> float:
        if state == "INSUFFICIENT_DATA":
            return 0.0

        base = 0.45
        if momentum.startswith("ACCELERATING_"):
            base += 0.18
        elif momentum.startswith("PERSISTENT_"):
            base += 0.10
        elif momentum.startswith("FADING_"):
            base -= 0.08

        if structure_alignment == "ALIGNED":
            base += 0.15 * structural_confidence
        elif structure_alignment == "CONFLICT":
            base -= 0.15 * max(structural_confidence, 0.5)

        if book_direction == pa_bias:
            base += book_confidence * (0.07 if book_correlated else 0.20)
        elif book_direction in {"BUY", "SELL"}:
            base -= 0.18 * max(book_confidence, 0.5)

        if conflict_count:
            base *= 0.75
        return round(min(max(base, 0.0), 1.0), 4)

    @staticmethod
    def _clamp(value) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(value, 0.0), 1.0), 4)
