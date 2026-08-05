"""
models/market_data.py

Representa o estado atual do mercado.

Centraliza todas as informações recebidas do Collector.
"""

from dataclasses import dataclass, field
from datetime import datetime

from models.candle import Candle
from models.candle_history import CandleHistory


@dataclass(slots=True)
class MarketData:

    # ==================================================
    # IDENTIFICAÇÃO
    # ==================================================

    symbol: str = ""

    timeframe: str = ""

    date: str = ""

    time: str = ""

    # ==================================================
    # PREÇOS
    # ==================================================

    open: float = 0.0

    high: float = 0.0

    low: float = 0.0

    close: float = 0.0

    last_price: float = 0.0

    volume: float = 0.0

    # ==================================================
    # FLUXO
    # ==================================================

    bid: float = 0.0

    ask: float = 0.0

    average_price: float = 0.0

    trades: int = 0

    # ==================================================
    # INDICADORES
    # ==================================================

    adx: float = 0.0

    macd: float = 0.0

    moving_average: float = 0.0

    # ==================================================
    # CONTROLE
    # ==================================================

    timestamp: datetime | None = None

    candles: CandleHistory = field(default_factory=CandleHistory)

    # ==================================================
    # CANDLES
    # ==================================================

    def add_candle(self, candle: Candle):

        self.open = candle.open
        self.high = candle.high
        self.low = candle.low
        self.close = candle.close

        self.last_price = candle.close
        self.volume = candle.volume
        self.timestamp = candle.timestamp

        self.candles.add(candle)

    # ==================================================
    # CONSULTAS
    # ==================================================

    @property
    def last_candle(self):

        return self.candles.last

    @property
    def previous_candle(self):

        return self.candles.previous

    @property
    def ready(self):

        return self.candles.size >= 5

    def last(self, periods: int):

        return self.candles.last_n(periods)

    def highest(self, periods: int):

        return self.candles.highest(periods)

    def lowest(self, periods: int):

        return self.candles.lowest(periods)

    def average_volume(self, periods: int):

        return self.candles.average_volume(periods)

    def clear(self):

        self.candles.clear()

    # ==================================================
    # SNAPSHOT
    # ==================================================

    def snapshot(self):

        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "price": self.close,
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
            "adx": self.adx,
            "macd": self.macd,
        }