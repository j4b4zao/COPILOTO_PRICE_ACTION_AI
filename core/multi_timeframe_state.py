"""
core/multi_timeframe_state.py

Contrato de mercado Multi-timeframe RC3.0.

Mantém builders e históricos independentes para M1, M5 e M15.
O mesmo tick de preço alimenta cada timeframe sem misturar candles.
"""

from __future__ import annotations

import math
from datetime import datetime

from core.candle_builder import CandleBuilder
from core.market_state import MarketState


class MultiTimeframeState:

    NAME = "MultiTimeframeState"

    VERSION = "RC3.0"

    TIMEFRAMES = (
        "M1",
        "M5",
        "M15",
    )

    PRIMARY_TIMEFRAME = "M1"

    # ==========================================================
    # CONSTRUTOR
    # ==========================================================

    def __init__(self):

        self._markets = {
            timeframe: MarketState(
                timeframe=timeframe
            )
            for timeframe in self.TIMEFRAMES
        }

        self._builders = {
            timeframe: CandleBuilder()
            for timeframe in self.TIMEFRAMES
        }

    # ==========================================================
    # ATUALIZAR TICK
    # ==========================================================

    def update_tick(
        self,
        *,
        symbol: str,
        price: float,
        cumulative_volume: float,
        timestamp: datetime,
    ) -> dict[str, bool]:
        """
        Atualiza todos os timeframes com a mesma leitura.

        Retorna um mapa indicando se cada timeframe iniciou
        um novo candle.
        """

        normalized_symbol = str(
            symbol
        ).strip()

        if not normalized_symbol:

            raise ValueError(
                "MultiTimeframeState requer um símbolo válido."
            )

        normalized_price = float(
            price
        )

        if (
            not math.isfinite(normalized_price)
            or normalized_price <= 0.0
        ):

            raise ValueError(
                "MultiTimeframeState requer preço positivo e finito."
            )

        normalized_volume = float(
            cumulative_volume
        )

        if (
            not math.isfinite(normalized_volume)
            or normalized_volume < 0.0
        ):

            raise ValueError(
                "MultiTimeframeState requer volume finito e não negativo."
            )

        if not isinstance(timestamp, datetime):

            raise TypeError(
                "MultiTimeframeState requer timestamp datetime."
            )

        new_candles = {}

        for timeframe in self.TIMEFRAMES:

            builder = self._builders[
                timeframe
            ]

            market = self._markets[
                timeframe
            ]

            candle, new_candle = builder.update(
                open_price=normalized_price,
                high=normalized_price,
                low=normalized_price,
                close=normalized_price,
                volume=normalized_volume,
                timeframe=timeframe,
                timestamp=timestamp,
            )

            market.update(
                candle=candle,
                symbol=normalized_symbol,
                timeframe=timeframe,
                volume=normalized_volume,
                timestamp=timestamp,
                new_candle=new_candle,
            )

            new_candles[
                timeframe
            ] = new_candle

        return new_candles

    # ==========================================================
    # CONSULTAS
    # ==========================================================

    def get(
        self,
        timeframe: str,
    ) -> MarketState:

        normalized = str(
            timeframe
        ).strip().upper()

        if normalized not in self._markets:

            supported = ", ".join(
                self.TIMEFRAMES
            )

            raise ValueError(
                f"Timeframe {timeframe!r} não suportado. "
                f"Use: {supported}."
            )

        return self._markets[
            normalized
        ]

    @property
    def primary(self) -> MarketState:

        return self.get(
            self.PRIMARY_TIMEFRAME
        )

    @property
    def markets(self) -> dict[str, MarketState]:

        return dict(
            self._markets
        )

    def is_ready(
        self,
        timeframe: str,
    ) -> bool:

        return self.get(
            timeframe
        ).ready

    @property
    def all_ready(self) -> bool:

        return all(
            market.ready
            for market in self._markets.values()
        )

    # ==========================================================
    # SNAPSHOT
    # ==========================================================

    def snapshot(self) -> dict:

        return {
            "name": self.NAME,
            "version": self.VERSION,
            "primary_timeframe": self.PRIMARY_TIMEFRAME,
            "all_ready": self.all_ready,
            "timeframes": {
                timeframe: {
                    "symbol": market.symbol,
                    "timeframe": market.timeframe,
                    "last_price": market.last_price,
                    "candle_count": market.candle_count,
                    "ready": market.ready,
                }
                for timeframe, market
                in self._markets.items()
            },
        }

    # ==========================================================
    # RESET
    # ==========================================================

    def clear(self) -> None:

        for timeframe, market in self._markets.items():

            market.clear()

            market.timeframe = timeframe

        self._builders = {
            timeframe: CandleBuilder()
            for timeframe in self.TIMEFRAMES
        }
