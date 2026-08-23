"""Relatório passivo de sessão do A/B Absorção/Exaustão × Estrutura."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.score_order_flow_structure_ab_recorder import (
    ScoreOrderFlowStructureABRecorder,
)


@dataclass(slots=True, frozen=True)
class OrderFlowStructureABSessionReport:
    version: str = "RC1-ORDER-FLOW-STRUCTURE-AB-SESSION-REPORT"
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


class OrderFlowStructureABSessionReporter:
    VERSION = "RC1-ORDER-FLOW-STRUCTURE-AB-SESSION-REPORTER"
    MIN_SAMPLES = 100

    def build(
        self,
        recorder: ScoreOrderFlowStructureABRecorder,
    ) -> OrderFlowStructureABSessionReport:
        if not isinstance(recorder, ScoreOrderFlowStructureABRecorder):
            raise TypeError("recorder deve ser ScoreOrderFlowStructureABRecorder")

        summary = recorder.summary()
        scenarios = recorder.scenario_summary()

        samples = int(summary.get("samples", 0) or 0)
        average_delta = float(summary.get("average_delta", 0.0) or 0.0)
        average_confidence = float(summary.get("average_confidence", 0.0) or 0.0)
        grade_changes = int(summary.get("grade_changes", 0) or 0)
        validity_changes = int(summary.get("validity_changes", 0) or 0)

        dominant_effect = self._dominant_effect(summary)
        best_scenario, best_delta = self._extreme_scenario(scenarios, highest=True)
        worst_scenario, worst_delta = self._extreme_scenario(scenarios, highest=False)
        recommendation = self._recommendation(
            samples=samples,
            dominant_effect=dominant_effect,
            grade_changes=grade_changes,
            validity_changes=validity_changes,
        )

        return OrderFlowStructureABSessionReport(
            samples=samples,
            average_delta=round(average_delta, 4),
            average_confidence=round(average_confidence, 4),
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
        for group_name in (
            "by_alignment",
            "by_pattern_direction",
            "by_bias",
            "by_confidence",
        ):
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
