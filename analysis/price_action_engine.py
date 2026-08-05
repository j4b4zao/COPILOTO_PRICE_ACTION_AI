class PriceActionEngine:

    def analisar(self, candle, estrutura):

        if not candle:
            return None

        corpo = candle.get("corpo", 0)
        sombra_sup = candle.get("sombra_superior", 0)
        sombra_inf = candle.get("sombra_inferior", 0)
        direcao = candle.get("direcao", "NEUTRO")

        padrao = "NENHUM"
        forca = "NORMAL"

        # Doji
        if corpo <= 0.1:
            padrao = "DOJI"
            forca = "INDEFINIDA"

        # Martelo
        elif sombra_inf > corpo * 2:
            padrao = "MARTELO"

            if direcao == "ALTA":
                forca = "FORTE_COMPRA"

        # Estrela
        elif sombra_sup > corpo * 2:
            padrao = "ESTRELA_REJEICAO"

            if direcao == "BAIXA":
                forca = "FORTE_VENDA"

        # Candle forte
        elif corpo > (sombra_sup + sombra_inf):
            padrao = "CANDLE_FORTE"

            if direcao == "ALTA":
                forca = "COMPRA"

            elif direcao == "BAIXA":
                forca = "VENDA"

        tendencia = "NEUTRO"
        evento = None

        if estrutura:
            tendencia = estrutura.get("tendencia", "NEUTRO")
            evento = estrutura.get("evento")

        return {
            "padrao": padrao,
            "forca": forca,
            "tendencia": tendencia,
            "evento": evento,
        }