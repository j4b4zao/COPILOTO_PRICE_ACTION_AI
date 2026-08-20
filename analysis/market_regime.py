"""
analysis/market_regime.py

Classificação do regime atual do mercado.

RC2.4 - CLOSED CANDLE REGIME

Responsabilidades:

- usar somente candles fechados;
- classificar tendência de alta, baixa ou range;
- registrar força, confiança e motivo;
- não tomar decisão operacional.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend


class MarketRegime(EngineBase):

    NAME = "MarketRegime"

    VERSION = "RC2.4-CLOSED-CANDLE"

    ENABLED = True

    PRIORITY = 10

    MIN_CLOSED_CANDLES = 5

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        result = context.regime

        result.clear()

        result.start()

        result.source = self.NAME

        candles = market.candles.all()

        # ------------------------------------------------------
        # O último candle está em formação e não participa da
        # classificação do regime.
        # ------------------------------------------------------

        if len(candles) < self.MIN_CLOSED_CANDLES + 1:

            result.skip()

            result.add_reason(
                "São necessários pelo menos cinco candles "
                "fechados e um candle atual."
            )

            return context

        closed_candles = candles[:-1]

        recent_closed = closed_candles[
            -self.MIN_CLOSED_CANDLES:
        ]

        previous = recent_closed[-2]

        current = recent_closed[-1]

        # A volatilidade permanece neutra nesta primeira
        # integração. Uma escala própria será incorporada em
        # etapa isolada, sem alterar a classificação direcional.
        result.volatility = "NORMAL"

        # ======================================================
        # TENDÊNCIA DE ALTA
        # ======================================================

        if (
            current.high > previous.high
            and current.low > previous.low
        ):

            result.regime = "TREND_UP"

            result.trend = Trend.UP

            result.strength = 0.70

            result.confidence = 0.70

            result.add_reason(
                "Últimos candles fechados confirmam "
                "máxima e mínima ascendentes."
            )

            result.validate()

            return context

        # ======================================================
        # TENDÊNCIA DE BAIXA
        # ======================================================

        if (
            current.high < previous.high
            and current.low < previous.low
        ):

            result.regime = "TREND_DOWN"

            result.trend = Trend.DOWN

            result.strength = 0.70

            result.confidence = 0.70

            result.add_reason(
                "Últimos candles fechados confirmam "
                "máxima e mínima descendentes."
            )

            result.validate()

            return context

        # ======================================================
        # RANGE
        # ======================================================

        result.regime = "RANGE"

        result.trend = Trend.SIDEWAYS

        result.strength = 0.40

        result.confidence = 0.50

        result.add_reason(
            "Últimos candles fechados não confirmam "
            "direção conjunta de máximas e mínimas."
        )

        result.validate()

        return context
