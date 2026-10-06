"""One-cycle producer for completed external observational audit evidence.

This module is deliberately not wired into startup or the Bot loop.  The caller
owns the provider, reference timestamp, staleness policy and optional symbol-map
snapshot.  One produce() call performs exactly one service snapshot and audits
only the observational evidence preserved by that same collection.
"""
from copy import deepcopy

from analysis.research.intermarket_external_context_bridge import (
    ExternalBridgeAudit,
    IntermarketExternalContextBridge,
)
from external_context.external_market_state import ExternalMarketState
from external_context.external_observational_snapshot import (
    ExternalObservationalSnapshot,
)


class ExternalObservationalProducerLifecycle:
    NAME = "ExternalObservationalProducerLifecycle"
    VERSION = "RC1"

    def __init__(self, service):
        if not callable(getattr(service, "snapshot", None)):
            raise TypeError("service must expose snapshot()")
        if not callable(getattr(service, "observational_snapshot", None)):
            raise TypeError("service must expose observational_snapshot()")
        self._service = service

    def produce(
        self,
        *,
        reference_timestamp,
        maximum_staleness_seconds,
        symbol_map=None,
    ) -> ExternalBridgeAudit:
        """Collect once and return the completed audit for that exact collection."""
        # Freeze caller-owned identity evidence before collection.  This prevents a
        # mutable mapping from changing provenance between fetch and audit.
        frozen_map = deepcopy(symbol_map) if symbol_map is not None else None

        # Validate caller-owned policy before any provider fetch.  The bridge is
        # the existing authority for timestamp, staleness and symbol-map contracts.
        IntermarketExternalContextBridge.audit(
            {},
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds,
            symbol_map=frozen_map,
        )

        state = self._service.snapshot()
        if not isinstance(state, ExternalMarketState):
            raise TypeError("service snapshot must return ExternalMarketState")

        snapshot = self._service.observational_snapshot()
        if not isinstance(snapshot, ExternalObservationalSnapshot):
            raise ValueError(
                "completed collection did not preserve observational evidence"
            )

        audit = snapshot.audit(
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds,
            symbol_map=frozen_map,
        )
        if not isinstance(audit, ExternalBridgeAudit):
            raise TypeError("observational audit returned invalid envelope")
        if audit.observational_only is not True:
            raise ValueError("producer accepts observational-only audit evidence")
        return audit
