"""
analysis/replay/score_order_flow_ab_recorder.py

Order Flow Score A/B RC1 - validação estritamente observacional.

Compara o score oficial já calculado pela pipeline com um score hipotético
ajustado pela dinâmica de Delta do Order Flow. Não reexecuta ScoreEngine e
não escreve em Strategy, Score, Risk ou Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreOrderFlowABSample:
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
    order_flow_status: str = "UNAVAILABLE"
    flow_momentum: str = "INSUFFICIENT_DATA"
    delta_persistence: float = 0.0
    delta_impulse_ratio: float = 0.0
    evidence_strength: float = 0.0
    adjustment: float = 0.0

    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreOrderFlowABRecorder:
    """Recorder passivo do efeito hipotético da dinâmica de Order Flow."""

    VERSION = "RC1-ORDER-FLOW-SCORE-AB"
    MAX_WEIGHT = 2.0
    FADING_FACTOR = 0.25

    def __init__(self, weight: float = 2.0, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B de Order Flow deve ficar entre 0 e 2.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreOrderFlowABSample] = []

    @property
    def samples(self) -> tuple[ScoreOrderFlowABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def record(self, context) -> ScoreOrderFlowABSample:
        score = context.score
        checklist = context.checklist

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()

        status = str(
            getattr(checklist, "order_flow_status", "UNAVAILABLE")
            or "UNAVAILABLE"
        ).upper()
        momentum = str(
            getattr(checklist, "order_flow_momentum", "INSUFFICIENT_DATA")
            or "INSUFFICIENT_DATA"
        ).upper()
        persistence = self._clamp(
            getattr(checklist, "order_flow_delta_persistence", 0.0)
        )
        impulse = self._clamp(
            getattr(checklist, "order_flow_delta_impulse_ratio", 0.0)
        )
        evidence_strength = round(0.60 * persistence + 0.40 * impulse, 4)
        adjustment = self._adjustment(status, evidence_strength, self.weight)

        adjusted_total = round(
            min(max(baseline_total + adjustment, 0.0), 100.0),
            2,
        )
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreOrderFlowABSample(
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
            order_flow_status=status,
            flow_momentum=momentum,
            delta_persistence=persistence,
            delta_impulse_ratio=impulse,
            evidence_strength=evidence_strength,
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

    @classmethod
    def _adjustment(cls, status: str, strength: float, weight: float) -> float:
        if status == "ALIGNED":
            return weight * strength
        if status == "CONFLICT":
            return -weight * strength
        if status == "FADING":
            return -(weight * cls.FADING_FACTOR * strength)
        return 0.0

    @staticmethod
    def _clamp(value) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return 0.0
        return round(min(max(numeric, 0.0), 1.0), 4)

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
