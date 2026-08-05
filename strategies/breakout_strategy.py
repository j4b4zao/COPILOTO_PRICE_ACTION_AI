from strategies.strategy import Strategy


class BreakoutStrategy(Strategy):

    def analyze(self, context):

        structure = context.structure

        pa = context.price_action

        if (
            structure.trend == "UP"
            and structure.bos
            and pa.bullish_engulfing
        ):

            return {

                "name": "BREAKOUT",

                "direction": "BUY",

                "score": 90,

                "confidence": 0.90,

                "reasons": [

                    "BOS",

                    "Bullish Engulfing"

                ]

            }

        if (
            structure.trend == "DOWN"
            and structure.bos
            and pa.bearish_engulfing
        ):

            return {

                "name": "BREAKOUT",

                "direction": "SELL",

                "score": 90,

                "confidence": 0.90,

                "reasons": [

                    "BOS",

                    "Bearish Engulfing"

                ]

            }

        return None