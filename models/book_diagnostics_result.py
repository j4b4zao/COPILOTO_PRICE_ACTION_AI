"""
models/book_diagnostics_result.py

Resultado passivo para diagnósticos derivados dos livros de Price Action.

RC7 - Observational synthesis.

Regras:
- não altera Score, Risk, Decision ou execução;
- concentra somente diagnósticos experimentais;
- organiza os sinais em Trend Control, Reversal Pressure e Market Environment;
- integração operacional futura exige validação por replay/testes A/B.
"""

from dataclasses import dataclass, field

from models.result_base import ResultBase


@dataclass(slots=True)
class BookDiagnosticsResult(ResultBase):

    passive_only: bool = True

    # Diagnósticos brutos selecionados.
    always_in: dict = field(default_factory=dict)
    trend_strength: dict = field(default_factory=dict)
    breakout_strength: dict = field(default_factory=dict)
    major_trend_reversal: dict = field(default_factory=dict)
    wedge_reversal: dict = field(default_factory=dict)
    tight_trading_range: dict = field(default_factory=dict)

    # Síntese direcional RC3+.
    directional_bias: str = "NONE"
    alignment: str = "NEUTRAL"
    aligned_diagnostics: int = 0
    conflicting_diagnostics: int = 0
    quality_score: float = 0.0

    # Overlay de reversão MTR.
    reversal_watch: bool = False
    reversal_confirmed: bool = False
    reversal_direction: str = "NONE"
    reversal_quality_score: float = 0.0
    trend_reversal_divergence: bool = False

    # Overlay de wedge.
    wedge_watch: bool = False
    wedge_confirmed: bool = False
    wedge_direction: str = "NONE"
    wedge_quality_score: float = 0.0
    mtr_wedge_confluence: bool = False
    mtr_wedge_conflict: bool = False

    # Overlay de ambiente lateral.
    tight_range_active: bool = False
    no_trade_zone_watch: bool = False
    range_breakout_confirmed: bool = False
    range_breakout_direction: str = "NONE"
    directional_signal_range_conflict: bool = False
    range_quality_penalty: float = 0.0

    # ==========================================================
    # RC7 - BLOCOS DE SÍNTESE OBSERVACIONAL
    # ==========================================================

    trend_control: dict = field(default_factory=dict)
    reversal_pressure: dict = field(default_factory=dict)
    market_environment: dict = field(default_factory=dict)

    synthesis_state: str = "NEUTRAL"
    synthesis_direction: str = "NONE"
    synthesis_score: float = 0.0
    caution_count: int = 0

    def clear(self) -> None:

        ResultBase.clear(self)

        self.passive_only = True

        self.always_in.clear()
        self.trend_strength.clear()
        self.breakout_strength.clear()
        self.major_trend_reversal.clear()
        self.wedge_reversal.clear()
        self.tight_trading_range.clear()

        self.directional_bias = "NONE"
        self.alignment = "NEUTRAL"
        self.aligned_diagnostics = 0
        self.conflicting_diagnostics = 0
        self.quality_score = 0.0

        self.reversal_watch = False
        self.reversal_confirmed = False
        self.reversal_direction = "NONE"
        self.reversal_quality_score = 0.0
        self.trend_reversal_divergence = False

        self.wedge_watch = False
        self.wedge_confirmed = False
        self.wedge_direction = "NONE"
        self.wedge_quality_score = 0.0
        self.mtr_wedge_confluence = False
        self.mtr_wedge_conflict = False

        self.tight_range_active = False
        self.no_trade_zone_watch = False
        self.range_breakout_confirmed = False
        self.range_breakout_direction = "NONE"
        self.directional_signal_range_conflict = False
        self.range_quality_penalty = 0.0

        self.trend_control.clear()
        self.reversal_pressure.clear()
        self.market_environment.clear()

        self.synthesis_state = "NEUTRAL"
        self.synthesis_direction = "NONE"
        self.synthesis_score = 0.0
        self.caution_count = 0
