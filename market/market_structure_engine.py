"""
market/market_structure_engine.py

Engine responsável pela análise da estrutura de mercado.

V2.1
- Refatoração interna
- Compatível com a versão anterior
- Preparada para histórico de candles
- Preparada para BOS/CHoCH nas próximas versões
"""


class MarketStructureEngine:

    # ==========================================================
    # PÚBLICO
    # ==========================================================

    def analisar(self, candle, historico=None):
        """
        Analisa a estrutura do mercado.

        Parameters
        ----------
        candle : dict
            Candle atual.

        historico : list | None
            Histórico de candles.
            Ainda não utilizado na V2.1.
        """

        if not self._validar_candle(candle):
            return self._resultado_padrao()

        tendencia = self._calcular_tendencia(candle)

        forca = self._calcular_forca(candle)

        estrutura, evento = self._determinar_estrutura(
            candle,
            tendencia,
            forca,
            historico,
        )

        return self._montar_resultado(
            tendencia=tendencia,
            estrutura=estrutura,
            forca=forca,
            evento=evento,
        )

    # ==========================================================
    # VALIDAÇÃO
    # ==========================================================

    def _validar_candle(self, candle):

        return bool(candle)

    # ==========================================================
    # RESULTADO PADRÃO
    # ==========================================================

    def _resultado_padrao(self):

        return {
            "tendencia": "NEUTRO",
            "estrutura": "INDEFINIDA",
            "forca": 0,
            "evento": None,
        }

    # ==========================================================
    # TENDÊNCIA
    # ==========================================================

    def _calcular_tendencia(self, candle):

        direcao = candle.get("direcao", "NEUTRO")

        if direcao == "ALTA":
            return "ALTA"

        if direcao == "BAIXA":
            return "BAIXA"

        return "LATERAL"

    # ==========================================================
    # FORÇA
    # ==========================================================

    def _calcular_forca(self, candle):

        corpo = candle.get("corpo", 0)

        sombra_sup = candle.get("sombra_superior", 0)

        sombra_inf = candle.get("sombra_inferior", 0)

        forca = 50

        if corpo > sombra_sup:
            forca += 20

        if corpo > sombra_inf:
            forca += 20

        return min(forca, 100)

    # ==========================================================
    # ESTRUTURA
    # ==========================================================

    def _determinar_estrutura(
        self,
        candle,
        tendencia,
        forca,
        historico=None,
    ):
        """
        V2.1

        Nesta versão ainda utilizamos a lógica antiga,
        porém isolada.

        Nas próximas versões este método utilizará:

        - Swing High
        - Swing Low
        - BOS
        - CHoCH
        - Consolidação
        """

        estrutura = "CONSOLIDACAO"

        evento = "SEM_ROMPIMENTO"

        direcao = candle.get("direcao", "NEUTRO")

        if direcao == "ALTA" and forca >= 80:

            estrutura = "IMPULSO_ALTA"

            evento = "BOS_COMPRA"

        elif direcao == "BAIXA" and forca >= 80:

            estrutura = "IMPULSO_BAIXA"

            evento = "BOS_VENDA"

        return estrutura, evento

    # ==========================================================
    # RESULTADO
    # ==========================================================

    def _montar_resultado(
        self,
        tendencia,
        estrutura,
        forca,
        evento,
    ):

        return {
            "tendencia": tendencia,
            "estrutura": estrutura,
            "forca": forca,
            "evento": evento,
        }