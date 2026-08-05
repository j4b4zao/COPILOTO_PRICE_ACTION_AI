"""
analysis/market_structure.py

Engine responsável por identificar
a estrutura do mercado.
"""

from ai.engine_base import EngineBase
from enums.trend import Trend


class MarketStructure(EngineBase):

    NAME = "MarketStructure"

    VERSION = "RC2"

    ENABLED = True

    PRIORITY = 20

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        if not market.ready:
            return context

        candles = market.candles.last_n(5)

        if len(candles) < 5:
            return context

        c1, c2, c3, c4, c5 = candles

        result = context.structure
        evidence = context.evidence

        result.clear()

        previous_trend = result.trend

        # ======================================================
        # SWINGS
        # ======================================================

        if c5.high > c4.high:

            result.hh = True
            evidence.add("HH")

        if c5.low > c4.low:

            result.hl = True
            evidence.add("HL")

        if c5.high < c4.high:

            result.lh = True
            evidence.add("LH")

        if c5.low < c4.low:

            result.ll = True
            evidence.add("LL")

        # ======================================================
        # TENDÊNCIA
        # ======================================================

        if result.hh and result.hl:

            result.trend = Trend.UP
            result.confidence = 0.70

            evidence.add("TREND_UP")

        elif result.lh and result.ll:

            result.trend = Trend.DOWN
            result.confidence = 0.70

            evidence.add("TREND_DOWN")

        else:

            result.trend = Trend.SIDEWAYS
            result.confidence = 0.40

            evidence.add("SIDEWAYS")

        # ======================================================
        # BOS
        # ======================================================

        if result.trend == Trend.UP:

            if c5.close > c4.high:

                result.bos_up = True
                result.confidence += 0.10

                evidence.add("BOS_UP")

        elif result.trend == Trend.DOWN:

            if c5.close < c4.low:

                result.bos_down = True
                result.confidence += 0.10

                evidence.add("BOS_DOWN")

        # ======================================================
        # CHOCH
        # ======================================================

        if previous_trend != Trend.UNKNOWN:

            if previous_trend != result.trend:

                result.choch = True
                result.confidence += 0.10

                evidence.add("CHOCH")

        # ======================================================
        # SWINGS
        # ======================================================

        result.last_high = c5.high
        result.last_low = c5.low

        result.valid = True

        return context