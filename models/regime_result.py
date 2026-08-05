"""
models/regime_result.py

Resultado da classificação do regime do mercado.
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class RegimeResult(ResultBase):

    regime: str = "UNKNOWN"

    trend: str = "NONE"

    volatility: str = "NORMAL"

    strength: float = 0.0

    confidence: float = 0.0

    def clear(self):

        ResultBase.clear(self)

        self.regime = "UNKNOWN"

        self.trend = "NONE"

        self.volatility = "NORMAL"

        self.strength = 0.0

        self.confidence = 0.0