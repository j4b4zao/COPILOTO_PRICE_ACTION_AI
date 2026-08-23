"""A/B passivo para evidência Absorção/Exaustão × Estrutura."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreOrderFlowStructureABSample:
    baseline_total: float = 0.0
    adjusted_total: float = 0.0
    delta: float = 0.0
    baseline_grade: str = "REPROVADO"
    adjusted_grade: str = "REPROVADO"
    grade_changed: bool = False
    baseline_valid: bool = False
    adjusted_valid: bool = False
    validity_changed: bool = False
    bias: str = "NONE"
    pattern_direction: str = "NONE"
    structure_alignment: str = "UNAVAILABLE"
    structural_confidence: float = 0.0
    adjustment: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreOrderFlowStructureABRecorder:
    """Mede efeito hipotético do padrão estrutural sem alterar o ciclo oficial."""

    VERSION = "RC1-ORDER-FLOW-STRUCTURE-SCORE-AB"
    MAX_WEIGHT = 1.5
    CONFLICT_FACTOR = 0.75
    NEUTRAL_FACTOR = 0.25

    def __init__(self, weight: float = 1.5, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B estrutural de Order Flow deve ficar entre 0 e 1.5.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreOrderFlowStructureABSample] = []

    @property
    def samples(self) -> tuple[ScoreOrderFlowStructureABSample, ...]:
        return tuple(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def record(self, context) -> ScoreOrderFlowStructureABSample:
        score = context.score
        checklist = context.checklist

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()
        pattern_direction = str(
            getattr(checklist, "order_flow_pattern_direction", "NONE") or "NONE"
        ).upper()
        alignment = str(
            getattr(checklist, "order_flow_structure_alignment", "UNAVAILABLE")
            or "UNAVAILABLE"
        ).upper()
        confidence = self._clamp(
            getattr(checklist, "order_flow_structural_confidence", 0.0)
        )

        adjustment = self._adjustment(
            bias=bias,
            pattern_direction=pattern_direction,
            alignment=alignment,
            confidence=confidence,
        )
        adjusted_total = round(min(max(baseline_total + adjustment, 0.0), 100.0), 2)
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreOrderFlowStructureABSample(
            baseline_total=round(baseline_total, 2),
            adjusted_total=adjusted_total,
            delta=round(adjusted_total - baseline_total, 2),
            baseline_grade=baseline_grade,
            adjusted_grade=adjusted_grade,
            grade_changed=baseline_grade != adjusted_grade,
            baseline_valid=baseline_valid,
            adjusted_valid=adjusted_valid,
            validity_changed=baseline_valid != adjusted_valid,
            bias=bias,
            pattern_direction=pattern_direction,
            structure_alignment=alignment,
            structural_confidence=confidence,
            adjustment=round(adjustment, 2),
            passive_only=True,
        )

        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]
        return sample

    def summary(self) -> dict:
        total = len(self._samples)
        positive = sum(s.delta > 0 for s in self._samples)
        negative = sum(s.delta < 0 for s in self._samples)
        neutral = total - positive - negative
        average_delta = (
            round(sum(s.delta for s in self._samples) / total, 4)
            if total else 0.0
        )
        return {
            "version": self.VERSION,
            "samples": total,
            "positive_adjustments": positive,
            "negative_adjustments": negative,
            "neutral_adjustments": neutral,
            "grade_changes": sum(s.grade_changed for s in self._samples),
            "validity_changes": sum(s.validity_changed for s in self._samples),
            "average_delta": average_delta,
            "weight": self.weight,
        }

    def _adjustment(self, *, bias, pattern_direction, alignment, confidence) -> float:
        if pattern_direction not in ("BUY", "SELL") or confidence <= 0.0:
            return 0.0

        same_bias = bias == pattern_direction
        if alignment == "ALIGNED":
            sign = 1.0 if same_bias else -1.0
            return sign * self.weight * confidence
        if alignment == "CONFLICT":
            sign = -1.0 if same_bias else 1.0
            return sign * self.weight * self.CONFLICT_FACTOR * confidence
        if alignment == "NEUTRAL":
            sign = 1.0 if same_bias else -1.0
            return sign * self.weight * self.NEUTRAL_FACTOR * confidence
        return 0.0

    @staticmethod
    def _clamp(value) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(value, 0.0), 1.0), 4)

    @staticmethod
    def _grade(total: float) -> str:
        if total >= 90.0:
            return "A+"
        if total >= 80.0:
            return "A"
        if total >= 70.0:
            return "B"
        if total >= 60.0:
            return "C"
        return "REPROVADO"
