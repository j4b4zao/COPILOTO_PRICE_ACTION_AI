"""
models/structure_result.py

Resultado produzido pela MarketStructure.

RC8
"""

from dataclasses import dataclass
from typing import Any

from enums.trend import Trend
from models.result_base import ResultBase


@dataclass(slots=True)
class StructureResult(ResultBase):

    # ==========================================================
    # TENDÊNCIA
    # ==========================================================

    trend: Trend = Trend.UNKNOWN

    # ==========================================================
    # SWINGS
    # ==========================================================

    swing_high: Any = None

    swing_low: Any = None

    hh: bool = False

    hl: bool = False

    lh: bool = False

    ll: bool = False

    # ==========================================================
    # MARKET STRUCTURE
    # ==========================================================

    bos_up: bool = False

    bos_down: bool = False

    choch: bool = False

    # ==========================================================
    # ÚLTIMA ESTRUTURA
    # ==========================================================

    last_high: float = 0.0

    last_low: float = 0.0

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    score: float = 0.0

    confluences: int = 0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        # Limpa os campos da classe base
        ResultBase.clear(self)

        # Tendência
        self.trend = Trend.UNKNOWN

        # Swings
        self.swing_high = None
        self.swing_low = None

        self.hh = False
        self.hl = False
        self.lh = False
        self.ll = False

        # Estrutura
        self.bos_up = False
        self.bos_down = False
        self.choch = False

        # Últimos níveis
        self.last_high = 0.0
        self.last_low = 0.0

        # Estatísticas
        self.score = 0.0
        self.confluences = 0