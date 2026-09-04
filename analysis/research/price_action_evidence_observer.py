"""Auditoria offline de evidencias para padroes de price action.

Consome classificacoes ja produzidas pelo projeto; nao detecta sinais, nao
altera score e nao participa do pipeline operacional.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True, slots=True)
class PriceActionEvidence:
    session_id: str
    pattern: str
    regime: str
    timeframe: str
    location_context: str
    horizon_steps: int
    forward_return: float
    volume: float | None = None
    baseline_volume: float | None = None

    def __post_init__(self) -> None:
        for name in ("session_id", "pattern", "regime", "timeframe", "location_context"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} deve ser texto nao vazio.")
        if (isinstance(self.horizon_steps, bool)
                or not isinstance(self.horizon_steps, int)
                or self.horizon_steps < 1):
            raise ValueError("horizon_steps deve ser inteiro positivo.")
        if not math.isfinite(float(self.forward_return)):
            raise ValueError("forward_return deve ser finito.")
        if (self.volume is None) != (self.baseline_volume is None):
            raise ValueError("volume e baseline_volume devem ser informados juntos.")
        if self.volume is not None:
            if not math.isfinite(float(self.volume)) or self.volume < 0:
                raise ValueError("volume deve ser finito e nao negativo.")
            if not math.isfinite(float(self.baseline_volume)) or self.baseline_volume <= 0:
                raise ValueError("baseline_volume deve ser finito e positivo.")


@dataclass(frozen=True, slots=True)
class PriceActionEvidenceBucket:
    key: str
    observations: int
    mean_forward_return: float
    positive_rate: float
    mean_volume_ratio: float | None
    sessions: int
    maximum_session_share: float
    session_mean_returns: tuple[tuple[str, float], ...]
    consistent_direction: str
    directional_session_share: float
    sample_sufficient: bool
    cross_session_sufficient: bool
    directional_stability_sufficient: bool
    additional_observations_lower_bound: int
    additional_sessions_lower_bound: int


@dataclass(frozen=True, slots=True)
class PriceActionEvidenceReport:
    status: str
    buckets: tuple[PriceActionEvidenceBucket, ...]
    insufficient_buckets: tuple[str, ...]
    reasons: tuple[str, ...]
    observational_only: bool = True
    predictive_claim_allowed: bool = False
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    alert_influence_allowed: bool = False
    order_execution_allowed: bool = False


class PriceActionEvidenceObserver:
    """Mede resultados por contexto sem transformar padroes em sinais."""

    NAME = "PriceActionEvidenceObserver"
    VERSION = "RC1"

    @staticmethod
    def _directional_session_gap(
        *, dominant_sessions: int, sessions: int, minimum_share: float
    ) -> int:
        additional = 0
        while ((dominant_sessions + additional) / (sessions + additional)
               < minimum_share):
            additional += 1
        return additional

    @staticmethod
    def analyze(
        evidence: tuple[PriceActionEvidence, ...],
        *,
        minimum_sample_per_bucket: int = 30,
        minimum_sessions_per_bucket: int = 3,
        minimum_directional_session_share: float = 2 / 3,
    ) -> PriceActionEvidenceReport:
        if not isinstance(evidence, tuple):
            raise TypeError("evidence deve ser tuple.")
        if (isinstance(minimum_sample_per_bucket, bool)
                or not isinstance(minimum_sample_per_bucket, int)
                or minimum_sample_per_bucket < 1):
            raise ValueError("minimum_sample_per_bucket deve ser inteiro positivo.")
        if (isinstance(minimum_sessions_per_bucket, bool)
                or not isinstance(minimum_sessions_per_bucket, int)
                or minimum_sessions_per_bucket < 1):
            raise ValueError("minimum_sessions_per_bucket deve ser inteiro positivo.")
        if (not math.isfinite(minimum_directional_session_share)
                or not 0.5 < minimum_directional_session_share <= 1.0):
            raise ValueError(
                "minimum_directional_session_share deve estar em (0.5, 1.0]."
            )

        grouped: dict[str, list[PriceActionEvidence]] = {}
        for item in evidence:
            if not isinstance(item, PriceActionEvidence):
                raise TypeError("evidence contem item incompatível.")
            key = "|".join(
                value.strip().upper()
                for value in (
                    item.pattern,
                    item.regime,
                    item.timeframe,
                    item.location_context,
                    f"H{item.horizon_steps}",
                )
            )
            grouped.setdefault(key, []).append(item)

        buckets = []
        for key, items in sorted(grouped.items()):
            returns = tuple(float(item.forward_return) for item in items)
            volume_ratios = tuple(
                float(item.volume) / float(item.baseline_volume)
                for item in items
                if item.volume is not None
            )
            session_counts: dict[str, int] = {}
            session_returns: dict[str, list[float]] = {}
            for item in items:
                session_counts[item.session_id] = session_counts.get(item.session_id, 0) + 1
                session_returns.setdefault(item.session_id, []).append(float(item.forward_return))
            sessions = len(session_counts)
            session_means = tuple(
                (session_id, fmean(values))
                for session_id, values in sorted(session_returns.items())
            )
            positive_sessions = sum(value > 0 for _, value in session_means)
            negative_sessions = sum(value < 0 for _, value in session_means)
            dominant_sessions = max(positive_sessions, negative_sessions)
            directional_share = dominant_sessions / sessions
            if positive_sessions > negative_sessions:
                direction = "POSITIVE"
            elif negative_sessions > positive_sessions:
                direction = "NEGATIVE"
            else:
                direction = "NONE"
            recurrence_gap = max(0, minimum_sessions_per_bucket - sessions)
            directional_gap = PriceActionEvidenceObserver._directional_session_gap(
                dominant_sessions=dominant_sessions,
                sessions=sessions,
                minimum_share=minimum_directional_session_share,
            )
            buckets.append(
                PriceActionEvidenceBucket(
                    key=key,
                    observations=len(items),
                    mean_forward_return=fmean(returns),
                    positive_rate=sum(value > 0 for value in returns) / len(returns),
                    mean_volume_ratio=fmean(volume_ratios) if volume_ratios else None,
                    sessions=sessions,
                    maximum_session_share=max(session_counts.values()) / len(items),
                    session_mean_returns=session_means,
                    consistent_direction=direction,
                    directional_session_share=directional_share,
                    sample_sufficient=len(items) >= minimum_sample_per_bucket,
                    cross_session_sufficient=sessions >= minimum_sessions_per_bucket,
                    directional_stability_sufficient=(
                        sessions >= minimum_sessions_per_bucket
                        and direction != "NONE"
                        and directional_share >= minimum_directional_session_share
                    ),
                    additional_observations_lower_bound=max(
                        0, minimum_sample_per_bucket - len(items)
                    ),
                    additional_sessions_lower_bound=max(
                        recurrence_gap, directional_gap
                    ),
                )
            )

        insufficient = tuple(
            bucket.key for bucket in buckets
            if (not bucket.sample_sufficient
                or not bucket.cross_session_sufficient
                or not bucket.directional_stability_sufficient)
        )
        reasons = []
        if not buckets:
            reasons.append("NO_PRICE_ACTION_EVIDENCE")
        if insufficient:
            if any(not bucket.sample_sufficient for bucket in buckets):
                reasons.append("INSUFFICIENT_CONTEXT_SAMPLE")
            if any(not bucket.cross_session_sufficient for bucket in buckets):
                reasons.append("INSUFFICIENT_CROSS_SESSION_RECURRENCE")
            if any(not bucket.directional_stability_sufficient for bucket in buckets):
                reasons.append("DIRECTIONAL_STABILITY_NOT_CONFIRMED")
        return PriceActionEvidenceReport(
            status=(
                "EVIDENCE_READY"
                if buckets and not insufficient
                else "MORE_EVIDENCE_REQUIRED"
            ),
            buckets=tuple(buckets),
            insufficient_buckets=insufficient,
            reasons=tuple(reasons),
        )
