"""
replay/replay_engine.py

Replay Engine

Executa a mesma pipeline utilizada
na operação em tempo real.

RC6
"""

from replay.replay_statistics import ReplayStatistics
from replay.trade_simulator import TradeSimulator


class ReplayEngine:

    NAME = "ReplayEngine"

    VERSION = "RC6"

    def __init__(self, pipeline):

        self.pipeline = pipeline

        self.statistics = ReplayStatistics()

        self.simulator = TradeSimulator()

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, context, candles):

        """
        Executa um replay candle a candle.

        Parameters
        ----------
        context : AnalysisContext

        candles : list[Candle]
        """

        for candle in candles:

            # --------------------------------------------------
            # Atualiza mercado
            # --------------------------------------------------

            context.market.candles.add(candle)

            context.market.ready = True

            self.statistics.result.candles += 1

            # --------------------------------------------------
            # Executa Pipeline
            # --------------------------------------------------

            self.pipeline.executar(context)

            strategy = context.strategy

            if not strategy.valid:
                continue

            # --------------------------------------------------
            # Simula Trade
            # --------------------------------------------------

            trade = self.simulator.simulate(

                strategy,

                candle

            )

            # --------------------------------------------------
            # Estatísticas
            # --------------------------------------------------

            self.statistics.register_operation(

                strategy,

                trade.profit

            )

        return self.statistics.finish()