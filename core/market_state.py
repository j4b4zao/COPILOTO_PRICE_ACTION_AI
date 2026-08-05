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
    """
    Estado atual do mercado.
    """

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

    candles: CandleHistory = field(default_factory=CandleHistory)

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
    ) -> None:
        """
        Atualiza o estado atual do mercado.
        """

        self.symbol = symbol
        self.timeframe = timeframe

        self.volume = volume

        self.last_price = candle.close

        self.timestamp = timestamp or datetime.now()

        self.candles.add(candle)

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
        """
        Indica se existe histórico suficiente
        para iniciar as análises.
        """

        return self.candles.size >= 5

    @property
    def candle_count(self) -> int:

        return self.candles.size

    # ==========================================================
    # ALIASES (RC9)
    # ==========================================================

    @property
    def history(self) -> CandleHistory:
        """
        Alias para manter compatibilidade com
        códigos antigos que utilizam market.history.
        """

        return self.candles

    @property
    def price(self) -> float:
        """
        Alias para o último preço.
        """

        return self.last_price

    @property
    def open(self) -> float:

        candle = self.last_candle

        if candle is None:
            return 0.0

        return candle.open

    @property
    def high(self) -> float:

        candle = self.last_candle

        if candle is None:
            return 0.0

        return candle.high

    @property
    def low(self) -> float:

        candle = self.last_candle

        if candle is None:
            return 0.0

        return candle.low

    @property
    def close(self) -> float:

        candle = self.last_candle

        if candle is None:
            return 0.0

        return candle.close

    @property
    def body(self) -> float:

        candle = self.last_candle

        if candle is None:
            return 0.0

        return candle.body

    @property
    def range(self) -> float:

        candle = self.last_candle

        if candle is None:
            return 0.0

        return candle.range

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