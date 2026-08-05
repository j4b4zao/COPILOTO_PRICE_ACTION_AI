"""
replay/trade_simulator.py

Trade Simulator

Responsável por simular operações durante
Replay e Backtest.

RC7
"""

from dataclasses import dataclass

from config.settings import (
    DEFAULT_STOP,
    DEFAULT_TARGET,
    DEFAULT_RR,
)


@dataclass(slots=True)
class TradeResult:

    opened: bool = False
    closed: bool = False

    direction: str = "NONE"

    entry: float = 0.0

    stop: float = 0.0

    target: float = 0.0

    exit: float = 0.0

    profit: float = 0.0

    bars: int = 0

    max_profit: float = 0.0

    max_loss: float = 0.0

    reason: str = ""

    setup: str = ""


class TradeSimulator:

    NAME = "TradeSimulator"

    VERSION = "RC7"

    def __init__(self):

        self.trade = None

    # ==========================================================
    # ABRIR OPERAÇÃO
    # ==========================================================

    def simulate(self, strategy, candle):

        trade = TradeResult()

        trade.opened = True

        trade.direction = strategy.signal

        trade.entry = candle.close

        trade.setup = strategy.name

        if strategy.signal == "BUY":

            trade.stop = trade.entry - DEFAULT_STOP

            trade.target = trade.entry + DEFAULT_TARGET

        elif strategy.signal == "SELL":

            trade.stop = trade.entry + DEFAULT_STOP

            trade.target = trade.entry - DEFAULT_TARGET

        self.trade = trade

        return trade

    # ==========================================================
    # ATUALIZAR OPERAÇÃO
    # ==========================================================

    def update(self, candle):

        if self.trade is None:

            return None

        trade = self.trade

        trade.bars += 1

        # ---------------------------------------------
        # BUY
        # ---------------------------------------------

        if trade.direction == "BUY":

            ganho = candle.high - trade.entry

            perda = trade.entry - candle.low

            trade.max_profit = max(

                trade.max_profit,

                ganho,

            )

            trade.max_loss = max(

                trade.max_loss,

                perda,

            )

            # STOP

            if candle.low <= trade.stop:

                trade.closed = True

                trade.exit = trade.stop

                trade.profit = -DEFAULT_STOP

                trade.reason = "STOP"

                self.trade = None

                return trade

            # TARGET

            if candle.high >= trade.target:

                trade.closed = True

                trade.exit = trade.target

                trade.profit = DEFAULT_TARGET

                trade.reason = "TARGET"

                self.trade = None

                return trade

        # ---------------------------------------------
        # SELL
        # ---------------------------------------------

        else:

            ganho = trade.entry - candle.low

            perda = candle.high - trade.entry

            trade.max_profit = max(

                trade.max_profit,

                ganho,

            )

            trade.max_loss = max(

                trade.max_loss,

                perda,

            )

            if candle.high >= trade.stop:

                trade.closed = True

                trade.exit = trade.stop

                trade.profit = -DEFAULT_STOP

                trade.reason = "STOP"

                self.trade = None

                return trade

            if candle.low <= trade.target:

                trade.closed = True

                trade.exit = trade.target

                trade.profit = DEFAULT_TARGET

                trade.reason = "TARGET"

                self.trade = None

                return trade

        return None

    # ==========================================================
    # EXISTE OPERAÇÃO?
    # ==========================================================

    @property
    def opened(self):

        return self.trade is not None

    # ==========================================================
    # FECHAR FORÇADO
    # ==========================================================

    def close(self, price):

        if self.trade is None:

            return None

        trade = self.trade

        trade.closed = True

        trade.exit = price

        if trade.direction == "BUY":

            trade.profit = price - trade.entry

        else:

            trade.profit = trade.entry - price

        trade.reason = "MANUAL"

        self.trade = None

        return trade