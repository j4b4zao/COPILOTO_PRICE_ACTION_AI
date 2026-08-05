"""
models/volume_result.py

Resultado produzido pela VolumeAnalysis.

RC2
"""

from dataclasses import dataclass

from models.result_base import ResultBase
from enums.volume_level import VolumeLevel


@dataclass(slots=True)
class VolumeResult(ResultBase):

    # ==========================================================
    # CLASSIFICAÇÃO
    # ==========================================================

    level: VolumeLevel = VolumeLevel.LOW

    # ==========================================================
    # FLAGS
    # ==========================================================

    high: bool = False

    medium: bool = False

    low: bool = False

    # ==========================================================
    # EVENTOS
    # ==========================================================

    climax_buy: bool = False

    climax_sell: bool = False

    absorption_buy: bool = False

    absorption_sell: bool = False

    increasing: bool = False

    decreasing: bool = False

    # ==========================================================
    # DADOS
    # ==========================================================

    current: float = 0.0

    average: float = 0.0

    strength: float = 0.0

    confluences: int = 0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.level = VolumeLevel.LOW

        self.high = False
        self.medium = False
        self.low = False

        self.climax_buy = False
        self.climax_sell = False

        self.absorption_buy = False
        self.absorption_sell = False

        self.increasing = False
        self.decreasing = False

        self.current = 0.0

        self.average = 0.0

        self.strength = 0.0

        self.confluences = 0