"""One-cycle producer for completed external observational audit evidence.

This module is deliberately not wired into startup or the Bot loop. The caller
owns the provider, reference timestamp, staleness policy and optional symbol-map
snapshot. One produce() call performs exactly one service snapshot and exactly
one completed observational audit over evidence from that same collection.
"""
from copy import deepcopy

from analysis.research.intermarket_context_observer import IntermarketContextObserver
from analysis.research.intermarket_external_context_bridge import ExternalBridgeAudit
from external_context.external_market_state import ExternalMarketState
from external_context.external_observational_snapshot import ExternalObservationalSnapshot


class ExternalObservationalProducerLifecycle:
    NAME = "ExternalObservationalProducerLifecycle"
    VERSION = "RC1.1-SINGLE-COMPLETED-AUDIT"

    def __init__(self, service):
        if not callable(getattr(service, "snapshot", None)):
            raise TypeError("service must expose snapshot()")
        if not callable(getattr(service, "observational_snapshot", None)):
            raise TypeError("service must expose observational_snapshot()")
        self._service = service

    @staticmethod
    def _freeze_and_validate_inputs(
        *,
        reference_timestamp,
        maximum_staleness_seconds,
        symbol_map,
    ):
        # Reuse the existing consumer contract for timestamp/staleness policy
        # without creating a disposable ExternalBridgeAudit.
        IntermarketContextObserver.audit_readiness(
            (),
            required_assets=(),
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds,
        )

        if symbol_map is None:
            return None
        if not isinstance(symbol_map, dict):
            raise TypeError("symbol_map must be ProviderSymbolMap.snapshot() or None")

        frozen_map = deepcopy(symbol_map)
        symbols = frozen_map.get("symbols", {})
        statuses = frozen_map.get("status", {})
        if not isinstance(symbols, dict) or not isinstance(statuses, dict):
            raise TypeError("invalid symbol map contract")
        return frozen_map

    def produce(
        self,
        *,
        reference_timestamp,
        maximum_staleness_seconds,
        symbol_map=None,
    ) -> ExternalBridgeAudit:
        """Collect once and return the single completed audit for that collection."""
        frozen_map = self._freeze_and_validate_inputs(
            reference_timestamp=reference_timestamp,
            maximum_staleness_seconds=maximum_staleness_seconds,
            symbol_map=symbol_map,
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
