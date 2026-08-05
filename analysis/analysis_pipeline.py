```python
"""
analysis/analysis_pipeline.py

Pipeline principal do
COPILOTO PRICE ACTION AI.

RC13
"""

from core.analysis_context import AnalysisContext

# ==========================================================
# PRICE ACTION
# ==========================================================

from analysis.market_structure import MarketStructure
from analysis.liquidity_analysis import LiquidityAnalysis
from analysis.volume_analysis import VolumeAnalysis
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
from risk.risk_engine import RiskEngine
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

            MarketStructure(),

            LiquidityAnalysis(),

            VolumeAnalysis(),

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

            RiskEngine(),

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

    def executar(self, market):

        self.context.market = market

        self.context.clear_results()

        for engine in self.engines:

            if not engine.ENABLED:

                continue

            engine.executar(self.context)

            self._publish_engine(engine)

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

            MarketStructure:
                EventType.STRUCTURE_UPDATED,

            LiquidityAnalysis:
                EventType.LIQUIDITY_UPDATED,

            VolumeAnalysis:
                EventType.VOLUME_UPDATED,

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
                EventType.SETUP_FOUND,

            ScoreEngine:
                EventType.SCORE_UPDATED,

            RiskEngine:
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
```
