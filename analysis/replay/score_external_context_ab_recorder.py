"""
analysis/replay/score_external_context_ab_recorder.py

External Context Score A/B RC1 - observational validation.

Compara o score oficial da pipeline com um score hipotético ajustado pelo
contexto externo, sem escrever em Strategy, Score, Risk ou Decision.

Regra experimental:
- ALIGNED: até +2 pontos, proporcional à confiança externa;
- CONFLICT: até -2 pontos, proporcional à confiança externa;
- NEUTRAL / LOW_CONFIDENCE / UNAVAILABLE: 0 ponto.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreExternalContextABSample:
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
    external_status: str = "UNAVAILABLE"
    external_risk: str = "NEUTRAL"
    external_bias: str = "NEUTRAL"
    external_confidence: float = 0.0
    adjustment: float = 0.0

    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreExternalContextABRecorder:
    """Recorder passivo para validar o efeito hipotético do contexto externo."""

    VERSION = "RC1-EXTERNAL-CONTEXT-SCORE-AB"
    MAX_WEIGHT = 2.0

    def __init__(self, weight: float = 2.0, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B do contexto externo deve ficar entre 0 e 2.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreExternalContextABSample] = []

    @property
    def samples(self) -> tuple[ScoreExternalContextABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def record(self, context) -> ScoreExternalContextABSample:
        score = context.score
        checklist = context.checklist

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()

        status = str(
            getattr(checklist, "external_context_status", "UNAVAILABLE")
            or "UNAVAILABLE"
        ).upper()
        confidence = self._clamp_confidence(
            getattr(checklist, "external_context_confidence", 0.0)
        )
        adjustment = self._adjustment(status, confidence, self.weight)

        adjusted_total = round(
            min(max(baseline_total + adjustment, 0.0), 100.0),
            2,
        )
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreExternalContextABSample(
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
            external_status=status,
            external_risk=str(getattr(context, "external_risk", "NEUTRAL") or "NEUTRAL").upper(),
            external_bias=str(getattr(context, "external_bias", "NEUTRAL") or "NEUTRAL").upper(),
            external_confidence=confidence,
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
        positive = sum(sample.delta > 0 for sample in self._samples)
        negative = sum(sample.delta < 0 for sample in self._samples)
        neutral = total - positive - negative
        average_delta = (
            round(sum(sample.delta for sample in self._samples) / total, 4)
            if total
            else 0.0
        )
        return {
            "version": self.VERSION,
            "samples": total,
            "positive_adjustments": positive,
            "negative_adjustments": negative,
            "neutral_adjustments": neutral,
            "grade_changes": sum(sample.grade_changed for sample in self._samples),
            "validity_changes": sum(sample.validity_changed for sample in self._samples),
            "average_delta": average_delta,
            "weight": self.weight,
        }

    @staticmethod
    def _clamp_confidence(value) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(numeric, 0.0), 1.0), 4)

    @classmethod
    def _adjustment(cls, status: str, confidence: float, weight: float) -> float:
        if status == "ALIGNED":
            return weight * confidence
        if status == "CONFLICT":
            return -weight * confidence
        return 0.0

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
