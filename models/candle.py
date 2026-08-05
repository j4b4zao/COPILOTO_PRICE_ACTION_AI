"""
core/candle.py

Representação de um candle OHLCV utilizado pelo
COPILOTO PRICE ACTION AI.

A classe Candle representa apenas um candle.
Nenhuma lógica de análise deve existir aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Candle:
    """
    Representa um candle do mercado.
    """

    open: float
    high: float
    low: float
    close: float

    volume: float = 0.0

    timestamp: datetime | None = None

    # ==========================================================
    # PROPRIEDADES
    # ==========================================================

    @property
    def body(self) -> float:
        """
        Tamanho do corpo do candle.
        """
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        """
        Amplitude total do candle.
        """
        return self.high - self.low

    @property
    def upper_wick(self) -> float:
        """
        Tamanho da sombra superior.
        """
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        """
        Tamanho da sombra inferior.
        """
        return min(self.open, self.close) - self.low

    @property
    def midpoint(self) -> float:
        """
        Ponto médio do candle.
        """
        return (self.high + self.low) / 2.0

    # ==========================================================
    # CLASSIFICAÇÃO
    # ==========================================================

    @property
    def bullish(self) -> bool:
        """
        Candle de alta.
        """
        return self.close > self.open

    @property
    def bearish(self) -> bool:
        """
        Candle de baixa.
        """
        return self.close < self.open

    @property
    def doji(self) -> bool:
        """
        Identificação simples de Doji.

        A confirmação definitiva ficará a cargo
        da engine PriceAction.
        """

        if self.range == 0:
            return False

        return (self.body / self.range) <= 0.10

    # ==========================================================
    # UTILIDADES
    # ==========================================================

    def to_dict(self) -> dict:
        """
        Converte o candle em dicionário.
        """

        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

    def __str__(self) -> str:

        return (
            f"Candle("
            f"O={self.open:.2f}, "
            f"H={self.high:.2f}, "
            f"L={self.low:.2f}, "
            f"C={self.close:.2f}, "
            f"V={self.volume:.0f})"
        )

    def __repr__(self) -> str:
        return self.__str__()