"""
price_action/setup_detector.py

Detector principal de setups do Copiloto Price Action AI.
Responsável por executar todos os setups cadastrados
e selecionar o melhor resultado.
"""

from core.base_module import BaseModule

from analysis.price_action.setups.pullback_setup import PullbackSetup
# Futuramente:
# from price_action.setups.continuation_setup import ContinuationSetup
# from price_action.setups.breakout_setup import BreakoutSetup
# from price_action.setups.reversal_setup import ReversalSetup


class SetupDetector(BaseModule):

    def __init__(self):

        super().__init__()

        self.setups = [

            PullbackSetup(),

            # ContinuationSetup(),
            # BreakoutSetup(),
            # ReversalSetup()

        ]

    # ==========================================================
    # EXECUTAR
    # ==========================================================

    def executar(self, market):

        melhor = None

        for setup in self.setups:

            resultado = setup.executar(market)

            if not resultado["valido"]:
                continue

            if melhor is None:

                melhor = resultado

            elif resultado["score"] > melhor["score"]:

                melhor = resultado

        if melhor is None:

            melhor = self.setup_vazio()

        market.setup = melhor

        return market

    # ==========================================================
    # SETUP VAZIO
    # ==========================================================

    def setup_vazio(self):

        return {

            "valido": False,

            "nome": "NENHUM",

            "lado": "NEUTRO",

            "score": 0,

            "classe": "SEM_SETUP",

            "motivos": []

        }
