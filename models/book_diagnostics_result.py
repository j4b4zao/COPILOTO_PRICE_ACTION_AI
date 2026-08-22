"""
models/book_diagnostics_result.py

Resultado passivo para diagnósticos derivados dos livros de Price Action.

RC1

Regras:
- não altera Score, Risk, Decision ou execução;
- concentra somente diagnósticos experimentais;
- cada família fica isolada em um dicionário próprio;
- integração operacional futura exige validação por replay/testes A/B.
"""

from dataclasses import dataclass, field

from models.result_base import ResultBase


@dataclass(slots=True)
class BookDiagnosticsResult(ResultBase):

    # ==========================================================
    # CONTROLE
    # ==========================================================

    passive_only: bool = True

    # ==========================================================
    # DIAGNÓSTICOS RC1
    # ==========================================================

    always_in: dict = field(default_factory=dict)

    trend_strength: dict = field(default_factory=dict)

    # ==========================================================
    # SÍNTESE PASSIVA
    # ==========================================================

    directional_bias: str = "NONE"

    alignment: str = "NEUTRAL"

    quality_score: float = 0.0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self) -> None:

        ResultBase.clear(self)

        self.passive_only = True

        self.always_in.clear()

        self.trend_strength.clear()

        self.directional_bias = "NONE"

        self.alignment = "NEUTRAL"

        self.quality_score = 0.0
