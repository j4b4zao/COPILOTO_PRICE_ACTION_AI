"""
analysis/smart_money/imbalance.py

Imbalance Engine

RC12
"""

from ai.engine_base import EngineBase


class Imbalance(EngineBase):

    NAME = "Imbalance"

    VERSION = "RC12"

    ENABLED = True

    PRIORITY = 52

    BASE_SCORE = 60

    STRONG_IMBALANCE = 20

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context):

        market = context.market

        if not market.ready:
            return context

        candles = market.candles.last_n(3)

        if len(candles) < 3:
            return context

        result = context.imbalance

        evidence = context.evidence

        result.clear()

        c1, c2, c3 = candles

        # ======================================================
        # BULLISH IMBALANCE
        # ======================================================

        if c1.high < c3.low:

            result.valid = True

            result.bullish = True

            result.high = c3.low

            result.low = c1.high

            evidence.add("BULLISH_IMBALANCE")

        # ======================================================
        # BEARISH IMBALANCE
        # ======================================================

        elif c1.low > c3.high:

            result.valid = True

            result.bearish = True

            result.high = c1.low

            result.low = c3.high

            evidence.add("BEARISH_IMBALANCE")

        else:

            return context

        # ======================================================
        # TAMANHO
        # ======================================================

        result.size = abs(

            result.high -

            result.low

        )

        result.midpoint = (

            result.high +

            result.low

        ) / 2

        # ======================================================
        # FORÇA
        # ======================================================

        if result.size >= 20:

            result.strength = 1.00

            result.score = self.BASE_SCORE + self.STRONG_IMBALANCE

        elif result.size >= 10:

            result.strength = 0.75

            result.score = self.BASE_SCORE + 10

        else:

            result.strength = 0.50

            result.score = self.BASE_SCORE

        # ======================================================
        # TESTADO
        # ======================================================

        last = market.last_candle

        if result.bullish:

            if last.low <= result.high:

                result.tested = True

            if last.close <= result.low:

                result.filled = True

        elif result.bearish:

            if last.high >= result.low:

                result.tested = True

            if last.close >= result.high:

                result.filled = True

        # ======================================================
        # FINALIZAÇÃO
        # ======================================================

        result.score = min(

            result.score,

            100,

        )

        result.confidence = (

            result.score / 100

        )

        return context