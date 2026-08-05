"""
market/market_state.py

Estado atual do mercado.

Armazena somente o estado do mercado.
Toda a inteligência permanece nas engines.
"""

from __future__ import annotations

from datetime import datetime

from models.candle import Candle
from models.candle_history import CandleHistory


class MarketState:

    def __init__(self):

        # ==========================================
        # IDENTIFICAÇÃO
        # ==========================================

        self.symbol = ""

        self.timeframe = "M1"

        # ==========================================
        # PREÇOS
        # ==========================================

        self.last_price = 0.0

        self.bid = 0.0

        self.ask = 0.0

        self.spread = 0.0

        # ==========================================
        # VOLUME
        # ==========================================

        self.volume = 0.0

        # ==========================================
        # TEMPO
        # ==========================================

        self.timestamp = None

        # ==========================================
        # HISTÓRICO
        # ==========================================

        self.candles = CandleHistory()

    # ==================================================
    # UPDATE
    # ==================================================

    def update(
        self,
        candle: Candle,
        symbol: str,
        timeframe: str,
        volume: float,
        timestamp: datetime,
        new_candle: bool,
    ):

        self.symbol = symbol

        self.timeframe = timeframe

        self.last_price = candle.close

        self.volume = volume

        self.timestamp = timestamp

        # ------------------------------------------
        # Histórico
        # ------------------------------------------

        if new_candle:

            self.candles.add(candle)

        else:

            if self.candles.empty:

                self.candles.add(candle)

            else:

                ultimo = self.candles.last()

                ultimo.open = candle.open
                ultimo.high = candle.high
                ultimo.low = candle.low
                ultimo.close = candle.close
                ultimo.volume = candle.volume
                ultimo.timestamp = candle.timestamp

    # ==================================================
    # CONSULTAS
    # ==================================================

    @property
    def ready(self):

        return self.candles.size >= 5

    @property
    def last_candle(self):

        return self.candles.last()

    @property
    def previous_candle(self):

        return self.candles.previous()

    def last(self, amount):

        return self.candles.last_n(amount)

    # ==================================================
    # RESET
    # ==================================================

    def clear(self):

        self.symbol = ""

        self.timeframe = "M1"

        self.last_price = 0.0

        self.bid = 0.0

        self.ask = 0.0

        self.spread = 0.0

        self.volume = 0.0

        self.timestamp = None

        self.candles.clear()

    # ==================================================
    # DEBUG
    # ==================================================

    def __repr__(self):

        return (
            f"MarketState("
            f"symbol={self.symbol}, "
            f"timeframe={self.timeframe}, "
            f"price={self.last_price}, "
            f"candles={self.candles.size})"
        )