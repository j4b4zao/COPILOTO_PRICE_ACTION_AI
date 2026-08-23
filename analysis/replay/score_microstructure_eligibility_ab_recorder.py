"""A/B passivo do impacto hipotético da elegibilidade de microestrutura no Score."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass

from ai.score_engine_rc13_2 import ScoreEngine as ScoreEngineRC13_2
from analysis.replay.microstructure_confluence import MicrostructureConfluenceAudit
from analysis.replay.microstructure_eligibility_policy import MicrostructureEligibilityPolicy


@dataclass(slots=True, frozen=True)
class ScoreMicrostructureEligibilityABSample:
    baseline_total: float = 0.0
    adjusted_total: float = 0.0
    delta: float = 0.0
    baseline_grade: str = "REPROVADO"
    adjusted_grade: str = "REPROVADO"
    grade_changed: bool = False
    baseline_valid: bool = False
    adjusted_valid: bool = False
    validity_changed: bool = False
    eligibility_state: str = "NOT_ELIGIBLE"
    eligibility_reason: str = "INSUFFICIENT_DATA"
    confluence_quality: str = "INSUFFICIENT_DATA"
    confidence: float = 0.0
    confidence_bucket: str = "UNAVAILABLE"
    independent_evidence_count: int = 0
    correlated_evidence_count: int = 0
    conflict_count: int = 0
    correlation_bucket: str = "INDEPENDENT"
    correlation_factor: float = 1.0
    raw_adjustment: float = 0.0
    adjustment: float = 0.0
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreMicrostructureEligibilityABRecorder:
    """Mede bônus hipotético de elegibilidade sem alterar o Score oficial."""

    VERSION = "RC2-MICROSTRUCTURE-ELIGIBILITY-SCORE-AB-SCENARIOS"
    MAX_WEIGHT = 1.5
    PROMISING_FACTOR = 0.50
    CORRELATION_FACTOR = 0.50

    def __init__(self, weight: float = 1.5, max_samples: int = 50000):
        weight = float(weight)
        if not 0.0 <= weight <= self.MAX_WEIGHT:
            raise ValueError("Peso A/B de elegibilidade deve ficar entre 0 e 1.5.")
        self.weight = weight
        self.max_samples = max(1, int(max_samples))
        self._samples: list[ScoreMicrostructureEligibilityABSample] = []
        self.audit = MicrostructureConfluenceAudit()
        self.policy = MicrostructureEligibilityPolicy()

    @property
    def samples(self) -> tuple[ScoreMicrostructureEligibilityABSample, ...]:
        return tuple(self._samples)

    @property
    def size(self) -> int:
        return len(self._samples)

    def clear(self) -> None:
        self._samples.clear()

    def record(self, context) -> ScoreMicrostructureEligibilityABSample:
        score = context.score
        snapshot = self.audit.analyze(context)
        decision = self.policy.evaluate(snapshot)
        baseline_total = float(getattr(score, "total", 0.0) or 0.0)
        baseline_grade = str(getattr(score, "grade", "REPROVADO") or "REPROVADO")
        baseline_valid = bool(getattr(score, "valid", False))
        raw_adjustment = self._raw_adjustment(decision.state)
        correlated = decision.correlated_evidence_count > 0
        correlation_factor = self.CORRELATION_FACTOR if correlated else 1.0
        adjustment = raw_adjustment * correlation_factor
        if decision.conflict_count > 0:
            adjustment = 0.0
        adjusted_total = round(min(max(baseline_total + adjustment, 0.0), 100.0), 2)
        adjusted_grade = self._grade(adjusted_total)
        adjusted_valid = bool(
            getattr(context.strategy, "valid", False)
            and adjusted_total >= ScoreEngineRC13_2.MIN_SCORE
        )
        sample = ScoreMicrostructureEligibilityABSample(
            baseline_total=round(baseline_total, 2), adjusted_total=adjusted_total,
            delta=round(adjusted_total - baseline_total, 2), baseline_grade=baseline_grade,
            adjusted_grade=adjusted_grade, grade_changed=baseline_grade != adjusted_grade,
            baseline_valid=baseline_valid, adjusted_valid=adjusted_valid,
            validity_changed=baseline_valid != adjusted_valid,
            eligibility_state=decision.state, eligibility_reason=decision.reason,
            confluence_quality=decision.confluence_quality, confidence=decision.confidence,
            confidence_bucket=self._confidence_bucket(decision.confidence, decision.state),
            independent_evidence_count=decision.independent_evidence_count,
            correlated_evidence_count=decision.correlated_evidence_count,
            conflict_count=decision.conflict_count,
            correlation_bucket="CORRELATED" if correlated else "INDEPENDENT",
            correlation_factor=correlation_factor, raw_adjustment=round(raw_adjustment, 2),
            adjustment=round(adjustment, 2), passive_only=True,
        )
        self._append(sample)
        return sample

    def summary(self) -> dict:
        return {"version": self.VERSION, **self._metrics(self._samples),
                "weight": self.weight, "promising_factor": self.PROMISING_FACTOR,
                "correlation_factor": self.CORRELATION_FACTOR, "passive_only": True}

    def scenario_summary(self) -> dict:
        return {
            "version": self.VERSION, "samples": self.size,
            "by_eligibility": self._group_by("eligibility_state"),
            "by_quality": self._group_by("confluence_quality"),
            "by_independent_evidence": self._group_by("independent_evidence_count"),
            "by_correlation": self._group_by("correlation_bucket"),
            "by_confidence": self._group_by("confidence_bucket"),
            "by_conflict": self._group_by("conflict_count"),
            "passive_only": True,
        }

    def scenario(self, *, eligibility=None, quality=None, independent=None,
                 correlation=None, confidence=None, conflict=None) -> dict:
        selected = list(self._samples)
        filters = {}
        specifications = (
            ("eligibility_state", eligibility, str),
            ("confluence_quality", quality, str),
            ("independent_evidence_count", independent, int),
            ("correlation_bucket", correlation, str),
            ("confidence_bucket", confidence, str),
            ("conflict_count", conflict, int),
        )
        for field, raw, caster in specifications:
            if raw is None:
                continue
            value = caster(raw)
            if caster is str:
                value = value.upper()
            filters[field] = value
            selected = [sample for sample in selected if getattr(sample, field) == value]
        return {"version": self.VERSION, "filters": filters, **self._metrics(selected),
                "weight": self.weight, "passive_only": True}

    def _append(self, sample) -> None:
        self._samples.append(sample)
        overflow = len(self._samples) - self.max_samples
        if overflow > 0:
            del self._samples[:overflow]

    def _group_by(self, field: str) -> dict:
        grouped = defaultdict(list)
        for sample in self._samples:
            grouped[getattr(sample, field)].append(sample)
        return {str(key): self._metrics(values) for key, values in sorted(grouped.items(), key=lambda item: str(item[0]))}

    @staticmethod
    def _metrics(samples) -> dict:
        samples = list(samples)
        total = len(samples)
        return {
            "samples": total,
            "positive_adjustments": sum(s.delta > 0 for s in samples),
            "neutral_adjustments": sum(s.delta == 0 for s in samples),
            "grade_changes": sum(s.grade_changed for s in samples),
            "validity_changes": sum(s.validity_changed for s in samples),
            "strong_candidate_samples": sum(s.eligibility_state == "STRONG_CANDIDATE" for s in samples),
            "promising_samples": sum(s.eligibility_state == "PROMISING" for s in samples),
            "correlated_samples": sum(s.correlated_evidence_count > 0 for s in samples),
            "conflict_samples": sum(s.conflict_count > 0 for s in samples),
            "average_delta": round(sum(s.delta for s in samples) / total, 4) if total else 0.0,
            "average_confidence": round(sum(s.confidence for s in samples) / total, 4) if total else 0.0,
            "average_independent_evidence": round(sum(s.independent_evidence_count for s in samples) / total, 4) if total else 0.0,
            "average_correlated_evidence": round(sum(s.correlated_evidence_count for s in samples) / total, 4) if total else 0.0,
        }

    def _raw_adjustment(self, state: str) -> float:
        if state == "STRONG_CANDIDATE":
            return self.weight
        if state == "PROMISING":
            return self.weight * self.PROMISING_FACTOR
        return 0.0

    @staticmethod
    def _confidence_bucket(confidence: float, state: str) -> str:
        if state == "NOT_ELIGIBLE" and confidence <= 0.0:
            return "UNAVAILABLE"
        if confidence < 0.50:
            return "LOW"
        if confidence < 0.75:
            return "MEDIUM"
        return "HIGH"

    @staticmethod
    def _grade(total: float) -> str:
        if total >= 90.0: return "A+"
        if total >= 80.0: return "A"
        if total >= 70.0: return "B"
        if total >= 60.0: return "C"
        return "REPROVADO"
