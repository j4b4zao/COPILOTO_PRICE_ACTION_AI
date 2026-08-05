"""
models/score_result.py

Resultado produzido pelo ScoreEngine.

Responsável por armazenar o score final da análise
e o detalhamento da pontuação de cada engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from models.result_base import ResultBase


@dataclass(slots=True)
class ScoreResult(ResultBase):
    """
    Resultado final do ScoreEngine.
    """

    # ==========================================================
    # SCORE FINAL
    # ==========================================================

    total: float = 0.0

    # ==========================================================
    # DETALHAMENTO DA PONTUAÇÃO
    # ==========================================================

    breakdown: dict[str, float] = field(default_factory=dict)

    # ==========================================================
    # CLASSIFICAÇÃO
    # ==========================================================

    grade: str = "REPROVADO"

    # ==========================================================
    # DIREÇÃO SUGERIDA
    # ==========================================================

    bias: str = "NONE"

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def add_score(self, engine: str, value: float) -> None:
        """
        Registra a contribuição de uma engine.
        """

        self.breakdown[engine] = round(float(value), 2)

    def calculate_total(self) -> None:
        """
        Recalcula automaticamente o score total.
        """

        self.total = round(sum(self.breakdown.values()), 2)

    def classify(self) -> None:
        """
        Classificação automática da qualidade da operação.
        """

        if self.total >= 90:
            self.grade = "A+"

        elif self.total >= 80:
            self.grade = "A"

        elif self.total >= 70:
            self.grade = "B"

        elif self.total >= 60:
            self.grade = "C"

        else:
            self.grade = "REPROVADO"

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self) -> None:

        # Limpa os campos herdados
        ResultBase.clear(self)

        # Limpa os campos específicos
        self.total = 0.0

        self.breakdown.clear()

        self.grade = "REPROVADO"

        self.bias = "NONE"