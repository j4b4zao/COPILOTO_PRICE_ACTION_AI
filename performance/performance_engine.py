import json
import os



class PerformanceEngine:


    def __init__(self):


        self.arquivo = (

            "dados/trades.json"

        )



    # =====================================
    # CARREGAR OPERAÇÕES
    # =====================================

    def carregar(self):


        if not os.path.exists(

            self.arquivo

        ):


            return []



        with open(

            self.arquivo,

            "r",

            encoding="utf-8"

        ) as arquivo:


            return json.load(

                arquivo

            )





    # =====================================
    # ESTATÍSTICA GERAL
    # =====================================

    def analisar(self):


        trades = self.carregar()



        total = len(

            trades

        )



        if total == 0:


            return {


                "operacoes":0,


                "win_rate":0,


                "pontos":0


            }




        wins = 0

        perdas = 0

        pontos = 0




        for trade in trades:



            resultado = trade.get(

                "resultado"

            )



            if resultado == "WIN":


                wins += 1



            elif resultado == "LOSS":


                perdas += 1




            pontos += trade.get(

                "pontos",

                0

            )





        win_rate = (

            wins

            /

            total

        ) * 100





        return {



            "operacoes":total,



            "wins":wins,



            "loss":perdas,



            "win_rate":round(

                win_rate,

                2

            ),



            "pontos":pontos


        }





    # =====================================
    # DESEMPENHO POR SETUP
    # =====================================

    def por_setup(self):


        trades = self.carregar()



        setups = {}



        for trade in trades:



            nome = trade.get(

                "setup",

                "NENHUM"

            )



            if nome not in setups:



                setups[nome] = {



                    "operacoes":0,


                    "wins":0,


                    "pontos":0


                }




            setups[nome]["operacoes"] += 1



            setups[nome]["pontos"] += trade.get(

                "pontos",

                0

            )



            if trade.get(

                "resultado"

            ) == "WIN":


                setups[nome]["wins"] += 1






        for nome, dados in setups.items():



            dados["win_rate"] = round(


                (

                    dados["wins"]

                    /

                    dados["operacoes"]

                )

                *

                100,

                2

            )



        return setups





    # =====================================
    # MOSTRAR RELATÓRIO
    # =====================================

    def relatorio(self):


        dados = self.analisar()



        print("\n")

        print("==============================")

        print(" PERFORMANCE COPILOTO ")

        print("==============================")


        print(

            "Operações:",

            dados["operacoes"]

        )


        print(

            "Win Rate:",

            dados["win_rate"],

            "%"

        )


        print(

            "Pontos:",

            dados["pontos"]

        )


        print("==============================")