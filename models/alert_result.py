"""
models/alert_result.py

Resultado produzido pelo AlertManager.

RC7
"""

from dataclasses import dataclass

from models.result_base import ResultBase


@dataclass(slots=True)
class AlertResult(ResultBase):

    # ==========================================================
    # IDENTIFICAÇÃO
    # ==========================================================

    timestamp: str = ""

    # ==========================================================
    # ALERTA
    # ==========================================================

    action: str = "NONE"

    signal: str = "NONE"

    setup: str = ""

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    score: float = 0.0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.timestamp = ""

        self.action = "NONE"

        self.signal = "NONE"

        self.setup = ""

        self.score = 0.0