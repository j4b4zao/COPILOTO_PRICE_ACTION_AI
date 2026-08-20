"""
models/alert_result.py

Resultado produzido pelo AlertManager.

RC9.1
"""

from dataclasses import dataclass, field

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

    direction: str = "NONE"

    signal: str = "NONE"

    setup: str = ""

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    score: float = 0.0

    confidence: float = 0.0

    # ==========================================================
    # MOTIVOS
    # ==========================================================

    reasons: list[str] = field(
        default_factory=list
    )

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        ResultBase.clear(self)

        self.timestamp = ""

        self.action = "NONE"

        self.direction = "NONE"

        self.signal = "NONE"

        self.setup = ""

        self.score = 0.0

        self.confidence = 0.0

        self.reasons.clear()