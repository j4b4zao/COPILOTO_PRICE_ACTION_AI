class PaperTrader:


    def __init__(self):


        self.saldo = 10000


        self.contrato = 1


        self.operacoes = 0


        self.ganhos = 0


        self.perdas = 0


        self.posicao = None




    def executar(

        self,

        resultado

    ):



        if self.posicao is not None:

            return



        decisao = resultado.decision



        risco = resultado.risk



        if decisao["acao"] != "OPERAR":

            return



        self.posicao = {


            "lado": decisao["lado"],


            "entrada": risco["entrada"],


            "stop": risco["stop"],


            "alvo": risco["alvo"]


        }



        self.operacoes += 1



        print(
            "\nPAPER TRADE ABERTO"
        )


        print(
            self.posicao
        )





    def monitorar(

        self,

        preco

    ):


        if self.posicao is None:

            return



        lado = self.posicao["lado"]



        resultado = None



        if lado == "COMPRA":


            if preco >= self.posicao["alvo"]:


                resultado = "WIN"



            elif preco <= self.posicao["stop"]:


                resultado = "LOSS"




        if lado == "VENDA":


            if preco <= self.posicao["alvo"]:


                resultado = "WIN"



            elif preco >= self.posicao["stop"]:


                resultado = "LOSS"




        if resultado:


            self.finalizar(
                resultado,
                preco
            )





    def finalizar(

        self,

        resultado,

        preco_saida

    ):


        entrada = self.posicao["entrada"]



        if self.posicao["lado"] == "COMPRA":


            pontos = preco_saida - entrada



        else:


            pontos = entrada - preco_saida




        financeiro = pontos * self.contrato



        self.saldo += financeiro




        if resultado == "WIN":


            self.ganhos += 1



        else:


            self.perdas += 1





        print(

            "PAPER RESULTADO:",

            resultado

        )


        print(

            "Pontos:",

            pontos

        )


        print(

            "Saldo:",

            self.saldo

        )



        self.posicao = None