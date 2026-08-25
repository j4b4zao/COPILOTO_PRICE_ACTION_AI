"""
analysis/replay/external_context_ab_session_report.py

External Context A/B Session Report RC1.

Resume uma sessão do ScoreExternalContextABRecorder sem alterar qualquer
resultado operacional. O relatório é estritamente observacional e não grava
arquivos por conta própria.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.score_external_context_ab_recorder import (
    ScoreExternalContextABRecorder,
)


@dataclass(slots=True, frozen=True)
class ExternalContextABSessionReport:
    version: str = "RC1-EXTERNAL-CONTEXT-AB-SESSION-REPORT"
    samples: int = 0
    average_delta: float = 0.0
    average_confidence: float = 0.0
    dominant_effect: str = "NO_DATA"
    best_scenario: str = "NONE"
    best_average_delta: float = 0.0
    worst_scenario: str = "NONE"
    worst_average_delta: float = 0.0
    grade_changes: int = 0
    validity_changes: int = 0
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ExternalContextABSessionReporter:
    VERSION = "RC1-EXTERNAL-CONTEXT-AB-SESSION-REPORTER"
    MIN_SAMPLES = 100

    def build(self, recorder: ScoreExternalContextABRecorder) -> ExternalContextABSessionReport:
        if not isinstance(recorder, ScoreExternalContextABRecorder):
            raise TypeError("recorder deve ser ScoreExternalContextABRecorder")

        summary = recorder.summary()
        scenarios = recorder.scenario_summary()
        samples = int(summary.get("samples", 0) or 0)
        average_delta = float(summary.get("average_delta", 0.0) or 0.0)
        grade_changes = int(summary.get("grade_changes", 0) or 0)
        validity_changes = int(summary.get("validity_changes", 0) or 0)

        confidence_values = [
            sample.external_confidence for sample in recorder.samples
        ]
        average_confidence = (
            round(sum(confidence_values) / len(confidence_values), 4)
            if confidence_values
            else 0.0
        )

        dominant_effect = self._dominant_effect(summary)
        best_scenario, best_delta = self._extreme_scenario(scenarios, highest=True)
        worst_scenario, worst_delta = self._extreme_scenario(scenarios, highest=False)
        recommendation = self._recommendation(
            samples=samples,
            dominant_effect=dominant_effect,
            grade_changes=grade_changes,
            validity_changes=validity_changes,
        )

        return ExternalContextABSessionReport(
            samples=samples,
            average_delta=round(average_delta, 4),
            average_confidence=average_confidence,
            dominant_effect=dominant_effect,
            best_scenario=best_scenario,
            best_average_delta=best_delta,
            worst_scenario=worst_scenario,
            worst_average_delta=worst_delta,
            grade_changes=grade_changes,
            validity_changes=validity_changes,
            recommendation=recommendation,
            passive_only=True,
        )

    @staticmethod
    def _dominant_effect(summary: dict) -> str:
        total = int(summary.get("samples", 0) or 0)
        if total == 0:
            return "NO_DATA"

        positive = int(summary.get("positive_adjustments", 0) or 0)
        negative = int(summary.get("negative_adjustments", 0) or 0)
        neutral = int(summary.get("neutral_adjustments", 0) or 0)

        if positive > negative and positive > neutral:
            return "POSITIVE"
        if negative > positive and negative > neutral:
            return "NEGATIVE"
        if neutral > positive and neutral > negative:
            return "NEUTRAL"
        return "MIXED"

    @staticmethod
    def _extreme_scenario(scenarios: dict, *, highest: bool) -> tuple[str, float]:
        candidates = []
        for group_name in ("by_risk", "by_status", "by_bias", "by_confidence"):
            groups = scenarios.get(group_name, {}) or {}
            for label, metrics in groups.items():
                samples = int(metrics.get("samples", 0) or 0)
                if samples <= 0:
                    continue
                delta = float(metrics.get("average_delta", 0.0) or 0.0)
                candidates.append((f"{group_name}:{label}", delta))

        if not candidates:
            return "NONE", 0.0

        chosen = max(candidates, key=lambda item: item[1]) if highest else min(
            candidates, key=lambda item: item[1]
        )
        return chosen[0], round(chosen[1], 4)

    @classmethod
    def _recommendation(
        cls,
        *,
        samples: int,
        dominant_effect: str,
        grade_changes: int,
        validity_changes: int,
    ) -> str:
        if samples < cls.MIN_SAMPLES:
            return "COLLECT_MORE_DATA"
        if validity_changes > 0 or grade_changes > 0:
            return "REVIEW_BEFORE_ENABLE"
        if dominant_effect in ("POSITIVE", "NEGATIVE", "MIXED"):
            return "KEEP_OBSERVING"
        return "COLLECT_MORE_DATA"
