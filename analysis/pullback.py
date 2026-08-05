class Pullback:

    def analisar(self, estrutura, history):

        resultado = {

            "pullback": False,

            "lado": None,

            "confirmado": False,

            "forca": 0

        }

        ultimo = history.last()
        anterior = history.last(2)

        if ultimo is None or anterior is None:
            return resultado

        if (
            estrutura.tendencia == "ALTA"
            and ultimo.close < anterior.close
        ):

            resultado["pullback"] = True
            resultado["lado"] = "COMPRA"
            resultado["forca"] = 70

        elif (
            estrutura.tendencia == "BAIXA"
            and ultimo.close > anterior.close
        ):

            resultado["pullback"] = True
            resultado["lado"] = "VENDA"
            resultado["forca"] = 70

        return resultado