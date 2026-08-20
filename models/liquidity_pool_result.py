"""
models/liquidity_pool_result.py

Liquidity Pool Result

RC13

Representa a interpretação institucional das regiões
de liquidez identificadas pelo COPILOTO PRICE ACTION AI.
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class LiquidityPoolResult(ResultBase):

    # ==========================================================
    # BUY SIDE
    # ==========================================================

    buy_side_pool: bool = False

    # ==========================================================
    # SELL SIDE
    # ==========================================================

    sell_side_pool: bool = False

    # ==========================================================
    # RANGE
    # ==========================================================

    range_pool: bool = False

    # ==========================================================
    # DIREÇÃO
    # ==========================================================

    bullish: bool = False

    bearish: bool = False

    # ==========================================================
    # FORÇA
    # ==========================================================

    strength: float = 0.0

    score: float = 0.0

    # ==========================================================
    # INFORMAÇÕES
    # ==========================================================

    nearest_pool: str = ""

    nearest_price: float = 0.0

    distance: float = 0.0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.buy_side_pool = False
        self.sell_side_pool = False
        self.range_pool = False

        self.bullish = False
        self.bearish = False

        self.strength = 0.0
        self.score = 0.0

        self.nearest_pool = ""
        self.nearest_price = 0.0
        self.distance = 0.0
