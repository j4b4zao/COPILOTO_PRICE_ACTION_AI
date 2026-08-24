"""
analysis/swing_analyzer.py

Responsável por localizar Swings no histórico
de candles.

Não toma decisões de trading.

RC15
"""

from models.candle_history import CandleHistory
from models.swing import Swing
from models.enums import SwingType


class SwingAnalyzer:

    WINDOW = 2  # 2 antes + pivô + 2 depois = 5 candles

    def __init__(self, history: CandleHistory):

        self.history = history

    # ==========================================================
    # API PÚBLICA
    # ==========================================================

    def find_swings(self) -> list[Swing]:

        candles = self.history.all()

        swings: list[Swing] = []

        if len(candles) < 5:
            return swings

        for i in range(2, len(candles) - 2):

            current = candles[i]

            # -----------------------------
            # Swing High
            # -----------------------------

            if (

                current.high > candles[i - 1].high
                and current.high > candles[i - 2].high
                and current.high > candles[i + 1].high
                and current.high > candles[i + 2].high

            ):

                swings.append(

                    Swing(

                        type=SwingType.HIGH,

                        candle_index=i,

                        timestamp=current.timestamp,

                        price=current.high,

                        left_strength=2,

                        right_strength=2,

                        confirmed=True,

                    )

                )

            # -----------------------------
            # Swing Low
            # -----------------------------

            elif (

                current.low < candles[i - 1].low
                and current.low < candles[i - 2].low
                and current.low < candles[i + 1].low
                and current.low < candles[i + 2].low

            ):

                swings.append(

                    Swing(

                        type=SwingType.LOW,

                        candle_index=i,

                        timestamp=current.timestamp,

                        price=current.low,

                        left_strength=2,

                        right_strength=2,

                        confirmed=True,

                    )

                )

        return swings

    # ==========================================================
    # CONSULTAS
    # ==========================================================

    def last_swing_high(self) -> Swing | None:

        swings = self.find_swings()

        highs = [s for s in swings if s.is_high]

        if not highs:
            return None

        return highs[-1]

    def last_swing_low(self) -> Swing | None:

        swings = self.find_swings()

        lows = [s for s in swings if s.is_low]

        if not lows:
            return None

        return lows[-1]