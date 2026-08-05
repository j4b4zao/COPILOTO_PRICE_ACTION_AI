"""
strategies/trend_pullback.py

Setup:
Trend Pullback

RC4
"""

from enums.trend import Trend

from strategies.setup_base import SetupBase


class TrendPullback(SetupBase):

    NAME = "TrendPullback"

    PRIORITY = 10

    def executar(self, context):

        result = context.strategy

        structure = context.structure
        volume = context.volume
        price = context.price_action
        market_context = context.context

        # ----------------------------
        # Contexto favorável
        # ----------------------------

        if not market_context.valid:
            return result

        # ----------------------------
        # Tendência
        # ----------------------------

        if structure.trend != Trend.UP:
            return result

        # ----------------------------
        # BOS
        # ----------------------------

        if not structure.bos_up:
            return result

        # ----------------------------
        # Pullback
        # ----------------------------

        if not price.pullback:
            return result

        # ----------------------------
        # Candle
        # ----------------------------

        if not (

            price.hammer

            or

            price.bullish_engulfing

        ):
            return result

        # ----------------------------
        # Volume
        # ----------------------------

        if volume.low:
            return result

        # ----------------------------
        # Setup encontrado
        # ----------------------------

        result.valid = True

        result.name = self.NAME

        result.signal = "BUY"

        result.score = 90

        result.reasons.extend([

            "Trend UP",

            "BOS",

            "Pullback",

            "Hammer/Engulfing",

            "Volume"

        ])

        result.classify()

        return result