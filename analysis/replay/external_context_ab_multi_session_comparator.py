"""
analysis/replay/external_context_ab_multi_session_comparator.py

External Context A/B Multi-Session Comparator RC1.

Compara relatórios passivos de múltiplos pregões para medir estabilidade do
efeito hipotético do contexto externo. Não altera Score, Risk ou Decision.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from analysis.replay.external_context_ab_session_report import (
    ExternalContextABSessionReport,
)


@dataclass(slots=True, frozen=True)
class ExternalContextABMultiSessionReport:
    version: str = "RC1-EXTERNAL-CONTEXT-AB-MULTI-SESSION"
    sessions: int = 0
    total_samples: int = 0
    weighted_average_delta: float = 0.0
    min_average_delta: float = 0.0
    max_average_delta: float = 0.0
    delta_spread: float = 0.0

    positive_sessions: int = 0
    negative_sessions: int = 0
    neutral_sessions: int = 0
    mixed_sessions: int = 0
    no_data_sessions: int = 0

    grade_change_sessions: int = 0
    validity_change_sessions: int = 0
    recommendation_conflicts: int = 0

    stability: str = "INSUFFICIENT_DATA"
    recommendation: str = "COLLECT_MORE_DATA"
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ExternalContextABMultiSessionComparator:
    VERSION = "RC1-EXTERNAL-CONTEXT-AB-MULTI-SESSION-COMPARATOR"
    MIN_SESSIONS = 3
    MIN_TOTAL_SAMPLES = 300
    MAX_STABLE_SPREAD = 1.0

    def compare(self, reports) -> ExternalContextABMultiSessionReport:
        reports = tuple(reports)
        if not all(isinstance(item, ExternalContextABSessionReport) for item in reports):
            raise TypeError("reports deve conter apenas ExternalContextABSessionReport")

        sessions = len(reports)
        total_samples = sum(max(int(item.samples), 0) for item in reports)

        weighted_average_delta = 0.0
        if total_samples > 0:
            weighted_average_delta = sum(
                float(item.average_delta) * max(int(item.samples), 0)
                for item in reports
            ) / total_samples

        deltas = [float(item.average_delta) for item in reports if item.samples > 0]
        min_delta = min(deltas) if deltas else 0.0
        max_delta = max(deltas) if deltas else 0.0
        spread = max_delta - min_delta if deltas else 0.0

        effects = [item.dominant_effect for item in reports]
        positive = effects.count("POSITIVE")
        negative = effects.count("NEGATIVE")
        neutral = effects.count("NEUTRAL")
        mixed = effects.count("MIXED")
        no_data = effects.count("NO_DATA")

        grade_change_sessions = sum(item.grade_changes > 0 for item in reports)
        validity_change_sessions = sum(item.validity_changes > 0 for item in reports)

        recommendations = {
            item.recommendation for item in reports if item.dominant_effect != "NO_DATA"
        }
        recommendation_conflicts = max(len(recommendations) - 1, 0)

        stability = self._stability(
            sessions=sessions,
            total_samples=total_samples,
            spread=spread,
            positive=positive,
            negative=negative,
            neutral=neutral,
            mixed=mixed,
            no_data=no_data,
            grade_change_sessions=grade_change_sessions,
            validity_change_sessions=validity_change_sessions,
        )
        recommendation = self._recommendation(
            stability=stability,
            sessions=sessions,
            total_samples=total_samples,
            grade_change_sessions=grade_change_sessions,
            validity_change_sessions=validity_change_sessions,
            recommendation_conflicts=recommendation_conflicts,
        )

        return ExternalContextABMultiSessionReport(
            sessions=sessions,
            total_samples=total_samples,
            weighted_average_delta=round(weighted_average_delta, 4),
            min_average_delta=round(min_delta, 4),
            max_average_delta=round(max_delta, 4),
            delta_spread=round(spread, 4),
            positive_sessions=positive,
            negative_sessions=negative,
            neutral_sessions=neutral,
            mixed_sessions=mixed,
            no_data_sessions=no_data,
            grade_change_sessions=grade_change_sessions,
            validity_change_sessions=validity_change_sessions,
            recommendation_conflicts=recommendation_conflicts,
            stability=stability,
            recommendation=recommendation,
            passive_only=True,
        )

    @classmethod
    def _stability(
        cls,
        *,
        sessions,
        total_samples,
        spread,
        positive,
        negative,
        neutral,
        mixed,
        no_data,
        grade_change_sessions,
        validity_change_sessions,
    ) -> str:
        if sessions < cls.MIN_SESSIONS or total_samples < cls.MIN_TOTAL_SAMPLES:
            return "INSUFFICIENT_DATA"

        if grade_change_sessions > 0 or validity_change_sessions > 0:
            return "UNSTABLE"

        if spread > cls.MAX_STABLE_SPREAD:
            return "UNSTABLE"

        effective_sessions = sessions - no_data
        if effective_sessions <= 0:
            return "INSUFFICIENT_DATA"

        threshold = max(2, (effective_sessions * 2 + 2) // 3)

        if positive >= threshold and negative == 0 and mixed == 0:
            return "STABLE_POSITIVE"
        if negative >= threshold and positive == 0 and mixed == 0:
            return "STABLE_NEGATIVE"
        if neutral >= threshold and positive == 0 and negative == 0 and mixed == 0:
            return "STABLE_NEUTRAL"
        return "INCONSISTENT"

    @classmethod
    def _recommendation(
        cls,
        *,
        stability,
        sessions,
        total_samples,
        grade_change_sessions,
        validity_change_sessions,
        recommendation_conflicts,
    ) -> str:
        if sessions < cls.MIN_SESSIONS or total_samples < cls.MIN_TOTAL_SAMPLES:
            return "COLLECT_MORE_DATA"
        if grade_change_sessions > 0 or validity_change_sessions > 0:
            return "REVIEW_BEFORE_ENABLE"
        if recommendation_conflicts > 0:
            return "REVIEW_BEFORE_ENABLE"
        if stability in ("UNSTABLE", "INCONSISTENT"):
            return "KEEP_OBSERVING"
        if stability.startswith("STABLE_"):
            return "KEEP_OBSERVING"
        return "COLLECT_MORE_DATA"
