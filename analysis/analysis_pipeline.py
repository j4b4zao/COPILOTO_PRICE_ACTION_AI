"""
analysis/analysis_pipeline.py

Pipeline principal do
COPILOTO PRICE ACTION AI.

RC14.4 - BOOK DIAGNOSTICS REPLAY/A-B OBSERVATIONAL
"""

from core.analysis_context import AnalysisContext

from analysis.market_structure import MarketStructure
from analysis.market_regime import MarketRegime
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from analysis.liquidity_analysis import LiquidityAnalysis
from analysis.volume_analysis import VolumeAnalysis
from analysis.order_flow import OrderFlow
from analysis.price_action.price_action import PriceAction
from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from analysis.replay.book_diagnostics_replay_recorder import BookDiagnosticsReplayRecorder

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

    def __init__(self, event_bus=None):

        self.event_bus = event_bus
        self.context = AnalysisContext()

        # Recorder estritamente passivo. Ele lê o resultado final do ciclo,
        # mas nunca escreve de volta no AnalysisContext.
        self.book_diagnostics_replay = BookDiagnosticsReplayRecorder()

        self.price_action_engines = [
            MarketRegime(),
            MultiTimeframeAnalysis(),
            MarketStructure(),
            LiquidityAnalysis(),
            VolumeAnalysis(),
            OrderFlow(),
            PriceAction(),
            BookDiagnosticsEngine(),
        ]

        self.smart_money_engines = [
            Imbalance(),
            OrderBlock(),
            FairValueGap(),
            LiquidityPool(),
        ]

        self.ai_engines = [
            ContextEngine(),
            StrategyEngine(),
            ScoreEngine(),
            RiskManager(),
            DecisionEngine(),
        ]

        self.engines = (
            self.price_action_engines
            + self.smart_money_engines
            + self.ai_engines
        )

        self.engines.sort(key=lambda engine: engine.PRIORITY)

    def executar(self, context):

        if not isinstance(context, AnalysisContext):
            raise TypeError(
                "AnalysisPipeline esperava AnalysisContext, "
                f"recebeu {type(context).__name__}"
            )

        self.context = context
        self.context.clear_results()

        for engine in self.engines:
            if not engine.ENABLED:
                continue

            engine.executar(self.context)
            self._publish_engine(engine)

        # O snapshot A/B é criado somente depois do DecisionEngine terminar.
        # Portanto, compara o núcleo oficial concluído contra a síntese RC7,
        # sem permitir qualquer influência no ciclo atual.
        self.book_diagnostics_replay.record(self.context)

        self._publish_loop()

        return self.context

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

        self.event_bus.publish(
            Event(
                event_type,
                self.context,
            )
        )

    def _publish_loop(self):

        if self.event_bus is None:
            return

        self.event_bus.publish(
            Event(
                EventType.LOOP_COMPLETED,
                self.context,
            )
        )
