"""
analysis/replay/score_regime_mtf_ab_recorder.py

Score A/B RC1 - Regime + MTF observational validation.

Compara o score oficial já calculado pela pipeline (baseline) com o score
hipotético que resultaria do ajuste experimental Regime+MTF RC13.2.

Não reexecuta o ScoreEngine e não escreve em Strategy, Score, Risk ou Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2


@dataclass(slots=True, frozen=True)
class ScoreRegimeMtfABSample:
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
    mtf_alignment: str = "INSUFFICIENT_DATA"
    regime_context: str = "UNKNOWN"
    regime_compatible: bool = False
    adjustment: float = 0.0

    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreRegimeMtfABRecorder:
    """Recorder estritamente passivo para validação A/B do ajuste RC13.2."""

    VERSION = "RC1-REGIME-MTF-SCORE-AB"

    def __init__(self, weight: float = 3.0, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= ScoreEngineRC13_2.MAX_REGIME_MTF_WEIGHT:
            raise ValueError("Peso A/B de Regime+MTF deve ficar entre 0 e 5.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreRegimeMtfABSample] = []

    @property
    def samples(self) -> tuple[ScoreRegimeMtfABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def record(self, context) -> ScoreRegimeMtfABSample:
        score = context.score
        mtf = context.multi_timeframe_analysis

        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        bias = str(getattr(score, "bias", "NONE") or "NONE").upper()

        adjustment = ScoreEngineRC13_2._contextual_adjustment(
            score_bias=bias,
            multi_timeframe=mtf,
            weight=self.weight,
        )

        adjusted_total = min(max(baseline_total + adjustment, 0.0), 100.0)
        adjusted_total = round(adjusted_total, 2)
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )

        sample = ScoreRegimeMtfABSample(
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
            mtf_alignment=str(getattr(mtf, "alignment", "INSUFFICIENT_DATA") or "INSUFFICIENT_DATA"),
            regime_context=str(getattr(mtf, "regime_context", "UNKNOWN") or "UNKNOWN"),
            regime_compatible=bool(getattr(mtf, "regime_compatible", False)),
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
        grade_changes = sum(sample.grade_changed for sample in self._samples)
        validity_changes = sum(sample.validity_changed for sample in self._samples)
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
            "grade_changes": grade_changes,
            "validity_changes": validity_changes,
            "average_delta": average_delta,
            "weight": self.weight,
        }

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
