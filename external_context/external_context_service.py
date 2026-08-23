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
    VERSION = "RC2.3-COLLECTOR-ENGINE-PIPELINE"

    def __init__(self, provider=None, collector=None, engine=None):
        if collector is not None and provider is not None:
            raise ValueError("Informe provider ou collector, não ambos.")

        self.collector = collector or ExternalMarketCollector(provider=provider)
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
