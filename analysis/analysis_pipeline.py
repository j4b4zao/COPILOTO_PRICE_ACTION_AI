"""
analysis/analysis_pipeline.py

Pipeline principal do
COPILOTO PRICE ACTION AI.

RC14.7 - EXTERNAL CONTEXT SCORE A/B OBSERVATIONAL
"""

from core.analysis_context import AnalysisContext
from external_context.external_market_state import ExternalMarketState

from analysis.market_structure import MarketStructure
from analysis.market_regime import MarketRegime
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from analysis.liquidity_analysis import LiquidityAnalysis
from analysis.volume_analysis import VolumeAnalysis
from analysis.order_flow import OrderFlow
from analysis.price_action.price_action import PriceAction
from analysis.book_diagnostics_engine import BookDiagnosticsEngine
from analysis.replay.book_diagnostics_replay_recorder import BookDiagnosticsReplayRecorder
from analysis.replay.score_regime_mtf_ab_recorder import ScoreRegimeMtfABRecorder
from analysis.replay.score_external_context_ab_recorder import ScoreExternalContextABRecorder

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

    def __init__(self, event_bus=None, external_context_service=None):

        if (
            external_context_service is not None
            and not callable(getattr(external_context_service, "snapshot", None))
        ):
            raise TypeError(
                "External context service deve expor snapshot()."
            )

        self.event_bus = event_bus
        self.external_context_service = external_context_service
        self.context = AnalysisContext()

        # Recorders estritamente passivos. Todos leem o resultado final do ciclo,
        # mas nunca escrevem de volta no AnalysisContext.
        self.book_diagnostics_replay = BookDiagnosticsReplayRecorder()
        self.score_regime_mtf_ab = ScoreRegimeMtfABRecorder()
        self.score_external_context_ab = ScoreExternalContextABRecorder()

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

        # O monitor externo é opcional e fail-safe. Falhas externas nunca
        # interrompem o núcleo WIN/WDO e nunca criam decisão operacional.
        self._refresh_external_context()

        self.context.clear_results()

        for engine in self.engines:
            if not engine.ENABLED:
                continue

            engine.executar(self.context)
            self._publish_engine(engine)

        # Snapshots A/B são criados somente depois do DecisionEngine terminar.
        # Portanto, nenhum deles influencia o ciclo oficial que está sendo medido.
        self.book_diagnostics_replay.record(self.context)
        self.score_regime_mtf_ab.record(self.context)
        self.score_external_context_ab.record(self.context)

        self._publish_loop()

        return self.context

    def _refresh_external_context(self) -> None:
        """Atualiza o snapshot externo sem permitir falha da fonte no núcleo."""
        if self.external_context_service is None:
            return

        try:
            state = self.external_context_service.snapshot()
        except Exception as exc:  # monitor externo não pode derrubar o núcleo
            self.context.external_market.clear()
            self.context.external_market.add_reason(
                "Contexto externo indisponível: "
                f"{type(exc).__name__}."
            )
            return

        if not isinstance(state, ExternalMarketState):
            self.context.external_market.clear()
            self.context.external_market.add_reason(
                "ExternalContextService retornou estado inválido."
            )
            return

        self.context.external_market = state

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
