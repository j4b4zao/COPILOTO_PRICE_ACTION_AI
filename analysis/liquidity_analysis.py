"""
analysis/liquidity_analysis.py

Engine de Liquidez

RC2
"""

from ai.engine_base import EngineBase


class LiquidityAnalysis(EngineBase):

    NAME = "LiquidityAnalysis"

    VERSION = "RC2"

    ENABLED = True

    PRIORITY = 30

    EQUAL_LEVEL_TOLERANCE = 2

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

        result = context.liquidity
        evidence = context.evidence

        result.clear()

        last = candles[-1]
        previous = candles[-2]

        # ======================================================
        # EQUAL HIGH
        # ======================================================

        for candle in candles[:-1]:

            if abs(candle.high - last.high) <= self.EQUAL_LEVEL_TOLERANCE:

                result.equal_highs = True
                evidence.add("EQUAL_HIGH")
                break

        # ======================================================
        # EQUAL LOW
        # ======================================================

        for candle in candles[:-1]:

            if abs(candle.low - last.low) <= self.EQUAL_LEVEL_TOLERANCE:

                result.equal_lows = True
                evidence.add("EQUAL_LOW")
                break

        # ======================================================
        # SWEEP HIGH
        # ======================================================

        if (

            last.high > previous.high

            and

            last.close < previous.high

        ):

            result.sweep_up = True

            evidence.add("SWEEP_HIGH")

        # ======================================================
        # SWEEP LOW
        # ======================================================

        if (

            last.low < previous.low

            and

            last.close > previous.low

        ):

            result.sweep_down = True

            evidence.add("SWEEP_LOW")

        # ======================================================
        # BUY / SELL SIDE
        # ======================================================

        result.buy_side = result.sweep_down

        result.sell_side = result.sweep_up

        if result.buy_side:
            evidence.add("BUY_SIDE")

        if result.sell_side:
            evidence.add("SELL_SIDE")

        # ======================================================
        # LIQUIDITY PRICE
        # ======================================================

        if result.sweep_up:

            result.liquidity_price = last.high

        elif result.sweep_down:

            result.liquidity_price = last.low

        # ======================================================
        # TOUCHES
        # ======================================================

        touches = 0

        for candle in candles[:-1]:

            if abs(candle.high - last.high) <= self.EQUAL_LEVEL_TOLERANCE:

                touches += 1

            if abs(candle.low - last.low) <= self.EQUAL_LEVEL_TOLERANCE:

                touches += 1

        result.touches = touches

        # ======================================================
        # CONFLUÊNCIAS
        # ======================================================

        result.confluences = len(evidence.evidences)

        result.valid = True

        return context