class TradeManager:


    def __init__(self):

        self.operacao = None



    # =====================================
    # ABRIR OPERAÇÃO
    # =====================================

    def abrir(

        self,

        decisao,

        risco

    ):


        if not decisao:

            return False



        if decisao.get("acao") != "OPERAR":

            return False



        self.operacao = {


            "lado": decisao["lado"],


            "entrada": risco["entrada"],


            "stop": risco["stop"],


            "alvo": risco["alvo"],


            "status": "ABERTA"


        }



        print(

            "\nTRADE ABERTO"

        )


        print(

            self.operacao

        )



        return True




    # =====================================
    # MONITORAR PREÇO
    # =====================================

    def monitorar(

        self,

        preco_atual

    ):



        if self.operacao is None:


            return None



        lado = self.operacao["lado"]



        resultado = None




        # ===============================
        # COMPRA
        # ===============================


        if lado == "COMPRA":



            if preco_atual <= self.operacao["stop"]:


                resultado = "LOSS"



            elif preco_atual >= self.operacao["alvo"]:


                resultado = "WIN"





        # ===============================
        # VENDA
        # ===============================


        elif lado == "VENDA":



            if preco_atual >= self.operacao["stop"]:


                resultado = "LOSS"



            elif preco_atual <= self.operacao["alvo"]:


                resultado = "WIN"





        if resultado:


            return self.fechar(

                resultado,

                preco_atual

            )



        return "OPERACAO ABERTA"





    # =====================================
    # FINALIZAR OPERAÇÃO
    # =====================================

    def fechar(

        self,

        resultado,

        preco_saida

    ):


        operacao_final = self.operacao.copy()



        entrada = operacao_final["entrada"]



        lado = operacao_final["lado"]



        if lado == "COMPRA":


            pontos = (

                preco_saida

                -

                entrada

            )



        else:


            pontos = (

                entrada

                -

                preco_saida

            )



        operacao_final["status"] = resultado


        operacao_final["saida"] = preco_saida


        operacao_final["pontos"] = pontos



        print(

            "\nTRADE FINALIZADO"

        )


        print(

            operacao_final

        )



        self.operacao = None



        return operacao_final