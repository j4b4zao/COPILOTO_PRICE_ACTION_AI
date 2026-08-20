"""
market/candle_engine.py

Converte MarketData em Candle.
"""

from models.candle import Candle


class CandleEngine:

    def criar(self, market):

        if market is None:
            return None

        try:

            open_price = float(market.open)
            high = float(market.high)
            low = float(market.low)
            close = float(market.close)

        except (AttributeError, TypeError, ValueError):

            return None

        if (
            high < max(open_price, close)
            or
            low > min(open_price, close)
            or
            high < low
        ):
            return None

        return Candle(
            open_price,
            high,
            low,
            close
        )
