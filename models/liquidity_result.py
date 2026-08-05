"""
models/liquidity_result.py

Resultado da análise de liquidez do mercado.

RC7
"""

from __future__ import annotations

from dataclasses import dataclass

from models.result_base import ResultBase
from models.swing import Swing


@dataclass(slots=True)
class LiquidityResult(ResultBase):
    """
    Resultado produzido pela LiquidityAnalysis.
    """

    # ==========================================================
    # Equal High / Equal Low
    # ==========================================================

    equal_highs: bool = False
    equal_lows: bool = False

    # ==========================================================
    # Liquidez
    # ==========================================================

    buy_side: bool = False
    sell_side: bool = False

    # ==========================================================
    # Sweeps
    # ==========================================================

    sweep_up: bool = False
    sweep_down: bool = False

    # ==========================================================
    # Informações adicionais
    # ==========================================================

    liquidity_price: float = 0.0

    nearest_high: Swing | None = None
    nearest_low: Swing | None = None

    touches: int = 0

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    confluences: int = 0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self) -> None:

        ResultBase.clear(self)

        self.equal_highs = False
        self.equal_lows = False

        self.buy_side = False
        self.sell_side = False

        self.sweep_up = False
        self.sweep_down = False

        self.liquidity_price = 0.0

        self.nearest_high = None
        self.nearest_low = None

        self.touches = 0

        self.confluences = 0