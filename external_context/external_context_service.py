"""
external_context/external_context_service.py

External Context Service

RC2.3 - COLLECTOR -> ENGINE PIPELINE

Responsabilidades:
- executar a coleta externa por provider;
- interpretar o snapshot com ExternalContextEngine;
- devolver somente ExternalMarketState contextual;
- permanecer isolado do núcleo operacional WIN/WDO.

Não:
- gera BUY/SELL;
- escreve Strategy/Score/Risk/Decision;
- executa ordens.
"""

from external_context.external_context_engine import ExternalContextEngine
from external_context.external_market_collector import ExternalMarketCollector
from external_context.external_market_state import ExternalMarketState


class ExternalContextService:
    NAME = "ExternalContextService"
    VERSION = "RC2.4-OBSERVATIONAL-SNAPSHOT"

    def __init__(self, provider=None, collector=None, engine=None, *, observational_snapshots=False):
        if collector is not None and provider is not None:
            raise ValueError("Informe provider ou collector, não ambos.")

        self.collector = collector or ExternalMarketCollector(
            provider=provider, preserve_quotes=observational_snapshots)
        if observational_snapshots and not getattr(self.collector, "preserve_quotes", False):
            raise ValueError("Injected collector must explicitly preserve quotes")
        self.engine = engine or ExternalContextEngine()

        if not callable(getattr(self.collector, "collect", None)):
            raise TypeError("Collector externo deve expor collect().")
        if not callable(getattr(self.engine, "executar", None)):
            raise TypeError("Engine externa deve expor executar(state).")

    def snapshot(self) -> ExternalMarketState:
        """Coleta e interpreta um snapshot externo completo."""
        state = self.collector.collect()
        if not isinstance(state, ExternalMarketState):
            raise TypeError("Collector externo deve retornar ExternalMarketState.")
        return self.engine.executar(state)

    def interpret(self, state: ExternalMarketState) -> ExternalMarketState:
        """Permite interpretar explicitamente um estado já coletado."""
        if not isinstance(state, ExternalMarketState):
            raise TypeError("ExternalContextService esperava ExternalMarketState.")
        return self.engine.executar(state)

    def observational_snapshot(self):
        """Read last completed collection evidence; never collect or infer it from state."""
        return getattr(self.collector, "observational_snapshot", None)

    def audit_observational_snapshot(self, *, reference_timestamp,
                                     maximum_staleness_seconds, symbol_map=None):
        snapshot = self.observational_snapshot()
        if snapshot is None:
            raise ValueError("No preserved per-asset snapshot available")
        return snapshot.audit(reference_timestamp=reference_timestamp,
                              maximum_staleness_seconds=maximum_staleness_seconds,
                              symbol_map=symbol_map)
