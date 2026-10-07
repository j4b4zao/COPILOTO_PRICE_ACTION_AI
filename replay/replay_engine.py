"""Offline lifecycle with engine-owned, immutable opening/abort evidence.

Known resources are blocked locally. Trusted custom code, globals and deepcopy
hooks remain the caller's responsibility; this gate is not a Python sandbox.
"""
from copy import deepcopy
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from types import SimpleNamespace

from analysis import analysis_pipeline as pipeline_module
from core.analysis_context import AnalysisContext
from models.candle import Candle
from models.decision_result import DecisionResult
from performance.order_flow_experiment_metrics import OrderFlowExperimentMetrics
from replay.replay_result import ReplayAuditSnapshot, ReplayClosedTradeSnapshot, ReplayResult
from replay.replay_statistics import ReplayStatistics
from replay.trade_simulator import TradeSimulator


class ReplayAbortedError(ValueError):
    """A failed session, never a completed result; original error is __cause__."""
    def __init__(self, audit_snapshot, result_snapshot=None):
        super().__init__(f"Replay aborted at {audit_snapshot.abort_stage}: {audit_snapshot.abort_reason}")
        self.audit_snapshot = audit_snapshot
        self.result_snapshot = result_snapshot


def _plain(value):
    """Copy only known value containers; never invoke a custom deepcopy hook."""
    if type(value) in (str, int, float, bool, datetime) or value is None:
        return value
    if type(value) is dict:
        return {_plain(key): _plain(item) for key, item in value.items()}
    if type(value) is tuple:
        return tuple(_plain(item) for item in value)
    if type(value) is list:
        return [_plain(item) for item in value]
    raise TypeError("Replay snapshots require plain values")


def _baseline(value, default, *, ignore=()):
    """Structural comparison of real defaults, without object identity equality."""
    if type(value) is not type(default):
        return False
    if is_dataclass(default):
        return all(_baseline(getattr(value, field.name), getattr(default, field.name))
                   for field in fields(default) if field.name not in ignore)
    if isinstance(default, Enum):
        return value == default
    if type(default) in (str, int, float, bool, datetime) or default is None:
        return value == default
    if type(default) in (list, tuple):
        return len(value) == len(default) and all(_baseline(a, b) for a, b in zip(value, default))
    if type(default) is dict:
        return value.keys() == default.keys() and all(_baseline(value[k], default[k]) for k in default)
    return False


class ReplayEngine:
    NAME = "ReplayEngine"
    VERSION = "OFFLINE-CAUSALITY-AUDIT-RC3"
    STAGES = ("VALIDATE", "MARKET", "UPDATE", "REGISTER", "PIPELINE", "METRICS", "OPEN",
              "SESSION_END_CLOSE", "SESSION_END_REGISTER", "FINISH", "SNAPSHOT", "ITERATE")
    _LIVE_RESOURCES = ("event_bus", "external_context_service", "book_depth_service",
                       "collector", "connection", "order_gateway", "execution",
                       "psychology_state_provider", "psychology_evidence_correlator",
                       "psychology_evidence_presenter", "psychology_confirmation_audit",
                       "psychology_session_journal")

    def __init__(self, pipeline, order_flow_metrics=None, *, trusted_offline=False):
        self.pipeline = pipeline
        self.trusted_offline = trusted_offline
        self.statistics = ReplayStatistics()
        self.simulator = TradeSimulator()
        self.order_flow_metrics = (OrderFlowExperimentMetrics()
                                   if order_flow_metrics is None else order_flow_metrics)

    @staticmethod
    def _context_gate(context):
        if type(context) is not AnalysisContext:
            raise TypeError("Replay requires exact AnalysisContext")
        default = AnalysisContext()
        market = context.market
        if (type(market) is not type(default.market)
                or type(market.candles) is not type(default.market.candles)
                or market.candle_count != 0
                or type(market.symbol) is not str or type(market.timeframe) is not str
                or market.last_price != 0 or market.volume != 0 or market.timestamp is not None):
            raise ValueError("Replay requires fresh market state")
        for field in fields(default):
            name = field.name
            if name == "market":
                continue  # Symbol/timeframe are caller-supplied identifiers.
            value, baseline = getattr(context, name), getattr(default, name)
            if name == "economic_calendar":
                # unavailable() stamps construction time; no historical input.
                valid = (type(value) is type(baseline) and type(value.observed_at) is datetime
                         and _baseline(value, baseline, ignore=("observed_at",)))
            else:
                valid = _baseline(value, baseline)
            if not valid:
                raise ValueError(f"Replay requires baseline {name}")

    def _session_pipeline(self):
        official = type(self.pipeline) is pipeline_module.AnalysisPipeline
        if not official and self.trusted_offline is not True:
            raise ValueError("Custom pipeline requires trusted_offline=True before copying")
        if any(getattr(self.pipeline, name, None) is not None for name in self._LIVE_RESOURCES):
            raise ValueError("Replay requires an offline pipeline without live resources")
        if official:
            self._context_gate(self.pipeline.context)
            expected = [getattr(pipeline_module, name) for name in (
                "MarketRegime", "MultiTimeframeAnalysis", "MarketStructure", "LiquidityAnalysis",
                "VolumeAnalysis", "OrderFlow", "BookDepthAnalysis", "PriceAction", "BookDiagnosticsEngine",
                "Imbalance", "OrderBlock", "FairValueGap", "LiquidityPool", "ContextEngine",
                "StrategyEngine", "ScoreEngine", "RiskManager", "DecisionEngine")]
            expected.sort(key=lambda cls: cls.PRIORITY)
            if [type(engine) for engine in self.pipeline.engines] != expected:
                raise ValueError("Official pipeline requires its audited engine types")
            for name, cls in (("psychology_runtime", pipeline_module.TraderPsychologyRuntime),
                              ("psychology_context_bridge", pipeline_module.TraderPsychologyContextBridge)):
                if type(getattr(self.pipeline, name)) is not cls:
                    raise ValueError("Official pipeline has a custom callback")
        try:
            pipeline = deepcopy(self.pipeline)
        except MemoryError:
            raise
        except Exception as exc:
            raise ValueError("Pipeline cannot be isolated for replay") from exc
        if pipeline is self.pipeline or not callable(getattr(pipeline, "executar", None)):
            raise ValueError("Pipeline cannot be isolated for replay")
        return pipeline, "KNOWN_OFFLINE_CONTRACT" if official else "CALLER_DECLARED"

    @staticmethod
    def _trade_snapshot(trade):
        if trade is None:
            return None
        data = {}
        for field in fields(ReplayClosedTradeSnapshot):
            value = getattr(trade, field.name)
            if field.name in ("direction", "setup", "reason"):
                valid = type(value) is str
            elif field.name in ("opened_at", "last_timestamp"):
                valid = value is None or type(value) is datetime
            elif field.name == "bars":
                valid = type(value) is int
            else:
                valid = type(value) in (int, float)
            if not valid:
                raise TypeError("Trade audit requires immutable primitive fields")
            data[field.name] = value
        return ReplayClosedTradeSnapshot(**data)

    def _register(self, trade):
        if trade is not None and trade.closed:
            self.statistics.register_operation(SimpleNamespace(name=trade.setup), trade.profit)

    def _checkpoint(self):
        return ReplayResult(**{field.name: _plain(getattr(self.statistics.result, field.name))
                               for field in fields(ReplayResult) if field.name != "audit"})

    @staticmethod
    def _snapshot_result(result):
        return deepcopy(result)

    @staticmethod
    def _audit(state, reasons, closed, pending, scope, *, completed=False,
               stage=None, index=None, timestamp=None, error=None, reason=None, uncertain=False):
        return ReplayAuditSnapshot(
            **state, completed=completed, aborted=error is not None,
            reason_counts=tuple((category, raw, count) for (category, raw), count in sorted(reasons.items())),
            abort_reason=reason, abort_stage=stage, abort_candle_index=index,
            abort_timestamp=timestamp, error_type=type(error).__name__ if error is not None else None,
            pending_open_trade=pending, closed_trades=tuple(closed),
            uncertain_state=uncertain, offline_scope=scope,
        )

    def executar(self, context, candles):
        # Preflight precedes copying, consuming inputs, or clearing metrics.
        self._context_gate(context)
        if type(self.order_flow_metrics) is not OrderFlowExperimentMetrics:
            raise TypeError("Replay requires isolated OrderFlowExperimentMetrics")
        pipeline, scope = self._session_pipeline()
        self.order_flow_metrics.clear()  # A failure here is fail-before-session.
        self.statistics = ReplayStatistics()
        self.simulator = TradeSimulator()
        state = dict(candles_processed=0, decision_buy_sell=0, trades_opened=0,
                     trades_closed=0, skipped=0, rejected=0, unresolved_candles=0,
                     statistics_committed_trades=0)
        reasons, closed = {}, []
        pending, last_candle, timestamp = None, None, None
        checkpoint = ReplayResult()
        metrics_checkpoint = {}
        stage, index, abort_reason = "ITERATE", 0, None
        try:
            iterator = iter(candles)
            while True:
                stage, abort_reason, timestamp = "ITERATE", None, None
                try:
                    source = next(iterator)
                except StopIteration:
                    break
                stage = "VALIDATE"
                raw_timestamp = getattr(source, "timestamp", None)
                timestamp = raw_timestamp if type(raw_timestamp) is datetime else None
                abort_reason = "INVALID_CANDLE"
                # Copy input values, not user-defined objects or deepcopy hooks.
                candle = Candle(**{name: _plain(getattr(source, name))
                                  for name in ("open", "high", "low", "close", "volume", "timestamp")})
                if not self.simulator.valid_candle(candle):
                    raise ValueError("Replay requires finite OHLC and explicit datetime timestamps")
                if last_candle is not None:
                    abort_reason = "INVALID_TIMESTAMP"
                    later = candle.timestamp > last_candle.timestamp
                    abort_reason = "NON_INCREASING_TIMESTAMP"
                    if not later:
                        raise ValueError("Replay timestamps must be strictly increasing")
                abort_reason = None
                stage = "MARKET"
                context.market.update(
                    candle=candle, symbol=context.market.symbol or "REPLAY",
                    timeframe=context.market.timeframe or "REPLAY", volume=candle.volume,
                    timestamp=candle.timestamp, new_candle=True,
                )
                state["candles_processed"] += 1
                state["unresolved_candles"] = 1
                self.statistics.result.candles += 1
                stage = "UPDATE"
                trade = self.simulator.update(candle)
                if trade is not None and trade.closed:
                    closed.append(self._trade_snapshot(trade))
                    state["trades_closed"] += 1
                pending = self._trade_snapshot(self.simulator.trade)
                if trade is not None and trade.closed:
                    stage = "REGISTER"
                    self._register(trade)
                    state["statistics_committed_trades"] += 1
                    checkpoint = self._checkpoint()
                stage = "PIPELINE"
                pipeline.executar(context)
                decision = context.decision
                if getattr(decision, "action", None) in ("BUY", "SELL"):
                    state["decision_buy_sell"] += 1
                expected_wait = (isinstance(decision, DecisionResult) and decision.action == "WAIT"
                                 and decision.direction == "NONE" and decision.signal == "NONE")
                stage = "METRICS"
                self.order_flow_metrics.register(context)
                metrics_checkpoint = _plain(self.order_flow_metrics.snapshot())
                stage = "OPEN"
                trade = self.simulator.simulate(context, candle)
                raw_reason = self.simulator.last_rejection  # Capture before any other simulator call.
                if trade is not None and trade.opened and not trade.closed:
                    state["trades_opened"] += 1
                else:
                    if not raw_reason:
                        raise RuntimeError("Simulator returned no opening outcome")
                    if expected_wait:
                        category = "EXPECTED_SKIP"
                        state["skipped"] += 1
                    else:
                        category = ("STATE_REJECTION" if raw_reason == "POSITION_ALREADY_OPEN" else
                                    "DATA_REJECTION" if raw_reason == "INVALID_CANDLE" else "CONTRACT_REJECTION")
                        state["rejected"] += 1
                    reasons[category, raw_reason] = reasons.get((category, raw_reason), 0) + 1
                state["unresolved_candles"] = 0
                pending = self._trade_snapshot(self.simulator.trade)
                last_candle = candle
                index += 1
            timestamp = last_candle.timestamp if last_candle is not None else None
            index = index - 1 if last_candle is not None else None
            stage = "SESSION_END_CLOSE"
            trade = self.simulator.close(last_candle.close, reason="SESSION_END") if last_candle else None
            if trade is not None and trade.closed:
                closed.append(self._trade_snapshot(trade))
                state["trades_closed"] += 1
            pending = self._trade_snapshot(self.simulator.trade)
            if trade is not None and trade.closed:
                stage = "SESSION_END_REGISTER"
                self._register(trade)
                state["statistics_committed_trades"] += 1
                checkpoint = self._checkpoint()
            stage = "FINISH"
            self.statistics.result.skipped = state["skipped"]
            result = self.statistics.finish()
            checkpoint = self._checkpoint()
            stage = "METRICS"
            result.order_flow_metrics = _plain(self.order_flow_metrics.snapshot())
            metrics_checkpoint = _plain(result.order_flow_metrics)
            stage = "SNAPSHOT"
            result.audit = self._audit(state, reasons, closed, pending, scope, completed=True)
            return self._snapshot_result(result)
        except MemoryError:
            raise
        except Exception as exc:
            # Certified primitives only: never retry a failed component or close
            # a position in the handler. Simulator failure may have mutated it;
            # pending then describes the last certified position, marked uncertain.
            uncertain = stage in ("UPDATE", "OPEN", "SESSION_END_CLOSE", "MARKET")
            audit = self._audit(state, reasons, closed, pending, scope, stage=stage,
                                index=index, timestamp=timestamp, error=exc,
                                reason=abort_reason or f"{stage}_ERROR", uncertain=uncertain)
            partial = ReplayResult(**{field.name: _plain(getattr(checkpoint, field.name))
                                      for field in fields(ReplayResult) if field.name != "audit"})
            partial.candles = state["candles_processed"]
            partial.skipped = state["skipped"]
            partial.order_flow_metrics = _plain(metrics_checkpoint)
            partial.audit = audit
            raise ReplayAbortedError(audit, partial) from exc
