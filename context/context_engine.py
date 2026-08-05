class ContextEngine:


    def analisar(
        self,
        estrutura,
        price_action,
        pullback,
        liquidity,
        order_flow,
        premium_discount,
        mercado
    ):


        resultado = {

            "mercado": "NEUTRO",

            "viés": "NEUTRO",

            "qualidade": 0,

            "motivos": []

        }


        pontos = 0


        # =================================
        # TENDÊNCIA
        # =================================


        if estrutura.tendencia == "ALTA":


            resultado["viés"] = "COMPRA"


            pontos += 20


            resultado["motivos"].append(
                "Tendência de alta"
            )



        elif estrutura.tendencia == "BAIXA":


            resultado["viés"] = "VENDA"


            pontos += 20


            resultado["motivos"].append(
                "Tendência de baixa"
            )



        # =================================
        # ESTRUTURA
        # =================================


        if estrutura.bos:


            pontos += 15


            resultado["motivos"].append(
                "BOS confirmado"
            )



        if estrutura.choch:


            pontos += 10


            resultado["motivos"].append(
                "CHoCH confirmado"
            )



        # =================================
        # LIQUIDEZ
        # =================================


        if liquidity["liquidez"]:


            pontos += 20


            resultado["motivos"].append(
                "Liquidez capturada"
            )



        # =================================
        # PULLBACK
        # =================================


        if pullback["pullback"]:


            pontos += 15


            resultado["motivos"].append(
                "Pullback confirmado"
            )



        # =================================
        # ORDER FLOW
        # =================================


        if order_flow["pressao"] == "COMPRA":


            pontos += 10


            resultado["motivos"].append(
                "Fluxo comprador"
            )



        elif order_flow["pressao"] == "VENDA":


            pontos += 10


            resultado["motivos"].append(
                "Fluxo vendedor"
            )



        # =================================
        # PREMIUM / DISCOUNT
        # =================================


        if (
            resultado["viés"] == "COMPRA"
            and
            premium_discount["favoravel_compra"]
        ):


            pontos += 10


            resultado["motivos"].append(
                "Preço em zona Discount"
            )



        elif (
            resultado["viés"] == "VENDA"
            and
            premium_discount["favoravel_venda"]
        ):


            pontos += 10


            resultado["motivos"].append(
                "Preço em zona Premium"
            )



        else:


            resultado["motivos"].append(
                "Preço fora da zona ideal"
            )



        # =================================
        # PRICE ACTION
        # =================================


        if price_action["confluencias"] >= 3:


            pontos += 10


            resultado["motivos"].append(
                "Confluência Price Action"
            )



        # =================================
        # RESULTADO
        # =================================


        resultado["qualidade"] = min(
            pontos,
            100
        )



        if pontos >= 75:


            resultado["mercado"] = "FAVORÁVEL"



        elif pontos >= 45:


            resultado["mercado"] = "OBSERVAÇÃO"



        else:


            resultado["mercado"] = "EVITAR"



        return resultado