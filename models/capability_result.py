"""
models/capability_result.py

Resultado padrão produzido por qualquer detector
de capacidade operacional do COPILOTO PRICE ACTION AI.
"""

from dataclasses import dataclass, field

from models.result_base import ResultBase


@dataclass(slots=True)
class CapabilityResult(ResultBase):

    # Nome da capacidade detectada
    name: str = ""

    # Recomendação operacional
    recommendation: str = "AGUARDAR"

    # Critérios atendidos
    reasons: list[str] = field(default_factory=list)

    # Alertas encontrados
    warnings: list[str] = field(default_factory=list)

    def clear(self):

        super().clear()

        self.name = ""

        self.recommendation = "AGUARDAR"

        self.reasons.clear()

        self.warnings.clear()