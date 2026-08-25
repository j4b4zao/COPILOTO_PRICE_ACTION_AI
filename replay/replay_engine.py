"""
replay/replay_engine.py

Replay Engine

Executa a mesma pipeline utilizada
na operação em tempo real.

RC6.1 - ORDER FLOW EXPERIMENT METRICS
"""

from performance.order_flow_experiment_metrics import (
    OrderFlowExperimentMetrics,
)
from replay.replay_statistics import ReplayStatistics
from replay.trade_simulator import TradeSimulator


class ReplayEngine:

    NAME = "ReplayEngine"

    VERSION = "RC6.1"

    def __init__(self, pipeline, order_flow_metrics=None):

        self.pipeline = pipeline

        self.statistics = ReplayStatistics()

        self.simulator = TradeSimulator()

        self.order_flow_metrics = (
            OrderFlowExperimentMetrics()
            if order_flow_metrics is None
            else order_flow_metrics
        )

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

            context.market.update(
                candle=candle,
                symbol=context.market.symbol or "REPLAY",
                timeframe=context.market.timeframe or "REPLAY",
                volume=candle.volume,
                timestamp=candle.timestamp,
                new_candle=True,
            )

            self.statistics.result.candles += 1

            # --------------------------------------------------
            # Executa Pipeline
            # --------------------------------------------------

            self.pipeline.executar(context)

            self.order_flow_metrics.register(context)

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

        result = self.statistics.finish()

        result.order_flow_metrics = (
            self.order_flow_metrics.snapshot()
        )

        return result
