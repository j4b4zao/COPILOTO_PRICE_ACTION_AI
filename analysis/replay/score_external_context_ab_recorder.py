"""
analysis/replay/score_external_context_ab_recorder.py

External Context Score A/B RC2 - scenario metrics.

Compara o score oficial da pipeline com um score hipotético ajustado pelo
contexto externo, sem escrever em Strategy, Score, Risk ou Decision, e agrega
métricas por risco externo, status, direção e faixa de confiança.

Regra experimental:
- ALIGNED: até +2 pontos, proporcional à confiança externa;
- CONFLICT: até -2 pontos, proporcional à confiança externa;
- NEUTRAL / LOW_CONFIDENCE / UNAVAILABLE: 0 ponto.
"""

from __future__ import annotations

from collections import defaultdict
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
    confidence_bucket: str = "UNAVAILABLE"
    adjustment: float = 0.0

    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreExternalContextABRecorder:
    """Recorder passivo para validar o efeito hipotético do contexto externo."""

    VERSION = "RC2-EXTERNAL-CONTEXT-SCORE-AB-SCENARIOS"
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
            external_risk=str(
                getattr(context, "external_risk", "NEUTRAL") or "NEUTRAL"
            ).upper(),
            external_bias=str(
                getattr(context, "external_bias", "NEUTRAL") or "NEUTRAL"
            ).upper(),
            external_confidence=confidence,
            confidence_bucket=self._confidence_bucket(status, confidence),
            adjustment=round(adjustment, 2),
            passive_only=True,
        )

        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]
        return sample

    def summary(self) -> dict:
        return {
            "version": self.VERSION,
            **self._metrics(self._samples),
            "weight": self.weight,
        }

    def scenario_summary(self) -> dict:
        return {
            "version": self.VERSION,
            "samples": len(self._samples),
            "weight": self.weight,
            "by_risk": self._group_by("external_risk"),
            "by_status": self._group_by("external_status"),
            "by_bias": self._group_by("bias"),
            "by_confidence": self._group_by("confidence_bucket"),
        }

    def scenario(
        self,
        *,
        risk=None,
        status=None,
        bias=None,
        confidence=None,
    ) -> dict:
        selected = self._samples
        filters = {}

        if risk is not None:
            value = str(risk).upper()
            filters["external_risk"] = value
            selected = [s for s in selected if s.external_risk == value]

        if status is not None:
            value = str(status).upper()
            filters["external_status"] = value
            selected = [s for s in selected if s.external_status == value]

        if bias is not None:
            value = str(bias).upper()
            filters["bias"] = value
            selected = [s for s in selected if s.bias == value]

        if confidence is not None:
            value = str(confidence).upper()
            filters["confidence_bucket"] = value
            selected = [s for s in selected if s.confidence_bucket == value]

        return {
            "version": self.VERSION,
            "filters": filters,
            **self._metrics(selected),
            "weight": self.weight,
        }

    def _group_by(self, field: str) -> dict:
        grouped = defaultdict(list)
        for sample in self._samples:
            grouped[getattr(sample, field)].append(sample)
        return {
            key: self._metrics(values)
            for key, values in sorted(grouped.items())
        }

    @staticmethod
    def _metrics(samples) -> dict:
        samples = list(samples)
        total = len(samples)
        positive = sum(sample.delta > 0 for sample in samples)
        negative = sum(sample.delta < 0 for sample in samples)
        neutral = total - positive - negative
        average_delta = (
            round(sum(sample.delta for sample in samples) / total, 4)
            if total
            else 0.0
        )
        average_confidence = (
            round(sum(sample.external_confidence for sample in samples) / total, 4)
            if total
            else 0.0
        )
        return {
            "samples": total,
            "positive_adjustments": positive,
            "negative_adjustments": negative,
            "neutral_adjustments": neutral,
            "grade_changes": sum(sample.grade_changed for sample in samples),
            "validity_changes": sum(sample.validity_changed for sample in samples),
            "average_delta": average_delta,
            "average_confidence": average_confidence,
        }

    @staticmethod
    def _clamp_confidence(value) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(numeric, 0.0), 1.0), 4)

    @staticmethod
    def _confidence_bucket(status: str, confidence: float) -> str:
        if status == "UNAVAILABLE":
            return "UNAVAILABLE"
        if confidence < 0.50:
            return "LOW"
        if confidence < 0.75:
            return "MEDIUM"
        return "HIGH"

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
