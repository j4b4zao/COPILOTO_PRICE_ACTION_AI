"""
models/fair_value_gap_result.py

Resultado da análise de Fair Value Gap (FVG).

RC11
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class FairValueGapResult(ResultBase):

    # ==========================================================
    # DIREÇÃO
    # ==========================================================

    bullish: bool = False

    bearish: bool = False

    # ==========================================================
    # REGIÃO
    # ==========================================================

    high: float = 0.0

    low: float = 0.0

    midpoint: float = 0.0

    # ==========================================================
    # STATUS
    # ==========================================================

    filled: bool = False

    tested: bool = False

    touches: int = 0

    # ==========================================================
    # QUALIDADE
    # ==========================================================

    strength: float = 0.0

    score: float = 0.0

    confidence: float = 0.0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        super().clear()

        self.bullish = False
        self.bearish = False

        self.high = 0.0
        self.low = 0.0
        self.midpoint = 0.0

        self.filled = False
        self.tested = False
        self.touches = 0

        self.strength = 0.0
        self.score = 0.0
        self.confidence = 0.0