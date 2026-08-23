"""
analysis/replay/score_regime_mtf_ab_multi_session.py

Score A/B RC6 - Multi-session comparator.

Compara relatórios RC5 de múltiplos pregões para medir consistência do efeito
hipotético Regime+MTF. Estritamente observacional: não altera Score, Risk,
Decision ou Strategy e não ativa o experimento.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from analysis.replay.score_regime_mtf_ab_session_report import (
    ScoreRegimeMtfABSessionReport,
)


@dataclass(slots=True, frozen=True)
class ScoreRegimeMtfABMultiSessionReport:
    version: str
    sessions: int
    total_samples: int
    weighted_average_delta: float
    min_session_delta: float
    max_session_delta: float
    delta_spread: float
    positive_sessions: int
    negative_sessions: int
    neutral_sessions: int
    mixed_sessions: int
    sessions_with_grade_changes: int
    sessions_with_validity_changes: int
    recommendation_agreement: bool
    recommendation: str
    stable_across_sessions: bool
    passive_only: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


class ScoreRegimeMtfABMultiSessionComparator:
    VERSION = "RC6-REGIME-MTF-SCORE-AB-MULTI-SESSION"
    MIN_SESSIONS = 3
    MAX_STABLE_SPREAD = 1.5

    @classmethod
    def compare(cls, reports) -> ScoreRegimeMtfABMultiSessionReport:
        reports = tuple(reports)
        for report in reports:
            if not isinstance(report, ScoreRegimeMtfABSessionReport):
                raise TypeError("Todos os itens devem ser ScoreRegimeMtfABSessionReport.")

        if not reports:
            return ScoreRegimeMtfABMultiSessionReport(
                version=cls.VERSION,
                sessions=0,
                total_samples=0,
                weighted_average_delta=0.0,
                min_session_delta=0.0,
                max_session_delta=0.0,
                delta_spread=0.0,
                positive_sessions=0,
                negative_sessions=0,
                neutral_sessions=0,
                mixed_sessions=0,
                sessions_with_grade_changes=0,
                sessions_with_validity_changes=0,
                recommendation_agreement=False,
                recommendation="NO_DATA",
                stable_across_sessions=False,
                passive_only=True,
            )

        total_samples = sum(max(0, int(r.samples)) for r in reports)
        if total_samples:
            weighted_average = sum(
                float(r.average_delta) * max(0, int(r.samples)) for r in reports
            ) / total_samples
        else:
            weighted_average = 0.0

        deltas = [float(r.average_delta) for r in reports]
        minimum = min(deltas)
        maximum = max(deltas)
        spread = maximum - minimum

        effects = [str(r.dominant_effect).upper() for r in reports]
        positive = effects.count("POSITIVE")
        negative = effects.count("NEGATIVE")
        neutral = effects.count("NEUTRAL")
        mixed = effects.count("MIXED")

        grade_change_sessions = sum(int(r.grade_changes) > 0 for r in reports)
        validity_change_sessions = sum(int(r.validity_changes) > 0 for r in reports)

        recommendations = [str(r.recommendation).upper() for r in reports]
        recommendation_agreement = len(set(recommendations)) == 1

        stable = cls._stable(
            reports=reports,
            spread=spread,
            positive=positive,
            negative=negative,
            neutral=neutral,
            mixed=mixed,
            validity_change_sessions=validity_change_sessions,
        )
        recommendation = cls._recommendation(
            reports=reports,
            total_samples=total_samples,
            weighted_average=weighted_average,
            stable=stable,
            grade_change_sessions=grade_change_sessions,
            validity_change_sessions=validity_change_sessions,
        )

        return ScoreRegimeMtfABMultiSessionReport(
            version=cls.VERSION,
            sessions=len(reports),
            total_samples=total_samples,
            weighted_average_delta=round(weighted_average, 4),
            min_session_delta=round(minimum, 4),
            max_session_delta=round(maximum, 4),
            delta_spread=round(spread, 4),
            positive_sessions=positive,
            negative_sessions=negative,
            neutral_sessions=neutral,
            mixed_sessions=mixed,
            sessions_with_grade_changes=grade_change_sessions,
            sessions_with_validity_changes=validity_change_sessions,
            recommendation_agreement=recommendation_agreement,
            recommendation=recommendation,
            stable_across_sessions=stable,
            passive_only=True,
        )

    @classmethod
    def _stable(
        cls,
        *,
        reports,
        spread,
        positive,
        negative,
        neutral,
        mixed,
        validity_change_sessions,
    ) -> bool:
        if len(reports) < cls.MIN_SESSIONS:
            return False
        if validity_change_sessions > 0:
            return False
        if not math.isfinite(spread) or spread > cls.MAX_STABLE_SPREAD:
            return False

        directional_sessions = positive + negative
        if directional_sessions == 0:
            return neutral == len(reports)
        if mixed > 0:
            return False
        return positive == len(reports) or negative == len(reports)

    @classmethod
    def _recommendation(
        cls,
        *,
        reports,
        total_samples,
        weighted_average,
        stable,
        grade_change_sessions,
        validity_change_sessions,
    ) -> str:
        if not reports:
            return "NO_DATA"
        if len(reports) < cls.MIN_SESSIONS or total_samples < 300:
            return "COLLECT_MORE_SESSIONS"
        if validity_change_sessions > 0 or grade_change_sessions > max(1, len(reports) // 3):
            return "REVIEW_BEFORE_ENABLE"
        if not stable:
            return "INCONSISTENT_KEEP_AB"
        if weighted_average > 0.0:
            return "CONSISTENTLY_PROMISING_KEEP_AB"
        if weighted_average < 0.0:
            return "CONSISTENT_NEGATIVE_REVIEW_PENALTIES"
        return "STABLE_NEUTRAL_KEEP_OBSERVING"
