"""
models/decision_result.py

Resultado produzido pelo DecisionEngine.
"""

from __future__ import annotations

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class DecisionResult(ResultBase):

    # Decisão final
    action: str = "WAIT"

    # BUY / SELL / NONE
    signal: str = "NONE"

    # Nome do setup escolhido
    setup: str = ""

    # Score utilizado
    score: float = 0.0

    # Risco x Retorno
    risk_reward: float = 0.0

    # Entrada
    entry: float = 0.0

    # Stop
    stop: float = 0.0

    # Alvo
    target: float = 0.0

    @property
    def approved(self):

        return self.action in ("BUY", "SELL")

    def clear(self):

        ResultBase.clear(self)

        self.action = "WAIT"

        self.signal = "NONE"

        self.setup = ""

        self.score = 0.0

        self.risk_reward = 0.0

        self.entry = 0.0

        self.stop = 0.0

        self.target = 0.0