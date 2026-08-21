"""
models/price_action_result.py

Resultado produzido pela PriceAction.

RC7.1 - BAR DYNAMICS
"""

from dataclasses import dataclass

from enums.trend import Trend
from models.result_base import ResultBase


@dataclass(slots=True)
class PriceActionResult(ResultBase):

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    trend: Trend = Trend.UNKNOWN

    bias: str = "NONE"

    structure: str = ""

    # ==========================================================
    # ESTRUTURA
    # ==========================================================

    bos: bool = False

    choch: bool = False

    last_high: float = 0.0

    last_low: float = 0.0

    # ==========================================================
    # PADRÕES
    # ==========================================================

    bullish_engulfing: bool = False

    bearish_engulfing: bool = False

    hammer: bool = False

    shooting_star: bool = False

    doji: bool = False

    inside_bar: bool = False

    outside_bar: bool = False

    # ==========================================================
    # DINÂMICA DA BARRA - BROOKS TRENDS CAP. 2
    # ==========================================================

    bar_classification: str = "UNKNOWN"

    bar_direction: str = "NONE"

    body_ratio: float = 0.0

    relative_body_ratio: float = 0.0

    close_position: float = 0.5

    trend_bar_strength: str = "UNKNOWN"

    climax_direction: str = "NONE"

    climax_length: int = 0

    climax_active: bool = False

    climax_ended: bool = False

    pause_detected: bool = False

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    breakout: bool = False

    pullback: bool = False

    continuation: bool = False

    rejection: bool = False

    fake_breakout: bool = False

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    score: float = 0.0

    confluences: int = 0

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        # Limpa os campos da classe base
        ResultBase.clear(self)

        # Contexto
        self.trend = Trend.UNKNOWN

        self.bias = "NONE"

        self.structure = ""

        # Estrutura
        self.bos = False

        self.choch = False

        self.last_high = 0.0

        self.last_low = 0.0

        # Padrões
        self.bullish_engulfing = False

        self.bearish_engulfing = False

        self.hammer = False

        self.shooting_star = False

        self.doji = False

        self.inside_bar = False

        self.outside_bar = False

        self.bar_classification = "UNKNOWN"

        self.bar_direction = "NONE"

        self.body_ratio = 0.0

        self.relative_body_ratio = 0.0

        self.close_position = 0.5

        self.trend_bar_strength = "UNKNOWN"

        self.climax_direction = "NONE"

        self.climax_length = 0

        self.climax_active = False

        self.climax_ended = False

        self.pause_detected = False

        # Price Action
        self.breakout = False

        self.pullback = False

        self.continuation = False

        self.rejection = False

        self.fake_breakout = False

        # Estatísticas
        self.score = 0.0

        self.confluences = 0
