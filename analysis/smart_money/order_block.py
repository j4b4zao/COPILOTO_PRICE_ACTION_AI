"""
analysis/smart_money/order_block.py

Bullish / Bearish Order Block

RC10
"""

from ai.engine_base import EngineBase


class OrderBlock(EngineBase):

    NAME = "OrderBlock"

    VERSION = "RC10"

    ENABLED = True

    PRIORITY = 55

    def executar(self, context):

        market = context.market

        if market.candle_count < 6:
            return context

        result = context.order_block

        result.clear()

        candles = market.candles.last_n(6)

        ob = candles[-2]

        current = candles[-1]

        structure = context.structure

        # ======================================================
        # BULLISH ORDER BLOCK
        # ======================================================

        if (

            not ob.bullish

            and

            structure.bos_up

            and

            current.close > ob.high

        ):

            result.valid = True

            result.bullish = True

            result.high = ob.high

            result.low = ob.low

            result.entry_price = (

                ob.high + ob.low

            ) / 2

            result.score = 80

            result.strength = 0.80

            result.reasons.append(

                "Bullish Order Block"

            )

        # ======================================================
        # BEARISH ORDER BLOCK
        # ======================================================

        elif (

            not ob.bearish

            and

            structure.bos_down

            and

            current.close < ob.low

        ):

            result.valid = True

            result.bearish = True

            result.high = ob.high

            result.low = ob.low

            result.entry_price = (

                ob.high + ob.low

            ) / 2

            result.score = 80

            result.strength = 0.80

            result.reasons.append(

                "Bearish Order Block"

            )

        return context