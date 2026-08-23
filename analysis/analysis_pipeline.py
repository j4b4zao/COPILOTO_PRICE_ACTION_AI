"""
analysis/analysis_pipeline.py

Pipeline principal do COPILOTO PRICE ACTION AI.

RC15.4 - MICROSTRUCTURE ELIGIBILITY REPLAY OBSERVATIONAL
"""

from core.analysis_context import AnalysisContext
from external_context.external_market_state import ExternalMarketState
from models.book_depth import BookDepthSnapshot

from analysis.market_structure import MarketStructure
from analysis.market_regime import MarketRegime
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from analysis.liquidity_analysis import LiquidityAnalysis
from analysis.volume_analysis import VolumeAnalysis
from analysis.order_flow import OrderFlow
from analysis.book_depth_analysis import BookDepthAnalysis
from analysis.price_action.price_action import PriceAction
from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from analysis.replay.book_diagnostics_replay_recorder import BookDiagnosticsReplayRecorder
from analysis.replay.score_regime_mtf_ab_recorder import ScoreRegimeMtfABRecorder
from analysis.replay.score_external_context_ab_recorder import ScoreExternalContextABRecorder
from analysis.replay.score_order_flow_ab_recorder import ScoreOrderFlowABRecorder
from analysis.replay.score_order_flow_structure_ab_recorder import ScoreOrderFlowStructureABRecorder
from analysis.replay.score_book_depth_ab_recorder import ScoreBookDepthABRecorder
from analysis.replay.microstructure_confluence_replay_recorder import (
    MicrostructureConfluenceReplayRecorder,
)
from analysis.replay.microstructure_eligibility_replay_recorder import (
    MicrostructureEligibilityReplayRecorder,
)

from analysis.smart_money.imbalance import Imbalance
from analysis.smart_money.order_block import OrderBlock
from analysis.smart_money.fair_value_gap import FairValueGap
from analysis.smart_money.liquidity_pool import LiquidityPool

from brain.context_engine import ContextEngine
from strategies.strategy_engine import StrategyEngine
from ai.score_engine_rc13_2 import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine

from core.event import Event
from core.event_types import EventType


class AnalysisPipeline:

    def __init__(self, event_bus=None, external_context_service=None, book_depth_service=None):
        if external_context_service is not None and not callable(
            getattr(external_context_service, "snapshot", None)
        ):
            raise TypeError("External context service deve expor snapshot().")
        if book_depth_service is not None and not callable(
            getattr(book_depth_service, "snapshot", None)
        ):
            raise TypeError("Book depth service deve expor snapshot(symbol).")

        self.event_bus = event_bus
        self.external_context_service = external_context_service
        self.book_depth_service = book_depth_service
        self.context = AnalysisContext()

        self.book_diagnostics_replay = BookDiagnosticsReplayRecorder()
        self.score_regime_mtf_ab = ScoreRegimeMtfABRecorder()
        self.score_external_context_ab = ScoreExternalContextABRecorder()
        self.score_order_flow_ab = ScoreOrderFlowABRecorder()
        self.score_order_flow_structure_ab = ScoreOrderFlowStructureABRecorder()
        self.score_book_depth_ab = ScoreBookDepthABRecorder()
        self.microstructure_confluence_replay = MicrostructureConfluenceReplayRecorder()
        self.microstructure_eligibility_replay = MicrostructureEligibilityReplayRecorder()

        self.price_action_engines = [
            MarketRegime(),
            MultiTimeframeAnalysis(),
            MarketStructure(),
            LiquidityAnalysis(),
            VolumeAnalysis(),
            OrderFlow(),
            BookDepthAnalysis(),
            PriceAction(),
            BookDiagnosticsEngine(),
        ]
        self.smart_money_engines = [Imbalance(), OrderBlock(), FairValueGap(), LiquidityPool()]
        self.ai_engines = [ContextEngine(), StrategyEngine(), ScoreEngine(), RiskManager(), DecisionEngine()]
        self.engines = self.price_action_engines + self.smart_money_engines + self.ai_engines
        self.engines.sort(key=lambda engine: engine.PRIORITY)

    def executar(self, context):
        if not isinstance(context, AnalysisContext):
            raise TypeError(
                "AnalysisPipeline esperava AnalysisContext, "
                f"recebeu {type(context).__name__}"
            )

        self.context = context
        self._refresh_external_context()
        self._refresh_book_depth()
        self.context.clear_results()

        for engine in self.engines:
            if not engine.ENABLED:
                continue
            engine.executar(self.context)
            self._publish_engine(engine)

        # Todos os recorders abaixo executam depois do DecisionEngine e apenas
        # leem o resultado oficial já fechado do ciclo.
        self.book_diagnostics_replay.record(self.context)
        self.score_regime_mtf_ab.record(self.context)
        self.score_external_context_ab.record(self.context)
        self.score_order_flow_ab.record(self.context)
        self.score_order_flow_structure_ab.record(self.context)
        self.score_book_depth_ab.record(self.context)
        self.microstructure_confluence_replay.record(self.context)
        self.microstructure_eligibility_replay.record(self.context)
        self._publish_loop()
        return self.context

    def _refresh_external_context(self) -> None:
        if self.external_context_service is None:
            return
        try:
            state = self.external_context_service.snapshot()
        except Exception as exc:
            self.context.external_market.clear()
            self.context.external_market.add_reason(
                "Contexto externo indisponível: " f"{type(exc).__name__}."
            )
            return
        if not isinstance(state, ExternalMarketState):
            self.context.external_market.clear()
            self.context.external_market.add_reason(
                "ExternalContextService retornou estado inválido."
            )
            return
        self.context.external_market = state

    def _refresh_book_depth(self) -> None:
        if self.book_depth_service is None:
            return
        symbol = str(getattr(self.context.market, "symbol", "") or "")
        try:
            snapshot = self.book_depth_service.snapshot(symbol)
        except Exception:
            self.context.book_depth = BookDepthSnapshot.unavailable(
                symbol=symbol,
                source="BOOK_DEPTH_SERVICE_ERROR",
            )
            return
        if not isinstance(snapshot, BookDepthSnapshot):
            self.context.book_depth = BookDepthSnapshot.unavailable(
                symbol=symbol,
                source="BOOK_DEPTH_INVALID_SNAPSHOT",
            )
            return
        self.context.book_depth = snapshot

    def _publish_engine(self, engine):
        if self.event_bus is None:
            return
        mapping = {
            MarketRegime: EventType.REGIME_UPDATED,
            MultiTimeframeAnalysis: EventType.MULTI_TIMEFRAME_UPDATED,
            MarketStructure: EventType.STRUCTURE_UPDATED,
            LiquidityAnalysis: EventType.LIQUIDITY_UPDATED,
            VolumeAnalysis: EventType.VOLUME_UPDATED,
            OrderFlow: EventType.ORDER_FLOW_UPDATED,
            PriceAction: EventType.PRICE_ACTION_UPDATED,
            BookDiagnosticsEngine: EventType.BOOK_DIAGNOSTICS_UPDATED,
            Imbalance: EventType.IMBALANCE_UPDATED,
            OrderBlock: EventType.ORDER_BLOCK_UPDATED,
            FairValueGap: EventType.FAIR_VALUE_GAP_UPDATED,
            LiquidityPool: EventType.LIQUIDITY_POOL_UPDATED,
            ContextEngine: EventType.CONTEXT_UPDATED,
            StrategyEngine: EventType.STRATEGY_UPDATED,
            ScoreEngine: EventType.SCORE_UPDATED,
            RiskManager: EventType.RISK_UPDATED,
            DecisionEngine: EventType.DECISION_UPDATED,
        }
        event_type = mapping.get(type(engine))
        if event_type is None:
            return
        self.event_bus.publish(Event(event_type, self.context))

    def _publish_loop(self):
        if self.event_bus is None:
            return
        self.event_bus.publish(Event(EventType.LOOP_COMPLETED, self.context))
