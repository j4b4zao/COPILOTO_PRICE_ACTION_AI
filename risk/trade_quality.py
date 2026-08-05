"""
quality/trade_quality.py

Calcula a qualidade da operação.
"""


class TradeQuality:

    def calcular(
        self,
        setup,
        estrutura,
        filtro,
        risco,
        score
    ):

        qualidade = 0

        # ==========================
        # SCORE
        # ==========================

        if score >= 90:
            qualidade += 40

        elif score >= 80:
            qualidade += 30

        elif score >= 70:
            qualidade += 20

        # ==========================
        # SETUP
        # ==========================

        if setup and setup.get("setup") != "NENHUM":
            qualidade += 20

        # ==========================
        # RISCO
        # ==========================

        if risco and risco.get("valido", False):
            qualidade += 20

        # ==========================
        # ESTRUTURA
        # ==========================

        if estrutura:

            evento = estrutura.get("evento")

            if evento in ("BOS_COMPRA", "BOS_VENDA"):
                qualidade += 20

            elif evento == "CHOCH":
                qualidade += 10

        # ==========================
        # LIMITE
        # ==========================

        qualidade = min(100, qualidade)

        return {
            "qualidade": qualidade,
            "classificacao": self.classificar(qualidade)
        }

    # =====================================================
    # CLASSIFICAÇÃO
    # =====================================================

    def classificar(self, qualidade):

        if qualidade >= 90:
            return "A+"

        elif qualidade >= 80:
            return "A"

        elif qualidade >= 70:
            return "B"

        elif qualidade >= 60:
            return "C"

        return "D"