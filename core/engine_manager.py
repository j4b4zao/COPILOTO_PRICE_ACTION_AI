"""
core/engine_manager.py

Gerenciador central de todas as engines do
COPILOTO PRICE ACTION AI.

Responsável por:

- Registrar engines
- Executar engines
- Ignorar engines desabilitadas
- Garantir a ordem correta de execução
"""

from analysis.market_regime import MarketRegime
from analysis.market_structure import MarketStructure
from analysis.liquidity_analysis import LiquidityAnalysis
from analysis.volume_analysis import VolumeAnalysis
from analysis.price_action.price_action import PriceAction
from brain.context_engine import ContextEngine

from strategies.strategy_engine import StrategyEngine

from ai.score_engine import ScoreEngine

from decision.decision_engine import DecisionEngine

from risk.risk_manager import RiskManager

from alerts.alert_manager import AlertManager


class EngineManager:

    def __init__(self):

        self.engines = [

            MarketRegime(),

            MarketStructure(),

            LiquidityAnalysis(),

            VolumeAnalysis(),

            PriceAction(),

            ContextEngine(),

            StrategyEngine(),

            ScoreEngine(),

            DecisionEngine(),

            RiskManager(),

            AlertManager(),

        ]

    # ======================================================
    # EXECUTAR
    # ======================================================

    def executar(self, context):

        for engine in self.engines:

            if not getattr(engine, "enabled", True):

                continue

            context = engine.executar(context)

        return context