"""
models/book_diagnostics_result.py

Resultado passivo para diagnósticos derivados dos livros de Price Action.

RC3 - Experimental breakout-strength observation.

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

    passive_only: bool = True

    always_in: dict = field(default_factory=dict)
    trend_strength: dict = field(default_factory=dict)
    breakout_strength: dict = field(default_factory=dict)

    directional_bias: str = "NONE"
    alignment: str = "NEUTRAL"
    aligned_diagnostics: int = 0
    conflicting_diagnostics: int = 0
    quality_score: float = 0.0

    def clear(self) -> None:

        ResultBase.clear(self)

        self.passive_only = True

        self.always_in.clear()
        self.trend_strength.clear()
        self.breakout_strength.clear()

        self.directional_bias = "NONE"
        self.alignment = "NEUTRAL"
        self.aligned_diagnostics = 0
        self.conflicting_diagnostics = 0
        self.quality_score = 0.0
