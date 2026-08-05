"""
replay/trade_manager.py

Trade Manager

Responsável pelo ciclo de vida das operações.

RC6
"""

from replay.trade_simulator import TradeSimulator


class TradeManager:

    NAME = "TradeManager"

    VERSION = "RC6"

    def __init__(self):

        self.simulator = TradeSimulator()

        self.trade = None

    # ==========================================================
    # EXISTE OPERAÇÃO?
    # ==========================================================

    @property
    def opened(self):

        return self.trade is not None

    # ==========================================================
    # ABRIR
    # ==========================================================

    def open(self, strategy, candle):

        self.trade = self.simulator.simulate(

            strategy,

            candle

        )

    # ==========================================================
    # ATUALIZAR
    # ==========================================================

    def update(self, candle):

        if self.trade is None:

            return None

        #
        # RC6
        #
        # Ainda não acompanha candles.
        #
        # RC7 fará:
        #
        # Stop
        # Gain
        # BreakEven
        # Parcial
        # Trailing Stop
        #

        return self.trade

    # ==========================================================
    # FECHAR
    # ==========================================================

    def close(self):

        trade = self.trade

        self.trade = None

        return trade