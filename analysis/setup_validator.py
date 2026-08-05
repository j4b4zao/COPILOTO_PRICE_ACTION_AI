class SetupValidator:


    def validar(self, timeframe):


        if (
            timeframe["M15"] == "ALTA"
            and
            timeframe["M5"] == "COMPRA"
        ):

            return "ALINHAMENTO COMPRADOR"



        elif (
            timeframe["M15"] == "BAIXA"
            and
            timeframe["M5"] == "VENDA"
        ):

            return "ALINHAMENTO VENDEDOR"



        else:

            return "SEM ALINHAMENTO"