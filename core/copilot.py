from core.market_state import MarketState
from market.market_structure_engine import MarketStructureEngine as MarketStructure

from analysis.price_action.price_action import PriceAction
from analysis.order_flow import OrderFlow

from ai.score_engine import ScoreEngine
from decision.decision_engine import DecisionEngine

from alerts.alert_manager import AlertManager


class Copilot:

    def __init__(self, engine):

        self.engine = engine

        self.market = MarketState()

        self.structure = MarketStructure()

        self.price_action = PriceAction()

        self.order_flow = OrderFlow()

        self.score_engine = ScoreEngine()

        self.decision_engine = DecisionEngine()

        self.alert_manager = AlertManager()

    def processar(self, dados):

        # Atualiza estado do mercado
        self.market.atualizar(dados)

        # Atualiza histórico de candles
        self.engine.atualizar(
            data=self.market.data,
            hora=self.market.hora,
            open_price=self.market.open,
            high=self.market.high,
            low=self.market.low,
            close=self.market.close,
            volume=self.market.negocios
        )

        self.market.candles = self.engine.historico()

        # Estrutura
        self.structure.analisar(
            self.market.candles
        )

        # Price Action
        resultado_pa = self.price_action.analisar(
            self.structure
        )

        # Fluxo
        resultado_fluxo = self.order_flow.analisar(
            self.market
        )

        # Score
        score = self.score_engine.calcular(
            resultado_pa,
            resultado_fluxo,
            self.structure.hh,
            self.structure.hl
        )

        # Decisão
        decisao = self.decision_engine.decidir(
            score
        )

        # Alerta
        self.alert_manager.enviar(
            decisao
        )

        # Log
        self.market.mostrar()

        self.structure.mostrar()

        print()

        print("PRICE ACTION")

        print(resultado_pa)

        print()

        print("SCORE")

        print(score)

        print()

        print("DECISÃO")

        print(decisao)

        return decisao
