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
    pattern: str
    regime: str
    timeframe: str
    location_context: str
    forward_return: float
    volume: float | None = None
    baseline_volume: float | None = None

    def __post_init__(self) -> None:
        for name in ("pattern", "regime", "timeframe", "location_context"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} deve ser texto nao vazio.")
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
    sample_sufficient: bool


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
    def analyze(
        evidence: tuple[PriceActionEvidence, ...],
        *,
        minimum_sample_per_bucket: int = 30,
    ) -> PriceActionEvidenceReport:
        if not isinstance(evidence, tuple):
            raise TypeError("evidence deve ser tuple.")
        if (isinstance(minimum_sample_per_bucket, bool)
                or not isinstance(minimum_sample_per_bucket, int)
                or minimum_sample_per_bucket < 1):
            raise ValueError("minimum_sample_per_bucket deve ser inteiro positivo.")

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
            buckets.append(
                PriceActionEvidenceBucket(
                    key=key,
                    observations=len(items),
                    mean_forward_return=fmean(returns),
                    positive_rate=sum(value > 0 for value in returns) / len(returns),
                    mean_volume_ratio=fmean(volume_ratios) if volume_ratios else None,
                    sample_sufficient=len(items) >= minimum_sample_per_bucket,
                )
            )

        insufficient = tuple(bucket.key for bucket in buckets if not bucket.sample_sufficient)
        reasons = []
        if not buckets:
            reasons.append("NO_PRICE_ACTION_EVIDENCE")
        if insufficient:
            reasons.append("INSUFFICIENT_CONTEXT_SAMPLE")
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
