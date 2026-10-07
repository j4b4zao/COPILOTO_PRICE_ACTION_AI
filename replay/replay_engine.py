"""Offline replay of official decisions, with independent execution sessions.

Sequence: market -> existing-position update -> pipeline -> metrics -> opening.
Only closed trades reach statistics. Zero realized profit retains the existing
statistics convention (win). Callers must supply an offline pipeline/context.
"""
from copy import deepcopy
from types import SimpleNamespace

from core.analysis_context import AnalysisContext
from performance.order_flow_experiment_metrics import OrderFlowExperimentMetrics
from replay.replay_statistics import ReplayStatistics
from replay.trade_simulator import TradeSimulator


class ReplayEngine:
    NAME = "ReplayEngine"
    VERSION = "CURRENT-DECISION-CONTRACT-RC1"
    _LIVE_RESOURCES = ("event_bus", "external_context_service", "book_depth_service",
                       "collector", "connection", "order_gateway", "execution")

    def __init__(self, pipeline, order_flow_metrics=None):
        self.pipeline = pipeline
        self.statistics = ReplayStatistics()
        self.simulator = TradeSimulator()
        self.order_flow_metrics = (OrderFlowExperimentMetrics()
                                   if order_flow_metrics is None else order_flow_metrics)

    def _session_pipeline(self):
        # Never reset/copy known live resources. Arbitrary injected code remains
        # the caller's responsibility; there is no live wiring in this driver.
        if any(getattr(self.pipeline, name, None) is not None for name in self._LIVE_RESOURCES):
            raise ValueError("Replay requires an offline pipeline without live resources")
        try:
            pipeline = deepcopy(self.pipeline)
        except Exception as exc:
            raise ValueError("Pipeline cannot be isolated for replay") from exc
        if pipeline is self.pipeline or not callable(getattr(pipeline, "executar", None)):
            raise ValueError("Pipeline cannot be isolated for replay")
        return pipeline

    def _register(self, trade):
        if trade is not None and trade.closed:
            self.statistics.register_operation(SimpleNamespace(name=trade.setup), trade.profit)

    def executar(self, context, candles):
        # Clear only replay-owned state, including empty sessions and failures.
        self.statistics = ReplayStatistics()
        self.simulator = TradeSimulator()
        if not isinstance(context, AnalysisContext):
            raise TypeError("Replay requires AnalysisContext")
        if context.market.candle_count:
            raise ValueError("Replay requires a fresh offline context for each session")
        if type(self.order_flow_metrics) is not OrderFlowExperimentMetrics:
            raise TypeError("Replay requires isolated OrderFlowExperimentMetrics")
        pipeline = self._session_pipeline()
        self.order_flow_metrics.clear()
        last_candle = None
        for candle in candles:
            if not self.simulator.valid_candle(candle):
                raise ValueError("Replay requires finite OHLC and explicit datetime timestamps")
            if last_candle is not None:
                try:
                    later = candle.timestamp > last_candle.timestamp
                except TypeError as exc:
                    raise ValueError("Replay timestamps must be comparable") from exc
                if not later:
                    raise ValueError("Replay timestamps must be strictly increasing")
            context.market.update(
                candle=candle, symbol=context.market.symbol or "REPLAY",
                timeframe=context.market.timeframe or "REPLAY", volume=candle.volume,
                timestamp=candle.timestamp, new_candle=True,
            )
            self.statistics.result.candles += 1
            self._register(self.simulator.update(candle))
            # Pipeline consumes the current candle before any new authorization.
            pipeline.executar(context)
            self.order_flow_metrics.register(context)
            self.simulator.simulate(context, candle)
            last_candle = candle
        if last_candle is not None:
            self._register(self.simulator.close(last_candle.close, reason="SESSION_END"))
        result = self.statistics.finish()
        result.order_flow_metrics = self.order_flow_metrics.snapshot()
        return deepcopy(result)
