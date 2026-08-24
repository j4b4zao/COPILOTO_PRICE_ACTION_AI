"""
models/decision_result.py

Resultado produzido pelo DecisionEngine.

RC9.1
"""

from __future__ import annotations

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class DecisionResult(ResultBase):

    # ==========================================================
    # DECISÃO FINAL
    # ==========================================================

    action: str = "WAIT"

    # ==========================================================
    # DIREÇÃO
    # ==========================================================

    direction: str = "NONE"

    # ==========================================================
    # SINAL
    # ==========================================================

    signal: str = "NONE"

    # ==========================================================
    # SETUP
    # ==========================================================

    setup: str = ""

    # ==========================================================
    # SCORE
    # ==========================================================

    score: float = 0.0

    # ==========================================================
    # RISCO / RETORNO
    # ==========================================================

    risk_reward: float = 0.0

    # ==========================================================
    # NÍVEIS
    # ==========================================================

    entry: float = 0.0

    stop: float = 0.0

    target: float = 0.0

    # ==========================================================
    # APROVAÇÃO
    # ==========================================================

    @property
    def approved(self) -> bool:

        return self.action in (
            "BUY",
            "SELL",
        )

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.action = "WAIT"

        self.direction = "NONE"

        self.signal = "NONE"

        self.setup = ""

        self.score = 0.0

        self.risk_reward = 0.0

        self.entry = 0.0

        self.stop = 0.0

        self.target = 0.0