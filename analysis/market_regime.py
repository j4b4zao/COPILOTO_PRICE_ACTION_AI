"""
analysis/market_regime.py

MarketRegimeEngine RC1

Responsável por identificar o regime atual do mercado.

Nenhuma decisão operacional é tomada aqui.

Esta engine apenas classifica o mercado.
"""

from enums.trend import Trend


class MarketRegime:

    NAME = "MarketRegime"

    def __init__(self):

        self.enabled = True

    # =====================================================
    # EXECUTAR
    # =====================================================

    def executar(self, context):

        market = context.market

        result = context.regime

        result.clear()

        if not market.ready:

            return context

        candles = market.last(5)

        c1, c2, c3, c4, c5 = candles

        # ==================================================
        # TREND UP
        # ==================================================

        if (

            c5.high > c4.high

            and

            c5.low > c4.low

        ):

            result.regime = "TREND_UP"

            result.trend = Trend.UP

            result.strength = 0.70

            result.confidence = 0.70

            result.valid = True

            return context

        # ==================================================
        # TREND DOWN
        # ==================================================

        if (

            c5.high < c4.high

            and

            c5.low < c4.low

        ):

            result.regime = "TREND_DOWN"

            result.trend = Trend.DOWN

            result.strength = 0.70

            result.confidence = 0.70

            result.valid = True

            return context

        # ==================================================
        # RANGE
        # ==================================================

        result.regime = "RANGE"

        result.trend = Trend.SIDEWAYS

        result.strength = 0.40

        result.confidence = 0.50

        result.valid = True

        return context