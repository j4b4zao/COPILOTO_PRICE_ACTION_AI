"""
core/market_state.py

Representa o estado atual do mercado.

É a única fonte de dados utilizada pelas engines
de análise do COPILOTO PRICE ACTION AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from models.candle import Candle
from models.candle_history import CandleHistory


@dataclass(slots=True)
class MarketState:


    # ==========================================================
    # IDENTIFICAÇÃO
    # ==========================================================

    symbol: str = ""
    timeframe: str = ""

    # ==========================================================
    # DADOS ATUAIS
    # ==========================================================

    last_price: float = 0.0
    volume: float = 0.0

    timestamp: datetime | None = None

    # ==========================================================
    # HISTÓRICO
    # ==========================================================

    candles: CandleHistory = field(
        default_factory=CandleHistory
    )

    # ==========================================================
    # ATUALIZAÇÃO
    # ==========================================================

    def update(
        self,
        candle: Candle,
        symbol: str,
        timeframe: str,
        volume: float = 0.0,
        timestamp: datetime | None = None,
        new_candle: bool = True,
    ) -> None:

        self.symbol = symbol
        self.timeframe = timeframe
        self.volume = volume
        self.last_price = candle.close
        self.timestamp = timestamp or datetime.now()

        # ======================================================
        # NOVO CANDLE
        # ======================================================

        if new_candle:

            self.candles.add(candle)

            return

        # ======================================================
        # ATUALIZAÇÃO DO CANDLE ATUAL
        # ======================================================

        if self.candles.empty:

            self.candles.add(candle)

            return

        ultimo = self.candles.last()

        if ultimo is None:

            self.candles.add(candle)

            return

        ultimo.high = max(
            ultimo.high,
            candle.high,
        )
        ultimo.low = min(
            ultimo.low,
            candle.low,
        )

        ultimo.close = candle.close

        ultimo.volume = candle.volume

        ultimo.timestamp = candle.timestamp

    # ==========================================================
    # CONSULTAS
    # ==========================================================

    @property
    def last_candle(self) -> Candle | None:

        return self.candles.last()

    @property
    def previous_candle(self) -> Candle | None:

        return self.candles.previous()

    @property
    def ready(self) -> bool:

        return self.candles.size >= 5

    @property
    def candle_count(self) -> int:

        return self.candles.size



    # ==========================================================
    # CONTROLE
    # ==========================================================

    def clear(self) -> None:

        self.symbol = ""
        self.timeframe = ""

        self.last_price = 0.0
        self.volume = 0.0

        self.timestamp = None

        self.candles.clear()

    # ==========================================================
    # REPRESENTAÇÃO
    # ==========================================================

    def __repr__(self) -> str:

        return (
            f"MarketState("
            f"symbol='{self.symbol}', "
            f"timeframe='{self.timeframe}', "
            f"price={self.last_price:.2f}, "
            f"candles={self.candle_count})"
        )
