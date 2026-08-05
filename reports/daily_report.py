from datetime import datetime



class DailyReport:



    def __init__(self, performance_engine):


        self.performance = performance_engine




    # =====================================
    # GERAR RELATÓRIO
    # =====================================


    def gerar(self):


        dados = self.performance.analisar()



        setups = self.performance.por_setup()



        melhor_setup = None



        maior_win = 0




        for nome, resultado in setups.items():


            if resultado["win_rate"] > maior_win:


                maior_win = resultado["win_rate"]


                melhor_setup = nome






        relatorio = {



            "data":

            datetime.now().strftime(

                "%d/%m/%Y"

            ),



            "operacoes":

            dados["operacoes"],



            "wins":

            dados.get(

                "wins",

                0

            ),



            "loss":

            dados.get(

                "loss",

                0

            ),



            "win_rate":

            dados["win_rate"],



            "pontos":

            dados["pontos"],



            "melhor_setup":

            melhor_setup



        }



        return relatorio





    # =====================================
    # EXIBIR
    # =====================================


    def mostrar(self):


        relatorio = self.gerar()



        print("\n")

        print("================================")

        print(" RELATÓRIO DIÁRIO COPILOTO ")

        print("================================")



        print(

            "Data:",

            relatorio["data"]

        )



        print(

            "Operações:",

            relatorio["operacoes"]

        )



        print(

            "Win Rate:",

            relatorio["win_rate"],

            "%"

        )



        print(

            "Pontos:",

            relatorio["pontos"]

        )



        print(

            "Melhor Setup:",

            relatorio["melhor_setup"]

        )



        print("================================")