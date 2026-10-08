"""
Replay Historical Multi-Timeframe Reconstruction

RC6 - HISTORICAL MTF RECONSTRUCTION

Reconstrói M1/M5/M15 exclusivamente a partir de candles M1 históricos
já observados.

Não fabrica ticks.
Não usa datetime.now().
Não consulta rede.
Não altera MultiTimeframeState/CandleBuilder operacionais.
"""

from __future__ import annotations

import math
from datetime import datetime

from core.market_state import MarketState
from models.candle import Candle


class HistoricalMultiTimeframeBuilder:

    NAME = "HistoricalMultiTimeframeBuilder"
    VERSION = "RC6-HISTORICAL-MTF"

    TIMEFRAMES = ("M1", "M5", "M15")
    PRIMARY_TIMEFRAME = "M1"

    _MINUTES = {
        "M1": 1,
        "M5": 5,
        "M15": 15,
    }

    def __init__(self, symbol: str = "REPLAY"):
        normalized_symbol = str(symbol).strip()

        if not normalized_symbol:
            raise ValueError(
                "HistoricalMultiTimeframeBuilder requer símbolo válido."
            )

        self.symbol = normalized_symbol

        self._markets = {
            timeframe: MarketState(
                symbol=self.symbol,
                timeframe=timeframe,
            )
            for timeframe in self.TIMEFRAMES
        }

        self._current_periods = {
            timeframe: None
            for timeframe in self.TIMEFRAMES
        }

        self._last_timestamp: datetime | None = None

    @staticmethod
    def _validate_candle(candle: Candle) -> None:
        if type(candle) is not Candle:
            raise TypeError(
                "RC6 requer Candle exato como entrada histórica."
            )

        if type(candle.timestamp) is not datetime:
            raise ValueError(
                "RC6 requer timestamp datetime explícito."
            )

        values = (
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        )

        if any(
            type(value) not in (int, float)
            or not math.isfinite(float(value))
            for value in values
        ):
            raise ValueError(
                "RC6 requer OHLCV finito."
            )

        if (
            candle.open <= 0
            or candle.high <= 0
            or candle.low <= 0
            or candle.close <= 0
        ):
            raise ValueError(
                "RC6 requer OHLC positivo."
            )

        if candle.volume < 0:
            raise ValueError(
                "RC6 requer volume não negativo."
            )

        if candle.high < max(
            candle.open,
            candle.close,
            candle.low,
        ):
            raise ValueError(
                "RC6 recebeu high inconsistente."
            )

        if candle.low > min(
            candle.open,
            candle.close,
            candle.high,
        ):
            raise ValueError(
                "RC6 recebeu low inconsistente."
            )

    @classmethod
    def _period(
        cls,
        timestamp: datetime,
        timeframe: str,
    ) -> datetime:
        minutes = cls._MINUTES[timeframe]

        minute = (
            timestamp.minute // minutes
        ) * minutes

        return timestamp.replace(
            minute=minute,
            second=0,
            microsecond=0,
        )

    @staticmethod
    def _copy_m1(
        source: Candle,
        timestamp: datetime,
    ) -> Candle:
        return Candle(
            open=float(source.open),
            high=float(source.high),
            low=float(source.low),
            close=float(source.close),
            volume=float(source.volume),
            timestamp=timestamp,
        )

    @staticmethod
    def _first_aggregate(
        source: Candle,
        period: datetime,
    ) -> Candle:
        return Candle(
            open=float(source.open),
            high=float(source.high),
            low=float(source.low),
            close=float(source.close),
            volume=float(source.volume),
            timestamp=period,
        )

    @staticmethod
    def _merge(
        current: Candle,
        source: Candle,
    ) -> Candle:
        return Candle(
            open=current.open,
            high=max(
                current.high,
                float(source.high),
            ),
            low=min(
                current.low,
                float(source.low),
            ),
            close=float(source.close),
            volume=(
                float(current.volume)
                + float(source.volume)
            ),
            timestamp=current.timestamp,
        )

    def _update_m1(
        self,
        source: Candle,
    ) -> None:
        market = self._markets["M1"]

        candle = self._copy_m1(
            source,
            source.timestamp,
        )

        market.update(
            candle=candle,
            symbol=self.symbol,
            timeframe="M1",
            volume=candle.volume,
            timestamp=source.timestamp,
            new_candle=True,
        )

        self._current_periods["M1"] = (
            self._period(
                source.timestamp,
                "M1",
            )
        )

    def _update_aggregate(
        self,
        timeframe: str,
        source: Candle,
    ) -> None:
        period = self._period(
            source.timestamp,
            timeframe,
        )

        market = self._markets[
            timeframe
        ]

        current_period = (
            self._current_periods[
                timeframe
            ]
        )

        if current_period is None:
            candle = self._first_aggregate(
                source,
                period,
            )

            market.update(
                candle=candle,
                symbol=self.symbol,
                timeframe=timeframe,
                volume=candle.volume,
                timestamp=source.timestamp,
                new_candle=True,
            )

            self._current_periods[
                timeframe
            ] = period

            return

        if period < current_period:
            raise ValueError(
                "RC6 detectou período histórico regressivo."
            )

        if period > current_period:
            candle = self._first_aggregate(
                source,
                period,
            )

            market.update(
                candle=candle,
                symbol=self.symbol,
                timeframe=timeframe,
                volume=candle.volume,
                timestamp=source.timestamp,
                new_candle=True,
            )

            self._current_periods[
                timeframe
            ] = period

            return

        current = market.last_candle

        if current is None:
            raise RuntimeError(
                "RC6 perdeu o candle agregado corrente."
            )

        candle = self._merge(
            current,
            source,
        )

        market.update(
            candle=candle,
            symbol=self.symbol,
            timeframe=timeframe,
            volume=candle.volume,
            timestamp=source.timestamp,
            new_candle=False,
        )

    def update(
        self,
        candle: Candle,
    ) -> dict[str, bool]:
        self._validate_candle(candle)

        if (
            self._last_timestamp is not None
            and candle.timestamp
            <= self._last_timestamp
        ):
            raise ValueError(
                "RC6 requer timestamps estritamente crescentes."
            )

        previous_periods = dict(
            self._current_periods
        )

        self._update_m1(candle)

        for timeframe in ("M5", "M15"):
            self._update_aggregate(
                timeframe,
                candle,
            )

        self._last_timestamp = (
            candle.timestamp
        )

        return {
            timeframe: (
                previous_periods[timeframe]
                != self._current_periods[
                    timeframe
                ]
            )
            for timeframe in self.TIMEFRAMES
        }

    def get(
        self,
        timeframe: str,
    ) -> MarketState:
        normalized = str(
            timeframe
        ).strip().upper()

        if normalized not in self._markets:
            raise ValueError(
                f"Timeframe histórico inválido: {timeframe!r}."
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

    @property
    def last_timestamp(
        self,
    ) -> datetime | None:
        return self._last_timestamp

    def snapshot(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "symbol": self.symbol,
            "primary_timeframe": (
                self.PRIMARY_TIMEFRAME
            ),
            "last_timestamp": (
                self._last_timestamp
            ),
            "all_ready": self.all_ready,
            "timeframes": {
                timeframe: {
                    "candle_count": (
                        market.candle_count
                    ),
                    "current_period": (
                        self._current_periods[
                            timeframe
                        ]
                    ),
                    "ready": market.ready,
                }
                for timeframe, market
                in self._markets.items()
            },
        }