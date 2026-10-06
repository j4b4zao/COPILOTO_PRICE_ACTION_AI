"""Explicit configuration boundary for external observational presentation.

This boundary composes already-audited components but does not activate them.
Construction performs no fetch, clock read, rendering, runtime bootstrap or
operational mutation. The caller remains the owner of provider selection,
reference timestamp, staleness policy and optional provider identity evidence.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from analysis.research.intermarket_context_observer import IntermarketContextObserver
from external_context.external_context_service import ExternalContextService
from external_context.external_observational_presentation_cycle import (
    ExternalObservationalPresentationCycle,
)
from external_context.external_observational_producer_lifecycle import (
    ExternalObservationalProducerLifecycle,
)


@dataclass(frozen=True, slots=True)
class ExternalObservationalCyclePolicy:
    reference_timestamp: datetime
    maximum_staleness_seconds: float
    symbol_map: dict | None = None

    def __post_init__(self):
        IntermarketContextObserver.audit_readiness(
            (),
            required_assets=(),
            reference_timestamp=self.reference_timestamp,
            maximum_staleness_seconds=self.maximum_staleness_seconds,
        )
        if self.symbol_map is not None:
            if not isinstance(self.symbol_map, dict):
                raise TypeError("symbol_map must be ProviderSymbolMap.snapshot() or None")
            frozen = deepcopy(self.symbol_map)
            symbols = frozen.get("symbols", {})
            statuses = frozen.get("status", {})
            if not isinstance(symbols, dict) or not isinstance(statuses, dict):
                raise TypeError("invalid symbol map contract")
            object.__setattr__(self, "symbol_map", frozen)


class ExternalObservationalCycleBoundary:
    NAME = "ExternalObservationalCycleBoundary"
    VERSION = "RC1"

    def __init__(self, *, provider):
        if not callable(getattr(provider, "fetch", None)):
            raise TypeError("provider must expose fetch(symbol)")
        self._service = ExternalContextService(
            provider=provider,
            observational_snapshots=True,
        )
        self._producer = ExternalObservationalProducerLifecycle(self._service)
        self._presentation = ExternalObservationalPresentationCycle(self._producer)

    def produce(self, policy: ExternalObservationalCyclePolicy):
        if not isinstance(policy, ExternalObservationalCyclePolicy):
            raise TypeError("policy must be ExternalObservationalCyclePolicy")
        return self._presentation.produce_for_presentation(
            reference_timestamp=policy.reference_timestamp,
            maximum_staleness_seconds=policy.maximum_staleness_seconds,
            symbol_map=policy.symbol_map,
        )

    def present(self, bot, context, policy: ExternalObservationalCyclePolicy):
        if not isinstance(policy, ExternalObservationalCyclePolicy):
            raise TypeError("policy must be ExternalObservationalCyclePolicy")
        return self._presentation.present(
            bot,
            context,
            reference_timestamp=policy.reference_timestamp,
            maximum_staleness_seconds=policy.maximum_staleness_seconds,
            symbol_map=policy.symbol_map,
        )
