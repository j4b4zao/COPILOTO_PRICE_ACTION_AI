"""
brain/context_engine.py

Responsável por interpretar o contexto atual do mercado.

Este módulo reúne informações vindas de:

- Price Action
- Market Structure
- ADX
- MACD
- Médias

e responde:

- O mercado está em tendência?
- Está lateral?
- Está acelerando?
- Está perdendo força?
- Vale procurar compras ou vendas?
"""

from typing import Dict


class ContextEngine:

    def __init__(self):

        self.ADX_FORTE = 25
        self.ADX_MUITO_FORTE = 40

    def analisar(self, market) -> Dict:

        contexto = {
            "mercado": "INDEFINIDO",
            "direcao": "NEUTRO",
            "forca": "FRACA",
            "momentum": "NEUTRO",
            "operavel": False,
            "motivos": []
        }

        estrutura = market.estrutura
        price_action = market.price_action

        adx = market.adx
        close = market.close
        media = market.media

        # ================================
        # Estrutura
        # ================================

        if estrutura.get("bos"):

            contexto["mercado"] = "TENDENCIA"

            contexto["motivos"].append("BOS confirmado")

        elif estrutura.get("choch"):

            contexto["mercado"] = "REVERSAO"

            contexto["motivos"].append("CHOCH detectado")

        else:

            contexto["mercado"] = "LATERAL"

        # ================================
        # Direção
        # ================================

        if close > media:

            contexto["direcao"] = "COMPRA"

        elif close < media:

            contexto["direcao"] = "VENDA"

        # ================================
        # Força
        # ================================

        if adx >= self.ADX_MUITO_FORTE:

            contexto["forca"] = "MUITO_FORTE"

        elif adx >= self.ADX_FORTE:

            contexto["forca"] = "FORTE"

        else:

            contexto["forca"] = "FRACA"

        # ================================
        # Momentum
        # ================================

        sinal = price_action.get("sinal", "")

        if sinal in ["FORTE_COMPRA", "COMPRA"]:

            contexto["momentum"] = "ALTA"

        elif sinal in ["FORTE_VENDA", "VENDA"]:

            contexto["momentum"] = "BAIXA"

        # ================================
        # Mercado Operável
        # ================================

        if (
            contexto["mercado"] != "LATERAL"
            and contexto["forca"] != "FRACA"
            and contexto["direcao"] != "NEUTRO"
        ):

            contexto["operavel"] = True

            contexto["motivos"].append(
                "Contexto favorável para operação"
            )

        market.contexto = contexto

        return contexto