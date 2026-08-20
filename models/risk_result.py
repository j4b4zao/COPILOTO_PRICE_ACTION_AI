"""
models/risk_result.py

Resultado produzido pelo RiskManager.

RC9.1
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class RiskResult(ResultBase):

    # ==========================================================
    # APROVAÇÃO
    # ==========================================================

    approved: bool = False

    risk_level: str = "UNKNOWN"

    # ==========================================================
    # SCORE
    # ==========================================================

    risk_score: float = 0.0

    # ==========================================================
    # NÍVEIS DA OPERAÇÃO
    # ==========================================================

    entry_price: float = 0.0

    stop_loss: float = 0.0

    take_profit: float = 0.0

    risk_reward: float = 0.0

    # ==========================================================
    # GERENCIAMENTO
    # ==========================================================

    position_size: float = 0.0

    # ==========================================================
    # CONFLUÊNCIAS
    # ==========================================================

    confluences: int = 0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.approved = False

        self.risk_level = "UNKNOWN"

        self.risk_score = 0.0

        self.entry_price = 0.0

        self.stop_loss = 0.0

        self.take_profit = 0.0

        self.risk_reward = 0.0

        self.position_size = 0.0

        self.confluences = 0