"""
analysis/smart_money_engine.py

Motor Smart Money Concepts (SMC)
Versão 1.0
"""


class SmartMoneyEngine:

    def executar(self, market):

        resultado = {

            "order_block": False,
            "order_block_tipo": None,

            "fvg": False,
            "fvg_tipo": None,

            "breaker": False,
            "mitigation": False,

            "premium": False,
            "discount": False,

            "imbalance": False

        }

        history = getattr(market, "history", None)

        estrutura = getattr(market, "estrutura", {})

        if history is None:

            market.smart_money = resultado
            return market

        if history.size() < 5:

            market.smart_money = resultado
            return market

        candles = history.all()

        c1 = candles[-3]
        c2 = candles[-2]
        c3 = candles[-1]

        # =====================================
        # FAIR VALUE GAP
        # =====================================

        if c3.low > c1.high:

            resultado["fvg"] = True
            resultado["fvg_tipo"] = "ALTA"
            resultado["imbalance"] = True

        elif c3.high < c1.low:

            resultado["fvg"] = True
            resultado["fvg_tipo"] = "BAIXA"
            resultado["imbalance"] = True

        # =====================================
        # ORDER BLOCK
        # =====================================

        if (

            estrutura.get("bos")

            and

            c2.bearish

            and

            c3.bullish

        ):

            resultado["order_block"] = True

            resultado["order_block_tipo"] = "COMPRA"

        elif (

            estrutura.get("bos")

            and

            c2.bullish

            and

            c3.bearish

        ):

            resultado["order_block"] = True

            resultado["order_block_tipo"] = "VENDA"

        market.smart_money = resultado

        return market