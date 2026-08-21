"""
analysis/analysis_pipeline.py

Pipeline principal do
COPILOTO PRICE ACTION AI.

RC14.2 - MULTI-TIMEFRAME SAFETY GATE
"""

from core.analysis_context import AnalysisContext

# ==========================================================

# PRICE ACTION

# ==========================================================

from analysis.market_structure import MarketStructure
from analysis.market_regime import MarketRegime
from analysis.multi_timeframe_analysis import MultiTimeframeAnalysis
from analysis.liquidity_analysis import LiquidityAnalysis
from analysis.volume_analysis import VolumeAnalysis
from analysis.order_flow import OrderFlow
from analysis.price_action.price_action import PriceAction

# ==========================================================

# SMART MONEY

# ==========================================================

from analysis.smart_money.imbalance import Imbalance
from analysis.smart_money.order_block import OrderBlock
from analysis.smart_money.fair_value_gap import FairValueGap
from analysis.smart_money.liquidity_pool import LiquidityPool

# ==========================================================

# IA

# ==========================================================

from brain.context_engine import ContextEngine

from strategies.strategy_engine import StrategyEngine

from ai.score_engine import ScoreEngine
from risk.risk_manager import RiskManager
from decision.decision_engine import DecisionEngine

# ==========================================================

# EVENTOS

# ==========================================================

from core.event import Event
from core.event_types import EventType


class AnalysisPipeline:


    def __init__(self, event_bus=None):

        self.event_bus = event_bus

        self.context = AnalysisContext()

    # ======================================================
    # PRICE ACTION
    # ======================================================

        self.price_action_engines = [

            MarketRegime(),

            MultiTimeframeAnalysis(),

            MarketStructure(),

            LiquidityAnalysis(),

            VolumeAnalysis(),

            OrderFlow(),

            PriceAction(),

        ]

    # ======================================================
    # SMART MONEY
    # ======================================================

        self.smart_money_engines = [

            Imbalance(),

            OrderBlock(),

            FairValueGap(),

            LiquidityPool(),

        ]

    # ======================================================
    # IA
    # ======================================================

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

        self.engines.sort(

            key=lambda engine: engine.PRIORITY

        )

# ==========================================================
# EXECUTAR
# ==========================================================

    def executar(self, context):

    # ======================================================
    # RECEBER O ANALYSIS CONTEXT DO COLLECTOR
    # ======================================================

        if not isinstance(context, AnalysisContext):

            raise TypeError(
                "AnalysisPipeline esperava AnalysisContext, "
                f"recebeu {type(context).__name__}"
            )

        self.context = context

    # ======================================================
    # LIMPAR RESULTADOS DA ANÁLISE ANTERIOR
    # ======================================================

        self.context.clear_results()

    # ======================================================
    # EXECUTAR ENGINES
    # ======================================================

        for engine in self.engines:

            if not engine.ENABLED:

                continue

            engine.executar(self.context)

            self._publish_engine(engine)

    # ======================================================
    # FINALIZAR LOOP
    # ======================================================

        self._publish_loop()

        return self.context

# ==========================================================
# PUBLICAR ENGINE
# ==========================================================

    def _publish_engine(self, engine):

        if self.event_bus is None:

            return

        mapping = {

        # ===============================================
        # PRICE ACTION
        # ===============================================

            MarketRegime:
                EventType.REGIME_UPDATED,

            MultiTimeframeAnalysis:
                EventType.MULTI_TIMEFRAME_UPDATED,

            MarketStructure:
                EventType.STRUCTURE_UPDATED,

            LiquidityAnalysis:
                EventType.LIQUIDITY_UPDATED,

            VolumeAnalysis:
                EventType.VOLUME_UPDATED,

            OrderFlow:
                EventType.ORDER_FLOW_UPDATED,

            PriceAction:
                EventType.PRICE_ACTION_UPDATED,

        # ===============================================
        # SMART MONEY
        # ===============================================

            Imbalance:
                EventType.IMBALANCE_UPDATED,

            OrderBlock:
                EventType.ORDER_BLOCK_UPDATED,

            FairValueGap:
                EventType.FAIR_VALUE_GAP_UPDATED,

            LiquidityPool:
                EventType.LIQUIDITY_POOL_UPDATED,

        # ===============================================
        # IA
        # ===============================================

            ContextEngine:
                EventType.CONTEXT_UPDATED,

            StrategyEngine:
                EventType.STRATEGY_UPDATED,

            ScoreEngine:
                EventType.SCORE_UPDATED,

            RiskManager:
                EventType.RISK_UPDATED,

            DecisionEngine:
                EventType.DECISION_UPDATED,

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

# ==========================================================
# LOOP
# ==========================================================

    def _publish_loop(self):

        if self.event_bus is None:

            return

        self.event_bus.publish(

            Event(

            EventType.LOOP_COMPLETED,

            self.context,

        )

    )
