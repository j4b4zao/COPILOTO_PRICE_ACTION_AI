"""
execution/signal_generator.py

Gera o sinal operacional do Copiloto Price Action AI.
"""

from datetime import datetime


class SignalGenerator:

    def gerar(self, market):

        # =====================================
        # DADOS DO MERCADO
        # =====================================

        ativo = market.ativo
        timeframe = market.timeframe
        close = market.close

        # =====================================
        # DADOS DA ESTRUTURA
        # =====================================

        tendencia = "N/D"
        regime = "N/D"

        if market.estrutura:

            tendencia = market.estrutura.get("tendencia", "N/D")
            regime = market.estrutura.get("regime", "N/D")

        # =====================================
        # DECISÃO
        # =====================================

        decisao = market.decisao or {}

        # =====================================
        # NÃO OPERAR
        # =====================================

        if decisao.get("acao") != "OPERAR":

            market.sinal = {

                "status": "AGUARDANDO",

                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),

                "ativo": ativo,

                "timeframe": timeframe,

                "lado": None,

                "entrada": None,

                "tendencia": tendencia,

                "regime": regime,

                "score": market.score,

                "confianca": decisao.get("confianca", 0),

                "motivo": decisao.get("motivo", [])

            }

            return market

        # =====================================
        # SINAL OPERACIONAL
        # =====================================

        market.sinal = {

            "status": "OPERAR",

            "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),

            "ativo": ativo,

            "timeframe": timeframe,

            "lado": decisao.get("lado"),

            "entrada": close,

            "tendencia": tendencia,

            "regime": regime,

            "score": market.score,

            "confianca": decisao.get("confianca", 0),

            "motivo": decisao.get("motivo", [])

        }

        return market