"""
market/market_regime.py

Identifica o regime atual do mercado.
"""

class MarketRegime:

    def analisar(self, market):

        contexto = {

            "regime": "INDEFINIDO",

            "volatilidade": "NORMAL",

            "forca": 0,

            "operavel": False

        }

        estrutura = market.estrutura
        price_action = market.price_action

        adx = market.adx

        # ======================================
        # VOLATILIDADE
        # ======================================

        if adx >= 35:

            contexto["volatilidade"] = "ALTA"

        elif adx <= 15:

            contexto["volatilidade"] = "BAIXA"

        else:

            contexto["volatilidade"] = "NORMAL"

        # ======================================
        # REGIME
        # ======================================

        if estrutura.get("bos"):

            if estrutura.get("tendencia") == "ALTA":

                contexto["regime"] = "TENDENCIA_ALTA"

            elif estrutura.get("tendencia") == "BAIXA":

                contexto["regime"] = "TENDENCIA_BAIXA"

        elif estrutura.get("choch"):

            contexto["regime"] = "REVERSAO"

        else:

            contexto["regime"] = "LATERAL"

        # ======================================
        # FORÇA
        # ======================================

        score = 0

        if contexto["regime"] != "LATERAL":
            score += 40

        if contexto["volatilidade"] == "NORMAL":
            score += 20

        if adx >= 25:
            score += 40

        contexto["forca"] = min(score, 100)

        # ======================================
        # OPERÁVEL
        # ======================================

        if (

            contexto["forca"] >= 60

            and

            contexto["regime"] != "LATERAL"

        ):

            contexto["operavel"] = True

        market.contexto = contexto

        return contexto