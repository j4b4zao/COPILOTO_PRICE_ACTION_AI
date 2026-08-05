"""
core/candle_builder.py

Responsável pela construção dos candles.

Decide quando:

- atualizar o candle atual;
- fechar um candle;
- iniciar um novo candle.

RC2
"""

from __future__ import annotations

from datetime import datetime

from models.candle import Candle


class CandleBuilder:

    def __init__(self):

        self.current = None

        self.current_period = None

    # =====================================================
    # NORMALIZAÇÃO DO PERÍODO
    # =====================================================

    def _normalize_period(self, timestamp: datetime, timeframe: str):

        timeframe = timeframe.upper()

        if timeframe == "M1":

            return timestamp.replace(second=0, microsecond=0)

        if timeframe == "M5":

            minute = (timestamp.minute // 5) * 5

            return timestamp.replace(
                minute=minute,
                second=0,
                microsecond=0,
            )

        if timeframe == "M15":

            minute = (timestamp.minute // 15) * 15

            return timestamp.replace(
                minute=minute,
                second=0,
                microsecond=0,
            )

        return timestamp.replace(second=0, microsecond=0)

    # =====================================================
    # UPDATE
    # =====================================================

    def update(

        self,

        open_price,

        high,

        low,

        close,

        volume,

        timeframe="M1",

        timestamp=None,

    ):

        timestamp = timestamp or datetime.now()

        period = self._normalize_period(
            timestamp,
            timeframe,
        )

        # ------------------------------------------
        # Primeiro candle
        # ------------------------------------------

        if self.current is None:

            self.current = Candle(

                open=open_price,

                high=high,

                low=low,

                close=close,

                volume=volume,

                timestamp=period,

            )

            self.current_period = period

            return self.current, True

        # ------------------------------------------
        # Mesmo candle
        # ------------------------------------------

        if period == self.current_period:

            self.current.high = max(
                self.current.high,
                high,
            )

            self.current.low = min(
                self.current.low,
                low,
            )

            self.current.close = close

            self.current.volume = volume

            return self.current, False

        # ------------------------------------------
        # Novo candle
        # ------------------------------------------

        self.current = Candle(

            open=open_price,

            high=high,

            low=low,

            close=close,

            volume=volume,

            timestamp=period,

        )

        self.current_period = period

        return self.current, True