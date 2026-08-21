"""
Estado de mercado construído por variação fixa de preço.

RC3.7 - RENKO

O último tijolo do histórico é sempre o tijolo atual. Tijolos
anteriores estão fechados e podem ser usados pelas análises.
"""

from __future__ import annotations

import math
from datetime import datetime

from core.market_state import MarketState
from models.candle import Candle


class RenkoState:

    NAME = "RenkoState"

    VERSION = "RC3.7"

    def __init__(self, brick_size=20.0):

        self.brick_size = self._validate_brick_size(
            brick_size
        )

        self.market = MarketState(
            timeframe=self.timeframe
        )

        self._current_open = None
        self._last_cumulative_volume = None
        self._brick_start_volume = None

    @property
    def timeframe(self):

        size = f"{self.brick_size:g}"

        return f"RENKO_{size}"

    # ==========================================================
    # ATUALIZAR TICK
    # ==========================================================

    def update_tick(
        self,
        *,
        symbol,
        price,
        cumulative_volume,
        timestamp,
    ):

        symbol = str(symbol).strip()
        price = float(price)
        cumulative_volume = float(cumulative_volume)

        if not symbol:

            raise ValueError(
                "RenkoState requer um símbolo válido."
            )

        if not math.isfinite(price) or price <= 0.0:

            raise ValueError(
                "RenkoState requer preço positivo e finito."
            )

        if (
            not math.isfinite(cumulative_volume)
            or cumulative_volume < 0.0
        ):

            raise ValueError(
                "RenkoState requer volume finito e não negativo."
            )

        if not isinstance(timestamp, datetime):

            raise TypeError(
                "RenkoState requer timestamp datetime."
            )

        if self._current_open is None:

            self._current_open = price
            self._last_cumulative_volume = cumulative_volume
            self._brick_start_volume = cumulative_volume

            self._add_current(
                symbol,
                price,
                0.0,
                timestamp,
            )

            return 0

        self._handle_volume_reset(
            cumulative_volume
        )

        closed = 0

        while abs(price - self._current_open) >= self.brick_size:

            direction = (
                1.0
                if price > self._current_open
                else -1.0
            )

            brick_close = (
                self._current_open
                + direction * self.brick_size
            )

            volume = self._current_volume(
                cumulative_volume
            )

            self._update_current(
                symbol,
                brick_close,
                volume,
                timestamp,
            )

            self._current_open = brick_close
            self._brick_start_volume = cumulative_volume

            self._add_current(
                symbol,
                brick_close,
                0.0,
                timestamp,
            )

            closed += 1

        self._update_current(
            symbol,
            price,
            self._current_volume(cumulative_volume),
            timestamp,
        )

        self._last_cumulative_volume = cumulative_volume

        return closed

    # ==========================================================
    # MERCADO
    # ==========================================================

    def _add_current(
        self,
        symbol,
        price,
        volume,
        timestamp,
    ):

        candle = self._candle(
            self._current_open,
            price,
            volume,
            timestamp,
        )

        self.market.update(
            candle=candle,
            symbol=symbol,
            timeframe=self.timeframe,
            volume=volume,
            timestamp=timestamp,
            new_candle=True,
        )

    def _update_current(
        self,
        symbol,
        price,
        volume,
        timestamp,
    ):

        candle = self._candle(
            self._current_open,
            price,
            volume,
            timestamp,
        )

        self.market.update(
            candle=candle,
            symbol=symbol,
            timeframe=self.timeframe,
            volume=volume,
            timestamp=timestamp,
            new_candle=False,
        )

    @staticmethod
    def _candle(open_price, close, volume, timestamp):

        return Candle(
            open=open_price,
            high=max(open_price, close),
            low=min(open_price, close),
            close=close,
            volume=volume,
            timestamp=timestamp,
        )

    # ==========================================================
    # VOLUME
    # ==========================================================

    def _handle_volume_reset(self, cumulative_volume):

        if cumulative_volume < self._last_cumulative_volume:

            self._brick_start_volume = cumulative_volume

    def _current_volume(self, cumulative_volume):

        return max(
            0.0,
            cumulative_volume - self._brick_start_volume,
        )

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self):

        self.market.clear()
        self.market.timeframe = self.timeframe

        self._current_open = None
        self._last_cumulative_volume = None
        self._brick_start_volume = None

    @staticmethod
    def _validate_brick_size(value):

        size = float(value)

        if not math.isfinite(size) or size <= 0.0:

            raise ValueError(
                "O tamanho do tijolo Renko deve ser positivo e finito."
            )

        return size
