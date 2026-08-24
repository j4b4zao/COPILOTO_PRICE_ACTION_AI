"""
core/analysis_context.py

Contexto compartilhado entre todas as engines do
COPILOTO PRICE ACTION AI.
"""

from dataclasses import dataclass, field

from core.market_state import MarketState

from external_context.external_market_state import (
    ExternalMarketState,
)

from models.structure_result import StructureResult
from models.liquidity_result import LiquidityResult
from models.volume_result import VolumeResult
from models.price_action_result import PriceActionResult

from models.context_result import ContextResult
from models.evidence_result import EvidenceResult

from models.imbalance_result import ImbalanceResult
from models.order_block_result import OrderBlockResult
from models.fair_value_gap_result import FairValueGapResult
from models.liquidity_pool_result import LiquidityPoolResult

from models.strategy_result import StrategyResult
from models.score_result import ScoreResult
from models.risk_result import RiskResult
from models.decision_result import DecisionResult
from models.alert_result import AlertResult

from models.trade_checklist import TradeChecklist
from models.market_narrative import MarketNarrative


@dataclass(slots=True)
class AnalysisContext:
    """
    Contexto compartilhado por todas as engines.

    Cada engine escreve apenas no seu próprio Result.
    As demais engines apenas consultam esses resultados.
    """

    # ==========================================================
    # ESTADO DO MERCADO
    # ==========================================================

    market: MarketState = field(
        default_factory=MarketState
    )

    # ==========================================================
    # MERCADO EXTERNO
    # ==========================================================

    external_market: ExternalMarketState = field(
        default_factory=ExternalMarketState
    )

    # ==========================================================
    # PRICE ACTION
    # ==========================================================

    structure: StructureResult = field(
        default_factory=StructureResult
    )

    liquidity: LiquidityResult = field(
        default_factory=LiquidityResult
    )

    volume: VolumeResult = field(
        default_factory=VolumeResult
    )

    price_action: PriceActionResult = field(
        default_factory=PriceActionResult
    )

    # ==========================================================
    # EVIDÊNCIAS
    # ==========================================================

    evidence: EvidenceResult = field(
        default_factory=EvidenceResult
    )

    # ==========================================================
    # SMART MONEY
    # ==========================================================

    imbalance: ImbalanceResult = field(
        default_factory=ImbalanceResult
    )

    order_block: OrderBlockResult = field(
        default_factory=OrderBlockResult
    )

    fair_value_gap: FairValueGapResult = field(
        default_factory=FairValueGapResult
    )

    liquidity_pool: LiquidityPoolResult = field(
        default_factory=LiquidityPoolResult
    )

    # ==========================================================
    # CONTEXTO
    # ==========================================================

    context: ContextResult = field(
        default_factory=ContextResult
    )

    # ==========================================================
    # ESTRATÉGIA
    # ==========================================================

    strategy: StrategyResult = field(
        default_factory=StrategyResult
    )

    # ==========================================================
    # SCORE
    # ==========================================================

    score: ScoreResult = field(
        default_factory=ScoreResult
    )

    # ==========================================================
    # RISCO
    # ==========================================================

    risk: RiskResult = field(
        default_factory=RiskResult
    )

    # ==========================================================
    # DECISÃO
    # ==========================================================

    decision: DecisionResult = field(
        default_factory=DecisionResult
    )

    # ==========================================================
    # ALERTA
    # ==========================================================

    alert: AlertResult = field(
        default_factory=AlertResult
    )

    # ==========================================================
    # CHECKLIST
    # ==========================================================

    checklist: TradeChecklist = field(
        default_factory=TradeChecklist
    )

    # ==========================================================
    # NARRATIVA
    # ==========================================================

    narrative: MarketNarrative = field(
        default_factory=MarketNarrative
    )

    # ==========================================================
    # LIMPAR RESULTADOS
    # ==========================================================

    def clear_results(self) -> None:
        """
        Limpa todos os resultados da pipeline,
        preservando os estados de mercado e externo.
        """

        # ------------------------------------------------------
        # PRICE ACTION
        # ------------------------------------------------------

        self.structure.clear()

        self.liquidity.clear()

        self.volume.clear()

        self.price_action.clear()

        # ------------------------------------------------------
        # EVIDÊNCIAS
        # ------------------------------------------------------

        self.evidence.clear()

        # ------------------------------------------------------
        # SMART MONEY
        # ------------------------------------------------------

        self.imbalance.clear()

        self.order_block.clear()

        self.fair_value_gap.clear()

        self.liquidity_pool.clear()

        # ------------------------------------------------------
        # CONTEXTO
        # ------------------------------------------------------

        self.context.clear()

        # ------------------------------------------------------
        # ESTRATÉGIA
        # ------------------------------------------------------

        self.strategy.clear()

        # ------------------------------------------------------
        # SCORE
        # ------------------------------------------------------

        self.score.clear()

        # ------------------------------------------------------
        # RISCO
        # ------------------------------------------------------

        self.risk.clear()

        # ------------------------------------------------------
        # DECISÃO
        # ------------------------------------------------------

        self.decision.clear()

        # ------------------------------------------------------
        # ALERTA
        # ------------------------------------------------------

        self.alert.clear()

        # ------------------------------------------------------
        # CHECKLIST
        # ------------------------------------------------------

        self.checklist.clear()

        # ------------------------------------------------------
        # NARRATIVA
        # ------------------------------------------------------

        

    # ==========================================================
    # RESET COMPLETO
    # ==========================================================

    def reset(self) -> None:
        """
        Reinicia completamente o contexto.
        """

        self.market.clear()

        self.external_market.clear()

        self.clear_results()