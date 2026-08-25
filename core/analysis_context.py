"""
core/analysis_context.py

Contexto compartilhado entre todas as engines do
COPILOTO PRICE ACTION AI.
"""

from dataclasses import dataclass, field

from core.market_state import MarketState
from core.multi_timeframe_state import MultiTimeframeState
from core.order_flow_state import OrderFlowState

from external_context.external_market_state import ExternalMarketState

from models.book_depth import BookDepthSnapshot
from models.book_depth_analysis_result import BookDepthAnalysisResult
from models.structure_result import StructureResult
from models.regime_result import RegimeResult
from models.multi_timeframe_result import MultiTimeframeResult
from models.liquidity_result import LiquidityResult
from models.volume_result import VolumeResult
from models.order_flow_result import OrderFlowResult
from models.price_action_result import PriceActionResult
from models.book_diagnostics_result import BookDiagnosticsResult
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
    """Contexto compartilhado por todas as engines."""

    market: MarketState = field(default_factory=MarketState)
    multi_timeframe: MultiTimeframeState | None = None
    multi_timeframe_analysis: MultiTimeframeResult = field(default_factory=MultiTimeframeResult)

    external_market: ExternalMarketState = field(default_factory=ExternalMarketState)
    book_depth: BookDepthSnapshot = field(default_factory=BookDepthSnapshot.unavailable)
    book_depth_analysis: BookDepthAnalysisResult = field(default_factory=BookDepthAnalysisResult)

    regime: RegimeResult = field(default_factory=RegimeResult)
    structure: StructureResult = field(default_factory=StructureResult)
    liquidity: LiquidityResult = field(default_factory=LiquidityResult)
    volume: VolumeResult = field(default_factory=VolumeResult)
    order_flow_state: OrderFlowState | None = None
    order_flow: OrderFlowResult = field(default_factory=OrderFlowResult)
    price_action: PriceActionResult = field(default_factory=PriceActionResult)

    book_diagnostics: BookDiagnosticsResult = field(default_factory=BookDiagnosticsResult)
    evidence: EvidenceResult = field(default_factory=EvidenceResult)

    imbalance: ImbalanceResult = field(default_factory=ImbalanceResult)
    order_block: OrderBlockResult = field(default_factory=OrderBlockResult)
    fair_value_gap: FairValueGapResult = field(default_factory=FairValueGapResult)
    liquidity_pool: LiquidityPoolResult = field(default_factory=LiquidityPoolResult)

    context: ContextResult = field(default_factory=ContextResult)
    strategy: StrategyResult = field(default_factory=StrategyResult)
    score: ScoreResult = field(default_factory=ScoreResult)
    risk: RiskResult = field(default_factory=RiskResult)
    decision: DecisionResult = field(default_factory=DecisionResult)
    alert: AlertResult = field(default_factory=AlertResult)
    checklist: TradeChecklist = field(default_factory=TradeChecklist)
    narrative: MarketNarrative = field(default_factory=MarketNarrative)

    @property
    def external_valid(self) -> bool:
        return bool(self.external_market.valid)

    @property
    def external_risk(self) -> str:
        return str(self.external_market.risk_on_off or "NEUTRAL")

    @property
    def external_bias(self) -> str:
        return str(self.external_market.global_bias or "NEUTRAL")

    @property
    def external_confidence(self) -> float:
        if not self.external_market.valid:
            return 0.0
        return float(self.external_market.confidence or 0.0)

    @property
    def book_available(self) -> bool:
        return bool(self.book_depth.available)

    @property
    def book_imbalance(self) -> float:
        return float(self.book_depth.imbalance if self.book_depth.available else 0.0)

    @property
    def book_liquidity_pressure(self) -> str:
        if not self.book_depth.available:
            return "UNAVAILABLE"
        return self.book_depth.liquidity_pressure

    def clear_results(self) -> None:
        """Limpa resultados, preservando estados de mercado, externo e Book."""
        self.regime.clear()
        self.multi_timeframe_analysis.clear()
        self.structure.clear()
        self.liquidity.clear()
        self.volume.clear()
        self.order_flow.clear()
        self.price_action.clear()
        self.book_depth_analysis.clear()
        self.book_diagnostics.clear()
        self.evidence.clear()
        self.imbalance.clear()
        self.order_block.clear()
        self.fair_value_gap.clear()
        self.liquidity_pool.clear()
        self.context.clear()
        self.strategy.clear()
        self.score.clear()
        self.risk.clear()
        self.decision.clear()
        self.alert.clear()
        self.checklist.clear()

    def reset(self) -> None:
        """Reinicia completamente o contexto."""
        self.market.clear()
        if self.multi_timeframe is not None:
            self.multi_timeframe.clear()
        if self.order_flow_state is not None:
            self.order_flow_state.clear()
        self.external_market.clear()
        self.book_depth = BookDepthSnapshot.unavailable()
        self.clear_results()
