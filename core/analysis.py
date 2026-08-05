"""
analysis.py

Pipeline principal de análise do Copiloto Price Action AI.
Responsável por coordenar todos os módulos de análise do mercado.
"""

from market.market_state import MarketState
from market.market_structure import MarketStructure

from analysis.price_action import PriceAction
from analysis.order_flow import OrderFlow
from analysis.liquidity import Liquidity
from analysis.premium_discount import PremiumDiscount

from ai.score_engine import ScoreEngine
from ai.decision_engine import DecisionEngine


class Analysis:

    def __init__(self):

        self.market_state = MarketState()
        self.market_structure = MarketStructure()

        self.price_action = PriceAction()
        self.order_flow = OrderFlow()
        self.liquidity = Liquidity()
        self.premium_discount = PremiumDiscount()

        self.score_engine = ScoreEngine()
        self.decision_engine = DecisionEngine()

    def run(self, market_data):

        result = {}

        # Estado do Mercado
        self.market_state.atualizar(market_data)

        result["market_state"] = {
            "ativo": self.market_state.ativo,
             "close": self.market_state.close,
              "media": self.market_state.media,
             "adx": self.market_state.adx,
             "macd": self.market_state.macd,
             "media_movel": self.market_state.media_movel,
}

        # Estrutura do Mercado
        result["market_structure"] = self.market_structure.analyze(
            market_data
        )

        # Price Action
        result["price_action"] = self.price_action.analyze(
            market_data
        )

        # Fluxo de Ordens
        result["order_flow"] = self.order_flow.analyze(
            market_data
        )

        # Liquidez
        result["liquidity"] = self.liquidity.analyze(
            market_data
        )

        # Premium / Discount
        result["premium_discount"] = self.premium_discount.analyze(
            market_data
        )

        # Score Geral
        result["score"] = self.score_engine.calculate(
            result
        )

        # Decisão Final
        result["decision"] = self.decision_engine.decide(
            result
        )

        return result