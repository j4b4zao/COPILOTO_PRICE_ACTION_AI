"""
LEGACY - DO NOT USE no pipeline RC3.0.

Esta implementação usa atributos que não existem no MarketState atual e
mistura M15/M5/M2 sem históricos independentes. O contrato oficial está em
core.multi_timeframe_state.MultiTimeframeState.
"""


class MultiTimeframe:


    def analisar(self, mercado):

        resultado = {}


        # Tempo maior
        if mercado.tendencia == "ALTA":

            resultado["M15"] = "ALTA"

        elif mercado.tendencia == "BAIXA":

            resultado["M15"] = "BAIXA"

        else:

            resultado["M15"] = "LATERAL"



        # Setup intermediário
        if mercado.fluxo == "COMPRADOR":

            resultado["M5"] = "COMPRA"

        elif mercado.fluxo == "VENDEDOR":

            resultado["M5"] = "VENDA"

        else:

            resultado["M5"] = "NEUTRO"



        # Gatilho
        resultado["M2"] = "AGUARDANDO CONFIRMAÇÃO"


        return resultado
