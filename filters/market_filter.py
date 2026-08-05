class MarketFilter:

    SCORE_MINIMO = 70
    FORCA_MINIMA = 50

    def analisar(
        self,
        score,
        setup,
        regime,
        risco
    ):

        motivos = []
        aprovado = True

        # ==================================
        # SCORE
        # ==================================

        if score < self.SCORE_MINIMO:

            aprovado = False
            motivos.append("Score abaixo do mínimo")

        # ==================================
        # SETUP
        # ==================================

        if not setup:

            aprovado = False
            motivos.append("Sem setup")

        elif setup.get("setup") == "NENHUM":

            aprovado = False
            motivos.append("Setup inválido")

        # ==================================
        # REGIME DE MERCADO
        # ==================================

        if regime:

            nome = regime.get("estrutura")
            forca = regime.get("forca", 0)

            if nome == "CONSOLIDACAO":

                aprovado = False
                motivos.append("Mercado em consolidação")

            if forca < self.FORCA_MINIMA:

                aprovado = False
                motivos.append("Estrutura fraca")

        # ==================================
        # RISCO
        # ==================================

        if risco:

            if not risco.get("valido", False):

                aprovado = False
                motivos.append(
                    risco.get(
                        "motivo",
                        "Risco inválido"
                    )
                )

        else:

            aprovado = False
            motivos.append("Sem análise de risco")

        # ==================================
        # RESULTADO
        # ==================================

        return {

            "aprovado": aprovado,

            "motivos": motivos

        }