"""
models/context_result.py

Resultado produzido pelo ContextEngine.

RC7
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class ContextResult(ResultBase):

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    market_state: str = "UNDEFINED"

    bias: str = "NONE"

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    score: float = 0.0

    confluences: int = 0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.market_state = "UNDEFINED"

        self.bias = "NONE"

        self.score = 0.0

        self.confluences = 0