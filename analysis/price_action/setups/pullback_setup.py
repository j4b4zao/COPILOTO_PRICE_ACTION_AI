"""
price_action/setups/pullback_setup.py
"""

from analysis.price_action.setups.base_setup import BaseSetup


class PullbackSetup(BaseSetup):

    def executar(self, market):

        resultado = self.resultado()

        estrutura = market.estrutura
        price = market.price_action

        if estrutura is None or price is None:
            return resultado

        # ==========================================
        # PULLBACK COMPRADOR
        # ==========================================

        if (

            estrutura["tendencia"] == "ALTA"

            and estrutura["bos"]

            and price["martelo"]

            and price["pullback"]

        ):

            resultado["valido"] = True

            resultado["nome"] = "PULLBACK_COMPRA"

            resultado["lado"] = "COMPRA"

            resultado["score"] = 90

            resultado["classe"] = self.classificar(90)

            resultado["motivos"] = [

                "Estrutura de Alta",

                "BOS",

                "Martelo",

                "Pullback"

            ]

        # ==========================================
        # PULLBACK VENDEDOR
        # ==========================================

        elif (

            estrutura["tendencia"] == "BAIXA"

            and estrutura["bos"]

            and price["engolfo_baixa"]

            and price["pullback"]

        ):

            resultado["valido"] = True

            resultado["nome"] = "PULLBACK_VENDA"

            resultado["lado"] = "VENDA"

            resultado["score"] = 90

            resultado["classe"] = self.classificar(90)

            resultado["motivos"] = [

                "Estrutura de Baixa",

                "BOS",

                "Engolfo de Baixa",

                "Pullback"

            ]

        return resultado
