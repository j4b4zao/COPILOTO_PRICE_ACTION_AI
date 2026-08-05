"""
models/order_block_result.py

Resultado da análise de Order Blocks.

RC10
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class OrderBlockResult(ResultBase):

    # ==========================================================
    # DETECÇÃO
    # ==========================================================

    bullish: bool = False

    bearish: bool = False

    # ==========================================================
    # REGIÃO
    # ==========================================================

    high: float = 0.0

    low: float = 0.0

    entry_price: float = 0.0

    # ==========================================================
    # STATUS
    # ==========================================================

    mitigated: bool = False

    tested: bool = False

    touches: int = 0

    # ==========================================================
    # QUALIDADE
    # ==========================================================

    strength: float = 0.0

    score: float = 0.0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.bullish = False
        self.bearish = False

        self.high = 0.0
        self.low = 0.0
        self.entry_price = 0.0

        self.mitigated = False
        self.tested = False
        self.touches = 0

        self.strength = 0.0
        self.score = 0.0