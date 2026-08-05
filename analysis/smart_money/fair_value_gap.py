"""
analysis/smart_money/fair_value_gap.py

Fair Value Gap Engine

RC11
"""

from ai.engine_base import EngineBase


class FairValueGap(EngineBase):

    NAME = "FairValueGap"

    VERSION = "RC11"

    ENABLED = True

    PRIORITY = 55

    # ==========================================================
    # SCORES
    # ==========================================================

    BASE_SCORE = 60

    STRONG_GAP = 20

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

        result = context.fair_value_gap

        evidence = context.evidence

        result.clear()

        c1, c2, c3 = candles

        # ======================================================
        # BULLISH FVG
        # ======================================================

        if c1.high < c3.low:

            result.valid = True

            result.bullish = True

            result.high = c3.low

            result.low = c1.high

            result.midpoint = (

                result.high +

                result.low

            ) / 2

            result.score = self.BASE_SCORE

            evidence.add("BULLISH_FVG")

        # ======================================================
        # BEARISH FVG
        # ======================================================

        elif c1.low > c3.high:

            result.valid = True

            result.bearish = True

            result.high = c1.low

            result.low = c3.high

            result.midpoint = (

                result.high +

                result.low

            ) / 2

            result.score = self.BASE_SCORE

            evidence.add("BEARISH_FVG")

        else:

            return context

        # ======================================================
        # GAP
        # ======================================================

        gap_size = abs(

            result.high -

            result.low

        )

        if gap_size > 20:

            result.strength = 1.0

            result.score += self.STRONG_GAP

        elif gap_size > 10:

            result.strength = 0.75

            result.score += 10

        else:

            result.strength = 0.50

        # ======================================================
        # FILLED
        # ======================================================

        last = market.last_candle

        if result.bullish:

            if last.low <= result.high:

                result.tested = True

            if last.close <= result.low:

                result.filled = True

        if result.bearish:

            if last.high >= result.low:

                result.tested = True

            if last.close >= result.high:

                result.filled = True

        # ======================================================
        # FINALIZAÇÃO
        # ======================================================

        result.confidence = result.score / 100

        result.score = min(result.score, 100)

        return context