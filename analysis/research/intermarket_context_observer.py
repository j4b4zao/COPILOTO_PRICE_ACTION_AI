"""Contrato observacional para dados intermercado sincronizados."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class IntermarketPoint:
    asset: str
    timestamp: datetime
    value: float

    def __post_init__(self) -> None:
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("asset deve ser texto nao vazio.")
        if not isinstance(self.timestamp, datetime) or self.timestamp.tzinfo is None:
            raise ValueError("timestamp deve possuir timezone.")
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise TypeError("value deve ser numerico.")
        if not math.isfinite(float(self.value)):
            raise ValueError("value deve ser finito.")


@dataclass(frozen=True, slots=True)
class IntermarketReadiness:
    status: str
    reference_timestamp: datetime
    available_assets: tuple[str, ...]
    missing_assets: tuple[str, ...]
    stale_assets: tuple[str, ...]
    maximum_observed_skew_seconds: float | None
    observational_only: bool = True
    predictive_claim_allowed: bool = False
    score_influence_allowed: bool = False
    risk_influence_allowed: bool = False
    decision_influence_allowed: bool = False
    order_execution_allowed: bool = False


class IntermarketContextObserver:
    NAME = "IntermarketContextObserver"
    VERSION = "RC1"

    @staticmethod
    def audit_readiness(
        points: tuple[IntermarketPoint, ...],
        *,
        required_assets: tuple[str, ...],
        reference_timestamp: datetime,
        maximum_staleness_seconds: float,
    ) -> IntermarketReadiness:
        if not isinstance(points, tuple) or not isinstance(required_assets, tuple):
            raise TypeError("points e required_assets devem ser tuple.")
        if reference_timestamp.tzinfo is None:
            raise ValueError("reference_timestamp deve possuir timezone.")
        if maximum_staleness_seconds < 0 or not math.isfinite(maximum_staleness_seconds):
            raise ValueError("maximum_staleness_seconds deve ser finito e nao negativo.")

        required = tuple(dict.fromkeys(asset.strip().upper() for asset in required_assets))
        if any(not asset for asset in required):
            raise ValueError("required_assets contem nome vazio.")
        latest: dict[str, IntermarketPoint] = {}
        for point in points:
            if not isinstance(point, IntermarketPoint):
                raise TypeError("points contem item incompatível.")
            key = point.asset.strip().upper()
            if key not in latest or point.timestamp > latest[key].timestamp:
                latest[key] = point

        missing = tuple(asset for asset in required if asset not in latest)
        ages = {
            asset: (reference_timestamp - latest[asset].timestamp).total_seconds()
            for asset in required if asset in latest
        }
        stale = tuple(
            asset for asset, age in ages.items()
            if age < 0 or age > maximum_staleness_seconds
        )
        return IntermarketReadiness(
            status="DATA_READY" if not missing and not stale else "DATA_NOT_READY",
            reference_timestamp=reference_timestamp,
            available_assets=tuple(asset for asset in required if asset in latest),
            missing_assets=missing,
            stale_assets=stale,
            maximum_observed_skew_seconds=max(ages.values()) if ages else None,
        )
