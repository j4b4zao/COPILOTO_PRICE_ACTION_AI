"""Política passiva de elegibilidade para confluência de microestrutura."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class MicrostructureEligibilityDecision:
    state: str = "NOT_ELIGIBLE"
    reason: str = "INSUFFICIENT_DATA"
    independent_evidence_count: int = 0
    confluence_quality: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    conflict_count: int = 0
    correlated_evidence_count: int = 0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class MicrostructureEligibilityPolicy:
    VERSION = "RC1-MICROSTRUCTURE-PASSIVE-ELIGIBILITY"
    MIN_CONFIDENCE_OBSERVABLE = 0.50
    MIN_CONFIDENCE_PROMISING = 0.65
    MIN_CONFIDENCE_STRONG = 0.75

    def evaluate(self, snapshot) -> MicrostructureEligibilityDecision:
        required = (
            "state",
            "confluence_quality",
            "confidence",
            "independent_evidence_count",
            "correlated_evidence_count",
            "conflict_count",
        )
        if not all(hasattr(snapshot, field) for field in required):
            raise TypeError("Snapshot de microestrutura inválido para elegibilidade.")

        state = str(snapshot.state).upper()
        quality = str(snapshot.confluence_quality).upper()
        confidence = self._clamp(snapshot.confidence)
        independent = int(snapshot.independent_evidence_count)
        correlated = int(snapshot.correlated_evidence_count)
        conflicts = int(snapshot.conflict_count)

        if state == "INSUFFICIENT_DATA" or independent <= 0:
            eligibility = "NOT_ELIGIBLE"
            reason = "INSUFFICIENT_DATA"
        elif conflicts > 0 or state == "CONFLICT":
            eligibility = "NOT_ELIGIBLE"
            reason = "CONFLICT_PRESENT"
        elif independent >= 3 and quality == "HIGH" and confidence >= self.MIN_CONFIDENCE_STRONG:
            eligibility = "STRONG_CANDIDATE"
            reason = "THREE_INDEPENDENT_HIGH_CONFIDENCE"
        elif independent >= 2 and quality in {"HIGH", "MEDIUM"} and confidence >= self.MIN_CONFIDENCE_PROMISING:
            eligibility = "PROMISING"
            reason = "MULTI_SOURCE_CONFLUENCE"
        elif independent >= 1 and confidence >= self.MIN_CONFIDENCE_OBSERVABLE:
            eligibility = "OBSERVABLE"
            reason = "MINIMUM_EVIDENCE_REACHED"
        else:
            eligibility = "NOT_ELIGIBLE"
            reason = "WEAK_OR_LOW_CONFIDENCE"

        if correlated > 0 and eligibility == "STRONG_CANDIDATE":
            eligibility = "PROMISING"
            reason = "CORRELATED_EVIDENCE_DISCOUNT"

        return MicrostructureEligibilityDecision(
            state=eligibility,
            reason=reason,
            independent_evidence_count=independent,
            confluence_quality=quality,
            confidence=confidence,
            conflict_count=conflicts,
            correlated_evidence_count=correlated,
            passive_only=True,
        )

    @staticmethod
    def _clamp(value) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(value, 0.0), 1.0), 4)
