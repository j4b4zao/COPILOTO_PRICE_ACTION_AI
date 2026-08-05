"""
models/candle_history.py

Gerencia o histórico de candles utilizado por todo o
COPILOTO PRICE ACTION AI.
"""

from __future__ import annotations

from collections import deque

from models.candle import Candle


class CandleHistory:
    """
    Histórico de candles do mercado.
    """

    def __init__(self, max_size: int = 500):

        self._candles = deque(maxlen=max_size)

    # ==========================================================
    # INSERÇÃO
    # ==========================================================

    def add(self, candle: Candle) -> None:
        self._candles.append(candle)

    # ==========================================================
    # CONSULTA
    # ==========================================================

    def last(self) -> Candle | None:

        if not self._candles:
            return None

        return self._candles[-1]

    def previous(self) -> Candle | None:

        if len(self._candles) < 2:
            return None

        return self._candles[-2]

    def get(self, index: int) -> Candle:
        return self._candles[index]

    def last_n(self, amount: int) -> list[Candle]:

        if amount <= 0:
            return []

        return list(self._candles)[-amount:]

    def all(self) -> list[Candle]:
        return list(self._candles)

    # ==========================================================
    # ESTATÍSTICAS
    # ==========================================================

    def highest_high(self, amount: int | None = None) -> float | None:

        candles = self.last_n(amount) if amount else self.all()

        if not candles:
            return None

        return max(c.high for c in candles)

    def lowest_low(self, amount: int | None = None) -> float | None:

        candles = self.last_n(amount) if amount else self.all()

        if not candles:
            return None

        return min(c.low for c in candles)

    # ==========================================================
    # CONTROLE
    # ==========================================================

    def clear(self) -> None:
        self._candles.clear()

    # ==========================================================
    # PROPRIEDADES
    # ==========================================================

    @property
    def size(self) -> int:
        return len(self._candles)

    @property
    def empty(self) -> bool:
        return len(self._candles) == 0

    # ==========================================================
    # PYTHON
    # ==========================================================

    def __len__(self) -> int:
        return len(self._candles)

    def __iter__(self):
        return iter(self._candles)

    def __getitem__(self, index):
        return self._candles[index]

    def __repr__(self) -> str:
        return f"CandleHistory(size={len(self._candles)})"