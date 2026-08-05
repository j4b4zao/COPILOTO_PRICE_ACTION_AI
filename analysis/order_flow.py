class OrderFlow:

    def analisar(self, mercado):

        resultado = {}

        if mercado.fluxo == "COMPRADOR":

            resultado["pressao"] = "COMPRA"
            resultado["delta"] = 70

        elif mercado.fluxo == "VENDEDOR":

            resultado["pressao"] = "VENDA"
            resultado["delta"] = -70

        else:

            resultado["pressao"] = "NEUTRA"
            resultado["delta"] = 0


        return resultado
    