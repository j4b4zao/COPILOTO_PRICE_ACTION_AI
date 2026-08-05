"""
analysis/swing_detector.py

Detecta Swing High e Swing Low a partir do histórico
de candles.

Não realiza nenhuma análise estrutural (HH, HL, BOS,
CHoCH ou tendência). Apenas identifica pivôs.
"""

from __future__ import annotations

from models.candle_history import CandleHistory
from models.swing import Swing
from models.enums import SwingType


class SwingDetector:

    def __init__(self, left_bars: int = 2, right_bars: int = 2):

        self.left_bars = left_bars
        self.right_bars = right_bars

    # ==========================================================
    # DETECÇÃO
    # ==========================================================

    def detectar(self, history: CandleHistory) -> list[Swing]:

        swings: list[Swing] = []

        if len(history) < (self.left_bars + self.right_bars + 1):
            return swings

        for i in range(
            self.left_bars,
            len(history) - self.right_bars,
        ):

            candle = history[i]

            if self._is_swing_high(history, i):

                swings.append(
                    self._build_high(
                        candle,
                        i,
                    )
                )

            elif self._is_swing_low(history, i):

                swings.append(
                    self._build_low(
                        candle,
                        i,
                    )
                )

        return swings

    # ==========================================================
    # SWING HIGH
    # ==========================================================

    def _is_swing_high(
        self,
        history: CandleHistory,
        index: int,
    ) -> bool:

        current = history[index]

        for i in range(
            index - self.left_bars,
            index,
        ):

            if history[i].high >= current.high:
                return False

        for i in range(
            index + 1,
            index + self.right_bars + 1,
        ):

            if history[i].high >= current.high:
                return False

        return True

    # ==========================================================
    # SWING LOW
    # ==========================================================

    def _is_swing_low(
        self,
        history: CandleHistory,
        index: int,
    ) -> bool:

        current = history[index]

        for i in range(
            index - self.left_bars,
            index,
        ):

            if history[i].low <= current.low:
                return False

        for i in range(
            index + 1,
            index + self.right_bars + 1,
        ):

            if history[i].low <= current.low:
                return False

        return True

    # ==========================================================
    # BUILDERS
    # ==========================================================

    def _build_high(
        self,
        candle,
        index: int,
    ) -> Swing:

        return Swing(
            type=SwingType.HIGH,
            candle_index=index,
            timestamp=candle.timestamp,
            price=candle.high,
            left_strength=self.left_bars,
            right_strength=self.right_bars,
            confirmed=True,
        )

    def _build_low(
        self,
        candle,
        index: int,
    ) -> Swing:

        return Swing(
            type=SwingType.LOW,
            candle_index=index,
            timestamp=candle.timestamp,
            price=candle.low,
            left_strength=self.left_bars,
            right_strength=self.right_bars,
            confirmed=True,
        )