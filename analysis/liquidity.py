class Liquidity:

    def analisar(self, estrutura, history):

        resultado = {

            "buy_side_sweep": False,

            "sell_side_sweep": False,

            "fake_breakout": False,

            "rejeicao": False,

            "liquidez": False,

            "forca": 0

        }

        # ============================================
        # HISTÓRICO
        # ============================================

        ultimo = history.last()

        if ultimo is None:
            return resultado

        # ============================================
        # BUY SIDE LIQUIDITY
        # Rompe o último Swing High
        # mas fecha abaixo dele
        # ============================================

        if estrutura.ultimo_swing_high is not None:

            if (
                ultimo.high > estrutura.ultimo_swing_high
                and
                ultimo.close < estrutura.ultimo_swing_high
            ):

                resultado["buy_side_sweep"] = True
                resultado["fake_breakout"] = True
                resultado["rejeicao"] = True
                resultado["liquidez"] = True
                resultado["forca"] = 90

        # ============================================
        # SELL SIDE LIQUIDITY
        # Rompe o último Swing Low
        # mas fecha acima dele
        # ============================================

        if estrutura.ultimo_swing_low is not None:

            if (
                ultimo.low < estrutura.ultimo_swing_low
                and
                ultimo.close > estrutura.ultimo_swing_low
            ):

                resultado["sell_side_sweep"] = True
                resultado["fake_breakout"] = True
                resultado["rejeicao"] = True
                resultado["liquidez"] = True
                resultado["forca"] = 90

        return resultado