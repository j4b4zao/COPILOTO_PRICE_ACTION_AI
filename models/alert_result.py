"""
models/alert_result.py

Resultado produzido pelo AlertManager.

RC9.2 - ORDER FLOW OBSERVABILITY
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
    # ORDER FLOW EXPERIMENTAL
    # ==========================================================

    order_flow_applied: bool = False

    order_flow_direction: str = "NONE"

    order_flow_sampling_mode: str = "NONE"

    order_flow_contribution: float = 0.0

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

        self.order_flow_applied = False

        self.order_flow_direction = "NONE"

        self.order_flow_sampling_mode = "NONE"

        self.order_flow_contribution = 0.0

        self.reasons.clear()
