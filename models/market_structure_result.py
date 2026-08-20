"""
models/market_structure_result.py

Resultado da análise estrutural do mercado.

Responsável por armazenar toda a leitura da
estrutura produzida pela MarketStructure.

RC15
"""

from dataclasses import dataclass

from enums.trend import Trend

from models.result_base import ResultBase


@dataclass(slots=True)
class MarketStructureResult(ResultBase):

    # ==========================================================
    # Estrutura
    # ==========================================================

    hh: bool = False
    hl: bool = False

    lh: bool = False
    ll: bool = False

    # ==========================================================
    # Tendência
    # ==========================================================

    trend: Trend = Trend.UNKNOWN

    # ==========================================================
    # Smart Money
    # ==========================================================

    bos_up: bool = False
    bos_down: bool = False

    choch: bool = False

    # ==========================================================
    # Swings
    # ==========================================================

    last_high: float = 0.0
    last_low: float = 0.0

    swing_high: float = 0.0
    swing_low: float = 0.0

    # ==========================================================
    # Classificação
    # ==========================================================

    structure_type: str = "UNKNOWN"

    # ==========================================================
    # LIMPAR
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.hh = False
        self.hl = False

        self.lh = False
        self.ll = False

        self.trend = Trend.UNKNOWN

        self.bos_up = False
        self.bos_down = False

        self.choch = False

        self.last_high = 0.0
        self.last_low = 0.0

        self.swing_high = 0.0
        self.swing_low = 0.0

        self.structure_type = "UNKNOWN"