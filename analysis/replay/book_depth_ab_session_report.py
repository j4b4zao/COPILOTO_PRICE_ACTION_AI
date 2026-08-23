"""Relatório passivo de sessão do A/B de BookDepth."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True, frozen=True)
class BookDepthABSessionReport:
    samples: int = 0
    average_delta: float = 0.0
    average_confidence: float = 0.0
    average_effective_strength: float = 0.0
    independent_samples: int = 0
    correlated_samples: int = 0
    independent_average_delta: float = 0.0
    correlated_average_delta: float = 0.0
    grade_changes: int = 0
    validity_changes: int = 0
    dominant_effect: str = "NO_DATA"
    independent_effect: str = "NO_DATA"
    correlated_effect: str = "NO_DATA"
    best_scenario: str = "NONE"
    worst_scenario: str = "NONE"
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class BookDepthABSessionReporter:
    VERSION = "RC1-BOOK-DEPTH-AB-SESSION-REPORT"
    MIN_SAMPLES = 100
    EFFECT_EPSILON = 0.05

    def build(self, recorder) -> BookDepthABSessionReport:
        samples = list(getattr(recorder, "samples", ()))
        self._validate_samples(samples)

        if not samples:
            return BookDepthABSessionReport()

        total = len(samples)
        average_delta = self._average(samples, "delta")
        average_confidence = self._average(samples, "confidence")
        average_effective_strength = self._average(samples, "effective_strength")
        grade_changes = sum(bool(s.grade_changed) for s in samples)
        validity_changes = sum(bool(s.validity_changed) for s in samples)

        independent = [s for s in samples if str(s.correlation_bucket).upper() == "INDEPENDENT"]
        correlated = [s for s in samples if str(s.correlation_bucket).upper() == "CORRELATED"]
        independent_delta = self._average(independent, "delta")
        correlated_delta = self._average(correlated, "delta")

        dominant_effect = self._effect(average_delta, samples)
        independent_effect = self._effect(independent_delta, independent)
        correlated_effect = self._effect(correlated_delta, correlated)
        best_scenario, worst_scenario = self._extreme_scenarios(recorder)
        recommendation = self._recommendation(
            total=total,
            grade_changes=grade_changes,
            validity_changes=validity_changes,
        )

        return BookDepthABSessionReport(
            samples=total,
            average_delta=average_delta,
            average_confidence=average_confidence,
            average_effective_strength=average_effective_strength,
            independent_samples=len(independent),
            correlated_samples=len(correlated),
            independent_average_delta=independent_delta,
            correlated_average_delta=correlated_delta,
            grade_changes=grade_changes,
            validity_changes=validity_changes,
            dominant_effect=dominant_effect,
            independent_effect=independent_effect,
            correlated_effect=correlated_effect,
            best_scenario=best_scenario,
            worst_scenario=worst_scenario,
            recommendation=recommendation,
            passive_only=True,
        )

    def _extreme_scenarios(self, recorder):
        scenario_summary = recorder.scenario_summary()
        candidates = []
        for group_name in ("by_status", "by_pressure", "by_bias", "by_correlation", "by_confidence"):
            for key, metrics in scenario_summary.get(group_name, {}).items():
                if int(metrics.get("samples", 0)) <= 0:
                    continue
                candidates.append((f"{group_name}:{key}", float(metrics.get("average_delta", 0.0))))
        if not candidates:
            return "NONE", "NONE"
        best = max(candidates, key=lambda item: item[1])[0]
        worst = min(candidates, key=lambda item: item[1])[0]
        return best, worst

    def _recommendation(self, *, total, grade_changes, validity_changes):
        if total < self.MIN_SAMPLES:
            return "COLLECT_MORE_DATA"
        if grade_changes or validity_changes:
            return "REVIEW_BEFORE_ENABLE"
        return "KEEP_OBSERVING"

    def _effect(self, average_delta, samples):
        if not samples:
            return "NO_DATA"
        positive = sum(float(s.delta) > self.EFFECT_EPSILON for s in samples)
        negative = sum(float(s.delta) < -self.EFFECT_EPSILON for s in samples)
        if positive and negative:
            return "MIXED"
        if average_delta > self.EFFECT_EPSILON:
            return "POSITIVE"
        if average_delta < -self.EFFECT_EPSILON:
            return "NEGATIVE"
        return "NEUTRAL"

    @staticmethod
    def _average(samples, field):
        if not samples:
            return 0.0
        return round(sum(float(getattr(s, field)) for s in samples) / len(samples), 4)

    @staticmethod
    def _validate_samples(samples):
        required = (
            "delta", "confidence", "effective_strength", "correlation_bucket",
            "grade_changed", "validity_changed",
        )
        for sample in samples:
            if not all(hasattr(sample, field) for field in required):
                raise TypeError("Amostra A/B de BookDepth inválida para relatório de sessão.")
