```python
"""
core/analysis_context.py

Analysis Context

RC13

Objeto compartilhado entre todas as engines do
COPILOTO PRICE ACTION AI.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ==========================================================
# MARKET
# ==========================================================

from models.market_result import MarketResult

# ==========================================================
# PRICE ACTION
# ==========================================================

from models.structure_result import StructureResult
from models.liquidity_result import LiquidityResult
from models.volume_result import VolumeResult
from models.price_action_result import PriceActionResult

# ==========================================================
# SMART MONEY
# ==========================================================

from models.imbalance_result import ImbalanceResult
from models.order_block_result import OrderBlockResult
from models.fair_value_gap_result import FairValueGapResult
from models.liquidity_pool_result import LiquidityPoolResult

# ==========================================================
# IA
# ==========================================================

from models.context_result import ContextResult
from models.evidence_result import EvidenceResult
from models.strategy_result import StrategyResult
from models.score_result import ScoreResult
from models.risk_result import RiskResult
from models.decision_result import DecisionResult
from models.alert_result import AlertResult


@dataclass(slots=True)
class AnalysisContext:

    # ==========================================================
    # MARKET
    # ==========================================================

    market: MarketResult = field(
        default_factory=MarketResult
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

    # Próximos módulos:
    #
    # breaker_block
    # mitigation_block
    # displacement
    # premium_discount
    # smt_divergence

    # ==========================================================
    # IA
    # ==========================================================

    context: ContextResult = field(
        default_factory=ContextResult
    )

    evidence: EvidenceResult = field(
        default_factory=EvidenceResult
    )

    strategy: StrategyResult = field(
        default_factory=StrategyResult
    )

    score: ScoreResult = field(
        default_factory=ScoreResult
    )

    risk: RiskResult = field(
        default_factory=RiskResult
    )

    decision: DecisionResult = field(
        default_factory=DecisionResult
    )

    alert: AlertResult = field(
        default_factory=AlertResult
    )

    # ==========================================================
    # RESET
    # ==========================================================

    def clear_results(self):

        # ------------------------------------------------------
        # PRICE ACTION
        # ------------------------------------------------------

        self.structure.clear()

        self.liquidity.clear()

        self.volume.clear()

        self.price_action.clear()

        # ------------------------------------------------------
        # SMART MONEY
        # ------------------------------------------------------

        self.imbalance.clear()

        self.order_block.clear()

        self.fair_value_gap.clear()

        self.liquidity_pool.clear()

        # ------------------------------------------------------
        # IA
        # ------------------------------------------------------

        self.context.clear()

        self.evidence.clear()

        self.strategy.clear()

        self.score.clear()

        self.risk.clear()

        self.decision.clear()

        self.alert.clear()
```
