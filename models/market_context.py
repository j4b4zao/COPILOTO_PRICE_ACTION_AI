"""
core/market_context.py

Barramento central de comunicação entre todas as engines
do COPILOTO PRICE ACTION AI.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from core.market_state import MarketState
from models.result_base import ResultBase


# LEGACY - DO NOT USE
class MarketContext:

    def __init__(self):

        # ==========================================
        # ESTADO DO MERCADO
        # ==========================================

        # Nunca deve ser None.
        # O Collector depende deste objeto.
        self.market = MarketState()

        # ==========================================
        # RESULTADOS DAS ENGINES
        # ==========================================

        self._results: Dict[str, ResultBase] = {}

        # ==========================================
        # LOG
        # ==========================================

        self.logs: List[str] = []

        # ==========================================
        # ESTATÍSTICAS
        # ==========================================

        self.statistics = {}

        # ==========================================
        # CONFIGURAÇÕES
        # ==========================================

        self.config = {}

    # ==========================================================
    # REGISTRO
    # ==========================================================

    def register(self, result: ResultBase) -> None:

        self._results[result.__class__.__name__] = result

    # ==========================================================
    # CONSULTA
    # ==========================================================

    def get(self, result_type: Type[ResultBase]) -> Optional[ResultBase]:

        return self._results.get(result_type.__name__)

    # ==========================================================
    # CONSULTA OBRIGATÓRIA
    # ==========================================================

    def require(self, result_type: Type[ResultBase]) -> ResultBase:

        result = self.get(result_type)

        if result is None:
            raise RuntimeError(
                f"{result_type.__name__} não encontrado no MarketContext."
            )

        return result

    # ==========================================================
    # EXISTE?
    # ==========================================================

    def has(self, result_type: Type[ResultBase]) -> bool:

        return result_type.__name__ in self._results

    # ==========================================================
    # LISTA DE RESULTADOS
    # ==========================================================

    def all_results(self):

        return list(self._results.values())

    # ==========================================================
    # ÚLTIMO RESULTADO
    # ==========================================================

    def last_result(self):

        if not self._results:
            return None

        return list(self._results.values())[-1]

    # ==========================================================
    # LOG
    # ==========================================================

    def log(self, message: str):

        self.logs.append(message)

    # ==========================================================
    # RESUMO
    # ==========================================================

    def summary(self):

        return {
            name: result.valid
            for name, result in self._results.items()
        }

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        self.market.clear()

        self._results.clear()

        self.logs.clear()

        self.statistics.clear()

        self.config.clear()
