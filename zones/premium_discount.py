class PremiumDiscount:


    def analisar(
        self,
        estrutura,
        mercado
    ):


        resultado = {

            "zona": "NEUTRA",

            "nivel_50": None,

            "favoravel_compra": False,

            "favoravel_venda": False,

            "forca": 0

        }



        # ==================================
        # VERIFICA SWINGS
        # ==================================


        high = estrutura.ultimo_swing_high

        low = estrutura.ultimo_swing_low



        if high is None or low is None:

            return resultado



        # ==================================
        # EQUILÍBRIO
        # ==================================


        meio = (high + low) / 2


        resultado["nivel_50"] = meio



        preco = mercado.close



        # ==================================
        # DISCOUNT
        # ==================================


        if preco < meio:


            resultado["zona"] = "DISCOUNT"


            resultado["favoravel_compra"] = True


            resultado["forca"] = 80



        # ==================================
        # PREMIUM
        # ==================================


        elif preco > meio:


            resultado["zona"] = "PREMIUM"


            resultado["favoravel_venda"] = True


            resultado["forca"] = 80



        else:


            resultado["zona"] = "EQUILIBRIO"


            resultado["forca"] = 50



        return resultado