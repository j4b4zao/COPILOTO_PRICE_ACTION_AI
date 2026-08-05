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