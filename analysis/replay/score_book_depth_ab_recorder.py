"""A/B passivo do impacto hipotético de BookDepth no Score oficial."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreBookDepthABSample:
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
    status: str = "UNAVAILABLE"
    pressure: str = "UNAVAILABLE"
    confidence: float = 0.0
    duplicate_evidence_risk: bool = False
    correlation_factor: float = 1.0
    effective_strength: float = 0.0
    adjustment: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreBookDepthABRecorder:
    """Mede efeito hipotético do Book sem alterar contexto oficial."""

    VERSION = "RC1-BOOK-DEPTH-SCORE-AB"
    MAX_WEIGHT = 1.0
    DUPLICATE_FACTOR = 0.35

    def __init__(self, weight: float = 1.0, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B de BookDepth deve ficar entre 0 e 1.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreBookDepthABSample] = []

    @property
    def samples(self) -> tuple[ScoreBookDepthABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def record(self, context) -> ScoreBookDepthABSample:
        score = context.score
        checklist = context.checklist

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()
        status = str(getattr(checklist, "book_depth_status", "UNAVAILABLE") or "UNAVAILABLE").upper()
        pressure = str(getattr(checklist, "book_depth_pressure", "UNAVAILABLE") or "UNAVAILABLE").upper()
        confidence = self._clamp(getattr(checklist, "book_depth_confidence", 0.0))
        duplicate = bool(getattr(checklist, "book_depth_duplicate_evidence_risk", False))
        correlation_factor = self.DUPLICATE_FACTOR if duplicate else 1.0
        effective_strength = round(confidence * correlation_factor, 4)
        adjustment = self._adjustment(status, effective_strength)

        adjusted_total = round(min(max(baseline_total + adjustment, 0.0), 100.0), 2)
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreBookDepthABSample(
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
            status=status,
            pressure=pressure,
            confidence=confidence,
            duplicate_evidence_risk=duplicate,
            correlation_factor=correlation_factor,
            effective_strength=effective_strength,
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
        return {
            "version": self.VERSION,
            "samples": total,
            "weight": self.weight,
            "duplicate_factor": self.DUPLICATE_FACTOR,
            "positive_adjustments": sum(s.delta > 0 for s in self._samples),
            "negative_adjustments": sum(s.delta < 0 for s in self._samples),
            "neutral_adjustments": sum(s.delta == 0 for s in self._samples),
            "grade_changes": sum(s.grade_changed for s in self._samples),
            "validity_changes": sum(s.validity_changed for s in self._samples),
            "duplicate_samples": sum(s.duplicate_evidence_risk for s in self._samples),
            "average_delta": round(sum(s.delta for s in self._samples) / total, 4) if total else 0.0,
            "average_effective_strength": round(sum(s.effective_strength for s in self._samples) / total, 4) if total else 0.0,
        }

    def _adjustment(self, status: str, strength: float) -> float:
        if status == "ALIGNED":
            return self.weight * strength
        if status == "CONFLICT":
            return -self.weight * strength
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
