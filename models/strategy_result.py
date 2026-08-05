"""
models/strategy_result.py

Resultado produzido pelos Setups.

RC7
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class StrategyResult(ResultBase):

    # ==========================================================
    # IDENTIFICAÇÃO
    # ==========================================================

    setup_id: str = ""

    name: str = ""

    setup_type: str = ""

    signal: str = "NONE"

    # ==========================================================
    # SCORE
    # ==========================================================

    score: float = 0.0

    probability: float = 0.0

    quality: str = "D"

    priority: int = 0

    # ==========================================================
    # RISCO
    # ==========================================================

    risk_reward: float = 0.0

    stop_loss: float = 0.0

    take_profit: float = 0.0

    # ==========================================================
    # CLASSIFICAÇÃO
    # ==========================================================

    def classify(self):

        if self.score >= 95:

            self.quality = "A+"

        elif self.score >= 90:

            self.quality = "A"

        elif self.score >= 80:

            self.quality = "B"

        elif self.score >= 70:

            self.quality = "C"

        else:

            self.quality = "D"

        self.confidence = self.score / 100

        self.probability = self.confidence

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.setup_id = ""

        self.name = ""

        self.setup_type = ""

        self.signal = "NONE"

        self.score = 0.0

        self.probability = 0.0

        self.quality = "D"

        self.priority = 0

        self.risk_reward = 0.0

        self.stop_loss = 0.0

        self.take_profit = 0.0