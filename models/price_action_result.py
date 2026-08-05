"""
models/price_action_result.py

Resultado produzido pela PriceAction.

RC7
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

        # Price Action
        self.breakout = False

        self.pullback = False

        self.continuation = False

        self.rejection = False

        self.fake_breakout = False

        # Estatísticas
        self.score = 0.0

        self.confluences = 0