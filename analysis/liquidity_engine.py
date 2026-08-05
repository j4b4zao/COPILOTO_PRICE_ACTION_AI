"""
analysis/liquidity_engine.py

Motor de Liquidez do COPILOTO PRICE ACTION AI.
"""

class LiquidityEngine:

    def executar(self, market):

        history = getattr(market, "history", None)

        estrutura = getattr(market, "estrutura", {})

        resultado = {

            "equal_high": False,

            "equal_low": False,

            "pool_compra": False,

            "pool_venda": False,

            "sweep_high": False,

            "sweep_low": False,

            "stop_hunt": False,

            "direcao": "NEUTRO"

        }

        if history is None:
            market.liquidez = resultado
            return market

        if history.size() < 5:
            market.liquidez = resultado
            return market

        candles = history.all()

        ultimo = candles[-1]

        anterior = candles[-2]

        tolerancia = 5

        # =====================================
        # Equal High
        # =====================================

        if abs(ultimo.high - anterior.high) <= tolerancia:

            resultado["equal_high"] = True

            resultado["pool_venda"] = True

        # =====================================
        # Equal Low
        # =====================================

        if abs(ultimo.low - anterior.low) <= tolerancia:

            resultado["equal_low"] = True

            resultado["pool_compra"] = True

        # =====================================
        # Sweep High
        # =====================================

        if (

            ultimo.high > anterior.high

            and

            ultimo.close < anterior.high

        ):

            resultado["sweep_high"] = True

            resultado["direcao"] = "VENDA"

        # =====================================
        # Sweep Low
        # =====================================

        if (

            ultimo.low < anterior.low

            and

            ultimo.close > anterior.low

        ):

            resultado["sweep_low"] = True

            resultado["direcao"] = "COMPRA"

        # =====================================
        # Stop Hunt
        # =====================================

        if resultado["sweep_high"] or resultado["sweep_low"]:

            resultado["stop_hunt"] = True

        market.liquidez = resultado

        return market