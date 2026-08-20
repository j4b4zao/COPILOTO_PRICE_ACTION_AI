"""
core/analysis.py

Fachada de compatibilidade do pipeline principal
do Copiloto Price Action AI.
"""

from core.analysis_context import AnalysisContext
from analysis.analysis_pipeline import AnalysisPipeline


class Analysis:

    def __init__(self):

        self.pipeline = AnalysisPipeline()

    def run(self, market_data):

        if not isinstance(market_data, AnalysisContext):

            raise TypeError(
                "Analysis.run() exige um AnalysisContext."
            )

        context = self.pipeline.executar(
            market_data
        )

        return {
            "market_state": context.market,
            "market_structure": context.structure,
            "liquidity": context.liquidity,
            "volume": context.volume,
            "price_action": context.price_action,
            "evidence": context.evidence,
            "imbalance": context.imbalance,
            "order_block": context.order_block,
            "fair_value_gap": context.fair_value_gap,
            "liquidity_pool": context.liquidity_pool,
            "context": context.context,
            "strategy": context.strategy,
            "score": context.score,
            "risk": context.risk,
            "decision": context.decision,
            "alert": context.alert,
            "checklist": context.checklist,
            "narrative": context.narrative,
        }